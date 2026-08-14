
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
print("Masukkan API ID dan API HASH Telegram.")
api_id=int(input("API ID: ").strip())
api_hash=input("API HASH: ").strip()
with TelegramClient(StringSession(),api_id,api_hash) as client:
    print("\nLogin Telegram...")
    print("\nSESSION_STRING:\n")
    print(client.session.save())
    print("\nSalin string di atas ke Railway Variable SESSION_STRING.")
