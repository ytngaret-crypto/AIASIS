import re
from telethon.tl.types import User

USERNAME_RE = re.compile(r"^@([A-Za-z0-9_]{3,32})$")


def is_group_message(message) -> bool:
    return bool(getattr(message, "is_group", False) or getattr(message, "is_channel", False))


def username_from_entity(entity):
    username = getattr(entity, "username", None)
    return f"@{username}" if username else str(getattr(entity, "id", "user"))


def clean_arg_username(value: str):
    value = value.strip()
    if value.startswith("@"):
        value = value[1:]
    return value


def parse_target_argument(text: str):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    arg = parts[1].strip()
    m = USERNAME_RE.match(arg)
    return m.group(1) if m else None
