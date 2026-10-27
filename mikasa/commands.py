"""Quick commands: jo kaam laptop pe turant ho sakte hain, AI ke bina.

Apps/websites kholna-band karna, YouTube/Google search, notes, tasks,
time/date, volume, screenshot. Jo yahan match nahi hota wo brain (OpenJarvis)
ke paas jata hai.
"""

from __future__ import annotations

import datetime as _dt
import difflib
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Callable, Optional

from mikasa import settings

# ── text helpers ──────────────────────────────────────────────────────────

_PUNCT = str.maketrans({c: " " for c in ".,!?।॥|\"'“”‘’:;()[]{}-–—/\\"})


def normalize(text: str) -> str:
    """lowercase, punctuation hatao, Devanagari nukta/chandrabindu ek jaisa karo."""
    t = text.lower().translate(_PUNCT)
    t = t.replace("़", "").replace("ँ", "ं")
    return " ".join(t.split())


def _n(words) -> list[str]:
    return [normalize(w) for w in words]


def has_phrase(text: str, phrases) -> bool:
    padded = f" {text} "
    return any(f" {p} " in padded for p in phrases)


def has_stem(tokens: list[str], stems) -> bool:
    return any(tok.startswith(s) for tok in tokens for s in stems)


# Aakhir se sirf ye hatao, taaki "kal dena hai" jaisa matlab na kate
TRAIL_FILLER = {normalize(w) for w in [
    "karo", "kar", "kardo", "lo", "le", "do", "de", "please", "plz", "na", "zara", "jara", "dena",
    "करो", "कर", "लो", "ले", "दो", "दे", "ना", "जरा", "देना", "ye", "yeh", "यह", "ये", "isko",
    "इसको", "isse", "इसे", "ko", "को", "mein", "में", "me", "pe", "par", "पर", "पे", "ki", "की", "कि",
]}


def _strip_edges(tokens: list[str], filler: set[str], trail: Optional[set[str]] = None) -> list[str]:
    trail = filler if trail is None else trail
    start, end = 0, len(tokens)
    while start < end and tokens[start] in filler:
        start += 1
    while end > start and tokens[end - 1] in trail:
        end -= 1
    return tokens[start:end]


def _extract_around(tokens: list[str], triggers: list[str], filler: set[str]) -> str:
    """Trigger phrase ke aage-peeche ka content nikalo, filler words hata ke."""
    for trig in sorted(triggers, key=len, reverse=True):
        t = trig.split()
        for i in range(len(tokens) - len(t) + 1):
            if tokens[i:i + len(t)] == t:
                before = _strip_edges(tokens[:i], filler, TRAIL_FILLER)
                after = _strip_edges(tokens[i + len(t):], filler, TRAIL_FILLER)
                return " ".join(before + after).strip()
    return " ".join(_strip_edges(tokens, filler, TRAIL_FILLER)).strip()


# ── wake word ─────────────────────────────────────────────────────────────

_WAKE = _n(settings.WAKE_WORDS)


def detect_wake(text: str) -> tuple[bool, str]:
    """Pehle 4 words mein "Mikasa" dhoondo. (mila?, baaki command) return karo."""
    tokens = normalize(text).split()
    for i in range(min(4, len(tokens))):
        for span in (1, 2):  # pehle single word, phir "mi kasa" jaise toote hue
            if i + span > len(tokens):
                continue
            chunk = tokens[i:i + span]
            candidates = {"".join(chunk), " ".join(chunk)}
            for cand in candidates:
                for w in _WAKE:
                    if cand == w or difflib.SequenceMatcher(None, cand, w).ratio() >= settings.WAKE_FUZZY:
                        return True, " ".join(tokens[i + span:])
    return False, normalize(text)


# ── vocab ─────────────────────────────────────────────────────────────────

