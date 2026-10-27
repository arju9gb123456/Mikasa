"""Reminders: "5 baje yaad dila dena", "10 minute baad", "kal subah 7 baje" samajhna
aur time aane pe Mikasa se bulwana.
"""

from __future__ import annotations

import datetime as _dt
import re
import threading
from typing import Callable, Optional

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_WORD_NUM = {
    "ek": 1, "एक": 1, "do": 2, "दो": 2, "teen": 3, "तीन": 3, "char": 4, "chaar": 4, "चार": 4, "paanch": 5,
    "panch": 5, "पांच": 5, "पाँच": 5, "chhe": 6, "chhah": 6, "छह": 6, "छः": 6, "saat": 7, "सात": 7, "aath": 8,
    "आठ": 8, "nau": 9, "नौ": 9, "das": 10, "दस": 10, "gyarah": 11, "ग्यारह": 11, "barah": 12, "baarah": 12,
    "बारह": 12, "pandrah": 15, "पंद्रह": 15, "bees": 20, "बीस": 20, "tees": 30, "तीस": 30, "chalis": 40,
    "पैंतालीस": 45, "pachas": 50, "पचास": 50,
}


def _prep(text: str) -> str:
    t = text.lower().translate(_DEV_DIGITS).replace("़", "")
    for w, n in _WORD_NUM.items():
        t = re.sub(rf"(?<![\wऀ-ॿ]){re.escape(w)}(?![\wऀ-ॿ])", str(n), t)
    return t


