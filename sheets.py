import gspread
from google.oauth2.service_account import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDS")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet_id = os.environ.get("SHEET_ID")
    return client.open_by_key(sheet_id).worksheet("reminders")

def get_reminders():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    return rows

def add_reminder(time, days, text):
    sheet = get_sheet()
    sheet.append_row([time, days, text])

def delete_reminder(index):
    sheet = get_sheet()
    sheet.delete_rows(index + 2)  # +2 karena header di baris 1