OPEN_STEMS = _n(["khol", "open", "chalu", "start", "launch", "check", "खोल", "ओपन", "चालू", "स्टार्ट", "लॉन्च", "चेक"])
CLOSE_STEMS = _n(["band", "close", "बंद", "क्लोज", "hata", "हटा"])
SEARCH_STEMS = _n(["search", "सर्च", "dhund", "dhoond", "ढूंढ", "ढूढ", "khoj", "खोज", "find"])
PLAY_STEMS = _n(["play", "प्ले", "baja", "बजा", "chala", "चला", "laga", "लगा", "suna", "सुना"])
SHOW_STEMS = _n(["bata", "बता", "suna", "सुना", "dikha", "दिखा", "padh", "पढ", "read", "show", "list"])
FILLER = set(_n([
    "pe", "par", "पर", "पे", "on", "in", "mein", "में", "me", "karo", "kar", "karna", "kardo",
    "karke", "करो", "कर", "करना", "करके", "do", "दो", "de", "दे", "dena", "देना", "please", "plz",
    "zara", "जरा", "jara", "mujhe", "मुझे", "liye", "लिए", "ek", "एक", "ko", "को", "and", "aur",
    "और", "jao", "जाओ", "ja", "जा", "na", "ना", "lo", "लो", "le", "ले", "hai", "है", "ki", "की",
    "कि", "ye", "yeh", "यह", "ये", "isko", "इसको", "isse", "इसे", "the", "a", "for", "wala", "वाला",
]))

SEARCH_URLS = {
    "youtube": "https://www.youtube.com/results?search_query={q}",
    "google": "https://www.google.com/search?q={q}",
    "chrome": "https://www.google.com/search?q={q}",
    "maps": "https://www.google.com/maps/search/{q}",
    "spotify": "https://open.spotify.com/search/{q}",
    "github": "https://github.com/search?q={q}",
    "gmail": "https://mail.google.com/mail/u/0/#search/{q}",
    "drive": "https://drive.google.com/drive/search?q={q}",
    "linkedin": "https://www.linkedin.com/search/results/all/?keywords={q}",
    "instagram": "https://www.instagram.com/explore/search/keyword/?q={q}",
}

PROCESS_NAMES = {  # band karne ke liye
    "chrome": {"win": "chrome.exe", "mac": "Google Chrome", "linux": "chrome"},
    "whatsapp": {"win": "WhatsApp.exe", "mac": "WhatsApp", "linux": "whatsapp"},
    "spotify": {"win": "Spotify.exe", "mac": "Spotify", "linux": "spotify"},
    "vscode": {"win": "Code.exe", "mac": "Visual Studio Code", "linux": "code"},
    "notepad": {"win": "notepad.exe", "mac": "TextEdit", "linux": "gedit"},
    "calculator": {"win": "CalculatorApp.exe", "mac": "Calculator", "linux": "gnome-calculator"},
}

_APP_NAMES = sorted(
    ((normalize(name), key) for key, app in settings.APPS.items() for name in app["names"]),
    key=lambda x: len(x[0]),
    reverse=True,
)

_HINDI_DAYS = ["Somvaar", "Mangalvaar", "Budhvaar", "Guruvaar", "Shukravaar", "Shanivaar", "Ravivaar"]
_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"]


def _platform() -> str:
    if sys.platform.startswith("win"):
        return "win"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def label(key: str) -> str:
    app = settings.APPS.get(key, {})
    return app.get("label") or app.get("names", [key])[0].title()


def find_app(text: str) -> tuple[Optional[str], Optional[str]]:
    """Text mein sabse lamba matching app naam dhoondo -> (app_key, matched_name)."""
    padded = f" {text} "
    for name, key in _APP_NAMES:
        if f" {name} " in padded:
            return key, name
    return None, None


# ── actions ───────────────────────────────────────────────────────────────

def open_app(key: str) -> bool:
    app = settings.APPS[key]
    plat = _platform()
    cmd = app.get(plat)
    if cmd:
        try:
            if plat == "win":
                try:
                    os.startfile(cmd)  # type: ignore[attr-defined]
                    return True
                except OSError:
                    exe = shutil.which(cmd)
                    if exe:
                        subprocess.Popen(f'"{exe}"', shell=True)
                        return True
            elif plat == "mac":
                if subprocess.run(["open", "-a", cmd], capture_output=True).returncode == 0:
                    return True
            else:
                exe = shutil.which(cmd)
                if exe:
                    subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
        except Exception:
            pass
    url = app.get("url")
    if url:
        webbrowser.open(url)
        return True
    return False


