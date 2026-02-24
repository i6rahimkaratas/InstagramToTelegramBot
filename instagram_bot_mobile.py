#!/usr/bin/env python3


import os
import re
import logging
import tempfile
import shutil
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import instaloader
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from config import TELEGRAM_BOT_TOKEN, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
except ImportError:
    logger.warning("config.py bulunamadı, environment variables kullanılıyor")
    import os
    TELEGRAM_BOT_TOKEN = os.getenv('i6rahimBot', '8698755439:AAG0rQrLM_NsZZ-RJvYs2ArXvt67j0mv1IQ')
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', '')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', '')

user_stats = {}

TEMP_FOLDER = tempfile.mkdtemp(prefix="instagram_bot_")

L = instaloader.Instaloader(
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    dirname_pattern=TEMP_FOLDER,
    filename_pattern='{shortcode}'
)

if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
    try:
        L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        logger.info("Instagram'a giriş yapıldı")
    except Exception as e:
        logger.warning(f"Instagram girişi başarısız: {e}")


def extract_shortcode(url: str) -> str:
    patterns = [
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/reels/([A-Za-z0-9_-]+)',
        r'instagram\.com/tv/([A-Za-z0-9_-]+)',
        r'instagr\.am/p/([A-Za-z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_content_type(url: str) -> str:
    """İçerik tipini belirle"""
    if '/reel/' in url or '/reels/' in url:
        return "Reels"
    elif '/p/' in url:
        return "Post"
    elif '/tv/' in url:
        return "IGTV"
    return "İçerik"


def init_user_stats(user_id: int):
    """Kullanıcı istatistiklerini başlat"""
    if user_id not in user_stats:
        user_stats[user_id] = {
            'downloads': 0,
            'videos': 0,
            'photos': 0,
            'first_use': datetime.now()
        }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlatıldığında gösterilecek mesaj"""
    user_id = update.effective_user.id
    init_user_stats(user_id)
    
    welcome_message = (
        "🎬 *Instagram İçerik İndirici Bot* 🎬\n\n"
        "Merhaba! Ben Instagram içeriklerinizi doğrudan Telegram'a indirmenize yardımcı oluyorum.\n\n"
        "📱 *Mobil Kullanım:*\n"
        "Instagram'dan bir link gönderin, ben de dosyayı doğrudan size göndereceğim!\n"
        "• Reels videolarını\n"
        "• Post'ları ve fotoğrafları\n"
        "• IGTV videolarını\n"
        "• Carousel (çoklu) içerikleri\n\n"
        "💾 *Dosyalar nasıl kaydedilir?*\n"
        "Telegram'da gönderilen dosyalara uzun basın ve 'Galeriye Kaydet' veya 'İndir' seçeneklerini kullanın.\n\n"
        "🔗 *Nasıl Kullanılır:*\n"
        "1️⃣ Instagram'da paylaş → Link'i kopyala\n"
        "2️⃣ Buraya yapıştır\n"
        "3️⃣ Dosya gelince telefonunuza kaydet!\n\n"
        "⌨️ *Komutlar:*\n"
        "/start - Hoş geldin mesajı\n"
        "/help - Detaylı yardım\n"
        "/stats - İndirme istatistikleriniz\n\n"
        "Haydi başlayalım! 🚀"
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım mesajı"""
    help_text = (
        "ℹ️ *Detaylı Yardım*\n\n"
        "*📱 Telefondan Kullanım:*\n\n"
        "*Adım 1:* Instagram'da beğendiğiniz içeriği bulun\n"
        "*Adım 2:* Üç nokta (⋯) menüsüne tıklayın\n"
        "*Adım 3:* 'Linki kopyala' seçeneğini seçin\n"
        "*Adım 4:* Telegram'da bu bota gidin\n"
        "*Adım 5:* Linki yapıştırın ve gönderin\n"
        "*Adım 6:* Video/fotoğraf gelince uzun basıp kaydedin!\n\n"
        "💾 *Dosyaları Telefonunuza Kaydetme:*\n\n"
        "📹 *Video için:*\n"
        "• Videoya uzun basın\n"
        "• 'Galeriye Kaydet' veya 'İndir' seçin\n\n"
        "🖼 *Fotoğraf için:*\n"
        "• Fotoğrafa uzun basın\n"
        "• 'Galeriye Kaydet' seçin\n\n"
        "📝 *Desteklenen Linkler:*\n"
        "```\n"
        "https://www.instagram.com/reel/ABC123/\n"
        "https://www.instagram.com/p/XYZ789/\n"
        "https://instagr.am/p/DEF456/\n"
        "```\n\n"
        "💡 *İpuçları:*\n"
        "• Carousel post'larda tüm fotoğraflar ayrı ayrı gelir\n"
        "• Videolar en yüksek kalitede indirilir\n"
        "• Gizli hesapların içerikleri indirilemez\n\n"
        "❓ *Sorun mu yaşıyorsunuz?*\n"
        "• Link'in doğru olduğundan emin olun\n"
        "• İçeriğin 'genel' (public) olduğundan emin olun\n"
        "• İnternet bağlantınızı kontrol edin"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_stats(user_id)
    
    stats = user_stats[user_id]
    days_using = (datetime.now() - stats['first_use']).days
    
    stats_text = (
        f"📊 *Kişisel İstatistikleriniz*\n\n"
        f"📥 Toplam indirme: *{stats['downloads']}*\n"
        f"🎥 Video: *{stats['videos']}*\n"
        f"🖼 Fotoğraf: *{stats['photos']}*\n"
        f"📅 Bot kullanım süresi: *{days_using} gün*\n"
        f"⏰ Son güncelleme: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"🎉 Harikasınız! Botu aktif kullanıyorsunuz."
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def download_instagram_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instagram içeriğini indir ve kullanıcıya gönder"""
    user_id = update.effective_user.id
    init_user_stats(user_id)
    
    message_text = update.message.text
    
    # Instagram linki kontrolü
    if 'instagram.com' not in message_text and 'instagr.am' not in message_text:
        return
    
    # Shortcode çıkar
    shortcode = extract_shortcode(message_text)
    
    if not shortcode:
        await update.message.reply_text(
            "❌ Geçerli bir Instagram linki bulunamadı.\n\n"
            "💡 Doğru format:\n"
            "`https://www.instagram.com/p/ABC123/`",
            parse_mode='Markdown'
        )
        return
    
    content_type = get_content_type(message_text)
    
    # İndirme başladı mesajı
    status_message = await update.message.reply_text(
        f"⏳ {content_type} indiriliyor...\n\n"
        "⚡️ Hızlı bağlantıda birkaç saniye\n"
        "🐌 Yavaş bağlantıda 30 saniyeye kadar sürebilir\n\n"
        "Lütfen bekleyin..."
    )
    
    try:
        # Instagram post'u al
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # İndir
        L.download_post(post, target=shortcode)
        
        # İndirilen dosyaları bul
        download_path = Path(TEMP_FOLDER) / shortcode
        
        if not download_path.exists():
            download_path = Path(TEMP_FOLDER)
        
        # Dosyaları topla
        video_files = list(download_path.glob('*.mp4'))
        image_files = list(download_path.glob('*.jpg')) + list(download_path.glob('*.png'))
        
        # Caption hazırla
        caption_text = post.caption[:200] if post.caption else ""
        
        caption = (
            f"✅ {content_type} indirildi!\n\n"
            f"👤 @{post.owner_username}\n"
            f"❤️ {post.likes:,} | 💬 {post.comments:,}\n"
        )
        
        if caption_text:
            caption += f"\n📝 {caption_text}..."
        
        # İstatistikleri güncelle
        user_stats[user_id]['downloads'] += 1
        
        # Videoları gönder
        for video_file in video_files:
            await update.message.reply_video(
                video=open(video_file, 'rb'),
                caption=caption,
                supports_streaming=True
            )
            user_stats[user_id]['videos'] += 1
            caption = None  # İlk dosyadan sonra caption tekrarlanmasın
        
        # Fotoğrafları gönder
        for image_file in image_files:
            await update.message.reply_photo(
                photo=open(image_file, 'rb'),
                caption=caption
            )
            user_stats[user_id]['photos'] += 1
            caption = None
        
        # Başarı mesajı
        total_files = len(video_files) + len(image_files)
        
        success_text = (
            f"✨ *{total_files} dosya gönderildi!*\n\n"
            f"💾 *Telefonunuza kaydetmek için:*\n"
            f"Dosyaya uzun basın → 'Galeriye Kaydet'\n\n"
            f"📊 Toplam indirmeniz: {user_stats[user_id]['downloads']}"
        )
        
        await status_message.edit_text(success_text, parse_mode='Markdown')
        
        # Geçici dosyaları temizle
        if download_path.exists():
            shutil.rmtree(download_path, ignore_errors=True)
        
    except instaloader.exceptions.LoginRequiredException:
        error_text = (
            "🔒 *Bu içerik gizli*\n\n"
            "Bu içeriğe erişmek için:\n"
            "• İçerik 'genel' (public) olmalı\n"
            "• Veya hesabı takip ediyor olmalısınız\n\n"
            "Sadece genel içerikler indirilebilir."
        )
        await status_message.edit_text(error_text, parse_mode='Markdown')
        logger.error(f"Login required for shortcode: {shortcode}")
        
    except instaloader.exceptions.InstaloaderException as e:
        error_text = (
            f"❌ *Instagram Hatası*\n\n"
            f"Hata: {str(e)}\n\n"
            "🔍 Kontrol edin:\n"
            "• Link doğru mu?\n"
            "• İçerik hala mevcut mu?\n"
            "• İçerik genel mi?"
        )
        await status_message.edit_text(error_text, parse_mode='Markdown')
        logger.error(f"Instaloader error for {shortcode}: {e}")
        
    except Exception as e:
        error_text = (
            f"❌ *Beklenmeyen Hata*\n\n"
            f"`{str(e)}`\n\n"
            "Lütfen tekrar deneyin veya farklı bir link gönderin."
        )
        await status_message.edit_text(error_text, parse_mode='Markdown')
        logger.error(f"Unexpected error for {shortcode}: {e}", exc_info=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


def main():
    """Bot'u başlat"""
    
    if TELEGRAM_BOT_TOKEN == "8698755439:AAG0rQrLM_NsZZ-RJvYs2ArXvt67j0mv1IQ":
        print("⚠️  UYARI: Bot token'ı ayarlanmamış!")
        print("📝 Lütfen şu adımları takip edin:")
        print("   1. config_example.py dosyasını config.py olarak kopyalayın")
        print("   2. config.py dosyasında TELEGRAM_BOT_TOKEN değerini ayarlayın")
        print("   3. Token almak için: https://t.me/BotFather")
        return
    
    # Application oluştur
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Komut handler'ları ekle
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Mesaj handler'ı ekle
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram_content)
    )
    
    # Hata handler'ı ekle
    application.add_error_handler(error_handler)
    
    # Bot'u başlat
    logger.info("=" * 60)
    logger.info("🤖 Instagram İndirici Bot (Mobil Versiyon) Başlatılıyor...")
    logger.info(f"📱 Dosyalar kullanıcılara doğrudan gönderilecek")
    logger.info(f"🔑 Instagram girişi: {'Aktif' if INSTAGRAM_USERNAME else 'Pasif'}")
    logger.info("=" * 60)
    print("\n✅ Bot çalışıyor ve her zaman aktif!")
    print("📱 Telefonunuzdan kullanabilirsiniz")
    print("💾 Dosyalar doğrudan Telegram'a gelecek\n")
    print("Durdurmak için Ctrl+C\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
