import requests
import logging
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================

BOT_TOKEN = "8665837848:AAGLLgN8-pbQkrzw-uA_krXqQxiERoGUL2A"
VIOTP_API_KEY = "ae73cc1bdf5c48c7a54346a87422ff47"

# ================= MENU =================

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📱 Beli Nomor Vietnam", callback_data="buy")],
        [InlineKeyboardButton("📦 Cek OTP", callback_data="otp")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        message = update.effective_message

        await message.reply_text(
            f"👋 Halo {user.first_name}\n\n"
            f"Bot OTP Vietnam siap digunakan.\n"
            f"Silakan pilih menu:",
            reply_markup=main_menu()
        )

    except Exception as e:
        print("ERROR START:", e)

# ================= API =================

def buy_number():

    try:

        url = "https://api.viotp.com/request/getvietnam"

        params = {
            "token": VIOTP_API_KEY,
            "service": "whatsapp"
        }

        r = requests.get(url, params=params, timeout=15)

        return r.json()

    except:
        return {"status": "error"}


def check_otp(request_id):

    try:

        url = "https://api.viotp.com/session/get"

        params = {
            "token": VIOTP_API_KEY,
            "request_id": request_id
        }

        r = requests.get(url, params=params, timeout=15)

        return r.json()

    except:
        return {"status": "error"}

# ================= BUTTON =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "buy":

            await query.edit_message_text("⏳ Membeli nomor...")

            result = buy_number()

            if result.get("status") == "success":

                phone = result.get("phone")
                request_id = result.get("request_id")

                context.user_data["request_id"] = request_id

                await query.edit_message_text(
                    f"📱 Nomor Vietnam:\n\n"
                    f"`{phone}`\n\n"
                    f"Gunakan untuk daftar WhatsApp.\n"
                    f"Setelah itu tekan *Cek OTP*.",
                    parse_mode="Markdown"
                )

            else:

                await query.edit_message_text(
                    "❌ Nomor tidak tersedia atau API error"
                )

        elif data == "otp":

            request_id = context.user_data.get("request_id")

            if not request_id:

                await query.edit_message_text(
                    "❌ Kamu belum membeli nomor."
                )
                return

            await query.edit_message_text("⏳ Mengecek OTP...")

            for i in range(20):

                result = check_otp(request_id)

                if result.get("status") == "success":

                    code = result.get("code")

                    await query.edit_message_text(
                        f"✅ OTP diterima\n\n`{code}`",
                        parse_mode="Markdown"
                    )

                    return

                await asyncio.sleep(5)

            await query.edit_message_text(
                "❌ OTP tidak diterima."
            )

    except Exception as e:

        print("ERROR BUTTON:", e)

# ================= ERROR HANDLER =================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("GLOBAL ERROR:", context.error)

# ================= MAIN =================

def main():

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_error_handler(error_handler)

    print("Bot berjalan...")

    app.run_polling()

if __name__ == "__main__":
    main()