def close_app(key: str) -> bool:
    proc = PROCESS_NAMES.get(key, {}).get(_platform())
    if not proc:
        return False
    plat = _platform()
    try:
        if plat == "win":
            r = subprocess.run(["taskkill", "/IM", proc, "/F"], capture_output=True)
        elif plat == "mac":
            r = subprocess.run(["osascript", "-e", f'quit app "{proc}"'], capture_output=True)
        else:
            r = subprocess.run(["pkill", "-f", proc], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


def open_url(url: str) -> None:
    webbrowser.open(url)


def change_volume(direction: str) -> bool:
    plat = _platform()
    try:
        if plat == "mac":
            script = {
                "up": "set volume output volume ((output volume of (get volume settings)) + 15)",
                "down": "set volume output volume ((output volume of (get volume settings)) - 15)",
                "mute": "set volume output muted not (output muted of (get volume settings))",
            }[direction]
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return True
        import pyautogui

        key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}[direction]
        pyautogui.press(key, presses=1 if direction == "mute" else 5)
        return True
    except Exception:
        return False


def take_screenshot() -> Optional[str]:
    try:
        import pyautogui

        folder = settings.DATA_DIR / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"screenshot_{_dt.datetime.now():%Y%m%d_%H%M%S}.png"
        pyautogui.screenshot(str(path))
        return str(path)
    except Exception:
        return None


# ── notes & tasks storage ─────────────────────────────────────────────────

def _notes_file():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.DATA_DIR / "notes.md"


def _tasks_file():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.DATA_DIR / "tasks.json"


def add_note(content: str) -> None:
    f = _notes_file()
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"- [{_dt.datetime.now():%d %b %Y, %I:%M %p}] {content}\n")


def recent_notes(n: int = 3) -> list[str]:
    f = _notes_file()
    if not f.exists():
        return []
    lines = [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("-")]
    return [ln.split("] ", 1)[-1] for ln in lines[-n:]]


def load_tasks() -> list[dict]:
    f = _tasks_file()
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_tasks(tasks: list[dict]) -> None:
    _tasks_file().write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def add_task(content: str) -> None:
    tasks = load_tasks()
    tasks.append({"task": content, "done": False, "added": _dt.datetime.now().isoformat(timespec="minutes")})
    save_tasks(tasks)


# ── the parser ────────────────────────────────────────────────────────────

@dataclass
class Reply:
    text: str
    sleep: bool = False   # wapas sirf "Mikasa" pe jaagegi
    quit: bool = False    # program band
    then: Optional[Callable[[], "Reply"]] = None  # bolne ke baad ye kaam (lamba kaam: code, WhatsApp)


QUIT_PHRASES = _n([
    "band ho ja", "band ho jao", "बंद हो जा", "बंद हो जाओ", "exit", "quit", "alvida", "अलविदा",
    "goodbye", "good bye", "bye bye", "बाय बाय", "shut down", "shutdown", "khud ko band karo",
])
SLEEP_PHRASES = _n([
    "so ja", "so jao", "सो जा", "सो जाओ", "sleep", "chup ho ja", "chup ho jao", "चुप हो जा",
    "चुप हो जाओ", "chup", "चुप", "bas", "बस", "thank you", "thanks", "shukriya", "शुक्रिया",
    "धन्यवाद", "dhanyavad", "kuch nahi", "कुछ नहीं", "nothing", "rehne do", "रहने दो", "cancel",
])

NOTE_TRIGGERS = _n(["note", "notes", "नोट", "नोट्स", "likh lo", "लिख लो", "likh le", "लिख ले",
                    "likh do", "लिख दो", "yaad rakhna", "याद रखना", "yaad rakh", "याद रख"])
NOTE_FILLER = FILLER | set(_n(["bana", "banao", "बना", "बनाओ", "बनाना", "likh", "likho", "लिख",
                               "लिखो", "rakh", "rakhna", "रख", "रखना", "add", "एड", "naya", "नया",
                               "save", "सेव", "that", "ki", "notes", "note", "नोट"]))
