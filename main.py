import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import start, handle_spotify, help_callback

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(help_callback, pattern="help"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_spotify))

if __name__ == "__main__":
    app.run_polling()
