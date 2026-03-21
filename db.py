import os
import random
import string
import json
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== HELPER =====
def generate_code():
    return "GRP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

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
    supabase.table("reminders").delete().in_("id", ids).eq("chat_id", chat_id).execute()

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
    supabase.table("notes").delete().in_("id", ids).eq("chat_id", chat_id).execute()

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
    supabase.table("titled_notes").delete().in_("id", ids).eq("chat_id", chat_id).execute()

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
    supabase.table("todos").delete().in_("id", ids).eq("chat_id", chat_id).execute()

def complete_todo(chat_id, todo_id):
    supabase.table("todos").update({"status": "✅"}).eq("id", todo_id).eq("chat_id", chat_id).execute()

def complete_todos_batch(chat_id, ids):
    supabase.table("todos").update({"status": "✅"}).in_("id", ids).eq("chat_id", chat_id).execute()

def edit_todo(chat_id, todo_id, value):
    supabase.table("todos").update({"task": value}).eq("id", todo_id).eq("chat_id", chat_id).execute()

# ===== GROUPS =====
def buat_grup(chat_id, name):
    code = generate_code()
    res = supabase.table("groups").insert({"code": code, "name": name, "owner_id": chat_id}).execute()
    group_id = res.data[0]['id']
    supabase.table("group_members").insert({"group_id": group_id, "chat_id": chat_id}).execute()
    return code, group_id

def join_grup(chat_id, code):
    res = supabase.table("groups").select("*").eq("code", code).execute()
    if not res.data:
        return None
    group = res.data[0]
    cek = supabase.table("group_members").select("*").eq("group_id", group['id']).eq("chat_id", chat_id).execute()
    if cek.data:
        return "sudah"
    supabase.table("group_members").insert({"group_id": group['id'], "chat_id": chat_id}).execute()
    return group

def get_my_groups(chat_id):
    res = supabase.table("group_members").select("group_id, groups(id, name, code, owner_id)").eq("chat_id", chat_id).execute()
    return [r['groups'] for r in res.data]

def get_group_members(group_id):
    res = supabase.table("group_members").select("*").eq("group_id", group_id).execute()
    return res.data

def keluar_grup(chat_id, group_id):
    supabase.table("group_members").delete().eq("chat_id", chat_id).eq("group_id", group_id).execute()

def hapus_grup(group_id):
    supabase.table("groups").delete().eq("id", group_id).execute()

# ===== PENDING CONFIRMATIONS =====
def buat_konfirmasi(from_chat_id, to_chat_id, kategori, data):
    res = supabase.table("pending_confirmations").insert({
        "from_chat_id": from_chat_id,
        "to_chat_id": to_chat_id,
        "kategori": kategori,
        "data": data
    }).execute()
    return res.data[0]['id']

def get_konfirmasi(konfirmasi_id):
    res = supabase.table("pending_confirmations").select("*").eq("id", konfirmasi_id).execute()
    if not res.data:
        return None
    k = res.data[0]
    # Cek expired
    from datetime import datetime, timezone
    expires = datetime.fromisoformat(k['expires_at'].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires:
        hapus_konfirmasi(konfirmasi_id)
        return "expired"
    return k

def hapus_konfirmasi(konfirmasi_id):
    supabase.table("pending_confirmations").delete().eq("id", konfirmasi_id).execute()

# ===== GET BY ID =====
def get_notes_by_id(note_id):
    res = supabase.table("notes").select("*").eq("id", note_id).execute()
    return res.data[0] if res.data else None

def get_todos_by_id(todo_id):
    res = supabase.table("todos").select("*").eq("id", todo_id).execute()
    return res.data[0] if res.data else None

def get_reminders_by_id(reminder_id):
    res = supabase.table("reminders").select("*").eq("id", reminder_id).execute()
    return res.data[0] if res.data else None

def get_titled_notes_by_id(note_id):
    res = supabase.table("titled_notes").select("*").eq("id", note_id).execute()
    return res.data[0] if res.data else None