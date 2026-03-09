import os
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# =============================================
# KONFIGURASI - ISI BAGIAN INI
# =============================================
BOT_TOKEN = "8665837848:AAGLLgN8-pbQkrzw-uA_krXqQxiERoGUL2A"
VIOTP_API_KEY = "ae73cc1bdf5c48c7a54346a87422ff47"
# =============================================

BASE_URL = "https://api.viotp.com"
WHATSAPP_SERVICE_ID = "1"  # Cek di dashboard viotp.com
COUNTRY = "vn"             # Vietnam
DATA_FILE = "users.json"   # File penyimpanan data user

# Simpan sesi aktif per user
user_sessions = {}

# ─── DATABASE JSON ───────────────────────────

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user(user_id, username, full_name):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "user_id": user_id,
            "username": username or "tidak ada",
            "full_name": full_name,
            "otp_success": 0,
            "otp_cancelled": 0,
            "total_buy": 0,
            "joined": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "last_active": datetime.now().strftime("%d-%m-%Y %H:%M"),
        }
    else:
        data[uid]["username"] = username or "tidak ada"
        data[uid]["full_name"] = full_name
        data[uid]["last_active"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    save_data(data)
    return data[uid]

def increment_stat(user_id, field):
    data = load_data()
    uid = str(user_id)
    if uid in data:
        data[uid][field] = data[uid].get(field, 0) + 1
        save_data(data)

# ─── FUNGSI API VIOTP ────────────────────────

def get_balance():
    try:
        r = requests.get(f"{BASE_URL}/users/balance", params={"token": VIOTP_API_KEY}, timeout=10)
        data = r.json()
        return data.get("data", {}).get("balance", "?")
    except:
        return "Error"

def buy_number():
    try:
        r = requests.get(
            f"{BASE_URL}/request/get",
            params={
                "token": VIOTP_API_KEY,
                "serviceId": WHATSAPP_SERVICE_ID,
                "country": COUNTRY,
            },
            timeout=15
        )
        data = r.json()
        if data.get("status") == 200:
            return {
                "success": True,
                "request_id": data["data"]["requestId"],
                "phone": data["data"]["phoneNumber"],
            }
        else:
            return {"success": False, "msg": data.get("message", "Gagal beli nomor")}
    except Exception as e:
        return {"success": False, "msg": str(e)}

def check_otp(request_id):
    try:
        r = requests.get(
            f"{BASE_URL}/session/get",
            params={"token": VIOTP_API_KEY, "requestId": request_id},
            timeout=10
        )
        data = r.json()
        if data.get("status") == 200:
            sms = data["data"].get("sms", "")
            if sms:
                return {"success": True, "otp": sms}
            else:
                return {"success": False, "msg": "OTP belum masuk"}
        else:
            return {"success": False, "msg": data.get("message", "Belum ada OTP")}
    except Exception as e:
        return {"success": False, "msg": str(e)}

def cancel_number(request_id):
    try:
        r = requests.get(
            f"{BASE_URL}/request/cancel",
            params={"token": VIOTP_API_KEY, "requestId": request_id},
            timeout=10
        )
        data = r.json()
        return data.get("status") == 200
    except:
        return False

# ─── KEYBOARD ────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Beli Nomor WhatsApp VN", callback_data="buy")],
        [InlineKeyboardButton("👤 Profil Saya", callback_data="profile"),
         InlineKeyboardButton("💰 Cek Saldo", callback_data="balance")],
    ])

def after_buy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh OTP", callback_data="refresh")],
        [InlineKeyboardButton("❌ Cancel Nomor", callback_data="cancel")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")],
    ])

def after_otp_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Beli Lagi", callback_data="buy")],
        [InlineKeyboardButton("❌ Delete / Cancel", callback_data="cancel")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")],
    ])

