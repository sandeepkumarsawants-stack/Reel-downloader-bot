import telebot
import yt_dlp
import re
import os
import time
import shutil
import uuid
import threading
import traceback

# ======================= ANIMATED EMOJIS =======================
def ce(name):
    if name in EMOJIS:
        emoji, emoji_id = EMOJIS[name]
        return f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>'
    return "✨"

EMOJIS = {
    "success": ("✅", "5316827280863934685"),
    "danger": ("❌", "4958526153955476488"),
    "warning": ("⚠️", "5447644880824181073"),
    "rocket": ("🚀", "5316571734604790521"),
    "download": ("📥", "5316571734604790521"),
    "video": ("🎬", "5447644880824181073"),
    "fire": ("🔥", "5447644880824181073"),
    "sparkle": ("✨", "5316827280863934685"),
    "time": ("⏳", "6089104607328342288"),
    "upload": ("📤", "5316571734604790521"),
    "progress": ("📊", "6089104607328342288"),
    "speed": ("⚡", "5447644880824181073"),
    "clock": ("🕐", "5316571734604790521"),
}

# ======================= CONFIG =======================
DOTENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

if os.path.exists(DOTENV_PATH):
    with open(DOTENV_PATH, "r", encoding="utf-8") as dotenv_file:
        for line in dotenv_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Create a .env file in the insta folder.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ======================= INSTAGRAM DOWNLOADER WITH PROGRESS =======================
HOME_DIR = os.path.expanduser("~")
TEMP_DIR = os.path.join(HOME_DIR, "tmp_reels")
os.makedirs(TEMP_DIR, exist_ok=True)

class ProgressHook:
    def __init__(self, chat_id, message_id, bot_instance):
        self.chat_id = chat_id
        self.message_id = message_id
        self.bot = bot_instance
        self.last_update = time.time()
        self.last_downloaded = 0
        
    def hook(self, d):
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                
                if total > 0:
                    percent = (downloaded / total) * 100
                    
                    # Update every 2 seconds
                    current_time = time.time()
                    if current_time - self.last_update >= 2 or percent >= 99:
                        # Calculate speed
                        speed = d.get('speed', 0)
                        speed_text = ""
                        if speed:
                            if speed > 1024 * 1024:
                                speed_text = f"{speed / (1024 * 1024):.1f} MB/s"
                            elif speed > 1024:
                                speed_text = f"{speed / 1024:.1f} KB/s"
                            else:
                                speed_text = f"{speed:.0f} B/s"
                        
                        # Calculate ETA
                        eta = d.get('eta', 0)
                        eta_text = ""
                        if eta and eta > 0:
                            if eta > 60:
                                mins = eta // 60
                                secs = eta % 60
                                eta_text = f"{mins}m {secs}s"
                            else:
                                eta_text = f"{eta}s"
                        
                        # Create progress bar
                        bar_length = 20
                        filled = int(bar_length * percent / 100)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        
                        status_text = f"""
{ce('progress')} <b>Downloading...</b>

<code>{bar}</code> {percent:.1f}%

{ce('download')} Downloaded: {downloaded / (1024 * 1024):.1f} MB
{ce('speed')} Speed: {speed_text}
{ce('clock')} ETA: {eta_text}
"""
                        
                        try:
                            self.bot.edit_message_text(
                                status_text,
                                self.chat_id,
                                self.message_id,
                                parse_mode="HTML"
                            )
                            self.last_update = current_time
                        except:
                            pass
                        
            except Exception as e:
                print(f"Progress error: {e}")

