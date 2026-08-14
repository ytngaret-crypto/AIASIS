
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from database import init_db
from config import API_ID,API_HASH,SESSION_STRING
from handlers.ai import register_ai
from handlers.commands import register_commands

async def main():
    init_db()
    if not SESSION_STRING:
        raise RuntimeError("SESSION_STRING belum diisi.")
    client=TelegramClient(StringSession(SESSION_STRING),API_ID,API_HASH)
    await client.start()
    me=await client.get_me()
    print(f"uBot online: {me.id} @{me.username or '(tanpa username)'}",flush=True)
    register_commands(client,me.id)
    register_ai(client)
    print("Handlers registered.",flush=True)
    await client.run_until_disconnected()

if __name__=="__main__":
    asyncio.run(main())
