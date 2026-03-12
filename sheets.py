import gspread
from google.oauth2.service_account import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    creds_json = os.environ.get("GOOGLE_CREDS")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(sheet_name):
    client = get_client()
    sheet_id = os.environ.get("SHEET_ID")
    return client.open_by_key(sheet_id).worksheet(sheet_name)

# ===== REMINDER =====
def get_reminders():
    return get_sheet("reminders").get_all_records()

def add_reminder(time, days, text):
    get_sheet("reminders").append_row([time, days, text])

def delete_reminder(index):
    get_sheet("reminders").delete_rows(index + 2)

# ===== CATATAN BEBAS =====
def get_notes():
    return get_sheet("notes").get_all_records()

def add_note(text):
    get_sheet("notes").append_row([text])

def delete_note(index):
    get_sheet("notes").delete_rows(index + 2)

# ===== CATATAN JUDUL & ISI =====
def get_titled_notes():
    return get_sheet("titled_notes").get_all_records()

def add_titled_note(title, content):
    get_sheet("titled_notes").append_row([title, content])

def delete_titled_note(index):
    get_sheet("titled_notes").delete_rows(index + 2)

# ===== TO-DO LIST =====
def get_todos():
    return get_sheet("todos").get_all_records()

def add_todo(task):
    get_sheet("todos").append_row([task, "❌"])

def complete_todo(index):
    get_sheet("todos").update_cell(index + 2, 2, "✅")

def delete_todo(index):
    get_sheet("todos").delete_rows(index + 2)