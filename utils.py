
import time
from collections import defaultdict
from telethon.tl.types import User

last=defaultdict(float)

def cooldown(key,seconds):
    t=time.monotonic()
    if t-last[key]<seconds: return False
    last[key]=t; return True

async def is_admin(client,chat_id,user_id):
    try:
        p=await client.get_permissions(chat_id,user_id)
        return bool(p.is_admin or p.is_creator)
    except Exception: return False

async def target(event,client):
    if event.is_reply:
        m=await event.get_reply_message()
        if m and m.sender_id:
            try: return await client.get_entity(m.sender_id)
            except Exception: pass
    p=event.raw_text.split(maxsplit=1)
    if len(p)>1 and p[1].split()[0].startswith("@"):
        try: return await client.get_entity(p[1].split()[0][1:])
        except Exception: pass
    return None

def name(entity):
    if isinstance(entity,User):
        return "@"+entity.username if entity.username else (entity.first_name or str(entity.id))
    return str(getattr(entity,"title",entity.id))
