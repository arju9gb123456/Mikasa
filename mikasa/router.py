"""Smart samajh: galat suna hua text bhi samajh ke sahi command nikalna.

Whisper kabhi "VS Code open karo" ko "bs को दोपन करो" sun leta hai. Rule-based
commands tab fail ho jaate hain. Ye router Ollama (local LLM) se ek hi tez call
mein poochta hai: Arjun sir ne asal mein kya bola, kaunsa kaam karna hai, aur
agar normal baat-cheet hai to uska chhota jawab.

Seedha Ollama HTTP API use hota hai (OpenJarvis agent se kaafi tez), model
memory mein garam rakha jata hai (keep_alive), aur Qwen3 ka "thinking" band.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from collections import deque
from typing import Optional

import httpx

from mikasa import persona, settings

INTENTS = """
open_app      {"app": KEY}                    app/website kholna
close_app     {"app": KEY}                    app band karna
search        {"app": KEY, "query": "..."}    kisi site pe search (google, youtube, gmail, maps, github, linkedin, instagram, spotify, drive)
play          {"query": "..."}                YouTube pe gaana/video chalana
note_add      {"text": "..."}                 note save / "yaad rakhna" wali baat
note_list     {}                              notes sunana
task_add      {"text": "...", "due": "YYYY-MM-DD HH:MM"}  task/reminder add; time bola ho to due bharo (abhi ke time se calculate karo), warna due khaali
task_list     {}                              pending tasks batana
task_done     {"text": "..."}                 task done mark
whatsapp      {"contact": "...", "message": "..."}  WhatsApp Web pe chat kholna / message type karna (message khaali ho sakta hai)
code_write    {"text": "..."}                 code likhna (VS Code mein khulega). text = kya banana hai
code_run      {}                              last code chalana
time          {}
date          {}
volume_up     {}
volume_down   {}
mute          {}
screenshot    {}
web           {"query": "..."}                aisa sawaal jiske liye internet chahiye (news, score, price, aaj ka mausam)
chat          {"reply": "..."}                normal baat-cheet / general knowledge sawaal - reply mein jawab
unclear       {"reply": "..."}                bilkul samajh na aaye - reply mein politely dobara bolne ko kaho
"""

SYSTEM = """Tum Mikasa ho: {user} ki personal AI voice assistant, jo unke Windows laptop pe chalti hai. \
Tumhe {creator} sir ne banaya hai. {user} ko hamesha "{user}" kehkar bulao.
{personality}

{user} ki awaaz ka speech-to-text NOISY hai: Hindi/Hinglish mein English app names aksar galat likhe aate hain. \
Examples:
- "मुझे bs को दोपन करो" = "mujhe VS Code open karo" -> open_app vscode
- "क्रो मुपन करूं" / "क्रोम ओपन" = "Chrome open karo" -> open_app chrome
- "जी मेल खोलो" / "gmail kholo" -> open_app gmail
- "यू ट्यूब पे अरिजीत के गाने" -> play "arijit singh songs"
- "वाट्स ऐप पे राहुल को बोलो मैं आ रहा हूं" -> whatsapp contact "Rahul" message "Main aa raha hoon"
Sabse sambhavit matlab socho. Command jaisa lage to command intent do, chat nahi.

Available app KEYs: {apps}

Intents (naam, fields, matlab):
{intents}

{memory}

Sirf ek JSON object do: {{"intent": "...", ...fields}}. Koi aur text nahi.
chat/unclear ka "reply": Hinglish (Roman script), upar wali personality mein, 1-3 natural sentences, bolne layak, \
koi markdown/emoji nahi, "{user}" kehkar. Abhi ka time: {now}."""


class Router:
    def __init__(self) -> None:
        self._history: deque[tuple[str, str]] = deque(maxlen=8)
        self._think_ok = True
        self.base = settings.OLLAMA_URL.rstrip("/")

    def _system(self) -> str:
        return SYSTEM.format(
            user=settings.USER_NAME,
            creator=settings.CREATOR_NAME,
            apps=", ".join(settings.APPS.keys()),
            intents=INTENTS.strip(),
            personality=persona.personality(),
            memory=self._memory(),
            now=_dt.datetime.now().strftime("%A %d %B %Y, %I:%M %p"),
        )

    @staticmethod
    def _memory() -> str:
        """Jo Arjun sir ne yaad rakhne ko kaha + pending tasks, taaki Mikasa baat-cheet mein yaad rakhe."""
        try:
            from mikasa.commands import load_tasks, recent_notes

            notes = recent_notes(12)
            tasks = [x for x in load_tasks() if not x.get("done")][:8]
        except Exception:
            return ""
        lines = []
        if notes:
            lines.append("Arjun sir ne ye baatein yaad rakhne/likhne ko kahi thi (zarurat ho to inka zikr karo):")
            lines += [f"- {n}" for n in notes]
        if tasks:
            lines.append("Unke pending tasks/reminders:")
            lines += [f"- {x['task']}" + (f" (due {x['due']})" if x.get("due") else "") for x in tasks]
        return "\n".join(lines)

    def _post(self, payload: dict, timeout: float) -> dict:
        r = httpx.post(f"{self.base}/api/chat", json=payload, timeout=timeout)
        if r.status_code == 400 and "think" in payload:
            # purana Ollama "think" option nahi jaanta
            self._think_ok = False
            payload.pop("think", None)
            r = httpx.post(f"{self.base}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _payload(self, messages: list[dict], json_mode: bool, max_tokens: int) -> dict:
        p = {
            "model": settings.BRAIN_MODEL or "qwen3:8b",
            "messages": messages,
            "stream": False,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
            "options": {"temperature": 0.6, "num_predict": max_tokens},
        }
        if json_mode:
            p["format"] = "json"
        if self._think_ok:
            p["think"] = False
        return p

    def warmup(self) -> bool:
        """Model ko GPU/RAM mein pehle se load kar do, taaki pehla jawab tez aaye."""
        try:
            self._post(self._payload([{"role": "user", "content": "hi"}], False, 1), timeout=120)
            print("[Mikasa] AI model ready.")
            return True
        except Exception as exc:
            print(f"[Mikasa] AI model abhi load nahi hua ({type(exc).__name__}). Ollama chalu hai?")
            return False

    def route(self, heard: str) -> Optional[dict]:
        messages = [{"role": "system", "content": self._system()}]
        for u, a in self._history:
            messages.append({"role": "user", "content": u})
            messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": heard})
        try:
            data = self._post(self._payload(messages, True, 260), timeout=60)
        except Exception as exc:
            print(f"[Mikasa] Router error: {exc}")
            return None
        content = (data.get("message") or {}).get("content", "")
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
        try:
            d = json.loads(content)
        except Exception:
            m = re.search(r"\{.*\}", content, flags=re.S)
            if not m:
                return None
            try:
                d = json.loads(m.group(0))
            except Exception:
                return None
        if not isinstance(d, dict) or "intent" not in d:
            return None
        self._history.append((heard, json.dumps(d, ensure_ascii=False)))
        print(f"\033[2m(samjha: {json.dumps(d, ensure_ascii=False)})\033[0m")
        return d
