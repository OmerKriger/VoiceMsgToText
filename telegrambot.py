import os
import json
import aiofiles
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

lists_lock = asyncio.Lock()


async def load_whitelist() -> set:
    async with aiofiles.open('whitelist.json', 'r') as json_file:
        content = await json_file.read()
        data = json.loads(content)
        allowed_users = set(data["allowed_users"])
        return allowed_users


async def load_admin_list() -> set:
    async with aiofiles.open('admin_list.json', 'r') as json_file:
        content = await json_file.read()
        data = json.loads(content)
        return set(data["admins"])


async def add_user_to_whitelist(self, user_id):
    async with lists_lock:
        allowed_users = await load_whitelist()
        allowed_users.add(user_id)
        data = {"allowed_users": list(allowed_users)}
        async with aiofiles.open('whitelist.json', 'w') as json_file:
            await json_file.write(json.dumps(data, indent=4))


async def add_user_to_admin_list(self, user_id):
    async with lists_lock:
        allowed_users = await load_whitelist()
        allowed_users.add(user_id)
        data = {"admins": list(allowed_users)}
        async with aiofiles.open('admin_list.json', 'w') as json_file:
            await json_file.write(json.dumps(data, indent=4))


# TranscriptBot - Bot Object
class TranscriptBot:
    def __init__(self):
        self.__TOKEN_TELEGRAM = os.environ.get("TELEGRAM_API_KEY")
        self.BOT_USERNAME = '@BotTranscriptBot'
        self.whitelist_loaded = False
        self.admin_list_loaded = False
        self.__whiteList = None
        self.__adminList = None

    def is_valid_tokens(self) -> bool:
        if self.__TOKEN_TELEGRAM:
            print("API key found in environment variable.")
            return True
        else:
            print("API key not found in environment variable.")
            return False

    async def load_whitelist(self):
        self.__whiteList = await load_whitelist()
        self.whitelist_loaded = True

    async def load_admin_list(self):
        self.__whiteList = await load_admin_list()
        self.admin_list_loaded = True

    async def is_user_allowed(self, userid: int) -> bool:
        if not self.whitelist_loaded:
            await self.load_whitelist()
        userid = str(userid)
        if userid in self.__whiteList:
            print("User is in the whitelist")
            return True
        else:
            print("User is not in the whitelist")
            return False

    async def is_user_admin(self, userid: int) -> bool:
        if not self.admin_list_loaded:
            await self.load_admin_list()
        userid = str(userid)
        if userid in self.__adminList:
            print("User is a admin")
            return True
        else:
            print("User is not admin")
            return False

    @staticmethod
    def __print_audio_details(audio) -> None:
        print(f'The audio file info\n'
              f'name: {audio.file_name}\n'
              f'duration: {audio.duration}\n'
              f'mine_type: {audio.mime_type}\n'
              f'size: {audio.file_size}\n')

    @staticmethod
    async def __start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            'Hello and Welcome, I\'m a transcript bot and i will help you with your voice messages.\n From now send me your voice messages and i will handle it.')

    @staticmethod
    async def __help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            'Hi, for use my service you just need send me a voice messages and i will doing the rest.')

    @staticmethod
    async def __test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('--- TESTING --- \n\n Check something')

    @staticmethod
    async def __requestList(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('--- This is the list of users requested to use me --- \n\n')
        # TODO: Finish here the request list approve

    async def __receive_audio_file(self, update: Update, context: ContextTypes):
        message_type: str = update.message.chat.type
        user_id = update.message.chat.id
        audio = update.message.audio
        # DEBUG - prints for debug level information.
        print(f'User ({user_id}) in {message_type} sent\n {update.message}.')
        self.__print_audio_details(audio=audio)
        # ------ DEBUG Print end ------
        if not await self.is_user_allowed(user_id):
            await update.message.reply_text("You are not allowed to send me audio files.")
            return None
        if audio.mime_type == 'audio/mpeg':
            await self.__process_audio(user_id, audio)
            await update.message.reply_text("Audio file received and processing right now")
        else:
            await update.message.reply_text("Unsupported audio file format")

    @staticmethod
    async def __process_audio(user_id: int, audio):
        file = await audio.get_file()
        file_name: str = f'{user_id}_{audio.file_name}'
        await file.download_to_drive(f'audioFiles\\{file_name}')
        # TODO: Need to complete the API request

    @staticmethod
    def __handle_response(text: str) -> str:
        low_text: str = text.lower()
        if low_text == 'admin':
            return 'You\'re the Admin'
        return "I am not understanding text that you write on the chat."

    async def __handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_type: str = update.message.chat.type
        text: str = update.message.text

        print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

        if message_type == 'group':
            if self.BOT_USERNAME in text:
                new_text: str = text.replace(self.BOT_USERNAME, "").strip()
                response: str = self.__handle_response(new_text)
            else:
                return
        else:
            response: str = self.__handle_response(text)

        print("Bot:", response)
        await update.message.reply_text(response)

    @staticmethod
    async def __error(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f'Update\n{update} \ncause error: {context.error}')

    def run(self):
        print("Checking for valid tokens...")
        self.is_valid_tokens()
        print("Starting Bot")
        app = Application.builder().token(self.__TOKEN_TELEGRAM).build()
        app.add_handler(CommandHandler('start', self.__start_command))
        app.add_handler(CommandHandler('help', self.__help_command))
        app.add_handler(CommandHandler('test', self.__test_command))

        app.add_handler(MessageHandler(filters.TEXT, self.__handle_message))
        app.add_handler(MessageHandler(filters.AUDIO, self.__receive_audio_file))

        app.add_error_handler(self.__error)

        print("Polling...")
        app.run_polling(poll_interval=3)