def download_reel_with_progress(url, chat_id, message_id):
    """Download Instagram Reel with real-time progress"""
    try:
        # Extract shortcode
        shortcode_match = re.search(r"/reel/([^/?]+)", url)
        if not shortcode_match:
            return None
        shortcode = shortcode_match.group(1)
        
        # Create unique temp directory
        temp_dir = os.path.join(TEMP_DIR, f"reel_{shortcode}_{uuid.uuid4().hex[:8]}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup progress hook
        progress_hook = ProgressHook(chat_id, message_id, bot)
        
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, f'{shortcode}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            'progress_hooks': [progress_hook.hook],
            'retries': 5,
            'fragment_retries': 5,
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            # Find downloaded video
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp4', '.mkv', '.webm')):
                    video_path = os.path.join(temp_dir, file)
                    return video_path
        
        return None
        
    except Exception as e:
        print(f"Download error: {e}")
        return None

# ======================= BOT COMMANDS =======================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = f"""
╔══════════════════════════════════════╗
║     {ce('video')} INSTAGRAM REEL DOWNLOADER     ║
╠══════════════════════════════════════╣
║  {ce('sparkle')} Send me any Instagram Reel URL   ║
║  {ce('download')} Real-time progress tracking     ║
║  {ce('speed')} Shows speed & ETA              ║
║  {ce('fire')} Fast & Free Service              ║
╠══════════════════════════════════════╣
║  📌 Example:                         ║
║  https://www.instagram.com/reel/xxx  ║
╚══════════════════════════════════════╝
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda msg: True)
def handle(message):
    url = message.text.strip()
    
    # Validate Instagram URL
    if "instagram.com" not in url:
        error_msg = f"""{ce('danger')} *Invalid Link*

📌 Please send a valid Instagram Reel URL
💡 Example: `https://www.instagram.com/reel/xxxxx/`"""
        bot.reply_to(message, error_msg, parse_mode="HTML")
        return

    # Send initial processing message
    processing_msg = bot.reply_to(message, f"{ce('time')} *Processing...*\n\n🔍 Fetching reel information...", parse_mode="HTML")
    
    time.sleep(1)
    
    # Start download with progress
    bot.edit_message_text(
        f"{ce('download')} *Starting Download...*\n\n⏬ Connecting to Instagram...",
        message.chat.id,
        processing_msg.message_id,
        parse_mode="HTML"
    )
    
    # Download the reel
    file_path = download_reel_with_progress(url, message.chat.id, processing_msg.message_id)
    
    if file_path and os.path.exists(file_path):
        bot.edit_message_text(
            f"{ce('upload')} *Uploading Video...*\n\n⬆️ Sending your reel...",
            message.chat.id,
            processing_msg.message_id,
            parse_mode="HTML"
        )
        
        try:
            # Get file size
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # in MB
            
            with open(file_path, "rb") as vid:
                caption_text = f"""{ce('success')} *Download Complete!*

{ce('video')} Reel downloaded successfully
📦 Size: {file_size:.1f} MB
{ce('fire')} Enjoy your video!

🔗 By Sandeep Sawant"""

                bot.send_video(message.chat.id, vid, caption=caption_text, parse_mode="HTML")

                # Delete processing message
                try:
                    bot.delete_message(message.chat.id, processing_msg.message_id)
                except:
                    pass
                
        except Exception as e:
            error_details = f"{type(e).__name__}: {e}"
            bot.edit_message_text(
                f"{ce('danger')} *Upload Failed*\n\n😕 Couldn't send the video.\n\n<code>{error_details}</code>",
                message.chat.id,
                processing_msg.message_id,
                parse_mode="HTML"
            )
            print("Upload error:")
            traceback.print_exc()
        
        # Cleanup
        try:
            temp_dir = os.path.dirname(file_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Cleanup error: {e}")
              
    else:
        error_text = f"""
{ce('danger')} *Download Failed*

📋 Possible reasons:
• Invalid or broken URL
• Private account or reel
• Network connection issue

💡 *Try these solutions:*
• Verify the link is correct
• Ensure reel is from public account
• Try again after a few minutes
        """
        bot.edit_message_text(error_text, message.chat.id, processing_msg.message_id, parse_mode="HTML")

# ======================= BOT STARTUP =======================
print("╔══════════════════════════════════════╗")
print("║     🤖 INSTAGRAM REEL BOT ONLINE     ║")
print("╠══════════════════════════════════════╣")
print("║  ✅ Bot is running successfully      ║")
print("║  📡 Waiting for messages...          ║")
print("║  🟢 Service Active                   ║")
print("╚══════════════════════════════════════╝")

# ======================= START POLLING =======================
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"⚠️ Connection error: {e}")
        print("🔄 Restarting bot in 10 seconds...")
        time.sleep(10)