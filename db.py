import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== REMINDER =====
def get_reminders(chat_id):
    res = supabase.table("reminders").select("*").eq("chat_id", chat_id).execute()
    return res.data

def add_reminder(chat_id, time, days, text):
    supabase.table("reminders").insert({"chat_id": chat_id, "time": time, "days": days, "text": text}).execute()

def add_reminders_batch(chat_id, items):
    rows = [{"chat_id": chat_id, "time": t, "days": d, "text": tx} for t, d, tx in items]
    supabase.table("reminders").insert(rows).execute()

def delete_reminder(chat_id, reminder_id):
    supabase.table("reminders").delete().eq("id", reminder_id).eq("chat_id", chat_id).execute()

def delete_reminders_batch(chat_id, ids):
    for rid in ids:
        supabase.table("reminders").delete().eq("id", rid).eq("chat_id", chat_id).execute()

def edit_reminder(chat_id, reminder_id, field, value):
    supabase.table("reminders").update({field: value}).eq("id", reminder_id).eq("chat_id", chat_id).execute()

# ===== NOTES =====
def get_notes(chat_id):
    res = supabase.table("notes").select("*").eq("chat_id", chat_id).execute()
    return res.data

def add_note(chat_id, text):
    supabase.table("notes").insert({"chat_id": chat_id, "text": text}).execute()

def delete_note(chat_id, note_id):
    supabase.table("notes").delete().eq("id", note_id).eq("chat_id", chat_id).execute()

def delete_notes_batch(chat_id, ids):
    for nid in ids:
        supabase.table("notes").delete().eq("id", nid).eq("chat_id", chat_id).execute()

def edit_note(chat_id, note_id, value):
    supabase.table("notes").update({"text": value}).eq("id", note_id).eq("chat_id", chat_id).execute()

# ===== TITLED NOTES =====
def get_titled_notes(chat_id):
    res = supabase.table("titled_notes").select("*").eq("chat_id", chat_id).execute()
    return res.data

def add_titled_note(chat_id, title, content):
    supabase.table("titled_notes").insert({"chat_id": chat_id, "title": title, "content": content}).execute()

def delete_titled_note(chat_id, note_id):
    supabase.table("titled_notes").delete().eq("id", note_id).eq("chat_id", chat_id).execute()

def delete_titled_notes_batch(chat_id, ids):
    for nid in ids:
        supabase.table("titled_notes").delete().eq("id", nid).eq("chat_id", chat_id).execute()

def edit_titled_note(chat_id, note_id, field, value):
    supabase.table("titled_notes").update({field: value}).eq("id", note_id).eq("chat_id", chat_id).execute()

# ===== TODOS =====
def get_todos(chat_id):
    res = supabase.table("todos").select("*").eq("chat_id", chat_id).execute()
    return res.data

def add_todo(chat_id, task):
    supabase.table("todos").insert({"chat_id": chat_id, "task": task, "status": "❌"}).execute()

def delete_todo(chat_id, todo_id):
    supabase.table("todos").delete().eq("id", todo_id).eq("chat_id", chat_id).execute()

def delete_todos_batch(chat_id, ids):
    for tid in ids:
        supabase.table("todos").delete().eq("id", tid).eq("chat_id", chat_id).execute()

def complete_todo(chat_id, todo_id):
    supabase.table("todos").update({"status": "✅"}).eq("id", todo_id).eq("chat_id", chat_id).execute()

def complete_todos_batch(chat_id, ids):
    for tid in ids:
        supabase.table("todos").update({"status": "✅"}).eq("id", tid).eq("chat_id", chat_id).execute()

def edit_todo(chat_id, todo_id, value):
    supabase.table("todos").update({"task": value}).eq("id", todo_id).eq("chat_id", chat_id).execute()