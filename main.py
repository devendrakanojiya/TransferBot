import os
import logging
import re
import signal
import sys
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_GROUP = 1

# Store user media temporarily
user_media = {}

# Global application instance
app_instance = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Copyright Freax\n\n'
        'I can help you send media from personal chat to any group.\n\n'
        '📷 Photos\n'
        '🎥 Videos\n'
        '📄 Documents\n'
        '🎵 Audio\n'
        '😀 Stickers\n'
        '🎞 GIFs/Animations\n'
        '💬 Text (in double quotes)\n\n'
        'Use /helppp to learn how to use the bot.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help information."""
    help_text = """
<b>Step 1: Send Media</b>
Send me any of the following:
• 📷 Photo/Video
• 📄 File/Audio
• 😀 Sticker/GIF
• 💬 Text message (must be in double quotes)

<b>Step 2: Provide Group Info</b>
After sending media, You can provide:
• Group username (e.g., <code>@mygroup</code>)
• Group chat ID (e.g., <code>-1001234567890</code>)
━━━━━━━━━━━━━━━━━━━━

<b>📝 Text Messages</b>
To send text messages, enclose them in double quotes:

✅ Correct: <code>"Hello Root"</code>
❌ Wrong: <code>Hello Root</code>

━━━━━━━━━━━━━━━━━━━━
<b>⚙️ Commands</b>

/starttt - Start the bot
/helppp - Show this help message
/cancel - Cancel current operation
━━━━━━━━━━━━━━━━━━━━

"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='HTML'
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming media files."""
    user_id = update.effective_user.id
    
    # Store the media information
    if update.message.photo:
        media_type = 'photo'
        media_file = update.message.photo[-1].file_id
        caption = update.message.caption
    elif update.message.document:
        media_type = 'document'
        media_file = update.message.document.file_id
        caption = update.message.caption
    elif update.message.video:
        media_type = 'video'
        media_file = update.message.video.file_id
        caption = update.message.caption
    elif update.message.audio:
        media_type = 'audio'
        media_file = update.message.audio.file_id
        caption = update.message.caption
    elif update.message.sticker:
        media_type = 'sticker'
        media_file = update.message.sticker.file_id
        caption = None
    elif update.message.animation:
        media_type = 'animation'
        media_file = update.message.animation.file_id
        caption = update.message.caption
    else:
        await update.message.reply_text("Unsupported media type!")
        return ConversationHandler.END
    
    # Store media data
    user_media[user_id] = {
        'type': media_type,
        'file_id': media_file,
        'caption': caption
    }
    
    media_name = media_type.capitalize()
    await update.message.reply_text(
        f'📤 {media_name} received!\n\n'
        'Now send me the group username (e.g., @groupname) or group chat ID where you want to send this.\n\n'
        'Use /cancel to abort.'
    )
    
    return WAITING_FOR_GROUP

async def handle_quoted_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages enclosed in double quotes."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if text is enclosed in double quotes
    quote_pattern = r'^"(.+)"$'
    match = re.match(quote_pattern, text, re.DOTALL)
    
    if match:
        # Extract the text without quotes
        quoted_text = match.group(1)
        
        # Store text data
        user_media[user_id] = {
            'type': 'text',
            'text': quoted_text,
            'caption': None
        }
        
        await update.message.reply_text(
            '💬 Text message received!\n\n'
            'Now send me the group username (e.g., @groupname) or group chat ID where you want to send this.\n\n'
            'Use /cancel to abort.'
        )
        
        return WAITING_FOR_GROUP
    
    # If not quoted, ignore
    return ConversationHandler.END

async def receive_group_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive group information and send media."""
    user_id = update.effective_user.id
    group_identifier = update.message.text.strip()
    
    # Check if user has media stored
    if user_id not in user_media:
        await update.message.reply_text('No media found. Please send media first.')
        return ConversationHandler.END
    
    media_data = user_media[user_id]
    
    try:
        # Send media to the specified group based on type
        if media_data['type'] == 'photo':
            await context.bot.send_photo(
                chat_id=group_identifier,
                photo=media_data['file_id'],
                caption=media_data['caption']
            )
        elif media_data['type'] == 'document':
            await context.bot.send_document(
                chat_id=group_identifier,
                document=media_data['file_id'],
                caption=media_data['caption']
            )
        elif media_data['type'] == 'video':
            await context.bot.send_video(
                chat_id=group_identifier,
                video=media_data['file_id'],
                caption=media_data['caption']
            )
        elif media_data['type'] == 'audio':
            await context.bot.send_audio(
                chat_id=group_identifier,
                audio=media_data['file_id'],
                caption=media_data['caption']
            )
        elif media_data['type'] == 'sticker':
            await context.bot.send_sticker(
                chat_id=group_identifier,
                sticker=media_data['file_id']
            )
        elif media_data['type'] == 'animation':
            await context.bot.send_animation(
                chat_id=group_identifier,
                animation=media_data['file_id'],
                caption=media_data['caption']
            )
        elif media_data['type'] == 'text':
            await context.bot.send_message(
                chat_id=group_identifier,
                text=media_data['text']
            )
        
        await update.message.reply_text('✅ Media sent successfully to the group!')
        
    except Exception as e:
        error_message = str(e)
        await update.message.reply_text(
            f'❌ Failed to send media!\n\n'
            f'Error: {error_message}\n\n'
            f'Make sure:\n'
            f'1. The bot is added to the group\n'
            f'2. The bot has permission to send messages\n'
            f'3. The username/ID is correct\n\n'
            f'Need help finding group info? Use /helppp'
        )
        logger.error(f"Error sending media: {e}")
    
    # Clean up
    del user_media[user_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation."""
    user_id = update.effective_user.id
    
    if user_id in user_media:
        del user_media[user_id]
    
    await update.message.reply_text(
        '❌ Operation cancelled.\n\n'
        'Send new media to start again or use /help for instructions.'
    )
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Exception while handling an update: {context.error}")

# Web server for Render health checks
async def health_check(request):
    """Health check endpoint for Render."""
    return web.Response(text="Bot is running!")

async def root(request):
    """Root endpoint."""
    return web.Response(text="Telegram Media Transfer Bot is Active!")

async def start_web_server():
    """Start the web server for Render."""
    app = web.Application()
    app.router.add_get('/', root)
    app.router.add_get('/health', health_check)
    
    port = int(os.environ.get('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")

async def post_init(application: Application):
    """Post initialization hook."""
    await start_web_server()

def main():
    """Start the bot."""
    global app_instance
    
    # Get token from environment variable
    BOT_TOKEN = os.environ.get('BOT_TOKEN', "8232825601:AAE412GnfxH-70qx-oCeHyMAiFR_bj27J1o")
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        print("Error: Please set BOT_TOKEN environment variable")
        return
    
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
        app_instance = application
        
        # Conversation handler for media workflow
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(
                    filters.PHOTO | filters.Document.ALL | filters.VIDEO | 
                    filters.AUDIO | filters.Sticker.ALL | filters.ANIMATION,
                    handle_media
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_quoted_text
                )
            ],
            states={
                WAITING_FOR_GROUP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_info)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # Add handlers
        application.add_handler(CommandHandler("starttt", start))
        application.add_handler(CommandHandler("helppp", help_command))
        application.add_handler(conv_handler)
        application.add_error_handler(error_handler)
        
        # Start the Bot
        logger.info("Bot started successfully!")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
