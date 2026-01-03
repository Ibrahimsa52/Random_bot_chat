"""
Admin commands for the Telegram bot
"""
from telegram import Update
from telegram.ext import ContextTypes
import config
import messages
from database import Database


async def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in config.ADMIN_IDS


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(messages.NOT_ADMIN)
        return
    
    stats = await Database.get_stats()
    
    message = messages.ADMIN_STATS.format(**stats)
    await update.message.reply_text(message, parse_mode='Markdown')


async def admin_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Block a user"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(messages.NOT_ADMIN)
        return
    
    # Check if user ID is provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "⚠️ استخدام خاطئ. استخدم: /admin_block <user_id>"
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        # Check if user exists
        if not await Database.user_exists(user_id):
            await update.message.reply_text(
                f"⚠️ المستخدم {user_id} غير موجود في قاعدة البيانات"
            )
            return
        
        # Block user
        await Database.block_user(user_id)
        
        # End their chat if in one
        await Database.end_chat(user_id)
        
        # Remove from queue if waiting
        await Database.remove_from_queue(user_id)
        
        await update.message.reply_text(
            messages.ADMIN_USER_BLOCKED.format(user_id=user_id),
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ رقم المستخدم يجب أن يكون رقماً صحيحاً"
        )


async def admin_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unblock a user"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(messages.NOT_ADMIN)
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "⚠️ استخدام خاطئ. استخدم: /admin_unblock <user_id>"
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        if not await Database.user_exists(user_id):
            await update.message.reply_text(
                f"⚠️ المستخدم {user_id} غير موجود في قاعدة البيانات"
            )
            return
        
        await Database.unblock_user(user_id)
        
        await update.message.reply_text(
            messages.ADMIN_USER_UNBLOCKED.format(user_id=user_id),
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ رقم المستخدم يجب أن يكون رقماً صحيحاً"
        )


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send broadcast message to all users"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(messages.NOT_ADMIN)
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "⚠️ استخدام خاطئ. استخدم: /admin_broadcast <message>"
        )
        return
    
    broadcast_message = ' '.join(context.args)
    user_ids = await Database.get_all_user_ids()
    
    sent_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 **رسالة من الإدارة:**\n\n{broadcast_message}",
                parse_mode='Markdown'
            )
            sent_count += 1
        except Exception as e:
            # User might have blocked the bot
            print(f"Failed to send to {user_id}: {e}")
    
    await update.message.reply_text(
        messages.ADMIN_BROADCAST_SENT.format(count=sent_count)
    )


async def admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all pending reports"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(messages.NOT_ADMIN)
        return
    
    reports = await Database.get_all_reports()
    
    if not reports:
        await update.message.reply_text(messages.ADMIN_NO_REPORTS)
        return
    
    message = "📝 **البلاغات المعلقة:**\n\n"
    
    for idx, report in enumerate(reports[:10], 1):  # Show max 10
        message += f"{idx}. المبلّغ: `{report['reporter_id']}`\n"
        message += f"   المبلّغ عنه: `{report['reported_id']}`\n"
        message += f"   السبب: {report['reason']}\n"
        message += f"   الوقت: {report['timestamp'].strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if len(reports) > 10:
        message += f"\n_... و {len(reports) - 10} بلاغات أخرى_"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def admin_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all active chats"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(messages.NOT_ADMIN)
        return
    
    stats = await Database.get_stats()
    active_count = stats['active_chats']
    waiting_count = stats['waiting_users']
    
    message = f"💬 **المحادثات النشطة:** {active_count}\n"
    message += f"⏳ **في قائمة الانتظار:** {waiting_count}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')
