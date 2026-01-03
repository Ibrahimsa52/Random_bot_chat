"""
Main Telegram Random Chat Bot Application
"""
import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

import config
import messages
from database import Database
from spam_protection import spam_protection
from admin import (
    admin_stats,
    admin_block,
    admin_unblock,
    admin_broadcast,
    admin_reports,
    admin_chats
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_main_keyboard():
    """Get the main keyboard with buttons"""
    keyboard = [
        [KeyboardButton(messages.BTN_START_SEARCH)],
        [KeyboardButton(messages.BTN_HELP)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_chat_keyboard():
    """Get keyboard for when user is in chat"""
    keyboard = [
        [KeyboardButton(messages.BTN_END_CHAT)],
        [KeyboardButton(messages.BTN_HELP)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Create user if doesn't exist
    if not await Database.user_exists(user_id):
        await Database.create_user(user_id)
        logger.info(f"New user created: {user_id}")
    
    # Check if blocked
    if await Database.is_blocked(user_id):
        await update.message.reply_text(messages.BLOCKED_USER)
        return
    
    # Send welcome message
    await update.message.reply_text(
        messages.WELCOME_MESSAGE,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle search for random partner"""
    user_id = update.effective_user.id
    
    # Check if blocked
    if await Database.is_blocked(user_id):
        await update.message.reply_text(messages.BLOCKED_USER)
        return
    
    # Check command cooldown
    if not spam_protection.check_command_cooldown(user_id):
        await update.message.reply_text(
            f"⏳ انتظر {config.COMMAND_COOLDOWN_SECONDS} ثواني قبل استخدام الأمر مرة أخرى"
        )
        return
    
    # Check if already in chat
    if await Database.is_in_chat(user_id):
        await update.message.reply_text(messages.ALREADY_IN_CHAT)
        return
    
    # Check if already in queue
    if await Database.is_in_queue(user_id):
        await update.message.reply_text(messages.ALREADY_SEARCHING)
        return
    
    # Try to find a match from queue
    partner_id = await Database.get_next_from_queue()
    
    if partner_id and partner_id != user_id:
        # Match found! Remove partner from queue
        await Database.remove_from_queue(partner_id)
        
        # Create chat
        await Database.create_chat(user_id, partner_id)
        
        # Notify both users
        await update.message.reply_text(
            messages.MATCHED_MESSAGE,
            reply_markup=get_chat_keyboard(),
            parse_mode='Markdown'
        )
        
        await context.bot.send_message(
            chat_id=partner_id,
            text=messages.MATCHED_MESSAGE,
            reply_markup=get_chat_keyboard(),
            parse_mode='Markdown'
        )
        
        logger.info(f"Matched: {user_id} <-> {partner_id}")
    else:
        # No match, add to queue
        await Database.add_to_queue(user_id)
        await update.message.reply_text(
            messages.SEARCHING_MESSAGE,
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} added to queue")


async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ending current chat"""
    user_id = update.effective_user.id
    
    # Check if in chat
    if not await Database.is_in_chat(user_id):
        # Maybe in queue?
        if await Database.is_in_queue(user_id):
            await Database.remove_from_queue(user_id)
            await update.message.reply_text(
                "✅ تم إلغاء البحث",
                reply_markup=get_main_keyboard()
            )
            return
        
        await update.message.reply_text(messages.NOT_IN_CHAT)
        return
    
    # End the chat
    partner_id = await Database.end_chat(user_id)
    
    # Notify user
    await update.message.reply_text(
        messages.YOU_DISCONNECTED,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    
    # Notify partner
    if partner_id:
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text=messages.PARTNER_DISCONNECTED,
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify partner {partner_id}: {e}")
    
    logger.info(f"Chat ended by {user_id}, partner was {partner_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    await update.message.reply_text(
        messages.HELP_MESSAGE,
        parse_mode='Markdown'
    )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /report command"""
    user_id = update.effective_user.id
    
    # Check if in chat
    if not await Database.is_in_chat(user_id):
        await update.message.reply_text(messages.REPORT_NO_CHAT)
        return
    
    # Get reason
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(messages.REPORT_INSTRUCTION)
        return
    
    reason = ' '.join(context.args)
    partner_id = await Database.get_current_chat(user_id)
    
    if partner_id:
        # Create report
        await Database.create_report(user_id, partner_id, reason)
        await update.message.reply_text(messages.REPORT_SUBMITTED)
        
        logger.info(f"Report: {user_id} reported {partner_id} for: {reason}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages and forward to chat partner"""
    user_id = update.effective_user.id
    
    # Handle button presses
    if update.message.text == messages.BTN_START_SEARCH:
        await search(update, context)
        return
    elif update.message.text == messages.BTN_END_CHAT:
        await end_chat(update, context)
        return
    elif update.message.text == messages.BTN_HELP:
        await help_command(update, context)
        return
    
    # Check if blocked
    if await Database.is_blocked(user_id):
        await update.message.reply_text(messages.BLOCKED_USER)
        return
    
    # Check if in chat
    if not await Database.is_in_chat(user_id):
        await update.message.reply_text(messages.NOT_IN_CHAT)
        return
    
    # Check spam
    if not spam_protection.check_message_rate(user_id):
        await update.message.reply_text(
            "⚠️ **تحذير: سبام!**\n\nانت بتبعت رسائل كتير جداً. استنى شوية.",
            parse_mode='Markdown'
        )
        return
    
    # Get partner
    partner_id = await Database.get_current_chat(user_id)
    
    if not partner_id:
        await update.message.reply_text(messages.NOT_IN_CHAT)
        return
    
    # Forward message to partner
    try:
        await context.bot.copy_message(
            chat_id=partner_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Failed to forward message from {user_id} to {partner_id}: {e}")
        await update.message.reply_text(
            "⚠️ حدث خطأ في إرسال الرسالة. ممكن الطرف التاني سد البوت."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("end", end_chat))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", report))
    
    # Admin commands
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("admin_block", admin_block))
    application.add_handler(CommandHandler("admin_unblock", admin_unblock))
    application.add_handler(CommandHandler("admin_broadcast", admin_broadcast))
    application.add_handler(CommandHandler("admin_reports", admin_reports))
    application.add_handler(CommandHandler("admin_chats", admin_chats))
    
    # Message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Check for Webhook configuration (for Render/Cloud)
    PORT = int(os.environ.get('PORT', '8080'))
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
    
    if WEBHOOK_URL:
        # Start with Webhook
        logger.info(f"Starting bot in Webhook mode on port {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{config.BOT_TOKEN}"
        )
    else:
        # Start with Polling
        logger.info("Starting bot in Polling mode")
        print("🤖 Bot is running on Polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