TASK_STRONG = _n(["task", "tasks", "टास्क", "टास्क्स", "todo", "to do", "reminder", "रिमाइंडर",
                  "yaad dila", "याद दिला", "yaad dilana", "याद दिलाना"])
TASK_WEAK = _n(["kaam", "काम"])
TASK_FILLER = NOTE_FILLER | set(_n(["jod", "jodo", "जोड", "जोडो", "daal", "dalo", "डाल", "डालो",
                                    "list", "लिस्ट", "dena", "देना", "dila", "दिला", "task", "टास्क"]))
TASK_DONE = _n(["ho gaya", "हो गया", "ho gayi", "हो गई", "ho gya", "done", "complete", "completed",
                "khatam", "खत्म", "kar liya", "कर लिया", "hata do", "हटा दो", "delete"])
TASK_ADD_STEMS = _n(["add", "एड", "jod", "जोड", "daal", "dal", "डाल", "bana", "बना", "likh", "लिख", "yaad", "याद"])



# ── identity ──
WHO_MADE = _n(["kisne", "किसने", "who made", "who created", "who built", "creator", "क्रिएटर",
               "banane wala", "बनाने वाला", "banaya kisne", "malik", "मालिक", "owner", "developer"])
WHO_ARE_YOU = _n(["kaun ho", "कौन हो", "who are you", "apna naam", "अपना नाम", "tumhara naam",
                  "तुम्हारा नाम", "aapka naam", "आपका नाम", "your name", "introduce", "parichay", "परिचय"])

# ── code ──
CODE_WORDS = _n(["code", "कोड", "program", "प्रोग्राम", "script", "स्क्रिप्ट", "website", "वेबसाइट",
                 "webpage", "html", "python", "पायथन", "function", "फंक्शन", "game", "गेम", "javascript"])
CODE_WRITE_STEMS = _n(["likh", "लिख", "bana", "बना", "write", "generat", "creat", "kar", "कर", "de", "दे"])
CODE_RUN_STEMS = _n(["run", "रन", "chala", "चला", "execut", "test", "टेस्ट"])

# ── WhatsApp ──
MSG_WORDS = _n(["message", "messages", "msg", "मैसेज", "मेसेज", "मैसेज़", "sms", "text", "टेक्स्ट"])
CHAT_WORDS = _n(["chat", "चैट"])
WA_SEPARATORS = set(_n(["aur", "और", "phir", "फिर", "then", "and", "pe", "par", "पर", "पे", "mein", "में",
                        "web", "वेब", "browser", "ब्राउजर", "ek", "एक", "please", "zara", "जरा", "kholo",
                        "खोलो", "open", "karo", "करो", "mujhe", "मुझे", "mere", "मेरे"]))
MSG_EDGE = set(_n(["message", "msg", "मैसेज", "मेसेज", "bhejo", "bhej", "भेजो", "भेज", "send", "karo", "करो",
                   "kar", "कर", "type", "टाइप", "likho", "लिखो", "likh", "लिख", "do", "दो", "de", "दे", "ek",
                   "एक", "ye", "yeh", "ये", "यह", "pe", "par", "पर", "पे", "whatsapp", "व्हाट्सएप", "dena",
                   "देना", "karna", "करना", "hai", "है", "ki", "कि", "की", "ke", "के"]))
YES_WORDS = set(_n(["haan", "han", "ha", "haa", "हां", "हा", "हाँ", "yes", "yeah", "yep", "ok", "okay", "ओके",
                    "bhej", "bhejo", "भेज", "भेजो", "send", "theek", "ठीक", "thik", "bilkul", "बिलकुल", "sure"]))
NO_WORDS = set(_n(["nahi", "nahin", "नहीं", "नही", "no", "nope", "mat", "मत", "cancel", "ruko", "रुको",
                   "rehne", "रहने", "galat", "गलत"]))


def _wa_contact(tokens: list[str], end: int) -> str:
    """tokens[:end] mein se contact ka naam: aakhri separator ke baad wale words."""
    start = 0
    for i in range(end - 1, -1, -1):
        tok = tokens[i]
        if tok in WA_SEPARATORS or find_app(tok)[0] == "whatsapp" or any(tok.startswith(s) for s in OPEN_STEMS):
            start = i + 1
            break
    return " ".join(tokens[start:end]).strip()


