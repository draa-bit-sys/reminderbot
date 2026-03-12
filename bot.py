import logging
import os
from telegram import Bot
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from reminders import REMINDERS

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

def setup_scheduler(app: Application):
    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)
    bot = app.bot

    for r in REMINDERS:
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
    setup_scheduler(app)
    logging.info("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()