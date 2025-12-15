from telegram.ext import Application, CommandHandler

TOKEN = "7994641332:AAFNNiYP475qYyWl5AOjR8UPaNmVpME9ZWs"

async def start(update, context):
    chat_id = update.effective_chat.id
    msg = f"👋 Ciao! Il tuo chat_id è: {chat_id}"
    print(msg)
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot avviato. Invia /start al bot su Telegram.")
    app.run_polling()

if __name__ == "__main__":
    main()
