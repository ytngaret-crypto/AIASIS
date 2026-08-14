from telethon import events
from database import *
from gemini import ask
from utils import cooldown,is_admin
from config import COOLDOWN_SECONDS,GROUP_COOLDOWN_SECONDS

async def can_group(client,event,uid):
    if is_banned(event.chat_id,uid) or is_muted(event.chat_id,uid):
        return False
    admin=await is_admin(client,event.chat_id,uid)
    return ai_permission_allows(event.chat_id,uid,admin) and group_ai_enabled(event.chat_id,uid)

async def generate(client,event,uid,prompt):
    key=(event.chat_id,uid)
    if not cooldown(key, GROUP_COOLDOWN_SECONDS if event.is_group else COOLDOWN_SECONDS):
        return
    history=get_memory(event.chat_id,uid)
    try:
        answer=await ask(history,prompt)
    except Exception as e:
        print("GEMINI ERROR:",repr(e),flush=True)
        await event.respond("⚠️ AI gagal memproses pesan. Cek log Railway untuk detailnya.")
        return
    add_memory(event.chat_id,uid,"user",prompt)
    add_memory(event.chat_id,uid,"model",answer)
    sent=await event.respond(answer)
    save_ai_message(event.chat_id,uid,sent.id)

async def handle_reply(client,event,uid):
    if not event.is_reply:
        return False
    r=await event.get_reply_message()
    if not r:
        return False
    me=await client.get_me()
    if r.sender_id != me.id:
        return False
    if not is_ai_message(event.chat_id,r.id):
        return False
    if event.is_group:
        if not await can_group(client,event,uid):
            return True
        await generate(client,event,uid,event.raw_text.strip())
        return True
    if not private_chat_enabled(event.chat_id):
        return True
    await generate(client,event,uid,event.raw_text.strip())
    return True

def register_ai(client):
    @client.on(events.NewMessage(incoming=True))
    async def incoming(event):
        if not (event.is_private or event.is_group):
            return
        text=(event.raw_text or "").strip()
        if not text or text.startswith("."):
            return
        sender=await event.get_sender()
        if not sender:
            return
        uid=sender.id

        if event.is_group:
            # Group: only active users, reply or mention.
            if await handle_reply(client,event,uid):
                return
            if not await can_group(client,event,uid):
                return
            me=await client.get_me()
            uname=(me.username or "").lower()
            if uname:
                prefix="@"+uname
                if text.lower().startswith(prefix):
                    prompt=text[len(prefix):].strip()
                    if prompt:
                        await generate(client,event,uid,prompt)
            return

        # Private incoming: .onbot activates the PRIVATE CHAT, not the other user's account ID.
        if not private_chat_enabled(event.chat_id):
            return
        # Required behavior: ordinary incoming messages are silent unless they reply to uBot.
        # Reply mode is the anti-spam path.
        await handle_reply(client,event,uid)

    @client.on(events.NewMessage(outgoing=True))
    async def outgoing(event):
        if not event.is_private:
            return
        text=(event.raw_text or "").strip()
        if not text or not event.is_reply:
            return
        me=await client.get_me()
        r=await event.get_reply_message()
        if not r or r.sender_id != me.id:
            return
        if not private_chat_enabled(event.chat_id):
            return
        # For outgoing self-chat replies, the owner is the conversation user.
        uid=me.id
        if not is_ai_message(event.chat_id,r.id):
            return
        await generate(client,event,uid,text)
