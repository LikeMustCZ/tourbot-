from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from states import *
from keyboards import *
from sheets import (
    create_trip, get_all_trips, get_trip_by_id, update_trip,
    archive_trip_db, restore_trip_db,
    create_booking, get_bookings_by_trip, get_booking_by_id,
    update_booking, delete_booking, search_bookings,
    get_trip_stats, get_daily_report
)

def user_name(update):
    u = update.effective_user
    return u.username or u.full_name or str(u.id)

def parse_money(text):
    """Extract a number from text like '9585кр', '1 325 CZK', '2,000'. Returns float."""
    import re
    if text is None:
        return 0.0
    s = str(text).replace(',', '.')
    # keep digits and dots
    cleaned = re.sub(r'[^0-9.]', '', s)
    # collapse multiple dots
    parts = cleaned.split('.')
    if len(parts) > 2:
        cleaned = parts[0] + '.' + ''.join(parts[1:])
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

# ─── START / CANCEL ───────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "👋 Привет! Я бот для управления бронями Happy Tours и Your Perfect Travel.\n\n"
        "Используй кнопки внизу для навигации.",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Отменено.", reply_markup=main_keyboard())
    return ConversationHandler.END

async def cancel_flow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Cancel from an inline button during any conversation step."""
    query = update.callback_query
    await query.answer()
    ctx.user_data.clear()
    await query.edit_message_text("❌ Отменено. Возвращаю в меню.")
    # Re-show main menu as a fresh message so the reply keyboard is visible
    await query.message.reply_text("Главное меню:", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── MAIN MENU ────────────────────────────────────────

async def main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == '🗺 Поездки':
        return await show_trips(update, ctx)
    elif text == '🔍 Найти':
        return await search_start(update, ctx)
    elif text == '📦 Архив':
        return await archive_list(update, ctx)
    elif text == '📊 Статистика':
        return await stats_menu(update, ctx)
    return ConversationHandler.END

# ─── TRIPS LIST ───────────────────────────────────────

async def show_trips(update, ctx):
    trips = get_all_trips('active')
    if not trips:
        await update.message.reply_text(
            "Активных поездок нет. Создай первую!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('➕ Новая поездка', callback_data='new_trip')]])
        )
    else:
        await update.message.reply_text(
            "🗺 *Активные поездки:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=trips_list_keyboard(trips)
        )
    return ConversationHandler.END

async def trips_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trips = get_all_trips('active')
    if not trips:
        await query.edit_message_text(
            "Активных поездок нет. Создай первую!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('➕ Новая поездка', callback_data='new_trip')]])
        )
    else:
        await query.edit_message_text(
            "🗺 *Активные поездки:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=trips_list_keyboard(trips)
        )
    return ConversationHandler.END

# ─── TRIP DETAIL ──────────────────────────────────────

async def trip_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith('archive_detail_'):
        trip_id = data.replace('archive_detail_', '')
        trip = get_trip_by_id(trip_id)
        if not trip:
            await query.edit_message_text("Поездка не найдена.")
            return ConversationHandler.END
        stats = get_trip_stats(trip_id)
        text = format_trip_detail(trip, stats)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=archive_detail_keyboard(trip_id))
        return ConversationHandler.END

    trip_id = data.replace('trip_', '')
    trip = get_trip_by_id(trip_id)
    if not trip:
        await query.edit_message_text("Поездка не найдена.")
        return ConversationHandler.END

    stats = get_trip_stats(trip_id)
    text = format_trip_detail(trip, stats)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=trip_detail_keyboard(trip_id))
    return ConversationHandler.END

def format_trip_detail(trip, stats):
    seats_info = f"{stats['passengers_count']}/{stats['total_seats']}" if stats else "?/?"
    paid = f"{stats['total_paid']:,.0f}" if stats else "0"
    balance = f"{stats['total_balance']:,.0f}" if stats else "0"
    return (
        f"🗺 *{trip['Route']}*\n"
        f"🏢 {trip['Company']}\n"
        f"💺 Мест: {seats_info}\n"
        f"💰 Собрано: {paid} | Долг: {balance}"
    )

# ─── NEW TRIP ─────────────────────────────────────────

async def new_trip_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data['new_trip'] = {}
    await query.edit_message_text("🏢 Выбери фирму:", reply_markup=company_keyboard())
    return TRIP_COMPANY

async def new_trip_company(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    company = query.data.replace('company_', '')
    ctx.user_data['new_trip']['company'] = company
    await query.edit_message_text(
        f"✅ Фирма: *{company}*\n\n"
        f"📍 Введи название поездки:\n_(например: Рим 3-6 июля или Верона/Венеция 20.08)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return TRIP_ROUTE

async def new_trip_route(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_trip']['route'] = update.message.text
    await update.message.reply_text("💺 Сколько мест в автобусе?", reply_markup=cancel_keyboard())
    return TRIP_SEATS

async def new_trip_seats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        seats = int(update.message.text)
        ctx.user_data['new_trip']['seats'] = seats
        d = ctx.user_data['new_trip']
        text = (
            f"📋 *Проверь данные:*\n\n"
            f"🏢 Фирма: {d['company']}\n"
            f"🗺 Поездка: {d['route']}\n"
            f"💺 Мест: {d['seats']}"
        )
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton('✅ Создать', callback_data='trip_create_confirm'),
                    InlineKeyboardButton('✏️ Исправить', callback_data='trip_create_restart'),
                ]
            ])
        )
        return TRIP_CONFIRM
    except ValueError:
        await update.message.reply_text("⚠️ Введи число, например: 40")
        return TRIP_SEATS

async def new_trip_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'trip_create_restart':
        ctx.user_data['new_trip'] = {}
        await query.edit_message_text("🏢 Выбери фирму:", reply_markup=company_keyboard())
        return TRIP_COMPANY

    d = ctx.user_data['new_trip']
    trip_id = create_trip(d['company'], d['route'], d['seats'], user_name(update))
    ctx.user_data.clear()
    await query.edit_message_text(
        f"✅ *Поездка создана!*\n\n{d['route']}\nID: `{trip_id}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🗺 К поездкам', callback_data='trips_menu')]])
    )
    return ConversationHandler.END

async def new_trip_price(update, ctx):
    pass

async def new_trip_save(update, ctx):
    pass

# ─── EDIT TRIP ────────────────────────────────────────

async def trip_edit_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith('edit_trip_'):
        trip_id = data.replace('edit_trip_', '')
        ctx.user_data['edit_trip_id'] = trip_id
        await query.edit_message_text("✏️ Что изменить?", reply_markup=trip_edit_keyboard(trip_id))
        return TRIP_EDIT_MENU

    if data.startswith('tedit_'):
        parts = data.split('_', 2)
        field = parts[1]
        trip_id = parts[2]
        ctx.user_data['edit_trip_id'] = trip_id
        ctx.user_data['edit_trip_field'] = field
        field_names = {'Route': 'название поездки', 'Total Seats': 'кол-во мест'}
        await query.edit_message_text(f"✏️ Введи новое значение ({field_names.get(field, field)}):")
        return TRIP_EDIT_FIELD

    return ConversationHandler.END

async def trip_edit_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    trip_id = ctx.user_data.get('edit_trip_id')
    field = ctx.user_data.get('edit_trip_field')
    value = update.message.text
    update_trip(trip_id, field, value, user_name(update))
    ctx.user_data.pop('edit_trip_id', None)
    ctx.user_data.pop('edit_trip_field', None)
    trip = get_trip_by_id(trip_id)
    stats = get_trip_stats(trip_id)
    text = format_trip_detail(trip, stats)
    await update.message.reply_text(
        f"✅ Обновлено!\n\n{text}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=trip_detail_keyboard(trip_id)
    )
    return ConversationHandler.END

async def trip_edit_save(update, ctx):
    pass

# ─── ARCHIVE ──────────────────────────────────────────

async def archive_trip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trip_id = query.data.replace('archive_trip_', '')
    trip = get_trip_by_id(trip_id)
    stats = get_trip_stats(trip_id)
    seats = f"{stats['passengers_count']}/{stats['total_seats']}" if stats else "?"
    paid = f"{stats['total_paid']:,.0f}" if stats else "0"
    balance = f"{stats['total_balance']:,.0f}" if stats else "0"
    text = (
        f"📦 *Архивировать поездку?*\n\n"
        f"{trip['Route']}\n"
        f"💺 {seats} мест | Собрано: {paid} | Долг: {balance}\n\n"
        f"Данные сохранятся в таблице."
    )
    ctx.user_data['archive_trip_id'] = trip_id
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=archive_confirm_keyboard(trip_id))
    return ARCHIVE_CONFIRM

async def archive_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith('confirm_archive_'):
        trip_id = query.data.replace('confirm_archive_', '')
        archive_trip_db(trip_id, user_name(update))
        await query.edit_message_text(
            "✅ Поездка архивирована.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🗺 К поездкам', callback_data='trips_menu')]])
        )
    else:
        trip_id = ctx.user_data.get('archive_trip_id')
        trip = get_trip_by_id(trip_id)
        stats = get_trip_stats(trip_id)
        text = format_trip_detail(trip, stats)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=trip_detail_keyboard(trip_id))
    return ConversationHandler.END

async def archive_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send = query.edit_message_text
    else:
        send = update.message.reply_text

    trips = get_all_trips('archived')
    if not trips:
        await send("📦 Архив пуст.")
        return ConversationHandler.END

    await send(
        "📦 *Архивные поездки:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=archive_list_keyboard(trips)
    )
    return ConversationHandler.END

async def restore_trip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trip_id = query.data.replace('restore_trip_', '')
    restore_trip_db(trip_id, user_name(update))
    await query.edit_message_text(
        "♻️ Поездка восстановлена!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🗺 К поездкам', callback_data='trips_menu')]])
    )
    return ConversationHandler.END

# ─── ADD BOOKING ──────────────────────────────────────

async def booking_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trip_id = query.data.replace('add_booking_', '')
    trip = get_trip_by_id(trip_id)
    ctx.user_data['new_booking'] = {
        'trip_id': trip_id,
        'trip_name': trip['Route'] if trip else trip_id
    }
    await query.edit_message_text(
        f"➕ *Новая бронь*\n_{ctx.user_data['new_booking']['trip_name']}_\n\n"
        f"🔗 Ссылка на клиента:\n_(Instagram, Telegram или напиши 'нет')_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_LINK

async def booking_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_booking']['link'] = update.message.text
    await update.message.reply_text("🏙 Город выезда клиента:", reply_markup=cancel_keyboard())
    return BOOKING_CITY

async def booking_city(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_booking']['city'] = update.message.text
    await update.message.reply_text(
        "💺 Сколько мест занимает бронь?\n_(просто число, например: 2)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_SEATS

async def booking_seats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        seats = int(parse_money(update.message.text))
        if seats < 1:
            raise ValueError
        ctx.user_data['new_booking']['seats'] = seats
    except (ValueError, TypeError):
        await update.message.reply_text("⚠️ Введи число, например: 2", reply_markup=cancel_keyboard())
        return BOOKING_SEATS
    await update.message.reply_text(
        "👥 Имена пассажиров:\n_(напиши всех как удобно, например:\nКатя Лутаенко, Иван Жуков)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_PASSENGERS

async def booking_passengers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_booking']['passengers'] = update.message.text
    await update.message.reply_text(
        "📱 Телефоны:\n_(напиши все номера, или 'нет' если нет)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_PAID

async def booking_paid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # This step now captures phones, then asks paid
    ctx.user_data['new_booking']['phones'] = update.message.text
    await update.message.reply_text(
        "💰 Сколько уже оплачено?\n_(например: 3000 или 3000кр)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_BALANCE

async def booking_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_booking']['paid'] = update.message.text
    await update.message.reply_text(
        "💳 Остаток к доплате?\n_(сумма или 0)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_COMMENT

async def booking_comment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_booking']['balance'] = update.message.text
    await update.message.reply_text(
        "💬 Комментарий?\n_(место у окна, день рождения и т.п. или 'нет')_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard()
    )
    return BOOKING_REVIEW

async def booking_review(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text
    if comment.lower() == 'нет':
        comment = ''
    ctx.user_data['new_booking']['comment'] = comment
    b = ctx.user_data['new_booking']

    balance_val = parse_money(b['balance'])
    debt_icon = '⚠️' if balance_val > 0 else '✅'
    phones = b['phones'] if b['phones'].lower() != 'нет' else '—'

    text = (
        f"📋 *Проверь бронь:*\n\n"
        f"🗺 {b['trip_name']}\n"
        f"🔗 {b['link']}\n"
        f"🏙 {b['city']}\n"
        f"💺 Мест: {b['seats']}\n"
        f"👥 {b['passengers']}\n"
        f"📱 {phones}\n"
        f"💰 Оплачено: {b['paid']} | Долг: {b['balance']} {debt_icon}\n"
        f"💬 {comment or '—'}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=booking_confirm_keyboard())
    return BOOKING_CONFIRM

async def booking_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'booking_edit_restart':
        b = ctx.user_data['new_booking']
        trip_id = b['trip_id']
        trip_name = b['trip_name']
        ctx.user_data['new_booking'] = {'trip_id': trip_id, 'trip_name': trip_name}
        await query.edit_message_text(
            "🔗 Ссылка на клиента:\n_(Instagram, Telegram или 'нет')_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_keyboard()
        )
        return BOOKING_LINK

    b = ctx.user_data['new_booking']
    phones = b['phones'] if b['phones'].lower() != 'нет' else ''
    booking_id = create_booking(
        b['trip_id'], b['link'], b['city'], b['seats'],
        b['passengers'], phones,
        b['paid'], b['balance'], b.get('comment', ''),
        user_name(update)
    )
    trip_id = b['trip_id']
    ctx.user_data.clear()
    await query.edit_message_text(
        f"✅ *Бронь сохранена!* ID: `{booking_id}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Ещё бронь', callback_data=f'add_booking_{trip_id}')],
            [InlineKeyboardButton('📋 Все брони', callback_data=f'booking_list_{trip_id}')],
        ])
    )
    return ConversationHandler.END

async def booking_save(update, ctx):
    pass

# ─── BOOKING LIST ─────────────────────────────────────

async def booking_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trip_id = query.data.replace('booking_list_', '')
    bookings = get_bookings_by_trip(trip_id)
    trip = get_trip_by_id(trip_id)
    trip_name = trip['Route'] if trip else trip_id

    if not bookings:
        await query.edit_message_text(
            f"📋 *{trip_name}*\n\nБроней нет.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('➕ Добавить бронь', callback_data=f'add_booking_{trip_id}')],
                [InlineKeyboardButton('◀️ Назад', callback_data=f'trip_{trip_id}')],
            ])
        )
        return ConversationHandler.END

    total = sum(int(parse_money(b.get('Seats', 0))) if b.get('Seats') else 0 for b in bookings)
    await query.edit_message_text(
        f"📋 *{trip_name}*\nПассажиров: {total}\n\nВыбери бронь:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=bookings_list_keyboard(bookings, trip_id)
    )
    return ConversationHandler.END

# ─── BOOKING DETAIL ───────────────────────────────────

async def booking_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith('bedit_') or data.startswith('bdelete_') or data.startswith('confirm_delete_'):
        return await booking_edit_menu(update, ctx)

    booking_id = data.replace('booking_', '')
    b = get_booking_by_id(booking_id)
    if not b:
        await query.edit_message_text("Бронь не найдена.")
        return ConversationHandler.END

    ctx.user_data['current_booking_id'] = booking_id
    ctx.user_data['current_trip_id'] = b.get('Trip ID')

    passengers = b.get('Passengers', '') or '—'
    phones = b.get('Phones', '') or '—'
    balance_val = parse_money(b.get('Balance'))
    debt_icon = f"⚠️ Долг: {b.get('Balance', 0)}" if balance_val > 0 else "✅ Оплачено"

    text = (
        f"👤 *Бронь {booking_id}*\n\n"
        f"🗺 {b.get('Route', '')}\n"
        f"🔗 {b.get('Link', '—')}\n"
        f"🏙 {b.get('City', '')}\n"
        f"💺 Мест: {b.get('Seats', '')}\n"
        f"👥 {passengers}\n"
        f"📱 {phones}\n"
        f"💰 Оплачено: {b.get('Paid', 0)} | {debt_icon}\n"
        f"💬 {b.get('Comment', '') or '—'}\n"
        f"📝 Добавил: {b.get('Added By', '')}"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=booking_detail_keyboard(booking_id, b.get('Trip ID', ''))
    )
    return ConversationHandler.END

# ─── BOOKING EDIT ─────────────────────────────────────

async def booking_edit_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith('bedit_city_'):
        booking_id = data.replace('bedit_city_', '')
        ctx.user_data['edit_booking_id'] = booking_id
        await query.edit_message_text("🏙 Введи новый город выезда:")
        return BOOKING_EDIT_CITY

    if data.startswith('bedit_paid_'):
        booking_id = data.replace('bedit_paid_', '')
        ctx.user_data['edit_booking_id'] = booking_id
        b = get_booking_by_id(booking_id)
        await query.edit_message_text(
            f"💰 Текущий долг: *{b.get('Balance', 0)}*\n\nСколько доплатили?",
            parse_mode=ParseMode.MARKDOWN
        )
        return BOOKING_EDIT_PAID

    if data.startswith('bedit_comment_'):
        booking_id = data.replace('bedit_comment_', '')
        ctx.user_data['edit_booking_id'] = booking_id
        await query.edit_message_text("💬 Введи новый комментарий:")
        return BOOKING_EDIT_COMMENT

    if data.startswith('bedit_link_'):
        booking_id = data.replace('bedit_link_', '')
        ctx.user_data['edit_booking_id'] = booking_id
        await query.edit_message_text("🔗 Введи новую ссылку:")
        return BOOKING_EDIT_LINK

    if data.startswith('bdelete_'):
        booking_id = data.replace('bdelete_', '')
        b = get_booking_by_id(booking_id)
        trip_id = b.get('Trip ID', '') if b else ''
        ctx.user_data['edit_booking_id'] = booking_id
        ctx.user_data['current_trip_id'] = trip_id
        passengers = b.get('Passengers', '') if b else ''
        await query.edit_message_text(
            f"🗑️ Удалить бронь?\n\n*{passengers}*\n\nЭто действие нельзя отменить.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=delete_confirm_keyboard(booking_id, trip_id)
        )
        return BOOKING_DELETE_CONFIRM

    if data.startswith('confirm_delete_'):
        parts = data.replace('confirm_delete_', '').split('_')
        booking_id = parts[0]
        trip_id = parts[1] if len(parts) > 1 else ctx.user_data.get('current_trip_id', '')
        return await booking_delete(update, ctx, booking_id, trip_id)

    return ConversationHandler.END

async def booking_edit_city(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    booking_id = ctx.user_data.get('edit_booking_id')
    update_booking(booking_id, 'City', update.message.text, user_name(update))
    b = get_booking_by_id(booking_id)
    await update.message.reply_text("✅ Город обновлён.", reply_markup=booking_detail_keyboard(booking_id, b.get('Trip ID', '')))
    return ConversationHandler.END

async def booking_edit_paid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    booking_id = ctx.user_data.get('edit_booking_id')
    b = get_booking_by_id(booking_id)
    try:
        added = parse_money(update.message.text)
        old_balance = parse_money(b.get('Balance'))
        old_paid = parse_money(b.get('Paid'))
        new_balance = max(0, old_balance - added)
        new_paid = old_paid + added
        update_booking(booking_id, 'Balance', new_balance, user_name(update))
        update_booking(booking_id, 'Paid', new_paid, user_name(update))
        status = "✅ Полностью оплачено!" if new_balance == 0 else f"⚠️ Остаток: {new_balance}"
        await update.message.reply_text(
            f"💰 Принято: {added}\n{status}",
            reply_markup=booking_detail_keyboard(booking_id, b.get('Trip ID', ''))
        )
    except ValueError:
        await update.message.reply_text("⚠️ Введи число, например: 500")
        return BOOKING_EDIT_PAID
    return ConversationHandler.END

async def booking_edit_comment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    booking_id = ctx.user_data.get('edit_booking_id')
    update_booking(booking_id, 'Comment', update.message.text, user_name(update))
    b = get_booking_by_id(booking_id)
    await update.message.reply_text("✅ Комментарий обновлён.", reply_markup=booking_detail_keyboard(booking_id, b.get('Trip ID', '')))
    return ConversationHandler.END

async def booking_edit_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    booking_id = ctx.user_data.get('edit_booking_id')
    update_booking(booking_id, 'Link', update.message.text, user_name(update))
    b = get_booking_by_id(booking_id)
    await update.message.reply_text("✅ Ссылка обновлена.", reply_markup=booking_detail_keyboard(booking_id, b.get('Trip ID', '')))
    return ConversationHandler.END

async def booking_delete_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith('confirm_delete_'):
        parts = data.replace('confirm_delete_', '').split('_')
        booking_id = parts[0]
        trip_id = parts[1] if len(parts) > 1 else ''
        return await booking_delete(update, ctx, booking_id, trip_id)
    else:
        booking_id = ctx.user_data.get('edit_booking_id')
        b = get_booking_by_id(booking_id)
        trip_id = b.get('Trip ID', '') if b else ''
        await query.edit_message_text("❌ Удаление отменено.", reply_markup=booking_detail_keyboard(booking_id, trip_id))
    return ConversationHandler.END

async def booking_delete(update, ctx, booking_id, trip_id):
    delete_booking(booking_id, user_name(update))
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "✅ Бронь удалена.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('📋 К списку броней', callback_data=f'booking_list_{trip_id}')]])
        )
    return ConversationHandler.END

# ─── STATS ────────────────────────────────────────────

async def stats_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send = lambda text, **kw: query.edit_message_text(text, **kw)
    else:
        send = lambda text, **kw: update.message.reply_text(text, **kw)

    trips = get_all_trips('active')
    if not trips:
        await send("📊 Нет активных поездок.")
        return ConversationHandler.END

    await send(
        "📊 *Статистика — выбери поездку:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=stats_trips_keyboard(trips)
    )
    return STATS_DETAIL

async def stats_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'stats_all':
        text = get_daily_report()
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    trip_id = data.replace('stats_', '')
    stats = get_trip_stats(trip_id)
    if not stats:
        await query.edit_message_text("Поездка не найдена.")
        return ConversationHandler.END

    trip = stats['trip']
    bookings = get_bookings_by_trip(trip_id)
    with_debt = [b for b in bookings if parse_money(b.get('Balance')) > 0]

    text = (
        f"📊 *{trip['Route']}*\n"
        f"🏢 {trip['Company']}\n\n"
        f"💺 Мест занято: {stats['passengers_count']}/{stats['total_seats']}\n"
        f"   Свободно: {stats['free_seats']}\n\n"
        f"💰 Собрано: {stats['total_paid']:,.0f}\n"
        f"⚠️ Ожидается доплат: {stats['total_balance']:,.0f}\n\n"
        f"📋 Броней: {stats['bookings_count']}\n"
        f"   Из них с долгом: {len(with_debt)}"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('◀️ Назад', callback_data='stats')]])
    )
    return ConversationHandler.END

# ─── SEARCH ───────────────────────────────────────────

async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("🔍 Введи имя, телефон или @ник:")
    else:
        await update.message.reply_text("🔍 Введи имя, телефон или @ник:")
    return SEARCH_QUERY

async def search_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.message.text
    results = search_bookings(q)

    if not results:
        await update.message.reply_text(f"🔍 По запросу «{q}» ничего не найдено.")
        return ConversationHandler.END

    lines = [f"🔍 *Найдено: {len(results)}*\n"]
    buttons = []
    for b in results[:10]:
        passengers = b.get('Passengers', '')
        balance_val = parse_money(b.get('Balance'))
        debt = f" | Долг: {b.get('Balance', 0)}" if balance_val > 0 else " | ✅"
        lines.append(
            f"*{passengers}*\n"
            f"🗺 {b.get('Route', '')} | {b.get('Company', '')}\n"
            f"📱 {b.get('Phones', '')} | 🏙 {b.get('City', '')}{debt}"
        )
        buttons.append([InlineKeyboardButton(f"Открыть: {passengers[:30]}", callback_data=f"booking_{b['ID']}")])

    await update.message.reply_text(
        '\n\n'.join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ConversationHandler.END

# ─── REPORT ───────────────────────────────────────────

async def report_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send = lambda text, **kw: query.edit_message_text(text, **kw)
    else:
        send = lambda text, **kw: update.message.reply_text(text, **kw)

    text = get_daily_report()
    await send(text, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END
