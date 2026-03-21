import logging
import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from db import (
    get_reminders, add_reminder, add_reminders_batch, delete_reminder, delete_reminders_batch, edit_reminder,
    get_notes, add_note, delete_note, delete_notes_batch, edit_note,
    get_titled_notes, add_titled_note, delete_titled_note, delete_titled_notes_batch, edit_titled_note,
    get_todos, add_todo, complete_todo, complete_todos_batch, delete_todo, delete_todos_batch, edit_todo,
    buat_grup, join_grup, get_my_groups, get_group_members, keluar_grup, hapus_grup,
    buat_konfirmasi, get_konfirmasi, hapus_konfirmasi
)

# ===== CONFIG =====
TOKEN    = os.environ.get("BOT_TOKEN")
CHAT_ID  = os.environ.get("CHAT_ID")
TIMEZONE = "Asia/Makassar"
# ==================

logging.basicConfig(level=logging.INFO)

DAY_MAP = {
    "mon": "mon", "tue": "tue", "wed": "wed",
    "thu": "thu", "fri": "fri", "sat": "sat", "sun": "sun",
    "daily": "mon,tue,wed,thu,fri,sat,sun"
}

DAY_LABELS = {
    "daily": "Setiap Hari",
    "mon": "Senin", "tue": "Selasa", "wed": "Rabu",
    "thu": "Kamis", "fri": "Jumat", "sat": "Sabtu", "sun": "Minggu"
}

scheduler = None

# ===== STATES =====
(
    TAMBAH_PILIH_KATEGORI,
    TAMBAH_PILIH_HARI,
    TAMBAH_JAM_PESAN,
    TAMBAH_INPUT_ARGS,
    TAMBAH_INPUT_CATAT,
    TAMBAH_INPUT_JUDUL,
    TAMBAH_INPUT_ISI_JUDUL,
    TAMBAH_INPUT_TODO,
    HAPUS_PILIH_KATEGORI,
    HAPUS_PILIH_NOMOR,
    EDIT_PILIH_KATEGORI,
    EDIT_PILIH_NOMOR,
    EDIT_PILIH_FIELD,
    EDIT_PILIH_HARI,
    EDIT_INPUT_NILAI,
    CHECK_TODOS,
    GRUP_JOIN_INPUT,
    GRUP_BUAT_INPUT,
    GRUP_KELUAR_PILIH,
    KIRIM_PILIH_KATEGORI,
    KIRIM_PILIH_DATA,
    KIRIM_PILIH_GRUP,
    KIRIM_PILIH_MEMBER,
) = range(23)

async def kirim_pesan(bot: Bot, chat_id: str, teks: str):
    await bot.send_message(chat_id=chat_id, text=teks)
    logging.info(f"Terkirim: {teks}")

# ===== GENERAL =====
async def test(update, context):
    await update.message.reply_text("✅ Bot aktif dan berjalan!")

async def batal(update, context):
    await update.message.reply_text("❌ Dibatalkan.")
    return ConversationHandler.END

async def help_command(update, context):
    msg = """📋 *Daftar Command:*

*Utama:*
/tambah - Tambah data
/hapus - Hapus data
/edit - Edit data

*Lihat:*
/list - Lihat semua reminder
/lihatcatat - Lihat catatan bebas
/lihatjudul - Lihat catatan judul
/listtodo - Lihat semua tugas

*To-Do:*
/checktodos - Tandai tugas selesai

*Grup:*
/buatgrup - Buat grup baru
/joingrup - Join grup
/infogrup - Info & member grup
/keluargrup - Keluar dari grup
/kirim - Kirim data ke member grup

/help - Tampilkan bantuan ini
/batal - Batalkan aksi saat ini"""
    await update.message.reply_text(msg, parse_mode="Markdown")

# ===== LIHAT =====
async def list_reminders(update, context):
    chat_id = str(update.effective_chat.id)
    reminders = get_reminders(chat_id)
    if not reminders:
        await update.message.reply_text("Belum ada reminder.")
        return
    msg = "📋 *Daftar Reminder:*\n\n"
    for i, r in enumerate(reminders):
        msg += f"{i+1}. `{r['time']}` | `{r['days']}` | {r['text']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def lihat_catat(update, context):
    chat_id = str(update.effective_chat.id)
    notes = get_notes(chat_id)
    if not notes:
        await update.message.reply_text("Belum ada catatan.")
        return
    msg = "📝 *Catatan:*\n\n"
    for i, n in enumerate(notes):
        msg += f"{i+1}. {n['text']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def lihat_judul(update, context):
    chat_id = str(update.effective_chat.id)
    notes = get_titled_notes(chat_id)
    if not notes:
        await update.message.reply_text("Belum ada catatan.")
        return
    msg = "📓 *Catatan Judul:*\n\n"
    for i, n in enumerate(notes):
        msg += f"{i+1}. *{n['title']}*\n{n['content']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_todo(update, context):
    chat_id = str(update.effective_chat.id)
    todos = get_todos(chat_id)
    if not todos:
        await update.message.reply_text("Belum ada tugas.")
        return
    msg = "📌 *To-Do List:*\n\n"
    for i, t in enumerate(todos):
        msg += f"{i+1}. {t['status']} {t['task']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ===== TAMBAH =====
