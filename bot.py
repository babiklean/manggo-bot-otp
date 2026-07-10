import telebot
import requests
import time
from flask import Flask, request

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = '8949297325:AAGiHjc3vofVuoF8BLvS0-hEkjHr5cy5f88'
API_KEY = 'fp_19915397fd5a07b86362d9191f5c2af38003db0d767d2c74'  # GANTI DENGAN X-API-KEY FELIXPEDIA MILIKMU
BASE_URL = 'https://otpfastmurah.orderhostid.my.id/api/v1'

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
app = Flask(__name__)

# Penyimpanan status session user sementara (In-Memory)
user_sessions = {}

# Header untuk otentikasi API FelixPedia
headers = {
    'x-api-key': API_KEY,
    'Content-Type': 'application/json'
}

# ==================== TELEGRAM BOT LOGIC ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_sessions[message.chat.id] = {}  # Reset session
    
    menu_text = (
        "🥭 *MANGGO BOT DB — OTP SYSTEM v1.0* 🥭\n"
        "╭──────────────────────────────╮\n"
        "  📱 *ORDER PLATFORM BY :* @ethernoctt \n"
        "╰──────────────────────────────╯\n\n"
        "Selamat datang! Platform otomatis penyedia Nomor Kosong (Nokos) untuk verifikasi OTP.\n\n"
        "🛠️ *MENU UTAMA BOT:*\n"
        " ├ 💰 /balance - Cek sisa saldo API\n"
        " ├ 📦 /services - Mulai order nomor virtual\n"
        " └ ❌ /cancel\_order - Batalkan pesanan aktif\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 Silakan ketik /services untuk melihat daftar aplikasi yang tersedia."
    )
    bot.reply_to(message, menu_text, parse_mode="Markdown")


