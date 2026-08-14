
from telethon import events
from database import *
from gemini import ask
from utils import cooldown,is_admin
from config import COOLDOWN_SECONDS,GROUP_COOLDOWN_SECONDS

async def can_group(client,event,uid):
    if is_banned(event.chat_id,uid) or is_muted(event.chat_id,uid): return False
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

def register_ai(client):
    @client.on(events.NewMessage(incoming=True))
    async def incoming(event):
        if not (event.is_private or event.is_group): return
        if not event.raw_text or event.raw_text.startswith("."): return
        sender=await event.get_sender()
        if not sender: return
        uid=sender.id

        if event.is_group:
            if not await can_group(client,event,uid): return
            if event.is_reply:
                r=await event.get_reply_message()
                me=await client.get_me()
                if r and r.sender_id==me.id and is_ai_message(event.chat_id,r.id,uid):
                    await generate(client,event,uid,event.raw_text.strip()); return
            me=await client.get_me()
            uname=(me.username or "").lower()
            if uname:
                prefix="@"+uname
                txt=event.raw_text.strip()
                if txt.lower().startswith(prefix):
                    prompt=txt[len(prefix):].strip()
                    if prompt: await generate(client,event,uid,prompt)

    @client.on(events.NewMessage(outgoing=True))
    async def outgoing_reply(event):
        if not event.is_private or not event.raw_text or event.raw_text.startswith(".") or not event.is_reply: return
        me=await client.get_me()
        r=await event.get_reply_message()
        if r and r.sender_id==me.id and is_ai_message(event.chat_id,r.id,me.id) and private_enabled(me.id):
            await generate(client,event,me.id,event.raw_text.strip())
