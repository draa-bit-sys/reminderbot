import logging
import os
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
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

async def kirim_pesan(bot: Bot, chat_id: str, teks: str):
    await bot.send_message(chat_id=chat_id, text=teks)
    logging.info(f"Terkirim: {teks}")

async def test(update, context):
    await update.message.reply_text("✅ Bot aktif dan berjalan!")

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
        # Format: /tambah 08:00 daily Minum obat
        args = context.args
        time = args[0]
        days = args[1]
        text = " ".join(args[2:])
        add_reminder(time, days, text)
        await update.message.reply_text(f"✅ Reminder ditambahkan!\n⏰ {time} | {days} | {text}")
    except Exception as e:
        await update.message.reply_text("❌ Format salah!\nGunakan: /tambah 08:00 daily Minum obat")

async def hapus_reminder(update, context):
    try:
        index = int(context.args[0]) - 1
        reminders = get_reminders()
        teks = reminders[index]['text']
        delete_reminder(index)
        await update.message.reply_text(f"🗑️ Reminder '{teks}' dihapus!")
    except Exception as e:
        await update.message.reply_text("❌ Format salah!\nGunakan: /hapus 1")

def setup_scheduler(app: Application):
    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)
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

    scheduler.start()
    return scheduler

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("tambah", tambah_reminder))
    app.add_handler(CommandHandler("hapus", hapus_reminder))
    setup_scheduler(app)
    logging.info("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()


## Step 7: Tambah Variables di Railway

# Buka Railway → **Variables** → tambahkan:
# ```
# SHEET_ID = ID_spreadsheet_kamu
# GOOGLE_CREDS = (isi dengan isi file JSON service account, semua dalam 1 baris)