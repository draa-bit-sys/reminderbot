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

def add_reminders_batch(items):
    # items = list of (time, days, text)
    sheet = get_sheet("reminders")
    rows = [[time, days, text] for time, days, text in items]
    sheet.append_rows(rows)

def delete_reminder(index):
    get_sheet("reminders").delete_rows(index + 2)

def delete_reminders_batch(indexes):
    # indexes sudah sorted descending
    sheet = get_sheet("reminders")
    for index in indexes:
        sheet.delete_rows(index + 2)

# ===== CATATAN BEBAS =====
def get_notes():
    return get_sheet("notes").get_all_records()

def add_note(text):
    get_sheet("notes").append_row([text])

def delete_note(index):
    get_sheet("notes").delete_rows(index + 2)

def delete_notes_batch(indexes):
    sheet = get_sheet("notes")
    for index in indexes:
        sheet.delete_rows(index + 2)

# ===== CATATAN JUDUL & ISI =====
def get_titled_notes():
    return get_sheet("titled_notes").get_all_records()

def add_titled_note(title, content):
    get_sheet("titled_notes").append_row([title, content])

def delete_titled_note(index):
    get_sheet("titled_notes").delete_rows(index + 2)

def delete_titled_notes_batch(indexes):
    sheet = get_sheet("titled_notes")
    for index in indexes:
        sheet.delete_rows(index + 2)

# ===== TO-DO LIST =====
def get_todos():
    return get_sheet("todos").get_all_records()

def add_todo(task):
    get_sheet("todos").append_row([task, "❌"])

def delete_todo(index):
    get_sheet("todos").delete_rows(index + 2)

def delete_todos_batch(indexes):
    sheet = get_sheet("todos")
    for index in indexes:
        sheet.delete_rows(index + 2)

def complete_todo(index):
    get_sheet("todos").update_cell(index + 2, 2, "✅")

def complete_todos_batch(indexes):
    sheet = get_sheet("todos")
    for index in indexes:
        sheet.update_cell(index + 2, 2, "✅")

# ===== EDIT =====
def edit_reminder(index, field, value):
    sheet = get_sheet("reminders")
    col = {"time": 1, "days": 2, "text": 3}[field]
    sheet.update_cell(index + 2, col, value)

def edit_note(index, value):
    get_sheet("notes").update_cell(index + 2, 1, value)

def edit_titled_note(index, field, value):
    sheet = get_sheet("titled_notes")
    col = {"title": 1, "content": 2}[field]
    sheet.update_cell(index + 2, col, value)

def edit_todo(index, value):
    get_sheet("todos").update_cell(index + 2, 1, value)