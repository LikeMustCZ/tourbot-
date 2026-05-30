import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from config import BOT_TOKEN
from handlers import (
    start, main_menu,
    trips_menu, new_trip_start, new_trip_company, new_trip_route,
    new_trip_seats, new_trip_price, new_trip_confirm,
    trip_detail, trip_edit_menu, trip_edit_field,
    archive_trip, archive_confirm, archive_list, restore_trip,
    booking_add_start, booking_link, booking_city, booking_passengers_count,
    booking_passenger_name, booking_passenger_phone, booking_paid, booking_balance,
    booking_comment, booking_confirm,
    booking_list, booking_detail, booking_edit_menu,
    booking_edit_city, booking_edit_paid, booking_edit_comment, booking_edit_link,
    booking_delete_confirm, booking_delete,
    stats_menu, stats_detail,
    search_start, search_query,
    report_menu,
    cancel
)
from states import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(new_trip_start, pattern='^new_trip$'),
            CallbackQueryHandler(trips_menu, pattern='^trips_menu$'),
            CallbackQueryHandler(trip_detail, pattern='^trip_[A-Z0-9]+$'),
            CallbackQueryHandler(trip_detail, pattern='^archive_detail_'),
            CallbackQueryHandler(booking_add_start, pattern='^add_booking_'),
            CallbackQueryHandler(booking_list, pattern='^booking_list_'),
            CallbackQueryHandler(booking_detail, pattern='^booking_[A-Z0-9]+$'),
            CallbackQueryHandler(stats_menu, pattern='^stats$'),
            CallbackQueryHandler(stats_detail, pattern='^stats_'),
            CallbackQueryHandler(archive_list, pattern='^archive$'),
            CallbackQueryHandler(restore_trip, pattern='^restore_trip_'),
            CallbackQueryHandler(search_start, pattern='^search$'),
            CallbackQueryHandler(report_menu, pattern='^report$'),
            CallbackQueryHandler(archive_trip, pattern='^archive_trip_'),
            CallbackQueryHandler(trip_edit_menu, pattern='^edit_trip_'),
        ],
        states={
            TRIP_COMPANY: [
                CallbackQueryHandler(new_trip_company, pattern='^company_'),
            ],
            TRIP_ROUTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, new_trip_route),
            ],
            TRIP_SEATS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, new_trip_seats),
            ],
            TRIP_CONFIRM: [
                CallbackQueryHandler(new_trip_confirm, pattern='^trip_create_confirm$'),
                CallbackQueryHandler(new_trip_confirm, pattern='^trip_create_restart$'),
            ],
            TRIP_EDIT_MENU: [
                CallbackQueryHandler(trip_edit_menu, pattern='^tedit_'),
                CallbackQueryHandler(trip_detail, pattern='^trip_[A-Z0-9]+$'),
            ],
            TRIP_EDIT_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trip_edit_field),
            ],
            ARCHIVE_CONFIRM: [
                CallbackQueryHandler(archive_confirm),
            ],
            BOOKING_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_link),
            ],
            BOOKING_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_city),
            ],
            BOOKING_PASSENGERS_COUNT: [
                CallbackQueryHandler(booking_passengers_count, pattern='^pcount_'),
            ],
            BOOKING_PASSENGER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_passenger_name),
            ],
            BOOKING_PASSENGER_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_passenger_phone),
            ],
            BOOKING_PAID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_paid),
            ],
            BOOKING_BALANCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_balance),
            ],
            BOOKING_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_comment),
            ],
            BOOKING_CONFIRM: [
                CallbackQueryHandler(booking_confirm, pattern='^booking_save$'),
                CallbackQueryHandler(booking_confirm, pattern='^booking_edit_restart$'),
            ],
            BOOKING_EDIT_MENU: [
                CallbackQueryHandler(booking_edit_menu, pattern='^bedit_|^bdelete_|^confirm_delete_'),
            ],
            BOOKING_EDIT_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_city),
            ],
            BOOKING_EDIT_PAID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_paid),
            ],
            BOOKING_EDIT_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_comment),
            ],
            BOOKING_EDIT_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_link),
            ],
            BOOKING_DELETE_CONFIRM: [
                CallbackQueryHandler(booking_delete_confirm),
            ],
            SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_query),
            ],
            STATS_DETAIL: [
                CallbackQueryHandler(stats_detail, pattern='^stats_'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
        ],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))

    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
