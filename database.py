
import sqlite3, threading
from datetime import datetime, timezone
from config import DB_PATH, MAX_MEMORY_MESSAGES

LOCK=threading.RLock()

def now(): return datetime.now(timezone.utc).isoformat()

def connect():
    con=sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK, connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS private_ai(user_id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS private_chats(chat_id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS groups(chat_id INTEGER PRIMARY KEY, ai_permission TEXT NOT NULL DEFAULT 'nobody',
                                           group_permission TEXT NOT NULL DEFAULT 'nobody');
        CREATE TABLE IF NOT EXISTS ai_allowed(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                                               PRIMARY KEY(chat_id,user_id));
        CREATE TABLE IF NOT EXISTS group_allowed(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                                                  PRIMARY KEY(chat_id,user_id));
        CREATE TABLE IF NOT EXISTS group_users(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                                                ai_enabled INTEGER NOT NULL DEFAULT 0,
                                                muted INTEGER NOT NULL DEFAULT 0,banned INTEGER NOT NULL DEFAULT 0,
                                                PRIMARY KEY(chat_id,user_id));
        CREATE TABLE IF NOT EXISTS memory(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                                          role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ai_messages(chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                                                message_id INTEGER NOT NULL,created_at TEXT NOT NULL,
                                                PRIMARY KEY(chat_id,message_id));
        """)

def ensure_group(chat_id):
    with LOCK,connect() as c:
        c.execute("INSERT OR IGNORE INTO groups(chat_id) VALUES(?)",(chat_id,))

def get_group(chat_id):
    ensure_group(chat_id)
    with connect() as c:
        return c.execute("SELECT * FROM groups WHERE chat_id=?",(chat_id,)).fetchone()

def set_ai_permission(chat_id,mode):
    ensure_group(chat_id)
    with LOCK,connect() as c:
        c.execute("UPDATE groups SET ai_permission=? WHERE chat_id=?",(mode,chat_id))
        if mode!="selected": c.execute("DELETE FROM ai_allowed WHERE chat_id=?",(chat_id,))

def add_ai_allowed(chat_id,user_id):
    ensure_group(chat_id)
    with LOCK,connect() as c:
        c.execute("UPDATE groups SET ai_permission='selected' WHERE chat_id=?",(chat_id,))
        c.execute("INSERT OR IGNORE INTO ai_allowed VALUES(?,?)",(chat_id,user_id))

def ai_allowed_selected(chat_id,user_id):
    with connect() as c: return bool(c.execute("SELECT 1 FROM ai_allowed WHERE chat_id=? AND user_id=?",(chat_id,user_id)).fetchone())

def set_group_permission(chat_id,mode):
    ensure_group(chat_id)
    with LOCK,connect() as c:
        c.execute("UPDATE groups SET group_permission=? WHERE chat_id=?",(mode,chat_id))
        if mode!="selected": c.execute("DELETE FROM group_allowed WHERE chat_id=?",(chat_id,))

def add_group_allowed(chat_id,user_id):
    ensure_group(chat_id)
    with LOCK,connect() as c:
        c.execute("UPDATE groups SET group_permission='selected' WHERE chat_id=?",(chat_id,))
        c.execute("INSERT OR IGNORE INTO group_allowed VALUES(?,?)",(chat_id,user_id))

def group_allowed_selected(chat_id,user_id):
    with connect() as c: return bool(c.execute("SELECT 1 FROM group_allowed WHERE chat_id=? AND user_id=?",(chat_id,user_id)).fetchone())

def set_private(user_id,on):
    with LOCK,connect() as c:
        c.execute("""INSERT INTO private_ai(user_id,enabled) VALUES(?,?)
                     ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled""",(user_id,int(on)))

def private_enabled(user_id):
    with connect() as c:
        r=c.execute("SELECT enabled FROM private_ai WHERE user_id=?",(user_id,)).fetchone()
        return bool(r and r["enabled"])

def set_private_chat(chat_id,on):
    with LOCK,connect() as c:
        c.execute("INSERT INTO private_chats(chat_id,enabled) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET enabled=excluded.enabled",(chat_id,int(on)))

def private_chat_enabled(chat_id):
    with connect() as c:
        r=c.execute("SELECT enabled FROM private_chats WHERE chat_id=?",(chat_id,)).fetchone()
        return bool(r and r["enabled"])

def ensure_group_user(chat_id,user_id):
    ensure_group(chat_id)
    with LOCK,connect() as c:
        c.execute("INSERT OR IGNORE INTO group_users(chat_id,user_id) VALUES(?,?)",(chat_id,user_id))

def set_group_ai(chat_id,user_id,on):
    ensure_group_user(chat_id,user_id)
    with LOCK,connect() as c:
        c.execute("UPDATE group_users SET ai_enabled=? WHERE chat_id=? AND user_id=?",(int(on),chat_id,user_id))

def group_ai_enabled(chat_id,user_id):
    with connect() as c:
        r=c.execute("SELECT ai_enabled FROM group_users WHERE chat_id=? AND user_id=?",(chat_id,user_id)).fetchone()
        return bool(r and r["ai_enabled"])

def status(chat_id,user_id):
    ensure_group_user(chat_id,user_id)
    with connect() as c: return c.execute("SELECT * FROM group_users WHERE chat_id=? AND user_id=?",(chat_id,user_id)).fetchone()

def set_status(chat_id,user_id,field,on):
    if field not in ("muted","banned"): raise ValueError(field)
    ensure_group_user(chat_id,user_id)
    with LOCK,connect() as c:
        c.execute(f"UPDATE group_users SET {field}=? WHERE chat_id=? AND user_id=?",(int(on),chat_id,user_id))

def is_muted(chat_id,user_id): return bool(status(chat_id,user_id)["muted"])
def is_banned(chat_id,user_id): return bool(status(chat_id,user_id)["banned"])

def ai_permission_allows(chat_id,user_id,admin):
    mode=get_group(chat_id)["ai_permission"]
    if mode in ("allmember","allmember+admin"): return True
    if mode=="selected": return ai_allowed_selected(chat_id,user_id)
    return False

def group_permission_allows(chat_id,user_id,admin):
    mode=get_group(chat_id)["group_permission"]
    if mode=="alladmin": return admin
    if mode=="selected": return group_allowed_selected(chat_id,user_id)
    return False

def add_memory(chat_id,user_id,role,content):
    with LOCK,connect() as c:
        c.execute("INSERT INTO memory VALUES(?,?,?,?,?)",(chat_id,user_id,role,content,now()))
        old=c.execute("""SELECT rowid FROM memory WHERE chat_id=? AND user_id=?
                         ORDER BY rowid DESC LIMIT -1 OFFSET ?""",
                      (chat_id,user_id,MAX_MEMORY_MESSAGES)).fetchall()
        for r in old: c.execute("DELETE FROM memory WHERE rowid=?",(r["rowid"],))

def get_memory(chat_id,user_id):
    with connect() as c:
        rows=c.execute("SELECT role,content FROM memory WHERE chat_id=? AND user_id=? ORDER BY rowid",(chat_id,user_id)).fetchall()
        return [(r["role"],r["content"]) for r in rows]

def clear_memory(chat_id,user_id):
    with LOCK,connect() as c: c.execute("DELETE FROM memory WHERE chat_id=? AND user_id=?",(chat_id,user_id))

def save_ai_message(chat_id,user_id,message_id):
    with LOCK,connect() as c:
        c.execute("INSERT OR REPLACE INTO ai_messages VALUES(?,?,?,?)",(chat_id,user_id,message_id,now()))

def is_ai_message(chat_id, message_id):
    with connect() as c:
        return bool(c.execute(
            "SELECT 1 FROM ai_messages WHERE chat_id=? AND message_id=?",
            (chat_id, message_id)
        ).fetchone())
