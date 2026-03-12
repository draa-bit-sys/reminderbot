import logging
import os
from telegram import Bot
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from sheets import get_reminders, add_reminder, delete_reminder

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

scheduler = None

async def kirim_pesan(bot: Bot, chat_id: str, teks: str):
    await bot.send_message(chat_id=chat_id, text=teks)
    logging.info(f"Terkirim: {teks}")

async def test(update, context):
    await update.message.reply_text("✅ Bot aktif dan berjalan!")

async def help_command(update, context):
    msg = """📋 *Daftar Command:*

/list - Lihat semua reminder
/tambah 08:00 daily Pesan - Tambah reminder baru
/hapus 1 - Hapus reminder nomor 1
/test - Cek bot aktif
/help - Tampilkan bantuan ini

*Hari yang tersedia:*
daily, mon, tue, wed, thu, fri, sat, sun"""
    await update.message.reply_text(msg, parse_mode="Markdown")

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
    try:
        raw = " ".join(context.args)
        items = raw.split(",")
        added = []

        for item in items:
            parts = item.strip().split(" ", 2)
            time = parts[0]
            days = parts[1]
            text = parts[2]
            add_reminder(time, days, text)
            added.append(f"⏰ {time} | {days} | {text}")

        setup_scheduler(context.application)
        msg = "✅ Reminder ditambahkan!\n\n" + "\n".join(added)
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text("❌ Format salah!\nGunakan:\n/tambah 08:00 daily Minum obat , 09:00 daily Olahraga")

async def hapus_reminder(update, context):
    try:
        indexes = [int(x.strip()) - 1 for x in " ".join(context.args).split(",")]
        indexes_sorted = sorted(indexes, reverse=True)  # hapus dari bawah biar index tidak geser
        reminders = get_reminders()
        deleted = []

        for index in indexes_sorted:
            deleted.append(reminders[index]['text'])
            delete_reminder(index)

        setup_scheduler(context.application)
        msg = "🗑️ Reminder dihapus:\n\n" + "\n".join(f"- {t}" for t in deleted)
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text("❌ Format salah!\nGunakan: /hapus 1,2,3")

async def post_init(application: Application):
    await application.bot.send_message(
        chat_id=CHAT_ID,
        text="""👋 *Bot Reminder aktif!*

📋 *Daftar Command:*

/list - Lihat semua reminder
/tambah 08:00 daily Pesan - Tambah reminder baru
/hapus 1 - Hapus reminder nomor 1
/test - Cek bot aktif
/help - Tampilkan bantuan ini

*Hari yang tersedia:*
daily, mon, tue, wed, thu, fri, sat, sun""",
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
        jam, menit = r["time"].split(":")
        hari = DAY_MAP.get(r["days"], "mon,tue,wed,thu,fri,sat,sun")
        teks = r["text"]

        scheduler.add_job(
            kirim_pesan,
            CronTrigger(day_of_week=hari, hour=int(jam), minute=int(menit), timezone=tz),
            args=[bot, CHAT_ID, teks]
        )
        logging.info(f"Reminder terdaftar: [{r['days']} {r['time']}] {teks}")

    # Reload otomatis tiap jam 00:01
    scheduler.add_job(
        setup_scheduler,
        CronTrigger(hour=0, minute=1, timezone=tz),
        args=[app]
    )

    logging.info(f"Scheduler diload ulang dengan {len(reminders)} reminder")
    return scheduler

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("tambah", tambah_reminder))
    app.add_handler(CommandHandler("hapus", hapus_reminder))
    setup_scheduler(app)
    logging.info("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()