def keyboard_kategori(prefix):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Reminder", callback_data=f"{prefix}_reminder"),
            InlineKeyboardButton("📝 Catatan", callback_data=f"{prefix}_catat"),
        ],
        [
            InlineKeyboardButton("📓 Catatan Judul", callback_data=f"{prefix}_judul"),
            InlineKeyboardButton("📌 To-Do", callback_data=f"{prefix}_todo"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"{prefix}_batal")]
    ])

async def tambah(update, context):
    chat_id = str(update.effective_chat.id)
    if context.args:
        try:
            raw = " ".join(context.args)
            items = raw.split(",")
            parsed = []

            for item in items:
                parts = item.strip().split(" ", 2)
                if len(parts) < 3:
                    await update.message.reply_text(f"❌ Format salah di: `{item.strip()}`", parse_mode="Markdown")
                    return ConversationHandler.END

                time, days, text = parts
                valid_days = ["daily", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                if days not in valid_days:
                    await update.message.reply_text(f"❌ Hari `{days}` tidak valid!", parse_mode="Markdown")
                    return ConversationHandler.END

                parsed.append((time, days, text))

            add_reminders_batch(chat_id, parsed)
            setup_scheduler(context.application)
            added = [f"⏰ {t} | {d} | {tx}" for t, d, tx in parsed]
            await update.message.reply_text("✅ Reminder ditambahkan!\n\n" + "\n".join(added))

        except Exception as e:
            await update.message.reply_text("❌ Format salah!")
        return ConversationHandler.END

    await update.message.reply_text("➕ *Tambah apa?*", reply_markup=keyboard_kategori("tambah"), parse_mode="Markdown")
    return TAMBAH_PILIH_KATEGORI

async def tambah_pilih_kategori(update, context):
    query = update.callback_query
    await query.answer()
    kategori = query.data.replace("tambah_", "")

    if kategori == "batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    context.user_data["tambah_kategori"] = kategori

    if kategori == "reminder":
        keyboard = [
            [InlineKeyboardButton("Setiap Hari", callback_data="tambahhari_daily")],
            [
                InlineKeyboardButton("Senin", callback_data="tambahhari_mon"),
                InlineKeyboardButton("Selasa", callback_data="tambahhari_tue"),
                InlineKeyboardButton("Rabu", callback_data="tambahhari_wed"),
                InlineKeyboardButton("Kamis", callback_data="tambahhari_thu"),
            ],
            [
                InlineKeyboardButton("Jumat", callback_data="tambahhari_fri"),
                InlineKeyboardButton("Sabtu", callback_data="tambahhari_sat"),
                InlineKeyboardButton("Minggu", callback_data="tambahhari_sun"),
            ],
            [InlineKeyboardButton("❌ Batal", callback_data="tambahhari_batal")]
        ]
        await query.edit_message_text("📅 Pilih hari:", reply_markup=InlineKeyboardMarkup(keyboard))
        return TAMBAH_PILIH_HARI
    elif kategori == "catat":
        await query.edit_message_text("📝 Ketik isi catatan:")
        return TAMBAH_INPUT_CATAT
    elif kategori == "judul":
        await query.edit_message_text("📓 Ketik judul catatan:")
        return TAMBAH_INPUT_JUDUL
    elif kategori == "todo":
        await query.edit_message_text("📌 Ketik nama tugas:")
        return TAMBAH_INPUT_TODO

async def tambah_pilih_hari(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "tambahhari_batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    hari = query.data.replace("tambahhari_", "")
    context.user_data["hari"] = hari
    label = DAY_LABELS.get(hari, hari)

    await query.edit_message_text(
        f"✅ Hari: *{label}*\n\nKetik jam dan pesan:\nFormat: `08:00 Minum obat`",
        parse_mode="Markdown"
    )
    return TAMBAH_JAM_PESAN

async def tambah_jam_pesan(update, context):
    chat_id = str(update.effective_chat.id)
    try:
        parts = update.message.text.strip().split(" ", 1)
        if len(parts) < 2:
            await update.message.reply_text("❌ Format salah!\nKirim: `08:00 Minum obat`", parse_mode="Markdown")
            return TAMBAH_JAM_PESAN

        time, pesan = parts
        hari = context.user_data.get("hari")
        label = DAY_LABELS.get(hari, hari)

        add_reminder(chat_id, time, hari, pesan)
        setup_scheduler(context.application)
        await update.message.reply_text(f"✅ Reminder ditambahkan!\n\n⏰ {time} | {label} | {pesan}")
    except:
        await update.message.reply_text("❌ Terjadi error, coba lagi.")
    return ConversationHandler.END

async def tambah_terima_catat(update, context):
    chat_id = str(update.effective_chat.id)
    text = update.message.text.strip()
    add_note(chat_id, text)
    await update.message.reply_text(f"✅ Catatan disimpan!\n\n{text}")
    return ConversationHandler.END

async def tambah_terima_judul(update, context):
    context.user_data["judul"] = update.message.text.strip()
    await update.message.reply_text("📝 Ketik isi catatan:")
    return TAMBAH_INPUT_ISI_JUDUL

async def tambah_terima_isi_judul(update, context):
    chat_id = str(update.effective_chat.id)
    title = context.user_data.get("judul")
    content = update.message.text.strip()
    add_titled_note(chat_id, title, content)
    await update.message.reply_text(f"✅ Catatan disimpan!\n\n*{title}*\n{content}", parse_mode="Markdown")
    return ConversationHandler.END

async def tambah_terima_todo(update, context):
    chat_id = str(update.effective_chat.id)
    task = update.message.text.strip()
    add_todo(chat_id, task)
    await update.message.reply_text(f"✅ Tugas ditambahkan!\n\n❌ {task}")
    return ConversationHandler.END

# ===== HAPUS =====
async def hapus(update, context):
    await update.message.reply_text("🗑️ *Hapus apa?*", reply_markup=keyboard_kategori("hapus"), parse_mode="Markdown")
    return HAPUS_PILIH_KATEGORI

async def hapus_pilih_kategori(update, context):
    query = update.callback_query
    await query.answer()
    kategori = query.data.replace("hapus_", "")

    if kategori == "batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    context.user_data["hapus_kategori"] = kategori
    chat_id = str(query.from_user.id)

    if kategori == "reminder":
        data = get_reminders(chat_id)
        if not data:
            await query.edit_message_text("Belum ada reminder.")
            return ConversationHandler.END
        msg = "🗑️ *Hapus Reminder*\n\n"
        for i, r in enumerate(data):
            msg += f"{i+1}. `{r['time']}` | `{r['days']}` | {r['text']}\n"
    elif kategori == "catat":
        data = get_notes(chat_id)
        if not data:
            await query.edit_message_text("Belum ada catatan.")
            return ConversationHandler.END
        msg = "🗑️ *Hapus Catatan*\n\n"
        for i, n in enumerate(data):
            msg += f"{i+1}. {n['text']}\n"
    elif kategori == "judul":
        data = get_titled_notes(chat_id)
        if not data:
            await query.edit_message_text("Belum ada catatan judul.")
            return ConversationHandler.END
        msg = "🗑️ *Hapus Catatan Judul*\n\n"
        for i, n in enumerate(data):
            msg += f"{i+1}. *{n['title']}* — {n['content'][:30]}...\n"
    elif kategori == "todo":
        data = get_todos(chat_id)
        if not data:
            await query.edit_message_text("Belum ada tugas.")
            return ConversationHandler.END
        msg = "🗑️ *Hapus Tugas*\n\n"
        for i, t in enumerate(data):
            msg += f"{i+1}. {t['status']} {t['task']}\n"

    context.user_data["hapus_data"] = data
    msg += "\nKetik nomor: `1` atau `1,2,3`"
    await query.edit_message_text(msg, parse_mode="Markdown")
    return HAPUS_PILIH_NOMOR

async def hapus_pilih_nomor(update, context):
    chat_id = str(update.effective_chat.id)
    try:
        indexes = sorted([int(x.strip()) - 1 for x in update.message.text.split(",")], reverse=True)
        kategori = context.user_data["hapus_kategori"]
        data = context.user_data["hapus_data"]
        deleted = []

        if kategori == "reminder":
            ids = [data[i]['id'] for i in indexes]
            deleted = [data[i]['text'] for i in indexes]
            delete_reminders_batch(chat_id, ids)
            setup_scheduler(context.application)
        elif kategori == "catat":
            ids = [data[i]['id'] for i in indexes]
            deleted = [data[i]['text'] for i in indexes]
            delete_notes_batch(chat_id, ids)
        elif kategori == "judul":
            ids = [data[i]['id'] for i in indexes]
            deleted = [data[i]['title'] for i in indexes]
            delete_titled_notes_batch(chat_id, ids)
        elif kategori == "todo":
            ids = [data[i]['id'] for i in indexes]
            deleted = [data[i]['task'] for i in indexes]
            delete_todos_batch(chat_id, ids)

        await update.message.reply_text("🗑️ Dihapus:\n\n" + "\n".join(f"- {t}" for t in deleted))
    except:
        await update.message.reply_text("❌ Format salah!\nKetik nomor: `1` atau `1,2,3`", parse_mode="Markdown")
    return ConversationHandler.END

# ===== EDIT =====
async def edit(update, context):
    await update.message.reply_text("✏️ *Edit apa?*", reply_markup=keyboard_kategori("edit"), parse_mode="Markdown")
    return EDIT_PILIH_KATEGORI

async def edit_pilih_kategori(update, context):
    query = update.callback_query
    await query.answer()
    kategori = query.data.replace("edit_", "")

    if kategori == "batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    context.user_data["edit_kategori"] = kategori
    chat_id = str(query.from_user.id)

    if kategori == "reminder":
        data = get_reminders(chat_id)
        if not data:
            await query.edit_message_text("Belum ada reminder.")
            return ConversationHandler.END
        msg = "✏️ *Edit Reminder*\n\n"
        for i, r in enumerate(data):
            msg += f"{i+1}. `{r['time']}` | `{r['days']}` | {r['text']}\n"
    elif kategori == "catat":
        data = get_notes(chat_id)
        if not data:
            await query.edit_message_text("Belum ada catatan.")
            return ConversationHandler.END
        msg = "✏️ *Edit Catatan*\n\n"
        for i, n in enumerate(data):
            msg += f"{i+1}. {n['text']}\n"
    elif kategori == "judul":
        data = get_titled_notes(chat_id)
        if not data:
            await query.edit_message_text("Belum ada catatan judul.")
            return ConversationHandler.END
        msg = "✏️ *Edit Catatan Judul*\n\n"
        for i, n in enumerate(data):
            msg += f"{i+1}. *{n['title']}* — {n['content'][:30]}...\n"
    elif kategori == "todo":
        data = get_todos(chat_id)
        if not data:
            await query.edit_message_text("Belum ada tugas.")
            return ConversationHandler.END
        msg = "✏️ *Edit Tugas*\n\n"
        for i, t in enumerate(data):
            msg += f"{i+1}. {t['status']} {t['task']}\n"

    context.user_data["edit_data"] = data
    msg += "\nKetik nomornya:"
    await query.edit_message_text(msg, parse_mode="Markdown")
    return EDIT_PILIH_NOMOR

async def edit_pilih_nomor(update, context):
    try:
        index = int(update.message.text.strip()) - 1
        context.user_data["edit_index"] = index
        kategori = context.user_data["edit_kategori"]
        data = context.user_data["edit_data"]
        context.user_data["edit_id"] = data[index]['id']

        if kategori == "reminder":
            keyboard = [
                [
                    InlineKeyboardButton("⏰ Jam", callback_data="editfield_time"),
                    InlineKeyboardButton("📅 Hari", callback_data="editfield_days"),
                    InlineKeyboardButton("💬 Pesan", callback_data="editfield_text"),
                ],
                [InlineKeyboardButton("❌ Batal", callback_data="editfield_batal")]
            ]
            await update.message.reply_text("✏️ Edit apa?", reply_markup=InlineKeyboardMarkup(keyboard))
            return EDIT_PILIH_FIELD
        elif kategori == "judul":
            keyboard = [
                [
                    InlineKeyboardButton("📌 Judul", callback_data="editfield_title"),
                    InlineKeyboardButton("📝 Isi", callback_data="editfield_content"),
                ],
                [InlineKeyboardButton("❌ Batal", callback_data="editfield_batal")]
            ]
            await update.message.reply_text("✏️ Edit apa?", reply_markup=InlineKeyboardMarkup(keyboard))
            return EDIT_PILIH_FIELD
        else:
            if kategori == "catat":
                await update.message.reply_text(f"✏️ Nilai lama: `{data[index]['text']}`\n\nKetik nilai baru:", parse_mode="Markdown")
            elif kategori == "todo":
                await update.message.reply_text(f"✏️ Nilai lama: `{data[index]['task']}`\n\nKetik nilai baru:", parse_mode="Markdown")
            context.user_data["edit_field"] = "value"
            return EDIT_INPUT_NILAI

    except:
        await update.message.reply_text("❌ Nomor tidak valid, coba lagi:")
        return EDIT_PILIH_NOMOR

async def edit_pilih_field(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "editfield_batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    field = query.data.replace("editfield_", "")
    context.user_data["edit_field"] = field
    kategori = context.user_data["edit_kategori"]
    data = context.user_data["edit_data"]
    index = context.user_data["edit_index"]

    if field == "days":
        keyboard = [
            [InlineKeyboardButton("Setiap Hari", callback_data="edithari_daily")],
            [
                InlineKeyboardButton("Senin", callback_data="edithari_mon"),
                InlineKeyboardButton("Selasa", callback_data="edithari_tue"),
                InlineKeyboardButton("Rabu", callback_data="edithari_wed"),
                InlineKeyboardButton("Kamis", callback_data="edithari_thu"),
            ],
            [
                InlineKeyboardButton("Jumat", callback_data="edithari_fri"),
                InlineKeyboardButton("Sabtu", callback_data="edithari_sat"),
                InlineKeyboardButton("Minggu", callback_data="edithari_sun"),
            ],
        ]
        await query.edit_message_text("📅 Pilih hari baru:", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_PILIH_HARI

    if kategori == "reminder":
        nilai_lama = data[index].get(field, "-")
    elif kategori == "judul":
        nilai_lama = data[index]["title"] if field == "title" else data[index]["content"]
    else:
        nilai_lama = "-"

    await query.edit_message_text(f"✏️ Nilai lama: `{nilai_lama}`\n\nKetik nilai baru:", parse_mode="Markdown")
    return EDIT_INPUT_NILAI

async def edit_pilih_hari_baru(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.from_user.id)

    hari = query.data.replace("edithari_", "")
    rid = context.user_data["edit_id"]
    label = DAY_LABELS.get(hari, hari)

    edit_reminder(chat_id, rid, "days", hari)
    await query.edit_message_text(f"✅ Hari diupdate ke *{label}*!", parse_mode="Markdown")
    return ConversationHandler.END

async def edit_input_nilai(update, context):
    chat_id = str(update.effective_chat.id)
    try:
        nilai_baru = update.message.text.strip()
        kategori = context.user_data["edit_kategori"]
        field = context.user_data["edit_field"]
        rid = context.user_data["edit_id"]

        if kategori == "reminder":
            edit_reminder(chat_id, rid, field, nilai_baru)
            await update.message.reply_text("✅ Reminder diupdate!")
        elif kategori == "catat":
            edit_note(chat_id, rid, nilai_baru)
            await update.message.reply_text(f"✅ Catatan diupdate!\n\n{nilai_baru}")
        elif kategori == "judul":
            edit_titled_note(chat_id, rid, field, nilai_baru)
            await update.message.reply_text("✅ Catatan diupdate!")
        elif kategori == "todo":
            edit_todo(chat_id, rid, nilai_baru)
            await update.message.reply_text(f"✅ Tugas diupdate!\n\n{nilai_baru}")

    except Exception as e:
        await update.message.reply_text("❌ Terjadi error, coba lagi.")
    return ConversationHandler.END

# ===== CHECKTODOS =====
async def check_todos(update, context):
    chat_id = str(update.effective_chat.id)
    todos = get_todos(chat_id)
    if not todos:
        await update.message.reply_text("Belum ada tugas.")
        return ConversationHandler.END

    msg = "✅ *Tandai Selesai*\n\n"
    for i, t in enumerate(todos):
        msg += f"{i+1}. {t['status']} {t['task']}\n"
    msg += "\nKetik nomor: `1` atau `1,2,3`"

    context.user_data["check_data"] = todos
    await update.message.reply_text(msg, parse_mode="Markdown")
    return CHECK_TODOS

async def konfirmasi_check_todos(update, context):
    chat_id = str(update.effective_chat.id)
    try:
        indexes = sorted([int(x.strip()) - 1 for x in update.message.text.split(",")], reverse=True)
        todos = context.user_data["check_data"]
        ids = [todos[i]['id'] for i in indexes]
        done = [todos[i]['task'] for i in indexes]
        complete_todos_batch(chat_id, ids)
        await update.message.reply_text("✅ Tugas selesai:\n\n" + "\n".join(f"- {t}" for t in done))
    except:
        await update.message.reply_text("❌ Format salah!\nKetik nomor: `1` atau `1,2,3`", parse_mode="Markdown")
    return ConversationHandler.END

# ===== GRUP =====
async def buat_grup_cmd(update, context):
    await update.message.reply_text("👥 Ketik nama grup:")
    return GRUP_BUAT_INPUT

async def buat_grup_input(update, context):
    chat_id = str(update.effective_chat.id)
    name = update.message.text.strip()
    code, group_id = buat_grup(chat_id, name)
    await update.message.reply_text(
        f"✅ Grup *{name}* dibuat!\n\nKode: `{code}`\n\nShare kode ini ke teman kamu!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def join_grup_cmd(update, context):
    await update.message.reply_text("🔑 Ketik kode grup:")
    return GRUP_JOIN_INPUT

async def join_grup_input(update, context):
    chat_id = str(update.effective_chat.id)
    code = update.message.text.strip().upper()
    result = join_grup(chat_id, code)

    if result is None:
        await update.message.reply_text("❌ Kode grup tidak ditemukan!")
    elif result == "sudah":
        await update.message.reply_text("⚠️ Kamu sudah bergabung di grup ini!")
    else:
        await update.message.reply_text(f"✅ Berhasil join grup *{result['name']}*!", parse_mode="Markdown")
    return ConversationHandler.END

async def info_grup(update, context):
    chat_id = str(update.effective_chat.id)
    groups = get_my_groups(chat_id)
    if not groups:
        await update.message.reply_text("Kamu belum bergabung di grup manapun.")
        return

    msg = "👥 *Grup Kamu:*\n\n"
    for g in groups:
        members = get_group_members(g['id'])
        msg += f"*{g['name']}*\n"
        msg += f"Kode: `{g['code']}`\n"
        msg += f"Member: {len(members)} orang\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def keluar_grup_cmd(update, context):
    chat_id = str(update.effective_chat.id)
    groups = get_my_groups(chat_id)
    if not groups:
        await update.message.reply_text("Kamu belum bergabung di grup manapun.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(g['name'], callback_data=f"keluargrup_{g['id']}")] for g in groups]
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="keluargrup_batal")])
    await update.message.reply_text("Pilih grup yang mau ditinggalkan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GRUP_KELUAR_PILIH

async def keluar_grup_pilih(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.from_user.id)

    if query.data == "keluargrup_batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    group_id = int(query.data.replace("keluargrup_", ""))
    keluar_grup(chat_id, group_id)
    await query.edit_message_text("✅ Berhasil keluar dari grup!")
    return ConversationHandler.END

# ===== KIRIM =====
async def kirim_cmd(update, context):
    await update.message.reply_text(
        "📤 *Kirim data apa?*",
        reply_markup=keyboard_kategori("kirim"),
        parse_mode="Markdown"
    )
    return KIRIM_PILIH_KATEGORI

async def kirim_pilih_kategori(update, context):
    query = update.callback_query
    await query.answer()
    kategori = query.data.replace("kirim_", "")

    if kategori == "batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    context.user_data["kirim_kategori"] = kategori
    chat_id = str(query.from_user.id)

    if kategori == "reminder":
        data = get_reminders(chat_id)
        if not data:
            await query.edit_message_text("Belum ada reminder.")
            return ConversationHandler.END
        msg = "📤 *Pilih Reminder:*\n\n"
        for i, r in enumerate(data):
            msg += f"{i+1}. `{r['time']}` | `{r['days']}` | {r['text']}\n"
    elif kategori == "catat":
        data = get_notes(chat_id)
        if not data:
            await query.edit_message_text("Belum ada catatan.")
            return ConversationHandler.END
        msg = "📤 *Pilih Catatan:*\n\n"
        for i, n in enumerate(data):
            msg += f"{i+1}. {n['text']}\n"
    elif kategori == "judul":
        data = get_titled_notes(chat_id)
        if not data:
            await query.edit_message_text("Belum ada catatan judul.")
            return ConversationHandler.END
        msg = "📤 *Pilih Catatan Judul:*\n\n"
        for i, n in enumerate(data):
            msg += f"{i+1}. *{n['title']}*\n"
    elif kategori == "todo":
        data = get_todos(chat_id)
        if not data:
            await query.edit_message_text("Belum ada tugas.")
            return ConversationHandler.END
        msg = "📤 *Pilih Tugas:*\n\n"
        for i, t in enumerate(data):
            msg += f"{i+1}. {t['status']} {t['task']}\n"

    context.user_data["kirim_data"] = data
    msg += "\nKetik nomor: `1` atau `1,2,3`"
    await query.edit_message_text(msg, parse_mode="Markdown")
    return KIRIM_PILIH_DATA

async def kirim_pilih_data(update, context):
    chat_id = str(update.effective_chat.id)
    try:
        indexes = [int(x.strip()) - 1 for x in update.message.text.split(",")]
        context.user_data["kirim_indexes"] = indexes

        groups = get_my_groups(chat_id)
        if not groups:
            await update.message.reply_text("❌ Kamu belum bergabung di grup manapun!")
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton(g['name'], callback_data=f"kirimgrup_{g['id']}")] for g in groups]
        keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="kirimgrup_batal")])
        context.user_data["kirim_groups"] = groups
        await update.message.reply_text("👥 Pilih grup tujuan:", reply_markup=InlineKeyboardMarkup(keyboard))
        return KIRIM_PILIH_GRUP
    except:
        await update.message.reply_text("❌ Format salah!")
        return KIRIM_PILIH_DATA

