"""
╔══════════════════════════════════════════╗
║        TIGER SMS API WRAPPER             ║
║     Khusus WhatsApp - TH / VN / PH       ║
║  Tinggal import ke bot Telegram kamu!    ║
╚══════════════════════════════════════════╝

Cara import:
    from tigersms import TigerSMS, COUNTRY
    sms = TigerSMS("API_KEY_KAMU")

Contoh pakai:
    # Cek saldo
    sms.get_balance()

    # Beli nomor WhatsApp Thailand
    result = sms.buy_number(COUNTRY["thailand"])

    # Cek OTP
    sms.get_otp(activation_id)

    # Cancel
    sms.cancel(activation_id)

    # Konfirmasi berhasil
    sms.confirm(activation_id)

    # Minta SMS baru (gratis)
    sms.request_new_sms(activation_id)

    # Cek harga WhatsApp per negara
    sms.get_price(COUNTRY["thailand"])

    # Cek provider tersedia
    sms.get_providers(COUNTRY["thailand"])
"""

import requests

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
SERVICE  = "wa"  # Khusus WhatsApp

# ─── 3 NEGARA YANG DISEDIAKAN ────────────────
COUNTRY = {
    "thailand":    52,
    "vietnam":     10,
    "philippines": 4,
}

# ─── LABEL NEGARA UNTUK TAMPILAN BOT ─────────
COUNTRY_LABEL = {
    "thailand":    "🇹🇭 Thailand (+66)",
    "vietnam":     "🇻🇳 Vietnam (+84)",
    "philippines": "🇵🇭 Philippines (+63)",
}


