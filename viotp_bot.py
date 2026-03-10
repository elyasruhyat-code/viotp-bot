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
BOT_TOKEN     = "8665837848:AAGLLgN8-pbQkrzw-uA_krXqQxiERoGUL2A"
TIGER_API_KEY = "b3KBCkAmn65rZuUJYHyiobDiQkhufeTM"
# =============================================

BASE_URL  = "https://api.tiger-sms.com/stubs/handler_api.php"
SERVICE   = "wa"
DATA_FILE = "users.json"

COUNTRY = {
    "thailand":    52,
    "vietnam":     10,
    "philippines": 4,
}

COUNTRY_LABEL = {
    "thailand":    "🇹🇭 Thailand (+66)",
    "vietnam":     "🇻🇳 Vietnam (+84)",
    "philippines": "🇵🇭 Philippines (+63)",
}

user_sessions = {}

# ─── TIGER SMS API ───────────────────────────

def _api(params: dict) -> str:
    params["api_key"] = TIGER_API_KEY
    try:
        r = requests.get(BASE_URL, params=params, timeout=15)
        return r.text.strip()
    except Exception as e:
        return f"ERROR:{str(e)}"

def get_balance() -> dict:
    res = _api({"action": "getBalance"})
    if res.startswith("ACCESS_BALANCE:"):
        return {"success": True, "balance": res.split(":")[1]}
    return {"success": False, "msg": res}

def buy_number(country: int) -> dict:
    res = _api({"action": "getNumber", "service": SERVICE, "country": country, "ref": ""})
    if res.startswith("ACCESS_NUMBER:"):
        parts = res.split(":")
        return {"success": True, "activation_id": parts[1], "phone": parts[2]}
    errors = {
        "NO_NUMBERS":  "❌ Stok nomor habis, coba negara lain",
        "NO_BALANCE":  "❌ Saldo tidak cukup, silakan top up",
        "BAD_SERVICE": "❌ Kode service salah",
        "BAD_KEY":     "❌ API Key salah",
    }
    return {"success": False, "msg": errors.get(res, res)}

def get_otp(activation_id: str) -> dict:
    res = _api({"action": "getStatus", "id": activation_id})
    if res.startswith("STATUS_OK:"):
        return {"success": True, "otp": res.split(":")[1]}
    statuses = {
        "STATUS_WAIT_CODE":   "⏳ OTP belum masuk, tunggu sebentar",
        "STATUS_WAIT_RETRY":  "⏳ Menunggu SMS berikutnya",
        "STATUS_WAIT_RESEND": "⏳ Menunggu resend",
        "STATUS_CANCEL":      "❌ Aktivasi dibatalkan",
        "NO_ACTIVATION":      "❌ ID aktivasi tidak valid",
        "BAD_KEY":            "❌ API Key salah",
    }
    return {"success": False, "msg": statuses.get(res, res)}

def set_sms_sent(activation_id: str):
    _api({"action": "setStatus", "status": "1", "id": activation_id})

def request_new_sms(activation_id: str) -> dict:
    res = _api({"action": "setStatus", "status": "3", "id": activation_id})
    if res == "ACCESS_RETRY_GET":
        return {"success": True}
    return {"success": False, "msg": res}

def confirm(activation_id: str):
    _api({"action": "setStatus", "status": "6", "id": activation_id})

def cancel(activation_id: str) -> dict:
    res = _api({"action": "setStatus", "status": "8", "id": activation_id})
    if res == "ACCESS_CANCEL":
        return {"success": True}
    errors = {
        "EARLY_CANCEL_DENIED": "❌ Belum bisa cancel, tunggu 2 menit dulu",
        "NO_ACTIVATION":       "❌ ID aktivasi tidak valid",
        "BAD_KEY":             "❌ API Key salah",
    }
    return {"success": False, "msg": errors.get(res, res)}

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
    uid  = str(user_id)
    if uid not in data:
        data[uid] = {
            "user_id":       user_id,
            "username":      username or "tidak ada",
            "full_name":     full_name,
            "otp_success":   0,
            "otp_cancelled": 0,
            "total_buy":     0,
            "joined":        datetime.now().strftime("%d-%m-%Y %H:%M"),
            "last_active":   datetime.now().strftime("%d-%m-%Y %H:%M"),
        }
    else:
        data[uid]["username"]    = username or "tidak ada"
        data[uid]["full_name"]   = full_name
        data[uid]["last_active"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    save_data(data)
    return data[uid]

def increment_stat(user_id, field):
    data = load_data()
    uid  = str(user_id)
    if uid in data:
        data[uid][field] = data[uid].get(field, 0) + 1
        save_data(data)

# ─── KEYBOARD ────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Beli Nomor WhatsApp", callback_data="select_country")],
        [InlineKeyboardButton("👤 Profil Saya",         callback_data="profile"),
         InlineKeyboardButton("💰 Cek Saldo",           callback_data="balance")],
    ])

def country_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇹🇭 Thailand",    callback_data="buy_thailand")],
        [InlineKeyboardButton("🇻🇳 Vietnam",     callback_data="buy_vietnam")],
        [InlineKeyboardButton("🇵🇭 Philippines", callback_data="buy_philippines")],
        [InlineKeyboardButton("🏠 Menu Utama",   callback_data="menu")],
    ])

