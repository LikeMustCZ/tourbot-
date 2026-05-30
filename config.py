import os
import json

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")

_creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CREDENTIALS = json.loads(_creds_raw) if _creds_raw else {}

COMPANIES = ["Happy Tours", "Your Perfect Travel"]

REPORT_HOUR = 20
REPORT_MINUTE = 0