async def kirim_pilih_grup(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "kirimgrup_batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    group_id = int(query.data.replace("kirimgrup_", ""))
    context.user_data["kirim_group_id"] = group_id
    chat_id = str(query.from_user.id)

    members = get_group_members(group_id)
    other_members = [m for m in members if m['chat_id'] != chat_id]

    if not other_members:
        await query.edit_message_text("❌ Tidak ada member lain di grup ini!")
        return ConversationHandler.END

    context.user_data["kirim_members"] = other_members
    keyboard = []
    for m in other_members:
        # Tampilkan nama kalau ada, fallback ke chat_id
        nama = m.get('nickname') or m['chat_id']
        keyboard.append([InlineKeyboardButton(f"👤 {nama}", callback_data=f"kirimmember_{m['chat_id']}")])
    keyboard.append([InlineKeyboardButton("👥 Semua Member", callback_data="kirimmember_all")])
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="kirimmember_batal")])

    await query.edit_message_text("👤 Kirim ke siapa?", reply_markup=InlineKeyboardMarkup(keyboard))
    return KIRIM_PILIH_MEMBER

async def kirim_pilih_member(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "kirimmember_batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    kategori = context.user_data["kirim_kategori"]
    indexes = context.user_data["kirim_indexes"]
    data = context.user_data["kirim_data"]
    members = context.user_data["kirim_members"]
    from_user = query.from_user
    from_name = from_user.first_name or from_user.username or from_user.id

    if query.data == "kirimmember_all":
        target_ids = [m['chat_id'] for m in members]
    else:
        target_ids = [query.data.replace("kirimmember_", "")]

    # Kirim konfirmasi ke tiap target
    for target_id in target_ids:
        # Buat preview pesan
        preview = ""
        items_data = []
        for i in indexes:
            item = data[i]
            if kategori == "reminder":
                preview += f"⏰ `{item['time']}` | `{item['days']}` | {item['text']}\n"
            elif kategori == "catat":
                preview += f"📝 {item['text']}\n"
            elif kategori == "judul":
                preview += f"📓 *{item['title']}*\n{item['content']}\n"
            elif kategori == "todo":
                preview += f"📌 {item['status']} {item['task']}\n"
            items_data.append(item)

        # Simpan ke db
        konfirmasi_id = buat_konfirmasi(
            from_chat_id=str(from_user.id),
            to_chat_id=target_id,
            kategori=kategori,
            data=items_data
        )

        # Kirim pesan konfirmasi dengan inline button
        msg = f"📨 *{from_name}* mengirimkan data ke kamu:\n\n{preview}\nTambahkan ke datamu?"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Tambahkan", callback_data=f"konfirmasi_yes_{konfirmasi_id}"),
                InlineKeyboardButton("❌ Tolak", callback_data=f"konfirmasi_no_{konfirmasi_id}"),
            ]
        ])
        await context.bot.send_message(
            chat_id=target_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    await query.edit_message_text(f"✅ Berhasil dikirim ke {len(target_ids)} member!")
    return ConversationHandler.END

# ===== HANDLER KONFIRMASI =====
async def handle_konfirmasi(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.from_user.id)

    action, konfirmasi_id = query.data.replace("konfirmasi_", "").split("_", 1)
    konfirmasi_id = int(konfirmasi_id)

    k = get_konfirmasi(konfirmasi_id)

    if k is None or k == "expired":
        await query.edit_message_text("⏰ Konfirmasi sudah expired (24 jam)!")
        return

    if action == "yes":
        kategori = k['kategori']
        items = k['data']

        if kategori == "reminder":
            for item in items:
                add_reminder(chat_id, item['time'], item['days'], item['text'])
            setup_scheduler(context.application)
            await query.edit_message_text("✅ Reminder berhasil ditambahkan ke datamu!")

        elif kategori == "catat":
            for item in items:
                add_note(chat_id, item['text'])
            await query.edit_message_text("✅ Catatan berhasil ditambahkan ke datamu!")

        elif kategori == "judul":
            for item in items:
                add_titled_note(chat_id, item['title'], item['content'])
            await query.edit_message_text("✅ Catatan judul berhasil ditambahkan ke datamu!")

        elif kategori == "todo":
            for item in items:
                add_todo(chat_id, item['task'])
            await query.edit_message_text("✅ Tugas berhasil ditambahkan ke datamu!")

        hapus_konfirmasi(konfirmasi_id)

    elif action == "no":
        hapus_konfirmasi(konfirmasi_id)
        await query.edit_message_text("❌ Data ditolak.")

# ===== SCHEDULER =====
async def post_init(application: Application):
    await application.bot.send_message(
        chat_id=CHAT_ID,
        text="👋 *Bot aktif!* Ketik /help untuk melihat daftar command.",
        parse_mode="Markdown"
    )

def setup_scheduler(app: Application):
    global scheduler
    tz = pytz.timezone(TIMEZONE)

    if scheduler and scheduler.running:
        scheduler.remove_all_jobs()
    else:
        scheduler = AsyncIOScheduler(timezone=tz)
        scheduler.start()

    bot = app.bot
    reminders = get_reminders(CHAT_ID)

    for r in reminders:
        try:
            jam, menit = r["time"].split(":")
            hari = DAY_MAP.get(r["days"], "mon,tue,wed,thu,fri,sat,sun")
            teks = r["text"]
            scheduler.add_job(
                kirim_pesan,
                CronTrigger(day_of_week=hari, hour=int(jam), minute=int(menit), timezone=tz),
                args=[bot, CHAT_ID, teks]
            )
            logging.info(f"Reminder terdaftar: [{r['days']} {r['time']}] {teks}")
        except Exception as e:
            logging.error(f"Skip reminder error: {r} — {e}")

    scheduler.add_job(
        setup_scheduler,
        CronTrigger(hour=0, minute=1, timezone=tz),
        args=[app]
    )

    logging.info(f"Scheduler diload ulang dengan {len(reminders)} reminder")
    return scheduler

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("tambah", tambah),
            CommandHandler("hapus", hapus),
            CommandHandler("edit", edit),
            CommandHandler("checktodos", check_todos),
            CommandHandler("buatgrup", buat_grup_cmd),
            CommandHandler("joingrup", join_grup_cmd),
            CommandHandler("keluargrup", keluar_grup_cmd),
            CommandHandler("kirim", kirim_cmd),
        ],
        states={
            TAMBAH_PILIH_KATEGORI: [CallbackQueryHandler(tambah_pilih_kategori, pattern="^tambah_")],
            TAMBAH_PILIH_HARI: [CallbackQueryHandler(tambah_pilih_hari, pattern="^tambahhari_")],
            TAMBAH_JAM_PESAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, tambah_jam_pesan)],
            TAMBAH_INPUT_CATAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tambah_terima_catat)],
            TAMBAH_INPUT_JUDUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, tambah_terima_judul)],
            TAMBAH_INPUT_ISI_JUDUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, tambah_terima_isi_judul)],
            TAMBAH_INPUT_TODO: [MessageHandler(filters.TEXT & ~filters.COMMAND, tambah_terima_todo)],
            HAPUS_PILIH_KATEGORI: [CallbackQueryHandler(hapus_pilih_kategori, pattern="^hapus_")],
            HAPUS_PILIH_NOMOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, hapus_pilih_nomor)],
            EDIT_PILIH_KATEGORI: [CallbackQueryHandler(edit_pilih_kategori, pattern="^edit_")],
            EDIT_PILIH_NOMOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_pilih_nomor)],
            EDIT_PILIH_FIELD: [CallbackQueryHandler(edit_pilih_field, pattern="^editfield_")],
            EDIT_PILIH_HARI: [CallbackQueryHandler(edit_pilih_hari_baru, pattern="^edithari_")],
            EDIT_INPUT_NILAI: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_input_nilai)],
            CHECK_TODOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi_check_todos)],
            GRUP_BUAT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, buat_grup_input)],
            GRUP_JOIN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, join_grup_input)],
            GRUP_KELUAR_PILIH: [CallbackQueryHandler(keluar_grup_pilih, pattern="^keluargrup_")],
            KIRIM_PILIH_KATEGORI: [CallbackQueryHandler(kirim_pilih_kategori, pattern="^kirim_")],
            KIRIM_PILIH_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, kirim_pilih_data)],
            KIRIM_PILIH_GRUP: [CallbackQueryHandler(kirim_pilih_grup, pattern="^kirimgrup_")],
            KIRIM_PILIH_MEMBER: [CallbackQueryHandler(kirim_pilih_member, pattern="^kirimmember_")],
        },
        fallbacks=[CommandHandler("batal", batal)],
        per_message=False,
        per_chat=True,
        conversation_timeout=60,
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_konfirmasi, pattern="^konfirmasi_"))  # tambah ini
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("lihatcatat", lihat_catat))
    app.add_handler(CommandHandler("lihatjudul", lihat_judul))
    app.add_handler(CommandHandler("listtodo", list_todo))
    app.add_handler(CommandHandler("infogrup", info_grup))

if __name__ == "__main__":
    main()