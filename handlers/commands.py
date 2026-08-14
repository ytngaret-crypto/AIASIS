from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.errors import RPCError

from config import OWNER_ID, AI_PREFIX
from handlers.utils import is_group_message, username_from_entity, parse_target_argument


def setup_command_handlers(client, db, state):
    async def sender_is_owner(event):
        return event.sender_id == OWNER_ID

    async def get_target(event, command_text):
        if event.is_reply:
            reply = await event.get_reply_message()
            return reply.sender_id, reply.sender
        username = parse_target_argument(command_text)
        if not username:
            return None, None
        try:
            entity = await client.get_entity(username)
            return entity.id, entity
        except Exception:
            return None, None

    async def is_admin(chat_id, user_id):
        if user_id == OWNER_ID:
            return True
        try:
            p = await client(GetParticipantRequest(chat_id, user_id))
            participant = p.participant
            return isinstance(participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
        except Exception:
            return False

    async def ai_allowed(chat_id, user_id):
        if user_id == OWNER_ID:
            return True
        muted, banned = db.get_restriction(chat_id, user_id)
        if muted or banned:
            return False
        row = db.get_group(chat_id)
        mode = row["ai_mode"]
        if mode == "allmember":
            return True
        if mode == "allmember+admin":
            return True
        return db.is_ai_explicitly_allowed(chat_id, user_id)

    @client.on(events.NewMessage(pattern=r"^\.onbot$"))
    async def onbot(event):
        if is_group_message(event.message):
            chat_id, user_id = event.chat_id, event.sender_id
            if not await ai_allowed(chat_id, user_id):
                await event.reply("❌ Kamu belum diizinkan menggunakan AI di grup ini.")
                return
            muted, banned = db.get_restriction(chat_id, user_id)
            if muted or banned:
                await event.reply("❌ Kamu sedang tidak memiliki akses AI.")
                return
        else:
            if not await sender_is_owner(event):
                return
            chat_id, user_id = event.chat_id, event.sender_id
        if db.is_enabled(chat_id, user_id):
            await event.reply("⚠️ Asisten AI sudah aktif sebelumnya.")
            return
        db.set_enabled(chat_id, user_id, True)
        await event.reply("🤖 Asisten AI telah menyala.\nSekarang kamu bisa chat seperti biasa tanpa command. Reply pesan AI agar aku merespons chatmu.")

    @client.on(events.NewMessage(pattern=r"^\.offbot$"))
    async def offbot(event):
        if is_group_message(event.message) and event.sender_id != OWNER_ID:
            # normal members can disable their own AI session
            pass
        elif not is_group_message(event.message) and event.sender_id != OWNER_ID:
            return
        chat_id, user_id = event.chat_id, event.sender_id
        if not db.is_enabled(chat_id, user_id):
            await event.reply("⚠️ Asisten AI memang sudah nonaktif.")
            return
        db.set_enabled(chat_id, user_id, False)
        await event.reply("🔴 Asisten AI telah dimatikan.")

    @client.on(events.NewMessage(pattern=r"^\.aistatus$"))
    async def status(event):
        chat_id, user_id = event.chat_id, event.sender_id
        enabled = db.is_enabled(chat_id, user_id)
        memory = bool(db.get_history(chat_id, user_id))
        if is_group_message(event.message):
            row = db.get_group(chat_id)
            text = ("🤖 AI Status\n\n"
                    f"Status: {'ON' if enabled else 'OFF'}\n"
                    f"Mode AI: {row['ai_mode']}\n"
                    f"Memory: {'ON' if memory else 'EMPTY'}")
        else:
            text = ("🤖 AI Status\n\n"
                    f"Status: {'ON' if enabled else 'OFF'}\n"
                    f"Memory: {'ON' if memory else 'EMPTY'}")
        await event.reply(text)

    @client.on(events.NewMessage(pattern=r"^\.aireset$"))
    async def reset(event):
        db.reset_conversation(event.chat_id, event.sender_id)
        await event.reply("🧠 Memory percakapan telah dihapus.")

    @client.on(events.NewMessage(pattern=r"^\.pai(?:\s+(.+))?$"))
    async def pai(event):
        # handled by ai.py; this handler only exists so command registration is explicit
        return

    @client.on(events.NewMessage(pattern=r"^\.allow(?:\s+(.+))?$"))
    async def allow(event):
        if not await sender_is_owner(event) or not is_group_message(event.message):
            return
        arg = (event.pattern_match.group(1) or "").strip().lower()
        chat_id = event.chat_id
        if arg == "allmember":
            db.set_ai_mode(chat_id, "allmember")
            db.clear_ai_users(chat_id)
            await event.reply("👥 Permission AI diubah ke semua member.")
            return
        if arg == "allmember+admin":
            db.set_ai_mode(chat_id, "allmember+admin")
            db.clear_ai_users(chat_id)
            await event.reply("👥 Permission AI diubah ke semua member + admin.")
            return
        if arg.startswith("@"):
            try:
                entity = await client.get_entity(arg)
                db.set_ai_mode(chat_id, "specific")
                db.clear_ai_users(chat_id)
                db.allow_ai_user(chat_id, entity.id)
                await event.reply(f"✅ {username_from_entity(entity)} sekarang diizinkan menggunakan AI.")
            except Exception:
                await event.reply("❌ User tidak ditemukan.")
            return
        await event.reply("❌ Format: .allow @username | .allow allmember | .allow allmember+admin")

    @client.on(events.NewMessage(pattern=r"^\.allow\s+grup(?:\s+(.+))?$"))
    async def allow_group(event):
        if not await sender_is_owner(event) or not is_group_message(event.message):
            return
        arg = (event.pattern_match.group(1) or "").strip().lower()
        chat_id = event.chat_id
        if arg == "nobody":
            db.set_group_mode(chat_id, "nobody")
            db.clear_group_managers(chat_id)
            await event.reply("🔒 Permission pengelolaan grup dimatikan untuk semua user. Hanya owner yang dapat menggunakannya.")
            return
        if arg == "all admin":
            db.set_group_mode(chat_id, "alladmin")
            db.clear_group_managers(chat_id)
            await event.reply("🛡️ Semua admin grup sekarang dapat menggunakan fitur pengelolaan grup.")
            return
        if arg.startswith("@"):
            try:
                entity = await client.get_entity(arg)
                db.set_group_mode(chat_id, "specific")
                db.clear_group_managers(chat_id)
                db.allow_group_manager(chat_id, entity.id)
                await event.reply(f"🛡️ {username_from_entity(entity)} sekarang dapat menggunakan fitur pengelolaan grup.")
            except Exception:
                await event.reply("❌ User tidak ditemukan.")
            return
        await event.reply("❌ Format: .allow grup @username | .allow grup all admin | .allow grup nobody")

    async def can_manage(event):
        if not is_group_message(event.message):
            return False
        if event.sender_id == OWNER_ID:
            return True
        row = db.get_group(event.chat_id)
        if row["group_mode"] == "alladmin":
            return await is_admin(event.chat_id, event.sender_id)
        if row["group_mode"] == "specific":
            return db.is_group_manager(event.chat_id, event.sender_id)
        return False

    async def moderation(event, action: str):
        if not await can_manage(event):
            await event.reply("❌ Kamu tidak memiliki permission untuk fitur pengelolaan grup.")
            return
        target_id, target = await get_target(event, event.raw_text)
        if not target_id:
            await event.reply(f"❌ Target tidak ditemukan. Reply pesan target atau gunakan .{action} @username")
            return
        if target_id == OWNER_ID:
            await event.reply("❌ Owner tidak dapat dikenai tindakan ini.")
            return
        if action == "mute":
            muted, banned = db.get_restriction(event.chat_id, target_id)
            if muted:
                await event.reply(f"⚠️ {username_from_entity(target)} sudah terkena mute sebelumnya.")
                return
            db.set_restriction(event.chat_id, target_id, muted=True)
            await event.reply(f"🔇 {username_from_entity(target)} berhasil di-mute.")
        elif action == "unmute":
            muted, banned = db.get_restriction(event.chat_id, target_id)
            if not muted:
                await event.reply(f"⚠️ {username_from_entity(target)} tidak sedang dalam status mute.")
                return
            db.set_restriction(event.chat_id, target_id, muted=False)
            await event.reply(f"🔊 {username_from_entity(target)} berhasil di-unmute.")
        elif action == "ban":
            muted, banned = db.get_restriction(event.chat_id, target_id)
            if banned:
                await event.reply(f"⚠️ {username_from_entity(target)} sudah terkena ban sebelumnya.")
                return
            db.set_restriction(event.chat_id, target_id, banned=True)
            await event.reply(f"🚫 {username_from_entity(target)} berhasil di-ban dari penggunaan AI.")
        elif action == "unban":
            muted, banned = db.get_restriction(event.chat_id, target_id)
            if not banned:
                await event.reply(f"⚠️ {username_from_entity(target)} tidak sedang terkena ban.")
                return
            db.set_restriction(event.chat_id, target_id, banned=False)
            await event.reply(f"✅ {username_from_entity(target)} berhasil di-unban.")

    @client.on(events.NewMessage(pattern=r"^\.mute(?:\s+@\w+)?$"))
    async def mute(event): await moderation(event, "mute")
    @client.on(events.NewMessage(pattern=r"^\.unmute(?:\s+@\w+)?$"))
    async def unmute(event): await moderation(event, "unmute")
    @client.on(events.NewMessage(pattern=r"^\.ban(?:\s+@\w+)?$"))
    async def ban(event): await moderation(event, "ban")
    @client.on(events.NewMessage(pattern=r"^\.unban(?:\s+@\w+)?$"))
    async def unban(event): await moderation(event, "unban")
