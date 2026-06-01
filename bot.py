import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ConversationHandler
)
from config import BOT_TOKEN
from sheets import ensure_setup
from handlers import (
    start, main_menu, cancel, cancel_flow,
    trips_menu, new_trip_start, new_trip_company, new_trip_route,
    new_trip_seats, new_trip_confirm,
    trip_detail, trip_edit_menu, trip_edit_field,
    archive_trip, archive_confirm, archive_list, restore_trip,
    booking_add_start, booking_link, booking_city, booking_seats,
    booking_passengers, booking_paid, booking_balance,
    booking_comment, booking_review, booking_confirm,
    booking_list, booking_detail, booking_edit_menu,
    booking_edit_city, booking_edit_paid, booking_edit_comment, booking_edit_link,
    booking_delete_confirm, booking_delete,
    stats_menu, stats_detail,
    search_start, search_query,
    report_menu
)
from states import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cancel button available in every conversation state
CANCEL = CallbackQueryHandler(cancel_flow, pattern=r'^cancel_flow$')


def main():
    try:
        ensure_setup()
        logger.info("Google Sheets настроены.")
    except Exception as e:
        logger.error(f"Ошибка настройки Google Sheets: {e}")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(new_trip_start, pattern=r'^new_trip$'),
            CallbackQueryHandler(trips_menu, pattern=r'^trips_menu$'),
            CallbackQueryHandler(trip_detail, pattern=r'^trip_[A-Z0-9]+$'),
            CallbackQueryHandler(trip_detail, pattern=r'^archive_detail_'),
            CallbackQueryHandler(booking_add_start, pattern=r'^add_booking_'),
            CallbackQueryHandler(booking_list, pattern=r'^booking_list_'),
            CallbackQueryHandler(booking_detail, pattern=r'^booking_[A-Z0-9]+$'),
            CallbackQueryHandler(stats_menu, pattern=r'^stats$'),
            CallbackQueryHandler(stats_detail, pattern=r'^stats_'),
            CallbackQueryHandler(archive_list, pattern=r'^archive$'),
            CallbackQueryHandler(restore_trip, pattern=r'^restore_trip_'),
            CallbackQueryHandler(search_start, pattern=r'^search$'),
            CallbackQueryHandler(report_menu, pattern=r'^report$'),
            CallbackQueryHandler(archive_trip, pattern=r'^archive_trip_'),
            CallbackQueryHandler(trip_edit_menu, pattern=r'^edit_trip_'),
        ],
        states={
            TRIP_COMPANY: [CANCEL, CallbackQueryHandler(new_trip_company, pattern=r'^company_')],
            TRIP_ROUTE: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, new_trip_route)],
            TRIP_SEATS: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, new_trip_seats)],
            TRIP_CONFIRM: [CANCEL, CallbackQueryHandler(new_trip_confirm, pattern=r'^trip_create_')],
            TRIP_EDIT_MENU: [
                CANCEL,
                CallbackQueryHandler(trip_edit_menu, pattern=r'^tedit_'),
                CallbackQueryHandler(trip_detail, pattern=r'^trip_[A-Z0-9]+$'),
            ],
            TRIP_EDIT_FIELD: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, trip_edit_field)],
            ARCHIVE_CONFIRM: [CANCEL, CallbackQueryHandler(archive_confirm)],
            BOOKING_LINK: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_link)],
            BOOKING_CITY: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_city)],
            BOOKING_SEATS: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_seats)],
            BOOKING_PASSENGERS: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_passengers)],
            BOOKING_PAID: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_paid)],
            BOOKING_BALANCE: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_balance)],
            BOOKING_COMMENT: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_comment)],
            BOOKING_REVIEW: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_review)],
            BOOKING_CONFIRM: [CANCEL, CallbackQueryHandler(booking_confirm, pattern=r'^booking_(save|edit_restart)$')],
            BOOKING_EDIT_MENU: [CANCEL, CallbackQueryHandler(booking_edit_menu, pattern=r'^(bedit_|bdelete_|confirm_delete_)')],
            BOOKING_EDIT_CITY: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_city)],
            BOOKING_EDIT_PAID: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_paid)],
            BOOKING_EDIT_COMMENT: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_comment)],
            BOOKING_EDIT_LINK: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, booking_edit_link)],
            BOOKING_DELETE_CONFIRM: [CANCEL, CallbackQueryHandler(booking_delete_confirm)],
            SEARCH_QUERY: [CANCEL, MessageHandler(filters.TEXT & ~filters.COMMAND, search_query)],
            STATS_DETAIL: [CANCEL, CallbackQueryHandler(stats_detail, pattern=r'^stats_')],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
            CANCEL,
        ],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))

    logger.info("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
