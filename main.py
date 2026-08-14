import asyncio
import os

from telethon import TelegramClient
from telethon.sessions import StringSession

from config import API_ID, API_HASH, SESSION_STRING, OWNER_ID
from database import Database
from handlers.commands import setup_command_handlers
from handlers.ai import setup_ai_handlers


async def main():
    db = Database()
    state = {"cooldowns": {}}

    session = StringSession(SESSION_STRING) if SESSION_STRING else "ubot_session"
    client = TelegramClient(session, API_ID, API_HASH)

    setup_command_handlers(client, db, state)
    setup_ai_handlers(client, db, state)

    await client.start()
    me = await client.get_me()
    print(f"uBot AI online as @{getattr(me, 'username', None) or me.id}")
    print(f"Owner ID: {OWNER_ID}")
    print("Gemini model configured via environment.")

    if not SESSION_STRING:
        print("IMPORTANT: After first login, create/export a StringSession and put it in Railway as SESSION_STRING.")

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
