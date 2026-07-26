import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)


def _list(key: str, default: str = "") -> list[str]:
    val = os.getenv(key, default)
    return [v.strip() for v in val.split(",") if v.strip()]


TG_API_ID = int(os.getenv("TG_API_ID") or "0")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_PHONE = os.getenv("TG_PHONE", "")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_CHAT_ID = os.getenv("BOT_CHAT_ID", "")

TG_CHANNELS: list[str] = _list("TG_CHANNELS")
KEYWORDS: list[str] = _list(
    "KEYWORDS",
    "нужен сайт,сделайте сайт,разработка сайта,создание сайта,лендинг,"
    "интернет-магазин,продвижение сайта,seo,контекстная реклама,верстка",
)
KEYWORDS = [k.lower() for k in KEYWORDS]

MIN_BUDGET: int = int(os.getenv("MIN_BUDGET") or "0")
MIN_RELEVANCE_SCORE: int = int(os.getenv("MIN_RELEVANCE_SCORE") or "80")
POLL_INTERVAL_MINUTES: int = int(os.getenv("POLL_INTERVAL_MINUTES") or "10")

DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

POLZA_API_KEY = os.getenv("POLZA_API_KEY", "")

VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_GROUPS: list[str] = _list(
    "VK_GROUPS",
    "freelance_pro,web_zakazy,seo_zakazy,it_freelance",
)

YOUDO_LOGIN = os.getenv("YOUDO_LOGIN", "")
YOUDO_PASSWORD = os.getenv("YOUDO_PASSWORD", "")
