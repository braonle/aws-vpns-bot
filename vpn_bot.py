import logging
import config
import boto3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

logging.basicConfig(format="{asctime} [{module}:{lineno}] [{levelname}] {message}", style="{",
                    datefmt="%d/%m/%Y %H:%M:%S", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with three inline buttons attached."""
    keyboard = [
        [
            InlineKeyboardButton("Start VM", callback_data="start"),
            InlineKeyboardButton("Stop VM", callback_data="stop"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Choose action", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")

async def raw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.to_dict())


async def start_vm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.delete_message(update.effective_chat.id, update.effective_message.id)

    aws_instance = config.chat_to_vpc_mapping[update.effective_chat.id]
    if not aws_instance["users"]:
        ec2 = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY,
            aws_secret_access_key=config.AWS_SECRET_KEY,
            region_name="eu-north-1"
        ).client("ec2")
        ec2.start_instances(InstanceIds=[aws_instance["instance_id"]])

    aws_instance["users"] += 1
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'VPN users: {aws_instance["users"]}')


async def stop_vm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.delete_message(update.effective_chat.id, update.effective_message.id)

    aws_instance = config.chat_to_vpc_mapping[update.effective_chat.id]
    if not aws_instance["users"]:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'VM is not active')
        return

    aws_instance["users"] -= 1

    if not aws_instance["users"]:
        ec2 = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY,
            aws_secret_access_key=config.AWS_SECRET_KEY,
            region_name="eu-north-1"
        ).client("ec2")
        ec2.stop_instances(InstanceIds=[aws_instance["instance_id"]])

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'VPN users: {aws_instance["users"]}')


bot = ApplicationBuilder().token(config.BOT_TOKEN).build()

bot.add_handler(CommandHandler('start', start))
bot.add_handler(CommandHandler('raw', raw))
bot.add_handler(CallbackQueryHandler(start_vm, pattern="start"))
bot.add_handler(CallbackQueryHandler(stop_vm, pattern="stop"))

if config.POLLING_BASED:
    bot.run_polling()