def parse_whatsapp(t: str) -> Optional[tuple[str, str, bool]]:
    """(contact, message, sirf_chat?) ya None agar WhatsApp command nahi hai."""
    tokens = t.split()
    app_key, _ = find_app(t)
    has_msg = any(tok in MSG_WORDS for tok in tokens)
    has_chat = any(tok in CHAT_WORDS for tok in tokens)
    # "priti ko good morning bhej do" - bina "whatsapp"/"message" bole bhi
    has_send_to = any(tok in ("ko", "को") for tok in tokens) and has_stem(tokens, _n(["bhej", "भेज", "send"])) \
        and app_key in (None, "whatsapp")
    if not (app_key == "whatsapp" or has_msg or has_send_to or (has_chat and app_key in (None, "whatsapp"))):
        return None
    # "rahul ki chat kholo"
    if has_chat:
        ci = next(i for i, tok in enumerate(tokens) if tok in CHAT_WORDS)
        j = ci - 1 if ci > 0 and tokens[ci - 1] in set(_n(["ki", "की", "ka", "का", "ke", "के", "wali", "वाली"])) else ci
        contact = _wa_contact(tokens, j)
        rest = tokens[ci + 1:]
        message = ""
        if any(tok in MSG_WORDS for tok in rest) or has_phrase(" ".join(rest), _n(["type", "टाइप"])):
            ko = [i for i, tok in enumerate(rest) if tok in ("ki", "कि", "that")]
            body = rest[ko[0] + 1:] if ko else rest
            message = " ".join(_strip_edges(body, MSG_EDGE))
        return contact, message, not message
    # "rahul ko message bhejo ki ..." / "rahul ko hello bhejo"
    ko_idx = [i for i, tok in enumerate(tokens) if tok in ("ko", "को")]
    if not ko_idx:
        return ("", "", True) if app_key == "whatsapp" else ("", "", False)
    k = ko_idx[0]
    contact = _wa_contact(tokens, k)
    after = tokens[k + 1:]
    ki = [i for i, tok in enumerate(after) if tok in ("ki", "कि", "that")]
    body = after[ki[0] + 1:] if ki else after
    message = " ".join(_strip_edges(body, MSG_EDGE))
    return contact, message, False