@bot.message_handler(commands=['balance'])
def check_balance(message):
    try:
        response = requests.get(f"{BASE_URL}/balance", headers=headers).json()
        if response.get('success'):
            text = (
                "💰 *REPORT UTILITY BALANCE*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                 f"👤 *Username :* `{response.get('username')}`\n"
                 f"💳 *Sisa Saldo:* `Rp {response.get('balance'):,}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Status: Koneksi API Terhubung dengan Baik ✅"
            )
        else:
            text = "❌ Gagal mengambil data saldo. Periksa x-api-key milikmu."
    except Exception as e:
        text = f"🚨 Terjadi kesalahan sistem: `{str(e)}`"
    
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=['services'])
def list_services(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        # Menembak endpoint daftar layanan server 1
        response = requests.get(f"{BASE_URL}/s1/nokos/services", headers=headers).json()
        if response.get('success') and response.get('data'):
            markup = telebot.types.InlineKeyboardMarkup()
            for service in response.get('data'):
                # Callback data format: svc_[code]_[name]
                callback_data = f"svc_{service['service_code']}_{service['service_name']}"
                markup.add(telebot.types.InlineKeyboardButton(text=f"🥭 {service['service_name']}", callback_data=callback_data))
            
            bot.reply_to(message, "📦 *PILIH LAYANAN APLIKASI:*", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Gagal memuat daftar layanan dari server.")
    except Exception as e:
        bot.reply_to(message, f"🚨 Error: `{str(e)}`")


@bot.callback_query_handler(func=lambda call: call.data.startswith('svc_'))
def handle_service_selection(call):
    chat_id = call.message.chat.id
    _, svc_code, svc_name = call.data.split('_')
    
    user_sessions[chat_id] = {
        'service_code': svc_code,
        'service_name': svc_name
    }
    
    bot.answer_callback_query(call.id, f"Memilih {svc_name}")
    
    # Lanjut mengambil daftar negara untuk layanan tersebut
    try:
        res = requests.get(f"{BASE_URL}/s1/nokos/countries?service_id={svc_code}", headers=headers).json()
        if res.get('success') and res.get('data'):
            markup = telebot.types.InlineKeyboardMarkup()
            for country in res.get('data'):
                # Batasi tampilan hanya yang ready stok saja
                if country['stock_total'] > 0:
                    # Callback data format: ctry_[id]_[name]
                    cb_data = f"ctry_{country['number_id']}_{country['name']}"
                    btn_text = f"🌐 {country['name']} ({country['prefix']}) — Rp {country['price_with_markup']}"
                    markup.add(telebot.types.InlineKeyboardButton(text=btn_text, callback_data=cb_data))
            
            bot.edit_message_text(f"🌍 *PILIH NEGARA ASAL NOMOR ({svc_name}):*", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Stok negara untuk layanan ini sedang kosong.", chat_id, call.message.message_id)
    except Exception as e:
        bot.send_message(chat_id, f"🚨 Error: `{str(e)}`")


@bot.callback_query_handler(func=lambda call: call.data.startswith('ctry_'))
def handle_country_selection(call):
    chat_id = call.message.chat.id
    _, ctry_id, ctry_name = call.data.split('_')
    
    if chat_id not in user_sessions or 'service_code' not in user_sessions[chat_id]:
        bot.send_message(chat_id, "🚨 Sesi kedaluwarsa, silakan ketik /services ulang.")
        return
        
    user_sessions[chat_id]['country_id'] = int(ctry_id)
    user_sessions[chat_id]['country_name'] = ctry_name
    
    svc_code = user_sessions[chat_id]['service_code']
    
    bot.answer_callback_query(call.id, f"Memilih {ctry_name}")
    
    # Ambil info operator dan harga pas
    try:
        res = requests.get(f"{BASE_URL}/s1/nokos/numbers?country_id={ctry_id}&service_id={svc_code}", headers=headers).json()
        if res.get('success') and res.get('data'):
            markup = telebot.types.InlineKeyboardMarkup()
            
            # Ambil item pertama sebagai perwakilan operator otomatis
            op_data = res.get('data')[0]
            cb_data = f"buy_{op_data['provider_id']}_{op_data['operator_id']}_{op_data['price']}"
            
            markup.add(telebot.types.InlineKeyboardButton(text="🛒 KLIK UNTUK BELI SEKARANG", callback_data=cb_data))
            
            detail_text = (
                "📋 *KONFIRMASI DETAIL ORDER NOCO:* \n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 *Aplikasi :* `{user_sessions[chat_id]['service_name']}`\n"
                f"🌍 *Negara   :* `{ctry_name}`\n"
                f"📶 *Operator :* `{op_data['operator_name'].upper()}`\n"
                f"💰 *Harga    :* `Rp {op_data['price_with_markup']}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sistem akan otomatis memotong saldo akun API utama kamu."
            )
            bot.edit_message_text(detail_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Gagal mendapatkan detail operator nomor.", chat_id, call.message.message_id)
    except Exception as e:
        bot.send_message(chat_id, f"🚨 Error: `{str(e)}`")


@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_purchase(call):
    chat_id = call.message.chat.id
    _, provider_id, operator_id, price_original = call.data.split('_')
    
    if chat_id not in user_sessions or 'service_code' not in user_sessions[chat_id]:
        bot.send_message(chat_id, "🚨 Sesi pesanan hilang, silakan ulangi.")
        return
        
    session = user_sessions[chat_id]
    
    # Eksekusi payload order sesuai dokumentasi Server 1
    payload = {
        "service_code": str(session['service_code']),
        "service_name": str(session['service_name']),
        "country_id": int(session['country_id']),
        "country_name": str(session['country_name']),
        "provider_id": str(provider_id),
        "operator_id": str(operator_id),
        "price_original": int(price_original)
    }
    
    bot.edit_message_text("⚡ _Sedang memproses orderan ke server... Mohon tunggu._", chat_id, call.message.message_id, parse_mode="Markdown")
    
    try:
        res = requests.post(f"{BASE_URL}/s1/nokos/order", json=payload, headers=headers).json()
        if res.get('success') and res.get('order'):
            order_info = res.get('order')
            order_id = order_info['id']
            phone_num = order_info['phone_number']
            
            # Simpan ID order aktif ke session user
            user_sessions[chat_id]['active_order_id'] = order_id
            
            success_text = (
                "✅ *NOMOR VIRTUAL BERHASIL DIDAPATKAN!*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *ID Order :* `{order_id}`\n"
                f"📱 *No HP    :* `{phone_num}`\n"
                f"💵 *Harga    :* `Rp {order_info['price']}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⏳ *STATUS OTP:* `Menunggu SMS Masuk...`\n\n"
                "Sistem otomatis mengecek kode OTP setiap 10 detik. Silakan masukkan nomor tersebut ke aplikasi target kamu sekarang."
            )
            bot.edit_message_text(success_text, chat_id, call.message.message_id, parse_mode="Markdown")
            
            # Memulai Polling Pengecekan OTP Otomatis (Maksimal 3 Menit/18 kali loop)
            loop_count = 0
            otp_found = False
            
            while loop_count < 18:
                time.sleep(10)
                loop_count += 1
                
                # Pastikan user belum membatalkan pesanan di tengah jalan
                if user_sessions.get(chat_id, {}).get('active_order_id') != order_id:
                    break
                    
                status_res = requests.get(f"{BASE_URL}/s1/nokos/status?order_id={order_id}", headers=headers).json()
                if status_res.get('success') and status_res.get('data'):
                    data_otp = status_res.get('data')
                    if data_otp.get('status') == 'received':
                        final_text = (
                            "🔥 *KODE OTP BERHASIL DITERIMA!* 🔥\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📱 *Nomor HP:* `{phone_num}`\n"
                            f"🔑 *KODE OTP:* `{data_otp.get('otp_code')}`\n"
                            f"📝 *Pesan   :* `{data_otp.get('otp_message')}`\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            "Transaksi Selesai. Terima kasih telah menggunakan Manggo Bot DB! 🥭"
                        )
                        bot.send_message(chat_id, final_text, parse_mode="Markdown")
                        otp_found = True
                        user_sessions[chat_id]['active_order_id'] = None
                        break
            
            if not otp_found and user_sessions.get(chat_id, {}).get('active_order_id') == order_id:
                timeout_text = (
                    "⏳ *WAKTU ORDER OTP HABIS*\n"
                    "SMS OTP tidak kunjung diterima dalam 3 menit.\n"
                    "Silakan ketik /cancel\_order untuk membatalkan transaksi dan mengembalikan saldo."
                )
                bot.send_message(chat_id, timeout_text, parse_mode="Markdown")
                
        else:
            bot.edit_message_text(f"❌ *Gagal melakukan order:* {res.get('message', 'Stok kosong atau saldo API tidak cukup.')}", chat_id, call.message.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"🚨 Error Pembelian: `{str(e)}`")


@bot.message_handler(commands=['cancel_order'])
def cancel_active_order(message):
    chat_id = message.chat.id
    order_id = user_sessions.get(chat_id, {}).get('active_order_id')
    
    if not order_id:
        bot.reply_to(message, "❌ Kamu tidak memiliki transaksi order nokos yang sedang aktif berjalan.")
        return
        
    payload = {"order_id": str(order_id)}
    try:
        res = requests.post(f"{BASE_URL}/s1/nokos/cancel", json=payload, headers=headers).json()
        if res.get('success'):
            user_sessions[chat_id]['active_order_id'] = None
            bot.reply_to(message, f"✅ *Sukses!* Order ID `{order_id}` telah dibatalkan, saldo kamu aman dan dikembalikan.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ *Gagal membatalkan:* {res.get('message', 'Minimal pembatalan adalah 10 menit sejak order dibuat sesuai aturan provider.')}")
    except Exception as e:
        bot.reply_to(message, f"🚨 Error Pembatalan: `{str(e)}`")

# ==================== VERCEL WEBHOOK ROUTING ====================

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Forbidden', 403

@app.route('/', methods=['GET'])
def index():
    return "Manggo Bot DB OTP Online!"
