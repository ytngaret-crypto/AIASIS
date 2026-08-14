from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("Telegram StringSession Generator")
api_id = int(input("API ID: ").strip())
api_hash = input("API Hash: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nLogin berhasil.")
    print("Salin SESSION_STRING berikut ke Railway Variables:\n")
    print(client.session.save())
