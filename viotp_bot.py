import requests
import logging
import asyncio
import os

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

    user = update.effective_user

    await update.message.reply_text(
        f"👋 Halo {user.first_name}\n\n"
        f"Bot OTP Vietnam siap digunakan.\n"
        f"Pilih menu di bawah.",
        reply_markup=main_menu()
    )

# ================= API =================

def buy_number():

    url = "https://api.viotp.com/request/getvietnam"

    params = {
        "token": VIOTP_API_KEY,
        "service": "whatsapp"
    }

    r = requests.get(url, params=params)

    return r.json()


def get_otp(request_id):

    url = "https://api.viotp.com/session/get"

    params = {
        "token": VIOTP_API_KEY,
        "request_id": request_id
    }

    r = requests.get(url, params=params)

    return r.json()

# ================= BUTTON =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "buy":

        await query.edit_message_text("⏳ Membeli nomor...")

        try:

            result = buy_number()

            if result["status"] == "success":

                phone = result["phone"]
                request_id = result["request_id"]

                context.user_data["request_id"] = request_id

                await query.edit_message_text(
                    f"📱 Nomor Vietnam:\n\n"
                    f"`{phone}`\n\n"
                    f"Gunakan untuk daftar WhatsApp.\n"
                    f"Lalu tekan tombol Cek OTP.",
                    parse_mode="Markdown"
                )

            else:

                await query.edit_message_text("❌ Nomor tidak tersedia")

        except Exception as e:

            await query.edit_message_text("⚠️ Error mengambil nomor")

    if data == "otp":

        request_id = context.user_data.get("request_id")

        if not request_id:

            await query.edit_message_text(
                "❌ Kamu belum membeli nomor."
            )
            return

        await query.edit_message_text("⏳ Mengecek OTP...")

        for i in range(20):

            result = get_otp(request_id)

            if result["status"] == "success":

                code = result["code"]

                await query.edit_message_text(
                    f"✅ OTP Diterima\n\n"
                    f"`{code}`",
                    parse_mode="Markdown"
                )

                return

            await asyncio.sleep(5)

        await query.edit_message_text(
            "❌ OTP tidak diterima."
        )

# ================= ERROR =================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    logging.error(msg="Exception while handling update:", exc_info=context.error)

# ================= MAIN =================

def main():

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(
