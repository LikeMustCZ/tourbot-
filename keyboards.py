from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# ─── MAIN MENU (всегда внизу) ─────────────────────────

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ['🗺 Поездки', '🔍 Найти'],
            ['📦 Архив', '📊 Статистика'],
        ],
        resize_keyboard=True
    )

# ─── СПИСОК ПОЕЗДОК ───────────────────────────────────

def trips_list_keyboard(trips):
    buttons = []
    for trip in trips:
        label = f"{trip['Route']} | {trip['Company']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"trip_{trip['ID']}")])
    buttons.append([InlineKeyboardButton('➕ Новая поездка', callback_data='new_trip')])
    return InlineKeyboardMarkup(buttons)

# ─── ДЕТАЛИ ПОЕЗДКИ ───────────────────────────────────

def trip_detail_keyboard(trip_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('➕ Добавить бронь', callback_data=f'add_booking_{trip_id}'),
            InlineKeyboardButton('📋 Брони', callback_data=f'booking_list_{trip_id}'),
        ],
        [
            InlineKeyboardButton('📊 Статистика', callback_data=f'stats_{trip_id}'),
            InlineKeyboardButton('✏️ Редактировать', callback_data=f'edit_trip_{trip_id}'),
        ],
        [InlineKeyboardButton('📦 Архивировать', callback_data=f'archive_trip_{trip_id}')],
        [InlineKeyboardButton('◀️ Назад', callback_data='trips_menu')],
    ])

# ─── РЕДАКТИРОВАТЬ ПОЕЗДКУ ────────────────────────────

def trip_edit_keyboard(trip_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('Маршрут', callback_data=f'tedit_Route_{trip_id}'),
            InlineKeyboardButton('Дата', callback_data=f'tedit_Date_{trip_id}'),
        ],
        [
            InlineKeyboardButton('Кол-во мест', callback_data=f'tedit_Total Seats_{trip_id}'),
            InlineKeyboardButton('Цена', callback_data=f'tedit_Price_{trip_id}'),
        ],
        [InlineKeyboardButton('◀️ Назад', callback_data=f'trip_{trip_id}')],
    ])

# ─── ПОДТВЕРЖДЕНИЕ АРХИВАЦИИ ──────────────────────────

def archive_confirm_keyboard(trip_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ Да, архивировать', callback_data=f'confirm_archive_{trip_id}'),
            InlineKeyboardButton('❌ Отмена', callback_data=f'trip_{trip_id}'),
        ]
    ])

# ─── АРХИВ ────────────────────────────────────────────

def archive_list_keyboard(trips):
    buttons = []
    for trip in trips:
        label = f"{trip['Route']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"archive_detail_{trip['ID']}")])
    return InlineKeyboardMarkup(buttons)

def archive_detail_keyboard(trip_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📋 Брони', callback_data=f'booking_list_{trip_id}')],
        [InlineKeyboardButton('♻️ Восстановить', callback_data=f'restore_trip_{trip_id}')],
    ])

# ─── КОМПАНИЯ ─────────────────────────────────────────

def company_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('Happy Tours', callback_data='company_Happy Tours'),
            InlineKeyboardButton('Your Perfect Travel', callback_data='company_Your Perfect Travel'),
        ]
    ])

# ─── КОЛ-ВО ПАССАЖИРОВ ───────────────────────────────

def passengers_count_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('1', callback_data='pcount_1'),
            InlineKeyboardButton('2', callback_data='pcount_2'),
            InlineKeyboardButton('3', callback_data='pcount_3'),
            InlineKeyboardButton('4', callback_data='pcount_4'),
        ]
    ])

# ─── ПОДТВЕРЖДЕНИЕ БРОНИ ─────────────────────────────

def booking_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ Сохранить', callback_data='booking_save'),
            InlineKeyboardButton('✏️ Исправить', callback_data='booking_edit_restart'),
        ]
    ])

# ─── СПИСОК БРОНЕЙ ───────────────────────────────────

def _kb_money(v):
    try:
        return float(str(v or 0).replace(',', '.').replace(' ', '') or 0)
    except (ValueError, TypeError):
        # strip non-numeric chars
        import re
        cleaned = re.sub(r'[^0-9.]', '', str(v).replace(',', '.'))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

def bookings_list_keyboard(bookings, trip_id):
    buttons = []
    for b in bookings:
        names = b.get('Passengers', '') or 'Без имени'
        # show first ~25 chars of names
        short = names[:25] + ('…' if len(names) > 25 else '')
        seats = b.get('Seats', '')
        seats_label = f" ({seats}м)" if seats else ''
        debt_icon = ' ⚠️' if _kb_money(b.get('Balance', 0)) > 0 else ' ✅'
        label = f"{short}{seats_label} | {b.get('City', '')}{debt_icon}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"booking_{b['ID']}")])
    buttons.append([InlineKeyboardButton('◀️ Назад к поездке', callback_data=f'trip_{trip_id}')])
    return InlineKeyboardMarkup(buttons)

# ─── ДЕТАЛИ БРОНИ ─────────────────────────────────────

def booking_detail_keyboard(booking_id, trip_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✏️ Город', callback_data=f'bedit_city_{booking_id}'),
            InlineKeyboardButton('💰 Доплата', callback_data=f'bedit_paid_{booking_id}'),
        ],
        [
            InlineKeyboardButton('💬 Комментарий', callback_data=f'bedit_comment_{booking_id}'),
            InlineKeyboardButton('🔗 Ссылка', callback_data=f'bedit_link_{booking_id}'),
        ],
        [InlineKeyboardButton('🗑️ Удалить бронь', callback_data=f'bdelete_{booking_id}')],
        [InlineKeyboardButton('◀️ Назад', callback_data=f'booking_list_{trip_id}')],
    ])

# ─── ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ───────────────────────────

def delete_confirm_keyboard(booking_id, trip_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ Да, удалить', callback_data=f'confirm_delete_{booking_id}_{trip_id}'),
            InlineKeyboardButton('❌ Отмена', callback_data=f'booking_{booking_id}'),
        ]
    ])

# ─── СТАТИСТИКА ───────────────────────────────────────

def stats_trips_keyboard(trips):
    buttons = []
    for trip in trips:
        label = f"{trip['Route']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"stats_{trip['ID']}")])
    buttons.append([InlineKeyboardButton('📊 Все поездки', callback_data='stats_all')])
    return InlineKeyboardMarkup(buttons)

# ─── ПРОПУСТИТЬ ───────────────────────────────────────

def skip_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('Пропустить', callback_data='skip')]
    ])

# ─── ОТМЕНА (выход в меню на любом шаге) ──────────────

def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('❌ Отмена / В меню', callback_data='cancel_flow')]
    ])
