import time
from telethon import events

from config import OWNER_ID, AI_PREFIX, AI_COOLDOWN_SECONDS
from gemini import generate_reply
from handlers.utils import is_group_message


def setup_ai_handlers(client, db, state):
    async def allowed(event):
        chat_id, user_id = event.chat_id, event.sender_id
        if user_id == OWNER_ID:
            return True
        if is_group_message(event.message):
            muted, banned = db.get_restriction(chat_id, user_id)
            if muted or banned:
                return False
            row = db.get_group(chat_id)
            if row["ai_mode"] == "allmember":
                return db.is_enabled(chat_id, user_id)
            if row["ai_mode"] == "allmember+admin":
                return db.is_enabled(chat_id, user_id)
            return db.is_enabled(chat_id, user_id) and db.is_ai_explicitly_allowed(chat_id, user_id)
        return db.is_enabled(chat_id, user_id)

    async def answer(event, prompt: str):
        if not await allowed(event):
            return
        key = (event.chat_id, event.sender_id)
        now = time.monotonic()
        last = state.get("cooldowns", {}).get(key, 0)
        if now - last < AI_COOLDOWN_SECONDS:
            return
        state.setdefault("cooldowns", {})[key] = now

        history = db.get_history(event.chat_id, event.sender_id)
        try:
            reply = generate_reply(history, prompt)
        except Exception as exc:
            print("Gemini error:", repr(exc))
            await event.reply("⚠️ AI sedang mengalami kendala. Coba lagi sebentar.")
            return

        history.append({"role": "user", "text": prompt})
        history.append({"role": "model", "text": reply})
        sent = await event.reply(reply)
        db.save_history(event.chat_id, event.sender_id, history, sent.id)

    @client.on(events.NewMessage(pattern=r"^\.pai\s+(.+)$"))
    async def command_ai(event):
        await answer(event, event.pattern_match.group(1).strip())

    @client.on(events.NewMessage())
    async def ai_message_handler(event):
        message = event.message
        if not message or message.raw_text is None:
            return
        # Ignore commands handled elsewhere.
        if message.raw_text.startswith("."):
            return
        if not await allowed(event):
            return

        # Reply mode: user replies to an AI message. For group/private, accept any message
        # sent by this userbot account, but only continue that user's own conversation.
        if message.is_reply:
            try:
                replied = await message.get_reply_message()
                if replied and replied.sender_id == (await client.get_me()).id:
                    await answer(event, message.raw_text.strip())
            except Exception as exc:
                print("Reply handler error:", repr(exc))
            return

        # Mention mode: mention the userbot in the message.
        me = await client.get_me()
        username = getattr(me, "username", None)
        if username and f"@{username.lower()}" in message.raw_text.lower():
            prompt = message.raw_text
            prompt = prompt.replace(f"@{username}", "", 1).strip()
            if prompt:
                await answer(event, prompt)