class Commands:
    def __init__(self, brain=None) -> None:
        self.pending: Optional[str] = None  # "note" / "task" / "wa_*" jab jawab ka intezaar ho
        self.brain = brain
        self._coder = None
        self._wa = None
        self._wa_contact: str = ""
        self._wa_retry = 0

    # ── lazy helpers ──
    def coder(self):
        if self._coder is None:
            from mikasa.coder import Coder

            self._coder = Coder(self.brain)
        return self._coder

    def wa(self):
        if self._wa is None:
            from mikasa.whatsapp import WhatsAppBot

            self._wa = WhatsAppBot()
        return self._wa

    def close(self) -> None:
        if self._wa is not None:
            self._wa.close()

    # ── WhatsApp flow ──
    def whatsapp_flow(self, contact: str, message: str, ask_message: bool) -> Reply:
        def after_login() -> Reply:
            bot = self.wa()
            if not bot.wait_login(120):
                return Reply("WhatsApp login nahi hua. QR scan karke phir boliye.")
            if not contact:
                if ask_message:
                    self.pending = "wa_contact"
                    return Reply("WhatsApp Web khul gaya. Kisko message bhejna hai?")
                return Reply("WhatsApp Web khul gaya.")
            try:
                name = bot.open_chat(contact)
            except Exception as exc:
                print(f"[Mikasa] WhatsApp chat error: {exc}")
                name = None
            if not name:
                return Reply(f"{contact} naam ki chat nahi mili. Naam phir se boliye ya settings mein CONTACTS add kariye.")
            self._wa_contact = name
            if not message:
                if ask_message:
                    self.pending = "wa_msg"
                    return Reply(f"{name} ki chat khul gayi. Kya message likhun?")
                return Reply(f"{name} ki chat khul gayi.")
            return self._wa_type(message)

        def start() -> Reply:
            bot = self.wa()
            try:
                bot.open()
            except Exception as exc:
                print(f"[Mikasa] WhatsApp browser error: {exc}")
                return Reply("WhatsApp ke liye browser nahi khul paya. Edge ya Chrome check kariye.")
            if not bot.is_logged_in(15):
                return Reply("Phone se WhatsApp Web ka QR code scan kariye. Main do minute wait kar rahi hoon.",
                             then=after_login)
            return after_login()

        return Reply("WhatsApp Web khol rahi hoon.", then=start)

    def _wa_type(self, message: str) -> Reply:
        message = message.strip()
        message = message[:1].upper() + message[1:]
        try:
            self.wa().type_message(message)
        except Exception as exc:
            print(f"[Mikasa] WhatsApp type error: {exc}")
            return Reply("Message type nahi ho paya. Chat khuli hai kya, check kariye.")
        self.pending = "wa_confirm"
        self._wa_retry = 0
        return Reply(f"{self._wa_contact} ko ye message type kar diya: {message}. Bhej dun? Haan ya na boliye.")

    def _wa_pending(self, text: str, tokens: list[str]) -> Reply:
        kind = self.pending
        if kind == "wa_contact":
            self.pending = None
            return self.whatsapp_flow(text.strip(), "", True)
        if kind == "wa_msg":
            self.pending = None
            return self._wa_type(text)
        # wa_confirm
        if any(tok in NO_WORDS for tok in tokens):
            self.pending = None
            self.wa().clear_message()
            return Reply("Theek hai, message nahi bheja. Hata diya.")
        if any(tok in YES_WORDS for tok in tokens):
            self.pending = None
            try:
                self.wa().send()
            except Exception as exc:
                print(f"[Mikasa] WhatsApp send error: {exc}")
                return Reply("Message bhej nahi paayi. Browser check kariye.")
            return Reply(f"Message bhej diya {self._wa_contact} ko.")
        self._wa_retry += 1
        if self._wa_retry >= 2:
            self.pending = None
            return Reply("Samajh nahi aaya, isliye message nahi bheja. Type kiya hua chat mein pada hai.")
        return Reply("Bhejna hai to haan boliye, nahi to na.")

    def handle(self, text: str) -> Optional[Reply]:
        t = normalize(text)
        tokens = t.split()
        if not tokens:
            return None
        name = settings.USER_NAME

        # 0. WhatsApp ka pending sawaal (haan/na, kisko, kya message)
        if self.pending and self.pending.startswith("wa_"):
            return self._wa_pending(text, tokens)

        # 0.1 pehchaan
        about_me = has_stem(tokens, _n(["banaya", "बनाया", "bana", "बना", "made", "creat", "built", "tumh", "तुम्ह",
                                        "tujh", "तुझ", "aapk", "आपक", "mikasa", "मिकासा", "you"]))
        if len(tokens) <= 10 and has_phrase(t, WHO_MADE) and (about_me or not has_phrase(t, _n(["kisne", "किसने"]))):
            return Reply(f"Mujhe {settings.CREATOR_NAME} sir ne banaya hai. "
                         f"Main {name} ki personal AI assistant Mikasa hoon.")
        if len(tokens) <= 8 and has_phrase(t, WHO_ARE_YOU):
            return Reply(f"Main Mikasa hoon, {name} ki personal AI assistant. Mujhe {settings.CREATOR_NAME} sir ne "
                         "banaya hai. Main aapke laptop pe apps khol sakti hoon, search, notes, tasks, code aur "
                         "WhatsApp message kar sakti hoon.")

        # 1. quit / sleep
        if has_phrase(t, QUIT_PHRASES) and len(tokens) <= 5:
            return Reply(f"Theek hai {name}, main band ho rahi hoon. Bye!", quit=True)
        if has_phrase(t, SLEEP_PHRASES) and len(tokens) <= 4:
            self.pending = None
            if has_phrase(t, _n(["thank you", "thanks", "shukriya", "शुक्रिया", "धन्यवाद", "dhanyavad"])):
                return Reply(f"Welcome {name}! Zarurat ho to bas Mikasa boliye.", sleep=True)
            return Reply("Theek hai.", sleep=True)

        # 2. pichhla sawaal ("kya likhun?") ka jawab
        if self.pending == "note":
            self.pending = None
            add_note(text.strip())
            return Reply("Note save kar diya.")
        if self.pending == "task":
            self.pending = None
            add_task(text.strip())
            return Reply("Task add kar diya.")

        # 2.5 code likhna / chalana (VS Code)
        vs_names = [normalize(n) for n in settings.APPS.get("vscode", {}).get("names", [])]
        body = f" {t} "
        for vn in sorted(vs_names, key=len, reverse=True):
            body = body.replace(f" {vn} ", " ")
        btoks = body.split()
        strong_write = has_stem(btoks, _n(["likh", "लिख", "bana", "बना", "write", "generat", "creat"]))
        core_code = any(tok in _n(["code", "कोड", "program", "प्रोग्राम", "script", "स्क्रिप्ट"]) for tok in btoks)
        if any(tok in CODE_WORDS for tok in btoks) and not has_stem(btoks, SEARCH_STEMS):
            if core_code and has_stem(btoks, CODE_RUN_STEMS) and not strong_write:
                return Reply("Code chala rahi hoon.", then=lambda: Reply(self.coder().run_last()))
            if strong_write or (core_code and has_stem(btoks, CODE_WRITE_STEMS)):
                task = " ".join(btoks)
                return Reply("Theek hai, code likh rahi hoon. Thoda time lagega.",
                             then=lambda: Reply(self.coder().write(task)))

        # 2.6 WhatsApp Web: chat kholna / message type karna
        wa = parse_whatsapp(t)
        if wa is not None and (settings.WHATSAPP_MODE == "web" or wa[0] or wa[1]):
            contact, message, only_open = wa
            if contact or message or has_stem(tokens, OPEN_STEMS) or any(tok in MSG_WORDS for tok in tokens) \
                    or len(tokens) <= 2:
                ask = not only_open or any(tok in MSG_WORDS for tok in tokens)
                return self.whatsapp_flow(contact, message, ask)

        # 3. notes
        if has_phrase(t, NOTE_TRIGGERS) and not has_phrase(t, TASK_STRONG):
            if has_stem(tokens, OPEN_STEMS):
                path = _notes_file()
                path.touch(exist_ok=True)
                open_url(path.resolve().as_uri())
                return Reply("Notes file khol di.")
            if has_stem(tokens, SHOW_STEMS) and not has_stem(tokens, _n(["likh", "लिख", "bana", "बना"])):
                notes = recent_notes(3)
                if not notes:
                    return Reply("Abhi koi note nahi hai.")
                return Reply("Aapke last notes: " + ". ".join(notes))
            content = _extract_around(tokens, NOTE_TRIGGERS, NOTE_FILLER)
            if not content:
                self.pending = "note"
                return Reply("Haan, kya likhun?")
            add_note(content)
            return Reply(f"Note save kar diya: {content}")

        # 4. tasks
        strong = has_phrase(t, TASK_STRONG)
        weak = has_phrase(t, TASK_WEAK)
        if strong or (weak and (has_stem(tokens, SHOW_STEMS) or has_stem(tokens, TASK_ADD_STEMS))):
            tasks = load_tasks()
            pending = [x for x in tasks if not x.get("done")]
            if has_phrase(t, TASK_DONE) and not has_stem(tokens, TASK_ADD_STEMS):
                if not pending:
                    return Reply("Koi pending task nahi hai.")
                if has_phrase(t, _n(["sab", "सब", "all", "saare", "सारे"])):
                    for x in tasks:
                        x["done"] = True
                    save_tasks(tasks)
                    return Reply("Saare tasks done mark kar diye.")
                query = _extract_around(tokens, TASK_STRONG + TASK_WEAK + TASK_DONE, TASK_FILLER)
                best = max(pending, key=lambda x: difflib.SequenceMatcher(None, normalize(x["task"]), query).ratio())
                best["done"] = True
                save_tasks(tasks)
                return Reply(f"Done mark kar diya: {best['task']}")
            if has_stem(tokens, SHOW_STEMS) or has_phrase(t, _n(["kya hai", "क्या है", "kitne", "कितने",
                                                                 "pending", "baki", "बाकी", "kya kya", "क्या क्या"])):
                if not pending:
                    return Reply("Koi pending task nahi hai. Sab clear!")
                items = ". ".join(f"{i + 1}, {x['task']}" for i, x in enumerate(pending[:7]))
                return Reply(f"Aapke {len(pending)} pending tasks hain. {items}")
            content = _extract_around(tokens, TASK_STRONG + TASK_WEAK, TASK_FILLER)
            if not content:
                self.pending = "task"
                return Reply("Kaunsa task add karun?")
            add_task(content)
            return Reply(f"Task add kar diya: {content}")

        # 5. volume / screenshot
        if has_stem(tokens, _n(["volume", "वॉल्यूम", "वोल्यूम", "awaz", "awaaz", "आवाज"])):
            if has_stem(tokens, _n(["mute", "म्यूट", "band", "बंद", "chup", "चुप"])):
                ok = change_volume("mute")
            elif has_stem(tokens, _n(["kam", "कम", "down", "dheer", "धीर", "low", "slow"])):
                ok = change_volume("down")
            else:
                ok = change_volume("up")
            return Reply("Ho gaya." if ok else "Volume change nahi ho paya.")
        if has_stem(tokens, _n(["screenshot", "स्क्रीनशॉट", "स्क्रीन शॉट"])) or has_phrase(t, _n(["screen shot"])):
            path = take_screenshot()
            return Reply("Screenshot le liya, Mikasa folder mein save hai." if path else "Screenshot nahi le paayi.")

        app_key, app_name = find_app(t)

        # 6. search / play
        searching = has_stem(tokens, SEARCH_STEMS)
        playing = has_stem(tokens, PLAY_STEMS) and not has_stem(tokens, OPEN_STEMS)
        if searching or playing:
            drop = set(FILLER)
            for stems in (SEARCH_STEMS, PLAY_STEMS, OPEN_STEMS):
                drop |= {tok for tok in tokens if any(tok.startswith(s) for s in stems)}
            body = f" {t} "
            if app_name:
                body = body.replace(f" {app_name} ", " ")
            q_tokens = _strip_edges([tok for tok in body.split()], drop)
            q_tokens = [tok for tok in q_tokens if tok not in SEARCH_STEMS]
            query = " ".join(q_tokens).strip()
            platform = app_key if app_key in SEARCH_URLS else ("youtube" if playing and not app_key else
                                                               ("google" if not app_key else None))
            if platform and query:
                open_url(SEARCH_URLS[platform].format(q=urllib.parse.quote_plus(query)))
                if playing and platform == "youtube":
                    return Reply(f"YouTube pe {query} laga rahi hoon.")
                return Reply(f"{label(platform)} pe {query} search kar rahi hoon.")
            if app_key:
                open_app(app_key)
                return Reply(f"{label(app_key)} khol rahi hoon.")

        # 7. close app
        if app_key and has_stem(tokens, CLOSE_STEMS) and not has_stem(tokens, OPEN_STEMS):
            ok = close_app(app_key)
            return Reply(f"{label(app_key)} band kar diya." if ok else f"{label(app_key)} band nahi ho paya.")

        # 8. open app / website
        if app_key and (has_stem(tokens, OPEN_STEMS) or len(tokens) <= 2):
            ok = open_app(app_key)
            return Reply(f"{label(app_key)} khol rahi hoon." if ok else f"{label(app_key)} nahi khul paya.")

        # 9. time / date
        asking = has_stem(tokens, _n(["kya", "क्या", "kitn", "कितन", "bata", "बता", "what", "kaun", "कौन"]))
        now = _dt.datetime.now()
        if asking and has_stem(tokens, _n(["time", "टाइम", "samay", "समय", "baj", "बज"])):
            return Reply(f"Abhi {now:%I:%M %p} ho rahe hain.".replace(" 0", " ", 1))
        if asking and has_stem(tokens, _n(["date", "डेट", "tarikh", "tareekh", "तारीख", "din", "दिन", "day"])):
            return Reply(f"Aaj {_HINDI_DAYS[now.weekday()]}, {now.day} {_MONTHS[now.month - 1]} {now.year} hai.")

        return None
