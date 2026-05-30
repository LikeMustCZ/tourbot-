import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
from config import GOOGLE_CREDENTIALS, SPREADSHEET_ID

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_sheet():
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

def get_trips_sheet():
    return get_sheet().worksheet('Trips')

def get_bookings_sheet():
    return get_sheet().worksheet('Bookings')

def get_log_sheet():
    return get_sheet().worksheet('Log')

def generate_id():
    return str(uuid.uuid4())[:8].upper()

# ─── TRIPS ───────────────────────────────────────────

def create_trip(company, route, seats, user_name):
    sheet = get_trips_sheet()
    trip_id = generate_id()
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    # Columns: ID, Company, Route, Date, Total Seats, Price, Default City, Status, Archived At, Created At
    row = [trip_id, company, route, '', seats, '', '', 'active', '', now]
    sheet.append_row(row)
    log_action(user_name, 'Создана поездка', route)
    return trip_id

def get_all_trips(status='active'):
    sheet = get_trips_sheet()
    records = sheet.get_all_records()
    # Filter out empty/bad rows
    return [r for r in records if r.get('ID') and str(r.get('Status', '')) == status]

def get_trip_by_id(trip_id):
    sheet = get_trips_sheet()
    records = sheet.get_all_records()
    for r in records:
        if r.get('ID') == trip_id:
            return r
    return None

def update_trip(trip_id, field, value, user_name):
    sheet = get_trips_sheet()
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    for i, r in enumerate(records, start=2):
        if r.get('ID') == trip_id:
            col = headers.index(field) + 1
            sheet.update_cell(i, col, value)
            log_action(user_name, f'Изменена поездка ({field})', f'ID:{trip_id} → {value}')
            return True
    return False

def archive_trip_db(trip_id, user_name):
    sheet = get_trips_sheet()
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    for i, r in enumerate(records, start=2):
        if r.get('ID') == trip_id:
            status_col = headers.index('Status') + 1
            archived_col = headers.index('Archived At') + 1
            sheet.update_cell(i, status_col, 'archived')
            sheet.update_cell(i, archived_col, now)
            log_action(user_name, 'Поездка архивирована', f'ID:{trip_id}')
            return True
    return False

def restore_trip_db(trip_id, user_name):
    sheet = get_trips_sheet()
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    for i, r in enumerate(records, start=2):
        if r.get('ID') == trip_id:
            status_col = headers.index('Status') + 1
            archived_col = headers.index('Archived At') + 1
            sheet.update_cell(i, status_col, 'active')
            sheet.update_cell(i, archived_col, '')
            log_action(user_name, 'Поездка восстановлена', f'ID:{trip_id}')
            return True
    return False

# ─── BOOKINGS ────────────────────────────────────────

def create_booking(trip_id, link, city, passengers, phones, paid, balance, comment, user_name):
    trip = get_trip_by_id(trip_id)
    sheet = get_bookings_sheet()
    booking_id = generate_id()
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    route = trip.get('Route', '') if trip else ''
    company = trip.get('Company', '') if trip else ''
    passengers_str = ' | '.join(passengers)
    phones_str = ' | '.join(phones)
    # Columns: ID, Trip ID, Route, Company, Link, City, Passengers, Phones, Paid, Balance, Comment, Added By, Created At, Updated At
    row = [
        booking_id, trip_id, route, company,
        link, city, passengers_str, phones_str,
        paid, balance, comment, user_name, now, now
    ]
    sheet.append_row(row)
    log_action(user_name, 'Добавлена бронь', f'{passengers_str} → {route}')
    return booking_id

def get_bookings_by_trip(trip_id):
    sheet = get_bookings_sheet()
    records = sheet.get_all_records()
    return [r for r in records if r.get('ID') and str(r.get('Trip ID', '')) == str(trip_id)]

def get_booking_by_id(booking_id):
    sheet = get_bookings_sheet()
    records = sheet.get_all_records()
    for r in records:
        if r.get('ID') == booking_id:
            return r
    return None

def update_booking(booking_id, field, value, user_name):
    sheet = get_bookings_sheet()
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    for i, r in enumerate(records, start=2):
        if r.get('ID') == booking_id:
            col = headers.index(field) + 1
            sheet.update_cell(i, col, value)
            updated_col = headers.index('Updated At') + 1
            sheet.update_cell(i, updated_col, now)
            log_action(user_name, f'Изменена бронь ({field})', f'ID:{booking_id} → {value}')
            return True
    return False

def delete_booking(booking_id, user_name):
    sheet = get_bookings_sheet()
    records = sheet.get_all_records()
    for i, r in enumerate(records, start=2):
        if r.get('ID') == booking_id:
            passengers = r.get('Passengers', '')
            sheet.delete_rows(i)
            log_action(user_name, 'Удалена бронь', f'ID:{booking_id} {passengers}')
            return True
    return False

def search_bookings(query):
    sheet = get_bookings_sheet()
    records = sheet.get_all_records()
    query = query.lower()
    results = []
    for r in records:
        if not r.get('ID'):
            continue
        searchable = ' '.join([
            str(r.get('Passengers', '')),
            str(r.get('Phones', '')),
            str(r.get('Link', '')),
            str(r.get('City', ''))
        ]).lower()
        if query in searchable:
            results.append(r)
    return results

# ─── STATS ───────────────────────────────────────────

def get_trip_stats(trip_id):
    trip = get_trip_by_id(trip_id)
    if not trip:
        return None
    bookings = get_bookings_by_trip(trip_id)
    total_seats = int(trip.get('Total Seats', 0) or 0)
    passengers_count = sum(
        len(b.get('Passengers', '').split(' | '))
        for b in bookings
        if b.get('Passengers')
    )
    total_paid = sum(float(str(b.get('Paid', 0) or 0).replace(',', '.')) for b in bookings)
    total_balance = sum(float(str(b.get('Balance', 0) or 0).replace(',', '.')) for b in bookings)
    return {
        'trip': trip,
        'bookings_count': len(bookings),
        'passengers_count': passengers_count,
        'total_seats': total_seats,
        'free_seats': max(0, total_seats - passengers_count),
        'total_paid': total_paid,
        'total_balance': total_balance,
    }

# ─── LOG ─────────────────────────────────────────────

def log_action(user, action, details=''):
    try:
        sheet = get_log_sheet()
        now = datetime.now().strftime('%d.%m.%Y %H:%M')
        sheet.append_row([now, user, action, details])
    except Exception:
        pass

# ─── DAILY REPORT ─────────────────────────────────────

def get_daily_report():
    active_trips = get_all_trips('active')
    if not active_trips:
        return "📊 Нет активных поездок."

    lines = ["📊 *Ежедневный отчёт*\n"]
    companies = {}
    for trip in active_trips:
        company = trip.get('Company', 'Неизвестно')
        if company not in companies:
            companies[company] = []
        companies[company].append(trip)

    total_balance_all = 0
    for company, trips in companies.items():
        lines.append(f"*{company}:*")
        for trip in trips:
            stats = get_trip_stats(trip['ID'])
            if stats:
                balance = stats['total_balance']
                total_balance_all += balance
                lines.append(
                    f"• {trip['Route']} — "
                    f"{stats['passengers_count']}/{stats['total_seats']} мест\n"
                    f"  Собрано: {stats['total_paid']:,.0f} | Ждём: {balance:,.0f}"
                )
        lines.append("")

    lines.append(f"💰 *Итого ждём доплат: {total_balance_all:,.0f}*")
    return '\n'.join(lines)
