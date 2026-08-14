
from database import *
from utils import target,name,is_admin
async def activation_allowed(client,event,uid):
    admin=await is_admin(client,event.chat_id,uid)
    return ai_permission_allows(event.chat_id,uid,admin) and not is_banned(event.chat_id,uid) and not is_muted(event.chat_id,uid)

async def moderation(client,event,cmd,uid,owners):
    if not event.is_group:
        await event.respond("❌ Fitur ini hanya bisa digunakan di grup."); return
    ok=uid in owners or await is_admin(client,event.chat_id,uid) and await is_admin(client,event.chat_id,uid) and group_permission_allows(event.chat_id,uid,True)
    if not ok:
        ok=uid in owners
    if not ok:
        await event.respond("❌ Kamu tidak memiliki permission pengelolaan grup."); return
    t=await target(event,client)
    if not t or not hasattr(t,"id"):
        await event.respond("❌ Target tidak ditemukan. Reply pesan target atau gunakan @username."); return
    me=await client.get_me()
    if t.id==me.id:
        await event.respond("❌ Aku tidak bisa mengelola akun userbot sendiri."); return
    if await is_admin(client,event.chat_id,t.id):
        await event.respond("❌ Target adalah admin grup."); return
    try:
        if cmd==".mute":
            if is_muted(event.chat_id,t.id):
                await event.respond(f"⚠️ {name(t)} sudah terkena mute sebelumnya."); return
            await client.edit_permissions(event.chat_id,t,send_messages=False)
            set_status(event.chat_id,t.id,"muted",True)
            await event.respond(f"🔇 {name(t)} berhasil di-mute.")
        elif cmd==".unmute":
            if not is_muted(event.chat_id,t.id):
                await event.respond(f"⚠️ {name(t)} tidak sedang terkena mute."); return
            await client.edit_permissions(event.chat_id,t,send_messages=True)
            set_status(event.chat_id,t.id,"muted",False)
            await event.respond(f"🔊 {name(t)} berhasil di-unmute.")
        elif cmd==".ban":
            if is_banned(event.chat_id,t.id):
                await event.respond(f"⚠️ {name(t)} sudah terkena ban sebelumnya."); return
            await client.edit_permissions(event.chat_id,t,view_messages=False)
            set_status(event.chat_id,t.id,"banned",True)
            await event.respond(f"🚫 {name(t)} berhasil di-ban.")
        elif cmd==".unban":
            if not is_banned(event.chat_id,t.id):
                await event.respond(f"⚠️ {name(t)} tidak sedang terkena ban."); return
            await client.edit_permissions(event.chat_id,t,view_messages=True,send_messages=True)
            set_status(event.chat_id,t.id,"banned",False)
            await event.respond(f"✅ {name(t)} berhasil di-unban.")
    except Exception as e:
        print("MODERATION ERROR:",repr(e),flush=True)
        await event.respond("❌ Aksi gagal. Pastikan userbot adalah admin grup dan punya izin.")
