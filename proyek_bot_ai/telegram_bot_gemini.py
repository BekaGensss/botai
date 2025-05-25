import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- KONFIGURASI ---
# GANTI DENGAN TOKEN API BOT TELEGRAM ANDA!
TELEGRAM_BOT_TOKEN = "7293315460:AAG_YcM4tdfaf6XjpgwtzKqe5Jabpggtw1c"

# GANTI DENGAN API KEY GEMINI ANDA!
GEMINI_API_KEY = "AIzaSyDwOfyboBVgFuXQcIuYtOjP0_88XCkSZ_c"

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Konfigurasi Model Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Pilih model Gemini yang sesuai. 'gemini-1.5-flash' adalah pilihan yang cepat dan efisien.
    # Anda bisa juga menggunakan 'gemini-pro'.
    # Menambahkan system instruction agar bot memiliki persona tertentu
    model_gemini = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction="Kamu adalah bot Telegram yang ramah, membantu, dan sedikit ceria. Jawablah pertanyaan pengguna dengan informatif dan bersahabat dalam bahasa Indonesia."
    )
    logger.info("Model Gemini berhasil dikonfigurasi.")
except Exception as e:
    logger.error(f"Error konfigurasi Gemini API: {e}. Pastikan API Key Anda benar dan pustaka terinstal.")
    model_gemini = None # Set ke None jika gagal agar bot tidak crash saat mencoba menggunakannya


# --- Logika "AI" dengan Gemini ---
async def get_gemini_response(user_text: str, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Menghasilkan respons bot menggunakan Gemini API, dengan manajemen histori sederhana."""
    if not model_gemini:
        return "Maaf, layanan AI sedang tidak tersedia. Coba beberapa saat lagi."

    # Inisialisasi histori chat untuk pengguna jika belum ada
    if 'chat_histories' not in context.bot_data:
        context.bot_data['chat_histories'] = {}
    if user_id not in context.bot_data['chat_histories']:
        context.bot_data['chat_histories'][user_id] = model_gemini.start_chat(history=[])
        logger.info(f"Membuat sesi chat baru untuk pengguna {user_id}")

    chat_session = context.bot_data['chat_histories'][user_id]

    try:
        logger.info(f"Mengirim ke Gemini untuk user {user_id}: '{user_text}'")
        # Mengirim pesan ke Gemini dan mendapatkan respons
        # Penting: Pustaka google-generativeai versi terbaru mungkin memiliki method send_message_async
        # Jika tidak, kita perlu menjalankannya di executor terpisah agar tidak memblokir loop asyncio telegram
        # Untuk saat ini, kita asumsikan ada cara async atau kita handle blocking di production
        
        # Untuk library google-generativeai yang mendukung async secara langsung:
        response = await chat_session.send_message_async(user_text)
        
        # Jika library tidak native async untuk send_message, ini cara untuk menjalankan fungsi sync di async:
        # loop = asyncio.get_running_loop()
        # response = await loop.run_in_executor(None, chat_session.send_message, user_text)

        logger.info(f"Respons dari Gemini untuk user {user_id}: '{response.text}'")
        return response.text
    except Exception as e:
        logger.error(f"Error saat memanggil Gemini API untuk user {user_id}: {e}")
        # Jika ada error, coba reset histori chat untuk pengguna ini agar tidak error terus-menerus
        # context.bot_data['chat_histories'][user_id] = model_gemini.start_chat(history=[])
        # logger.info(f"Histori chat untuk user {user_id} direset karena error.")
        return "Maaf, terjadi sedikit gangguan saat saya mencoba berpikir. Bisa ulangi pertanyaanmu?"

# --- Handler untuk Perintah ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan ketika perintah /start dikeluarkan."""
    user = update.effective_user
    # Reset histori chat pengguna saat /start
    if 'chat_histories' in context.bot_data and user.id in context.bot_data['chat_histories']:
        del context.bot_data['chat_histories'][user.id]
        logger.info(f"Histori chat untuk pengguna {user.id} direset karena perintah /start.")

    await update.message.reply_html(
        rf"Halo {user.mention_html()}! Saya adalah bot AI yang didukung oleh Gemini. "
        "Silakan ajukan pertanyaan atau ajak saya mengobrol!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan ketika perintah /help dikeluarkan."""
    help_text = (
        "Saya bot AI yang didukung Gemini. Anda bisa:\n"
        "- Mengobrol dengan saya tentang topik apa pun.\n"
        "- Mengajukan pertanyaan.\n\n"
        "Perintah yang tersedia:\n"
        "/start - Memulai/mereset percakapan dengan saya\n"
        "/help - Menampilkan pesan bantuan ini\n"
        "/clear - Menghapus histori percakapan kita (jika Anda merasa respons saya aneh)"
    )
    await update.message.reply_text(help_text)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menghapus histori percakapan pengguna."""
    user_id = update.effective_user.id
    if 'chat_histories' in context.bot_data and user_id in context.bot_data['chat_histories']:
        del context.bot_data['chat_histories'][user_id]
        await update.message.reply_text("Histori percakapan kita sudah saya lupakan. Mari mulai dari awal!")
        logger.info(f"Histori chat untuk pengguna {user_id} dihapus dengan perintah /clear.")
    else:
        await update.message.reply_text("Tidak ada histori percakapan yang perlu dihapus.")


# --- Handler untuk Pesan Teks Biasa ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani pesan teks biasa dari pengguna dan meresponsnya menggunakan Gemini."""
    user_id = update.effective_user.id
    text = update.message.text

    logger.info(f'Pengguna ({user_id}): "{text}"')

    # Dapatkan respons dari logika Gemini kita
    # Memberitahu pengguna bahwa bot sedang "berpikir"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    response_text = await get_gemini_response(text, user_id, context)
    
    await update.message.reply_text(response_text)

# --- Handler untuk Error ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencatat error yang disebabkan oleh Update."""
    logger.error(f"Update {update} menyebabkan error {context.error}", exc_info=context.error)


def main() -> None:
    """Memulai bot."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "TOKEN_API_TELEGRAM_ANDA":
        logger.error("TOKEN_API_TELEGRAM_ANDA belum diatur! Bot tidak bisa dijalankan.")
        return
    if not GEMINI_API_KEY or GEMINI_API_KEY == "API_KEY_GEMINI_ANDA":
        logger.error("API_KEY_GEMINI_ANDA belum diatur! Bot mungkin tidak bisa menggunakan AI Gemini.")
        # Kita bisa memilih untuk tetap menjalankan bot dengan fungsionalitas terbatas
        # atau menghentikannya. Untuk sekarang, kita biarkan berjalan agar perintah lokal tetap bisa.
    if not model_gemini:
         logger.warning("Model Gemini tidak terinisialisasi. Bot akan memiliki fungsionalitas AI terbatas.")


    logger.info("Memulai bot dengan integrasi Gemini...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Daftarkan handler untuk berbagai perintah
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))

    # Daftarkan handler untuk pesan teks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Daftarkan error handler
    application.add_error_handler(error_handler)

    # Simpan data bot (untuk histori chat)
    # Ini adalah penyimpanan sederhana dalam memori. Untuk produksi, pertimbangkan database.
    application.bot_data = {}


    logger.info("Bot sedang berjalan. Tekan Ctrl-C untuk menghentikan.")
    application.run_polling()

if __name__ == "__main__":
    main()