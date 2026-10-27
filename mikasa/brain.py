"""Mikasa ka dimaag: OpenJarvis agent. Jo quick command nahi hai, wo yahan aata hai."""

from __future__ import annotations

import datetime as _dt
import re
from collections import deque

from mikasa import settings

PERSONA = (
    "Tum Mikasa ho, {name} ki personal AI assistant, jo unke laptop pe chalti hai. "
    "Tumhe {creator} ne banaya hai; koi pooche ki tumhe kisne banaya to garv se batao ki {name} ne banaya hai. "
    "User ko hamesha '{name}' kehkar bulao, respect ke saath. "
    "Hamesha Hinglish (Roman script mein Hindi + English) mein jawab do, jaise dost se baat karte hain. "
    "Jawab bolkar sunaya jayega, isliye chhota rakho: 1 se 3 sentences, koi markdown, list ya emoji nahi. "
    "Zarurat ho to tools use karo (web search, weather, calculator). "
    "Abhi ka time: {now}."
)


class Brain:
    def __init__(self) -> None:
        self._jarvis = None
        self._error: str | None = None
        self._history: deque[tuple[str, str]] = deque(maxlen=settings.HISTORY_TURNS)

    def _get(self):
        # Laptop start hote waqt Ollama der se ready hota hai, isliye fail hone pe
        # agli baar phir try karte hain (permanent fail nahi maante).
        if self._jarvis is None:
            try:
                from openjarvis import Jarvis

                kwargs = {"model": settings.BRAIN_MODEL} if settings.BRAIN_MODEL else {}
                self._jarvis = Jarvis(**kwargs)
                self._error = None
            except Exception as exc:
                if self._error != str(exc):
                    print(f"[Mikasa] OpenJarvis abhi start nahi hua (baad mein phir try karungi): {exc}")
                self._error = str(exc)
        return self._jarvis

    def _build_query(self, text: str) -> str:
        now = _dt.datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
        lines = [PERSONA.format(name=settings.USER_NAME, creator=settings.CREATOR_NAME + ' (' + settings.USER_NAME + ')', now=now)]
        if self._history:
            lines.append("\nPichhli baatein:")
            for user, bot in self._history:
                lines.append(f"{settings.USER_NAME}: {user}\nMikasa: {bot}")
        lines.append(f"\n{settings.USER_NAME}: {text}\nMikasa:")
        query = "\n".join(lines)
        if "qwen3" in (settings.BRAIN_MODEL or "").lower():
            query += " /no_think"  # Qwen3: lamba sochna band, jawab jaldi
        return query

    @staticmethod
    def _clean(answer: str) -> str:
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S)
        answer = answer.replace("Mikasa:", "").strip()
        if len(answer) > settings.BRAIN_MAX_SPOKEN_CHARS:
            cut = answer[: settings.BRAIN_MAX_SPOKEN_CHARS]
            answer = cut[: max(cut.rfind("."), cut.rfind("?"), cut.rfind("!"), 200) + 1]
        return answer

    OFFLINE_MSG = ("Mera AI dimaag abhi connect nahi hai. Ollama chalu karo aur "
                   "jarvis doctor chala ke check karo. Tab tak apps kholna, search, notes aur tasks kaam karenge.")

    def answer(self, text: str) -> str:
        j = self._get()
        if j is None:
            return self.OFFLINE_MSG
        query = self._build_query(text)
        try:
            raw = j.ask(query, agent=settings.BRAIN_AGENT, tools=settings.BRAIN_TOOLS)
        except Exception as exc:
            print(f"[Mikasa] Agent error ({exc}), simple mode try kar rahi hoon.")
            try:
                raw = j.ask(query, agent="simple")
            except Exception as exc2:
                print(f"[Mikasa] Brain error: {exc2}")
                if "engine" in str(exc2).lower() or "ollama" in str(exc2).lower():
                    # Ollama baad mein chalu ho sakta hai: agli baar fresh connect karo
                    self.close()
                    self._jarvis = None
                    return self.OFFLINE_MSG
                return "Sorry, abhi jawab nahi de paayi. Model check karo."
        answer = self._clean(raw or "") or "Hmm, iska jawab nahi mila."
        self._history.append((text, answer))
        return answer

    def close(self) -> None:
        if self._jarvis is not None:
            try:
                self._jarvis.close()
            except Exception:
                pass
