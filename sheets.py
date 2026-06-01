import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
from config import GOOGLE_CREDENTIALS, SPREADSHEET_ID

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ─── SHEET STRUCTURE ──────────────────────────────────
# These headers are the single source of truth. The bot
# creates/fixes them automatically on startup, so the user
# never has to type anything into the sheet manually.

TRIPS_HEADERS = [
    'ID', 'Company', 'Route', 'Total Seats',
    'Status', 'Archived At', 'Created At'
]

BOOKINGS_HEADERS = [
    'ID', 'Trip ID', 'Route', 'Company', 'Link', 'City',
    'Passengers', 'Phones', 'Paid', 'Balance', 'Comment',
    'Added By', 'Created At', 'Updated At'
]

LOG_HEADERS = ['Date', 'User', 'Action', 'Details']

_client = None

def get_client():
    global _client
    if _client is None:
        creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client

def get_spreadsheet():
    return get_client().open_by_key(SPREADSHEET_ID)

def _get_or_create_ws(spreadsheet, title, headers):
    """Return worksheet, creating it and/or fixing headers if needed."""
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(20, len(headers)))
    # Ensure header row is correct
    current = ws.row_values(1)
    if current != headers:
        ws.update([headers], 'A1')
    return ws

def ensure_setup():
    """Called once on startup. Guarantees all sheets and headers exist."""
    ss = get_spreadsheet()
    _get_or_create_ws(ss, 'Trips', TRIPS_HEADERS)
    _get_or_create_ws(ss, 'Bookings', BOOKINGS_HEADERS)
    _get_or_create_ws(ss, 'Log', LOG_HEADERS)

def get_trips_sheet():
    return get_spreadsheet().worksheet('Trips')

def get_bookings_sheet():
    return get_spreadsheet().worksheet('Bookings')

def get_log_sheet():
    return get_spreadsheet().worksheet('Log')

def generate_id():
    return str(uuid.uuid4())[:8].upper()

def _append_dict(sheet, data):
    """Write a dict as a row, ordered to match the sheet's actual headers.
    This makes column order in the sheet completely irrelevant."""
    headers = sheet.row_values(1)
    row = [data.get(h, '') for h in headers]
    sheet.append_row(row, value_input_option='USER_ENTERED')

def _records(sheet):
    """Safe read of all records, filtering out empty rows."""
    try:
        records = sheet.get_all_records()
    except Exception:
        return []
    return [r for r in records if r.get('ID')]

# ─── TRIPS ───────────────────────────────────────────

def create_trip(company, route, seats, user_name):
    sheet = get_trips_sheet()
    trip_id = generate_id()
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    _append_dict(sheet, {
        'ID': trip_id,
        'Company': company,
        'Route': route,
        'Total Seats': seats,
        'Status': 'active',
        'Archived At': '',
        'Created At': now,
    })
    log_action(user_name, 'Создана поездка', route)
    return trip_id

def get_all_trips(status='active'):
    return [r for r in _records(get_trips_sheet()) if str(r.get('Status', '')).strip() == status]

def get_trip_by_id(trip_id):
    for r in _records(get_trips_sheet()):
        if str(r.get('ID')) == str(trip_id):
            return r
    return None

def update_trip(trip_id, field, value, user_name):
    sheet = get_trips_sheet()
    headers = sheet.row_values(1)
    records = _records(sheet)
    for i, r in enumerate(records, start=2):
        if str(r.get('ID')) == str(trip_id):
            col = headers.index(field) + 1
            sheet.update_cell(i, col, value)
            log_action(user_name, f'Изменена поездка ({field})', f'ID:{trip_id} → {value}')
            return True
    return False

def archive_trip_db(trip_id, user_name):
    sheet = get_trips_sheet()
    headers = sheet.row_values(1)
    records = _records(sheet)
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    for i, r in enumerate(records, start=2):
        if str(r.get('ID')) == str(trip_id):
            sheet.update_cell(i, headers.index('Status') + 1, 'archived')
            sheet.update_cell(i, headers.index('Archived At') + 1, now)
            log_action(user_name, 'Поездка архивирована', f'ID:{trip_id}')
            return True
    return False

def restore_trip_db(trip_id, user_name):
    sheet = get_trips_sheet()
    headers = sheet.row_values(1)
    records = _records(sheet)
    for i, r in enumerate(records, start=2):
        if str(r.get('ID')) == str(trip_id):
            sheet.update_cell(i, headers.index('Status') + 1, 'active')
            sheet.update_cell(i, headers.index('Archived At') + 1, '')
            log_action(user_name, 'Поездка восстановлена', f'ID:{trip_id}')
            return True
    return False

