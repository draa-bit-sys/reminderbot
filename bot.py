import logging
import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from sheets import (
    get_reminders, add_reminder, delete_reminder,
    get_notes, add_note, delete_note,
    get_titled_notes, add_titled_note, delete_titled_note,
    get_todos, add_todo, complete_todo, delete_todo
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

# ConversationHandler states
PILIH_HARI, TUNGGU_JAM_PESAN = range(2)

async def kirim_pesan(bot: Bot, chat_id: str, teks: str):
    await bot.send_message(chat_id=chat_id, text=teks)
    logging.info(f"Terkirim: {teks}")

# ===== GENERAL =====
async def test(update, context):
    await update.message.reply_text("✅ Bot aktif dan berjalan!")

async def help_command(update, context):
    msg = """📋 *Daftar Command:*

*Reminder:*
/list - Lihat semua reminder
/tambah - Tambah reminder (tombol hari)
/tambah 08:00 daily Pesan , 09:00 daily Pesan - Tambah multiple
/hapus 1,2,3 - Hapus reminder

*Catatan Bebas:*
/catat Isi catatan - Tambah catatan
/lihatcatat - Lihat semua catatan
/hapuscatat 1,2,3 - Hapus catatan

*Catatan Judul & Isi:*
/catatjudul Judul | Isi catatan - Tambah catatan
/lihatjudul - Lihat semua catatan
/hapusjudul 1,2,3 - Hapus catatan

*To-Do List:*
/todo Nama tugas - Tambah tugas
/listtodo - Lihat semua tugas
/selesai 1,2,3 - Tandai selesai
/hapustodo 1,2,3 - Hapus tugas

/help - Tampilkan bantuan ini"""
    await update.message.reply_text(msg, parse_mode="Markdown")

# ===== REMINDER =====
async def list_reminders(update, context):
    reminders = get_reminders()
    if not reminders:
        await update.message.reply_text("Belum ada reminder.")
        return
    msg = "📋 *Daftar Reminder:*\n\n"
    for i, r in enumerate(reminders):
        msg += f"{i+1}. `{r['time']}` | `{r['days']}` | {r['text']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def tambah_reminder(update, context):
    # Kalau ada args, pakai format teks
    if context.args:
        try:
            raw = " ".join(context.args)
            items = raw.split(",")
            parsed = []

            for item in items:
                parts = item.strip().split(" ", 2)
                if len(parts) < 3:
                    await update.message.reply_text(
                        f"❌ Format salah di: `{item.strip()}`\n"
                        f"Gunakan: /tambah 08:00 daily Pesan , 09:00 daily Pesan",
                        parse_mode="Markdown"
                    )
                    return

                time, days, text = parts
                valid_days = ["daily", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                if days not in valid_days:
                    await update.message.reply_text(
                        f"❌ Hari `{days}` tidak valid!\n"
                        f"Hari yang tersedia: daily, mon, tue, wed, thu, fri, sat, sun",
                        parse_mode="Markdown"
                    )
                    return

                parsed.append((time, days, text))

            for time, days, text in parsed:
                add_reminder(time, days, text)

            setup_scheduler(context.application)
            added = [f"⏰ {t} | {d} | {tx}" for t, d, tx in parsed]
            await update.message.reply_text("✅ Reminder ditambahkan!\n\n" + "\n".join(added))

        except Exception as e:
            await update.message.reply_text("❌ Format salah!\nGunakan: /tambah 08:00 daily Minum obat")
        return ConversationHandler.END

    # Kalau tidak ada args, tampilkan tombol hari
    keyboard = [
        [InlineKeyboardButton("Setiap Hari", callback_data="hari_daily")],
        [
            InlineKeyboardButton("Senin", callback_data="hari_mon"),
            InlineKeyboardButton("Selasa", callback_data="hari_tue"),
            InlineKeyboardButton("Rabu", callback_data="hari_wed"),
            InlineKeyboardButton("Kamis", callback_data="hari_thu"),
        ],
        [
            InlineKeyboardButton("Jumat", callback_data="hari_fri"),
            InlineKeyboardButton("Sabtu", callback_data="hari_sat"),
            InlineKeyboardButton("Minggu", callback_data="hari_sun"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="hari_batal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📅 Pilih hari:", reply_markup=reply_markup)
    return PILIH_HARI

async def pilih_hari_callback(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "hari_batal":
        await query.edit_message_text("❌ Dibatalkan.")
        return ConversationHandler.END

    hari = query.data.replace("hari_", "")
    context.user_data["hari"] = hari
    label = DAY_LABELS.get(hari, hari)

    await query.edit_message_text(
        f"✅ Hari dipilih: *{label}*\n\nSekarang kirim jam dan pesan:\nFormat: `08:00 Minum obat`",
        parse_mode="Markdown"
    )
    return TUNGGU_JAM_PESAN

async def terima_jam_pesan(update, context):
    try:
        text = update.message.text.strip()
        parts = text.split(" ", 1)
        if len(parts) < 2:
            await update.message.reply_text("❌ Format salah!\nKirim: `08:00 Minum obat`", parse_mode="Markdown")
            return TUNGGU_JAM_PESAN

        time, pesan = parts
        hari = context.user_data.get("hari")
        label = DAY_LABELS.get(hari, hari)

        add_reminder(time, hari, pesan)
        setup_scheduler(context.application)

        await update.message.reply_text(
            f"✅ Reminder ditambahkan!\n\n⏰ {time} | {label} | {pesan}"
        )
    except Exception as e:
        await update.message.reply_text("❌ Terjadi error, coba lagi.")

    return ConversationHandler.END

async def hapus_reminder(update, context):
    try:
        indexes = sorted([int(x.strip()) - 1 for x in " ".join(context.args).split(",")], reverse=True)
        reminders = get_reminders()
        deleted = []
        for index in indexes:
            deleted.append(reminders[index]['text'])
            delete_reminder(index)
        setup_scheduler(context.application)
        await update.message.reply_text("🗑️ Reminder dihapus:\n\n" + "\n".join(f"- {t}" for t in deleted))
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /hapus 1,2,3")

# ===== CATATAN BEBAS =====
async def catat(update, context):
    try:
        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("❌ Catatan kosong!\nGunakan: /catat Isi catatan")
            return
        add_note(text)
        await update.message.reply_text(f"📝 Catatan disimpan!\n\n{text}")
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /catat Isi catatan")

async def lihat_catat(update, context):
    notes = get_notes()
    if not notes:
        await update.message.reply_text("Belum ada catatan.")
        return
    msg = "📝 *Catatan:*\n\n"
    for i, n in enumerate(notes):
        msg += f"{i+1}. {n['text']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hapus_catat(update, context):
    try:
        indexes = sorted([int(x.strip()) - 1 for x in " ".join(context.args).split(",")], reverse=True)
        notes = get_notes()
        deleted = []
        for index in indexes:
            deleted.append(notes[index]['text'])
            delete_note(index)
        await update.message.reply_text("🗑️ Catatan dihapus:\n\n" + "\n".join(f"- {t}" for t in deleted))
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /hapuscatat 1,2,3")

# ===== CATATAN JUDUL & ISI =====
async def catat_judul(update, context):
    try:
        raw = " ".join(context.args)
        if "|" not in raw:
            await update.message.reply_text("❌ Format salah!\nGunakan: /catatjudul Judul | Isi catatan")
            return
        title, content = raw.split("|", 1)
        add_titled_note(title.strip(), content.strip())
        await update.message.reply_text(f"📓 Catatan disimpan!\n\n*{title.strip()}*\n{content.strip()}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /catatjudul Judul | Isi catatan")

async def lihat_judul(update, context):
    notes = get_titled_notes()
    if not notes:
        await update.message.reply_text("Belum ada catatan.")
        return
    msg = "📓 *Catatan:*\n\n"
    for i, n in enumerate(notes):
        msg += f"{i+1}. *{n['title']}*\n{n['content']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hapus_judul(update, context):
    try:
        indexes = sorted([int(x.strip()) - 1 for x in " ".join(context.args).split(",")], reverse=True)
        notes = get_titled_notes()
        deleted = []
        for index in indexes:
            deleted.append(notes[index]['title'])
            delete_titled_note(index)
        await update.message.reply_text("🗑️ Catatan dihapus:\n\n" + "\n".join(f"- {t}" for t in deleted))
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /hapusjudul 1,2,3")

# ===== TO-DO LIST =====
async def todo(update, context):
    try:
        task = " ".join(context.args)
        if not task:
            await update.message.reply_text("❌ Tugas kosong!\nGunakan: /todo Nama tugas")
            return
        add_todo(task)
        await update.message.reply_text(f"✅ Tugas ditambahkan!\n\n❌ {task}")
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /todo Nama tugas")

async def list_todo(update, context):
    todos = get_todos()
    if not todos:
        await update.message.reply_text("Belum ada tugas.")
        return
    msg = "📌 *To-Do List:*\n\n"
    for i, t in enumerate(todos):
        msg += f"{i+1}. {t['status']} {t['task']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def selesai_todo(update, context):
    try:
        indexes = sorted([int(x.strip()) - 1 for x in " ".join(context.args).split(",")], reverse=True)
        todos = get_todos()
        done = []
        for index in indexes:
            complete_todo(index)
            done.append(todos[index]['task'])
        await update.message.reply_text("✅ Tugas selesai:\n\n" + "\n".join(f"- {t}" for t in done))
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /selesai 1,2,3")

async def hapus_todo(update, context):
    try:
        indexes = sorted([int(x.strip()) - 1 for x in " ".join(context.args).split(",")], reverse=True)
        todos = get_todos()
        deleted = []
        for index in indexes:
            deleted.append(todos[index]['task'])
            delete_todo(index)
        await update.message.reply_text("🗑️ Tugas dihapus:\n\n" + "\n".join(f"- {t}" for t in deleted))
    except:
        await update.message.reply_text("❌ Format salah!\nGunakan: /hapustodo 1,2,3")

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
    reminders = get_reminders()

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

    # ConversationHandler untuk /tambah dengan tombol
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("tambah", tambah_reminder)],
        states={
            PILIH_HARI: [CallbackQueryHandler(pilih_hari_callback, pattern="^hari_")],
            TUNGGU_JAM_PESAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, terima_jam_pesan)],
        },
        fallbacks=[CommandHandler("batal", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("hapus", hapus_reminder))
    app.add_handler(CommandHandler("catat", catat))
    app.add_handler(CommandHandler("lihatcatat", lihat_catat))
    app.add_handler(CommandHandler("hapuscatat", hapus_catat))
    app.add_handler(CommandHandler("catatjudul", catat_judul))
    app.add_handler(CommandHandler("lihatjudul", lihat_judul))
    app.add_handler(CommandHandler("hapusjudul", hapus_judul))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("listtodo", list_todo))
    app.add_handler(CommandHandler("selesai", selesai_todo))
    app.add_handler(CommandHandler("hapustodo", hapus_todo))
    setup_scheduler(app)
    logging.info("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()