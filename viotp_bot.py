import os
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ─── IMPORT TIGER SMS ────────────────────────
from tigersms import TigerSMS, COUNTRY, COUNTRY_LABEL

# =============================================
# KONFIGURASI - ISI BAGIAN INI
# =============================================
BOT_TOKEN      = "8665837848:AAGLLgN8-pbQkrzw-uA_krXqQxiERoGUL2A"
TIGER_API_KEY  = "b3KBCkAmn65rZuUJYHyiobDiQkhufeTM"
# =============================================

sms       = TigerSMS(TIGER_API_KEY)
DATA_FILE = "users.json"
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
    uid  = str(user_id)
    if uid not in data:
        data[uid] = {
            "user_id":      user_id,
            "username":     username or "tidak ada",
            "full_name":    full_name,
            "otp_success":  0,
            "otp_cancelled":0,
            "total_buy":    0,
            "joined":       datetime.now().strftime("%d-%m-%Y %H:%M"),
            "last_active":  datetime.now().strftime("%d-%m-%Y %H:%M"),
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
        [InlineKeyboardButton("🔄 Refresh OTP",      callback_data="refresh")],
        [InlineKeyboardButton("📨 Minta SMS Baru",   callback_data="resend")],
        [InlineKeyboardButton("❌ Cancel Nomor",     callback_data="cancel")],
        [InlineKeyboardButton("🏠 Menu Utama",       callback_data="menu")],
    ])

def after_otp_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Beli Lagi",        callback_data="select_country")],
        [InlineKeyboardButton("🏠 Menu Utama",       callback_data="menu")],
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

    # ── MENU UTAMA ──
    if data == "menu":
        await query.edit_message_text(
            "🏠 *Menu Utama*\n\nPilih aksi:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    # ── PILIH NEGARA ──
    elif data == "select_country":
        await query.edit_message_text(
            "🌏 *Pilih Negara*\n\nMau nomor WhatsApp dari mana?",
            parse_mode="Markdown",
            reply_markup=country_keyboard()
        )

    # ── PROFIL ──
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

    # ── CEK SALDO ──
    elif data == "balance":
        result = sms.get_balance()
        saldo  = result["balance"] if result["success"] else "Error"
        await query.edit_message_text(
            f"💰 *Saldo Tiger-SMS:* `${saldo}`\n\nKembali ke menu:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    # ── BELI NOMOR ──
    elif data in ("buy_thailand", "buy_vietnam", "buy_philippines"):
        country_key   = data.replace("buy_", "")
        country_code  = COUNTRY[country_key]
        country_label = COUNTRY_LABEL[country_key]

        await query.edit_message_text(f"⏳ Sedang membeli nomor {country_label}...")

        result = sms.buy_number(country=country_code)

        if result["success"]:
            user_sessions[user_id] = {
                "activation_id": result["activation_id"],
                "phone":         result["phone"],
                "country":       country_label,
            }
            increment_stat(user_id, "total_buy")
            # Opsional: beritahu tiger-sms bahwa SMS sudah dikirim
            sms.set_sms_sent(result["activation_id"])
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

    # ── REFRESH OTP ──
    elif data == "refresh":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif. Silakan beli nomor dulu.",
                reply_markup=main_keyboard()
            )
            return

        result = sms.get_otp(session["activation_id"])

        if result["success"]:
            increment_stat(user_id, "otp_success")
            sms.confirm(session["activation_id"])
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

    # ── MINTA SMS BARU ──
    elif data == "resend":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif.",
                reply_markup=main_keyboard()
            )
            return

        result = sms.request_new_sms(session["activation_id"])
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

    # ── CANCEL ──
    elif data == "cancel":
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text(
                "⚠️ Tidak ada sesi aktif.",
                reply_markup=main_keyboard()
            )
            return

        result = sms.cancel(session["activation_id"])
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

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ TigerOTP Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