def after_buy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh OTP",    callback_data="refresh")],
        [InlineKeyboardButton("📨 Minta SMS Baru", callback_data="resend")],
        [InlineKeyboardButton("❌ Cancel Nomor",   callback_data="cancel")],
        [InlineKeyboardButton("🏠 Menu Utama",     callback_data="menu")],
    ])

def after_otp_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Beli Lagi",  callback_data="select_country")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")],
    ])

# ─── HANDLER ─────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        f"👋 Halo *{user.full_name}*!\n\n"
        f"Selamat datang di *TigerOTP Bot* 🐯\n"
        f"Bot ini membantu kamu beli nomor untuk verifikasi *WhatsApp*.\n\n"
        f"Tersedia: 🇹🇭 Thailand | 🇻🇳 Vietnam | 🇵🇭 Philippines\n\n"
        f"Pilih menu di bawah:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    user_id = user.id
    get_user(user_id, user.username, user.full_name)
    data = query.data

    if data == "menu":
        await query.edit_message_text(
            "🏠 *Menu Utama*\n\nPilih aksi:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif data == "select_country":
        await query.edit_message_text(
            "🌏 *Pilih Negara*\n\nMau nomor WhatsApp dari mana?",
            parse_mode="Markdown",
            reply_markup=country_keyboard()
        )

    elif data == "profile":
        all_data = load_data()
        uid = str(user_id)
        p   = all_data.get(uid, {})
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

    elif data == "balance":
        result = get_balance()
        saldo  = result["balance"] if result["success"] else "Error"
        await query.edit_message_text(
            f"💰 *Saldo Tiger-SMS:* `${saldo}`\n\nKembali ke menu:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif data in ("buy_thailand", "buy_vietnam", "buy_philippines"):
        country_key   = data.replace("buy_", "")
        country_code  = COUNTRY[country_key]
        country_label = COUNTRY_LABEL[country_key]

        await query.edit_message_text(f"⏳ Sedang membeli nomor {country_label}...")

        result = buy_number(country=country_code)

        if result["success"]:
            user_sessions[user_id] = {
                "activation_id": result["activation_id"],
                "phone":         result["phone"],
                "country":       country_label,
            }
            increment_stat(user_id, "total_buy")
            set_sms_sent(result["activation_id"])
            await query.edit_message_text(
                f"✅ *Nomor berhasil dibeli!*\n\n"
                f"🌏 *Negara:* {country_label}\n"
                f"📱 *Nomor:* `{result['phone']}`\n\n"
                f"Masukkan nomor ini ke WhatsApp,\n"
                f"lalu tekan *Refresh OTP* setelah minta kode.",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ *Gagal beli nomor!*\n\n{result['msg']}",
                parse_mode="Markdown",
                reply_markup=country_keyboard()
            )

    elif data == "refresh":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif. Silakan beli nomor dulu.",
                reply_markup=main_keyboard()
            )
            return

        result = get_otp(session["activation_id"])

        if result["success"]:
            increment_stat(user_id, "otp_success")
            confirm(session["activation_id"])
            user_sessions.pop(user_id, None)
            await query.edit_message_text(
                f"🎉 *OTP Masuk!*\n\n"
                f"🌏 *Negara:* {session['country']}\n"
                f"📱 *Nomor:* `{session['phone']}`\n"
                f"🔑 *OTP:* `{result['otp']}`\n\n"
                f"Salin kode di atas dan masukkan ke WhatsApp ✅",
                parse_mode="Markdown",
                reply_markup=after_otp_keyboard()
            )
        else:
            await query.edit_message_text(
                f"⏳ *OTP belum masuk...*\n\n"
                f"🌏 *Negara:* {session['country']}\n"
                f"📱 *Nomor:* `{session['phone']}`\n\n"
                f"{result['msg']}\n\n"
                f"Tekan *Refresh* lagi atau *Minta SMS Baru*.",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )

    elif data == "resend":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif.",
                reply_markup=main_keyboard()
            )
            return

        result = request_new_sms(session["activation_id"])
        if result["success"]:
            await query.edit_message_text(
                f"📨 *SMS baru sedang dikirim...*\n\n"
                f"📱 *Nomor:* `{session['phone']}`\n\n"
                f"Tekan *Refresh OTP* setelah beberapa detik.",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ Gagal minta SMS baru.\n{result['msg']}",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )

    elif data == "cancel":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif.",
                reply_markup=main_keyboard()
            )
            return

        result = cancel(session["activation_id"])
        user_sessions.pop(user_id, None)
        increment_stat(user_id, "otp_cancelled")

        if result["success"]:
            await query.edit_message_text(
                "✅ *Nomor berhasil di-cancel!*\n\nSaldo otomatis direfund jika OTP belum masuk.",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ Gagal cancel.\n{result['msg']}",
                parse_mode="Markdown",
                reply_markup=after_buy_keyboard()
            )

# ─── MAIN ────────────────────────────────────

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ TigerOTP Bot berjalan...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