# ─── BOOKINGS ────────────────────────────────────────

def create_booking(trip_id, link, city, passengers, phones, paid, balance, comment, user_name):
    trip = get_trip_by_id(trip_id)
    sheet = get_bookings_sheet()
    booking_id = generate_id()
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    _append_dict(sheet, {
        'ID': booking_id,
        'Trip ID': trip_id,
        'Route': trip.get('Route', '') if trip else '',
        'Company': trip.get('Company', '') if trip else '',
        'Link': link,
        'City': city,
        'Passengers': ' | '.join(passengers),
        'Phones': ' | '.join(phones),
        'Paid': paid,
        'Balance': balance,
        'Comment': comment,
        'Added By': user_name,
        'Created At': now,
        'Updated At': now,
    })
    log_action(user_name, 'Добавлена бронь', f"{' | '.join(passengers)} → {trip.get('Route','') if trip else ''}")
    return booking_id

def get_bookings_by_trip(trip_id):
    return [r for r in _records(get_bookings_sheet()) if str(r.get('Trip ID', '')) == str(trip_id)]

def get_booking_by_id(booking_id):
    for r in _records(get_bookings_sheet()):
        if str(r.get('ID')) == str(booking_id):
            return r
    return None

def update_booking(booking_id, field, value, user_name):
    sheet = get_bookings_sheet()
    headers = sheet.row_values(1)
    records = _records(sheet)
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    for i, r in enumerate(records, start=2):
        if str(r.get('ID')) == str(booking_id):
            sheet.update_cell(i, headers.index(field) + 1, value)
            sheet.update_cell(i, headers.index('Updated At') + 1, now)
            log_action(user_name, f'Изменена бронь ({field})', f'ID:{booking_id} → {value}')
            return True
    return False

def delete_booking(booking_id, user_name):
    sheet = get_bookings_sheet()
    records = _records(sheet)
    for i, r in enumerate(records, start=2):
        if str(r.get('ID')) == str(booking_id):
            sheet.delete_rows(i)
            log_action(user_name, 'Удалена бронь', f"ID:{booking_id} {r.get('Passengers','')}")
            return True
    return False

def search_bookings(query):
    query = query.lower().strip()
    results = []
    for r in _records(get_bookings_sheet()):
        searchable = ' '.join([
            str(r.get('Passengers', '')),
            str(r.get('Phones', '')),
            str(r.get('Link', '')),
            str(r.get('City', '')),
        ]).lower()
        if query in searchable:
            results.append(r)
    return results

# ─── STATS ───────────────────────────────────────────

def _to_float(v):
    try:
        return float(str(v or 0).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0

def get_trip_stats(trip_id):
    trip = get_trip_by_id(trip_id)
    if not trip:
        return None
    bookings = get_bookings_by_trip(trip_id)
    total_seats = int(_to_float(trip.get('Total Seats', 0)))
    passengers_count = sum(
        len(str(b.get('Passengers', '')).split(' | '))
        for b in bookings if b.get('Passengers')
    )
    total_paid = sum(_to_float(b.get('Paid')) for b in bookings)
    total_balance = sum(_to_float(b.get('Balance')) for b in bookings)
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
        _append_dict(sheet, {'Date': now, 'User': user, 'Action': action, 'Details': details})
    except Exception:
        pass

# ─── DAILY REPORT ─────────────────────────────────────

def get_daily_report():
    active_trips = get_all_trips('active')
    if not active_trips:
        return "📊 Нет активных поездок."

    companies = {}
    for trip in active_trips:
        companies.setdefault(trip.get('Company', 'Неизвестно'), []).append(trip)

    lines = ["📊 *Сводка*\n"]
    total_balance_all = 0
    for company, trips in companies.items():
        lines.append(f"*{company}:*")
        for trip in trips:
            stats = get_trip_stats(trip['ID'])
            if stats:
                total_balance_all += stats['total_balance']
                lines.append(
                    f"• {trip['Route']} — {stats['passengers_count']}/{stats['total_seats']} мест\n"
                    f"  Собрано: {stats['total_paid']:,.0f} | Ждём: {stats['total_balance']:,.0f}"
                )
        lines.append("")
    lines.append(f"💰 *Итого ждём доплат: {total_balance_all:,.0f}*")
    return '\n'.join(lines)