# ─── HANDLER ─────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        f"👋 Halo *{user.full_name}*!\n\n"
        f"Selamat datang di *VioOTP Bot* 🤖\n"
        f"Bot ini membantu kamu beli nomor Vietnam untuk verifikasi WhatsApp.\n\n"
        f"Pilih menu di bawah:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id

    get_user(user_id, user.username, user.full_name)
    data = query.data

    # ── MENU UTAMA ──
    if data == "menu":
        await query.edit_message_text(
            "🏠 *Menu Utama*\n\nPilih aksi:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    # ── PROFIL ──
    elif data == "profile":
        all_data = load_data()
        uid = str(user_id)
        p = all_data.get(uid, {})
        username_display = f"@{p.get('username')}" if p.get('username') != 'tidak ada' else 'tidak ada'
        await query.edit_message_text(
            f"👤 *Profil Kamu*\n\n"
            f"🪪 *Nama:* {p.get('full_name', '-')}\n"
            f"🔖 *Username:* {username_display}\n"
            f"🆔 *Telegram ID:* `{user_id}`\n\n"
            f"📊 *Statistik:*\n"
            f"├ 🛒 Total beli nomor : *{p.get('total_buy', 0)}x*\n"
            f"├ ✅ OTP berhasil     : *{p.get('otp_success', 0)}x*\n"
            f"└ ❌ Dibatalkan       : *{p.get('otp_cancelled', 0)}x*\n\n"
            f"📅 *Bergabung:* {p.get('joined', '-')}\n"
            f"🕐 *Terakhir aktif:* {p.get('last_active', '-')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]
            ])
        )

    # ── CEK SALDO ──
    elif data == "balance":
        saldo = get_balance()
        await query.edit_message_text(
            f"💰 *Saldo viotp:* `{saldo}` VND\n\nKembali ke menu:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    # ── BELI NOMOR ──
    elif data == "buy":
        await query.edit_message_text("⏳ Sedang membeli nomor, tunggu sebentar...")
        result = buy_number()

        if result["success"]:
            user_sessions[user_id] = {
                "request_id": result["request_id"],
                "phone": result["phone"],
            }
            increment_stat(user_id, "total_buy")
            await query.edit_message_text(
                f"✅ *Nomor berhasil dibeli!*\n\n"
                f"📱 *Nomor:* `{result['phone']}`\n"
                f"🆔 *Request ID:* `{result['request_id']}`\n\n"
                f"Masukkan nomor ini ke WhatsApp,\nlalu tekan *Refresh OTP* setelah minta kode.",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ *Gagal beli nomor!*\n\nError: `{result['msg']}`",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

    # ── REFRESH OTP ──
    elif data == "refresh":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif. Silakan beli nomor dulu.",
                reply_markup=main_keyboard()
            )
            return

        result = check_otp(session["request_id"])

        if result["success"]:
            increment_stat(user_id, "otp_success")
            user_sessions.pop(user_id, None)
            await query.edit_message_text(
                f"🎉 *OTP Masuk!*\n\n"
                f"📱 *Nomor:* `{session['phone']}`\n"
                f"🔑 *OTP:* `{result['otp']}`\n\n"
                f"Salin kode di atas dan masukkan ke WhatsApp ✅",
                parse_mode="Markdown",
                reply_markup=after_otp_keyboard()
            )
        else:
            await query.edit_message_text(
                f"⏳ *OTP belum masuk...*\n\n"
                f"📱 *Nomor:* `{session['phone']}`\n\n"
                f"Tekan *Refresh* lagi setelah beberapa detik.",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )

    # ── CANCEL ──
    elif data == "cancel":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif.",
                reply_markup=main_keyboard()
            )
            return

        success = cancel_number(session["request_id"])
        user_sessions.pop(user_id, None)
        increment_stat(user_id, "otp_cancelled")

        if success:
            await query.edit_message_text(
                "✅ *Nomor berhasil di-cancel!*\n\nSaldo otomatis direfund jika OTP belum masuk.",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Gagal cancel. Coba lagi atau hubungi admin.",
                reply_markup=main_keyboard()
            )

# ─── MAIN ────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ VioOTP Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
