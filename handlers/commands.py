
from telethon import events
from database import *
from handlers.ai import generate
from handlers.group import activation_allowed,moderation
from utils import is_admin,name
from config import OWNER_IDS

def register_commands(client,login_id):
    owners=set(OWNER_IDS)|{login_id}

    @client.on(events.NewMessage(incoming=True,outgoing=True))
    async def commands(event):
        txt=(event.raw_text or "").strip()
        if not txt.startswith("."): return
        p=txt.split()
        cmd=p[0].lower()
        sender=await event.get_sender()
        if not sender: return
        uid=sender.id

        if cmd==".onbot":
            if event.is_group:
                if not await activation_allowed(client,event,uid):
                    await event.respond("❌ Kamu belum diizinkan menggunakan AI di grup ini."); return
                if group_ai_enabled(event.chat_id,uid):
                    await event.respond("⚠️ Asisten AI kamu sudah menyala."); return
                set_group_ai(event.chat_id,uid,True)
                await event.respond("👋 Halo, salam kenal. Saya Setyaa — Asisten AI Anda.

🤖 Saya hadir untuk membantu menjawab pertanyaan, memberikan informasi, serta menemani berbagai kebutuhan Anda.

💬 Silakan mulai percakapan. Saya siap membantu kapan saja.")
            else:
                if private_chat_enabled(event.chat_id):
                    await event.respond("⚠️ Asisten AI kamu sudah menyala."); return
                set_private_chat(event.chat_id,True)
                await event.respond("👋 Halo, salam kenal!
Saya Setya, Asisten AI yang siap menemani Anda berbicara, bertukar pikiran, atau sekadar menjadi teman cerita.

✨ Silakan sampaikan apa pun yang ingin Anda ceritakan. Saya siap mendengarkan.

❗ This account is now registered as a user of Setya AI Bot.
📩 To contact the owner, please reach out to @padukaanse")
            return

        if cmd==".offbot":
            if event.is_group: set_group_ai(event.chat_id,uid,False)
            else: set_private_chat(event.chat_id,False)
            await event.respond("🔴 Asisten AI telah dimatikan."); return

        if cmd==".aistatus":
            if event.is_group:
                g=get_group(event.chat_id)
                await event.respond(f"🤖 AI Status\nStatus: {'ON' if group_ai_enabled(event.chat_id,uid) else 'OFF'}\nPermission: {g['ai_permission']}\nMemory: ON")
            else:
                await event.respond(f"🤖 AI Status\nStatus: {'ON' if private_chat_enabled(event.chat_id) else 'OFF'}\nMemory: ON")
            return

        if cmd==".aireset":
            clear_memory(event.chat_id,uid); await event.respond("🧠 Memory percakapan kamu telah dihapus."); return

        if cmd==".pai":
            if len(p)<2:
                await event.respond("Gunakan: `.pai <pertanyaan>`"); return
            if event.is_group:
                if not await activation_allowed(client,event,uid) or not group_ai_enabled(event.chat_id,uid):
                    await event.respond("❌ Aktifkan AI dulu dengan `.onbot` dan pastikan kamu punya izin."); return
            elif not private_chat_enabled(event.chat_id):
                await event.respond("❌ Aktifkan AI dulu dengan `.onbot`."); return
            await generate(client,event,uid,txt.split(maxsplit=1)[1])
            return

        if cmd==".allow":
            if uid not in owners:
                await event.respond("❌ Command ini hanya untuk owner."); return
            args=p[1:]
            if args and args[0].lower()=="grup":
                await group_permission(event,args[1:]); return
            await ai_permission(event,args); return

        if cmd in (".mute",".unmute",".ban",".unban"):
            await moderation(client,event,cmd,uid,owners); return

        if cmd==".menu":
            await event.respond(
                "🤖 uBot AI\n\n"
                ".onbot — aktifkan AI\n.offbot — matikan AI\n.aistatus — status\n.aireset — reset memory\n"
                ".pai <pertanyaan> — tanya AI\n\n"
                "Permission AI:\n.allow @username\n.allow allmember\n.allow allmember+admin\n\n"
                "Permission grup:\n.allow grup @username\n.allow grup all admin\n.allow grup nobody\n\n"
                ".mute / .unmute / .ban / .unban — target via reply/@username"
            )

    async def ai_permission(event,args):
        if not event.is_group:
            await event.respond("❌ Permission AI hanya bisa diatur di grup."); return
        if not args:
            await event.respond("Format: `.allow @username` | `.allow allmember` | `.allow allmember+admin`"); return
        x=args[0].lower()
        if x=="allmember":
            set_ai_permission(event.chat_id,"allmember"); await event.respond("👥 Permission AI diubah ke semua member."); return
        if x=="allmember+admin":
            set_ai_permission(event.chat_id,"allmember+admin"); await event.respond("👥 Permission AI diubah ke semua member + admin."); return
        if x.startswith("@"):
            try: t=await event.client.get_entity(x[1:])
            except Exception:
                await event.respond("❌ User tidak ditemukan."); return
            if ai_allowed_selected(event.chat_id,t.id):
                await event.respond(f"⚠️ {name(t)} sudah memiliki akses AI."); return
            add_ai_allowed(event.chat_id,t.id); await event.respond(f"✅ {name(t)} sekarang diizinkan menggunakan AI."); return
        await event.respond("❌ Format tidak dikenali.")

    async def group_permission(event,args):
        if not event.is_group:
            await event.respond("❌ Permission grup hanya bisa diatur di grup."); return
        if args and args[0].lower()=="all" and len(args)>1 and args[1].lower()=="admin":
            set_group_permission(event.chat_id,"alladmin"); await event.respond("🛡️ Semua admin sekarang dapat mengelola grup."); return
        if args and args[0].lower()=="nobody":
            set_group_permission(event.chat_id,"nobody"); await event.respond("🔒 Permission pengelolaan grup dinonaktifkan untuk user lain."); return
        if args and args[0].startswith("@"):
            try: t=await event.client.get_entity(args[0][1:])
            except Exception:
                await event.respond("❌ User tidak ditemukan."); return
            if group_allowed_selected(event.chat_id,t.id):
                await event.respond(f"⚠️ {name(t)} sudah memiliki permission pengelolaan grup."); return
            add_group_allowed(event.chat_id,t.id); await event.respond(f"🛡️ {name(t)} sekarang dapat mengelola grup."); return
        await event.respond("❌ Format tidak dikenali.")