class TigerSMS:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, params: dict) -> str:
        """Internal: kirim GET request ke tiger-sms"""
        params["api_key"] = self.api_key
        try:
            r = requests.get(BASE_URL, params=params, timeout=15)
            return r.text.strip()
        except Exception as e:
            return f"ERROR:{str(e)}"

    # ─────────────────────────────────────────
    # 1. CEK SALDO
    # Endpoint: ?action=getBalance
    # Response: ACCESS_BALANCE:80
    # ─────────────────────────────────────────
    def get_balance(self) -> dict:
        """Cek saldo akun tiger-sms"""
        res = self._get({"action": "getBalance"})
        if res.startswith("ACCESS_BALANCE:"):
            balance = res.split(":")[1]
            return {"success": True, "balance": balance}
        return {"success": False, "msg": res}

    # ─────────────────────────────────────────
    # 2. BELI NOMOR WHATSAPP
    # Endpoint: ?action=getNumber&service=wa&country=52&ref=
    # Response: ACCESS_NUMBER:activation_id:phone
    # ─────────────────────────────────────────
    def buy_number(self, country: int) -> dict:
        """
        Beli nomor WhatsApp.
        :param country: pakai COUNTRY["thailand"] / COUNTRY["vietnam"] / COUNTRY["philippines"]
        """
        res = self._get({
            "action":  "getNumber",
            "service": SERVICE,
            "country": country,
            "ref":     "",
        })
        if res.startswith("ACCESS_NUMBER:"):
            parts = res.split(":")
            return {
                "success":       True,
                "activation_id": parts[1],
                "phone":         parts[2],
            }
        errors = {
            "NO_NUMBERS":  "❌ Stok nomor habis, coba negara lain",
            "NO_BALANCE":  "❌ Saldo tidak cukup, silakan top up",
            "BAD_SERVICE": "❌ Kode service salah",
            "BAD_KEY":     "❌ API Key salah",
            "BAD_ACTION":  "❌ Action tidak valid",
            "ERROR_SQL":   "❌ Error server tiger-sms",
        }
        return {"success": False, "msg": errors.get(res, res)}

    # ─────────────────────────────────────────
    # 3. CEK OTP
    # Endpoint: ?action=getStatus&id=activation_id
    # Response sukses : STATUS_OK:123456
    # Response tunggu : STATUS_WAIT_CODE
    # ─────────────────────────────────────────
    def get_otp(self, activation_id: str) -> dict:
        """Cek apakah OTP sudah masuk"""
        res = self._get({
            "action": "getStatus",
            "id":     activation_id,
        })
        if res.startswith("STATUS_OK:"):
            otp = res.split(":")[1]
            return {"success": True, "otp": otp}
        statuses = {
            "STATUS_WAIT_CODE":   "⏳ OTP belum masuk, tunggu sebentar",
            "STATUS_WAIT_RETRY":  "⏳ Menunggu SMS berikutnya",
            "STATUS_WAIT_RESEND": "⏳ Menunggu resend",
            "STATUS_CANCEL":      "❌ Aktivasi dibatalkan",
            "STATUS_BANNED":      "❌ Nomor kena ban",
            "NO_ACTIVATION":      "❌ ID aktivasi tidak valid",
            "BAD_KEY":            "❌ API Key salah",
        }
        return {"success": False, "msg": statuses.get(res, res)}

    # ─────────────────────────────────────────
    # 4. BERITAHU SMS SUDAH DIKIRIM (opsional)
    # Endpoint: ?action=setStatus&status=1&id=activation_id
    # Response: ACCESS_READY
    # ─────────────────────────────────────────
    def set_sms_sent(self, activation_id: str) -> dict:
        """(Opsional) Beritahu tiger-sms bahwa SMS sudah dikirim ke nomor"""
        res = self._get({
            "action": "setStatus",
            "status": "1",
            "id":     activation_id,
        })
        if res == "ACCESS_READY":
            return {"success": True}
        return {"success": False, "msg": res}

    # ─────────────────────────────────────────
    # 5. MINTA SMS BARU (GRATIS)
    # Endpoint: ?action=setStatus&status=3&id=activation_id
    # Response: ACCESS_RETRY_GET
    # ─────────────────────────────────────────
    def request_new_sms(self, activation_id: str) -> dict:
        """Minta kirim ulang SMS OTP (gratis)"""
        res = self._get({
            "action": "setStatus",
            "status": "3",
            "id":     activation_id,
        })
        if res == "ACCESS_RETRY_GET":
            return {"success": True}
        return {"success": False, "msg": res}

    # ─────────────────────────────────────────
    # 6. KONFIRMASI OTP BERHASIL
    # Endpoint: ?action=setStatus&status=6&id=activation_id
    # Response: STATUS_OK
    # ─────────────────────────────────────────
    def confirm(self, activation_id: str) -> dict:
        """Konfirmasi OTP berhasil dipakai — wajib dipanggil setelah OTP sukses!"""
        res = self._get({
            "action": "setStatus",
            "status": "6",
            "id":     activation_id,
        })
        if res == "STATUS_OK":
            return {"success": True}
        return {"success": False, "msg": res}

    # ─────────────────────────────────────────
    # 7. CANCEL NOMOR
    # Endpoint: ?action=setStatus&status=8&id=activation_id
    # Response: ACCESS_CANCEL
    # ─────────────────────────────────────────
    def cancel(self, activation_id: str) -> dict:
        """Cancel nomor. Saldo direfund jika OTP belum masuk"""
        res = self._get({
            "action": "setStatus",
            "status": "8",
            "id":     activation_id,
        })
        if res == "ACCESS_CANCEL":
            return {"success": True}
        errors = {
            "EARLY_CANCEL_DENIED": "❌ Belum bisa cancel, tunggu 2 menit dulu",
            "NO_ACTIVATION":       "❌ ID aktivasi tidak valid",
            "BAD_KEY":             "❌ API Key salah",
            "BAD_STATUS":          "❌ Status tidak valid",
        }
        return {"success": False, "msg": errors.get(res, res)}

    # ─────────────────────────────────────────
    # 8. CEK HARGA WHATSAPP
    # Endpoint: ?action=getPrices&service=wa&country=52
    # ─────────────────────────────────────────
    def get_price(self, country: int) -> dict:
        """Cek harga nomor WhatsApp untuk negara tertentu"""
        res = self._get({
            "action":  "getPrices",
            "service": SERVICE,
            "country": country,
        })
        try:
            import json
            data = json.loads(res)
            return {"success": True, "data": data}
        except:
            return {"success": False, "msg": res}

    # ─────────────────────────────────────────
    # 9. CEK PROVIDER TERSEDIA
    # Endpoint: ?action=getProviders&service=wa&country=52
    # ─────────────────────────────────────────
    def get_providers(self, country: int) -> dict:
        """Cek provider/operator yang tersedia untuk negara tertentu"""
        res = self._get({
            "action":  "getProviders",
            "service": SERVICE,
            "country": country,
        })
        try:
            import json
            data = json.loads(res)
            return {"success": True, "data": data}
        except:
            return {"success": False, "msg": res}