def parse_due(text: str, now: Optional[_dt.datetime] = None) -> Optional[_dt.datetime]:
    """Hinglish/Hindi time phrase -> datetime. Na mile to None."""
    now = now or _dt.datetime.now()
    t = _prep(text)

    # aadha ghanta / aadhe ghante baad
    if re.search(r"(aadh|aadhe|आध)\S*\s*(ghant|घंट)", t):
        return now + _dt.timedelta(minutes=30)
    # N minute / ghante / second baad
    m = re.search(r"(\d+)\s*(minute|minutes|min|mins|मिनट|ghante|ghanta|ghanton|hour|hours|hr|घंटे|घंटा|second|seconds|sec|सेकंड)"
                  r"\s*(baad|बाद|mein|में|me|later|after)?", t)
    if m and (m.group(3) or re.search(r"(baad|बाद|later|after)", t)):
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith(("min", "मिनट")):
            return now + _dt.timedelta(minutes=n)
        if unit.startswith(("sec", "सेकंड")):
            return now + _dt.timedelta(seconds=n)
        return now + _dt.timedelta(hours=n)

    day = 0
    if re.search(r"(parso|parson|परसों|परसो)", t):
        day = 2
    elif re.search(r"(?<![\wऀ-ॿ])(kal|कल|tomorrow)(?![\wऀ-ॿ])", t):
        day = 1

    period = None
    if re.search(r"(subah|सुबह|morning|savere|सवेरे)", t):
        period = "am"
    elif re.search(r"(dopahar|dopehar|दोपहर|afternoon)", t):
        period = "noon"
    elif re.search(r"(shaam|sham|शाम|evening)", t):
        period = "pm"
    elif re.search(r"(raat|रात|night)", t):
        period = "night"
    if re.search(r"\b(am|a\.m)\b", t):
        period = "am"
    elif re.search(r"\b(pm|p\.m)\b", t):
        period = "pm"

    hour = minute = None
    m = re.search(r"(\d{1,2})\s*[:.]\s*(\d{2})", t)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"(\d{1,2})\s*(baje|बजे|baj|बज|o'?clock|vaje)", t)
        if m:
            hour, minute = int(m.group(1)), 0
            m2 = re.search(r"(sava|savva|सवा)\s*" + re.escape(str(hour)), t)
            m3 = re.search(r"(saadhe|sadhe|साढ़े|साढे)\s*" + re.escape(str(hour)), t)
            m4 = re.search(r"(pone|paune|पौने)\s*" + re.escape(str(hour)), t)
            if m2:
                minute = 15
            elif m3:
                minute = 30
            elif m4:
                hour, minute = hour - 1, 45
        elif period and day:
            hour, minute = {"am": 8, "noon": 13, "pm": 18, "night": 21}[period], 0
        elif day:
            hour, minute = 9, 0  # "kal yaad dilana" -> kal subah 9 baje
    if hour is None or not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return None

    if hour < 12:
        if period in ("pm", "noon") or (period == "night" and hour >= 6):
            hour += 12
        elif period is None and 1 <= hour <= 7:
            # "5 baje" bina subah/shaam ke -> aam taur pe shaam ke 5
            hour += 12
    base = (now + _dt.timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if day == 0 and period is None and base <= now and hour < 12:
        # "5 baje" bola aur subah ke 5 nikal gaye -> shaam ke 5
        if base + _dt.timedelta(hours=12) > now:
            base += _dt.timedelta(hours=12)
    if base <= now:
        base += _dt.timedelta(days=1)
    return base


_TIME_BITS = [
    r"(aadh|aadhe|आध)\S*\s*(ghant|घंट)\S*\s*(baad|बाद)?",
    r"\d+\s*(minute|minutes|min|mins|मिनट|ghante|ghanta|hour|hours|hr|घंटे|घंटा|second|seconds|sec|सेकंड)\s*(baad|बाद|mein|में|me|later)?",
    r"(sava|savva|सवा|saadhe|sadhe|साढ़े|साढे|pone|paune|पौने)\s*(?=\d)",
    r"\d{1,2}\s*[:.]\s*\d{2}\s*(baje|बजे|pe|पे|par|पर|ko|को|am|pm)?",
    r"\d{1,2}\s*(baje|बजे|baj|बज|o'?clock)\s*(pe|पे|par|पर|ko|को)?",
    r"(?<![\w\u0900-\u097f])(kal|कल|parso|parson|परसों|tomorrow|aaj|आज)(?![\w\u0900-\u097f])",
    r"(subah|सुबह|savere|सवेरे|dopahar|dopehar|दोपहर|shaam|sham|शाम|raat|रात)\s*(ko|को)?",
]


def strip_time(text: str) -> str:
    """Task text se time wale words hatao: "kal 5 baje gym jana hai" -> "gym jana hai"."""
    t = _prep(text)
    for pat in _TIME_BITS:
        t = re.sub(pat, " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    return t or text


def spoken_time(due: _dt.datetime, now: Optional[_dt.datetime] = None) -> str:
    now = now or _dt.datetime.now()
    clock = due.strftime("%I:%M %p").lstrip("0")
    if due.date() == now.date():
        mins = int((due - now).total_seconds() // 60)
        if mins < 60:
            return f"{max(mins, 1)} minute baad" if mins >= 1 else "abhi thodi der mein"
        return f"aaj {clock} pe"
    if due.date() == (now + _dt.timedelta(days=1)).date():
        return f"kal {clock} pe"
    return due.strftime("%d %b, ") + clock + " pe"


class ReminderWatcher:
    """Background thread: har 15 second tasks check karo, time aaya to callback(task_text)."""

    def __init__(self, load: Callable[[], list], save: Callable[[list], None], fire: Callable[[str, bool], None]) -> None:
        self._load, self._save, self._fire = load, save, fire
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.check()
            except Exception as exc:
                print(f"[Mikasa] Reminder check error: {exc}")
            self._stop.wait(15)

    def check(self) -> None:
        now = _dt.datetime.now()
        with self._lock:
            tasks = self._load()
            changed = False
            for x in tasks:
                due = x.get("due")
                if not due or x.get("done") or x.get("notified"):
                    continue
                try:
                    when = _dt.datetime.fromisoformat(due)
                except Exception:
                    continue
                if when <= now:
                    x["notified"] = True
                    changed = True
                    late = (now - when).total_seconds() > 300
                    self._fire(x["task"], late)
            if changed:
                self._save(tasks)
