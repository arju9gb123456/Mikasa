"""Mikasa ki awaaz. Edge neural voice (free, natural), na chale to offline pyttsx3."""

from __future__ import annotations

import asyncio
import re

from mikasa import settings


def _clean_for_speech(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```.*?```", " code diya hai screen pe. ", text, flags=re.S)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[*_#`>|]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class Speaker:
    def __init__(self) -> None:
        self._engine = settings.TTS_ENGINE
        self._pyttsx = None

    def say(self, text: str) -> None:
        print(f"\n\033[95mMikasa:\033[0m {text}\n")
        spoken = _clean_for_speech(text)
        if not spoken:
            return
        if self._engine == "edge":
            try:
                self._say_edge(spoken)
                return
            except Exception as exc:  # internet nahi / package nahi
                print(f"[Mikasa] Edge voice nahi chali ({type(exc).__name__}), offline voice use kar rahi hoon.")
                self._engine = "pyttsx3"
        try:
            self._say_pyttsx3(spoken)
        except Exception as exc:
            print(f"[Mikasa] Voice output fail: {exc}")

    # ── engines ──
    def _say_edge(self, text: str) -> None:
        import edge_tts
        import miniaudio
        import numpy as np
        import sounddevice as sd

        async def fetch() -> bytes:
            com = edge_tts.Communicate(text, settings.TTS_VOICE, rate=settings.TTS_RATE)
            buf = bytearray()
            async for chunk in com.stream():
                if chunk.get("type") == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf)

        mp3 = asyncio.run(fetch())
        if not mp3:
            raise RuntimeError("empty audio")
        decoded = miniaudio.decode(
            mp3, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=24000
        )
        samples = np.frombuffer(decoded.samples, dtype=np.int16)
        sd.play(samples, 24000)
        sd.wait()

    def _say_pyttsx3(self, text: str) -> None:
        if self._pyttsx is None:
            import pyttsx3

            self._pyttsx = pyttsx3.init()
            for v in self._pyttsx.getProperty("voices"):
                name = (getattr(v, "name", "") or "").lower()
                if "hindi" in name or "kalpana" in name or "heera" in name or "zira" in name:
                    self._pyttsx.setProperty("voice", v.id)
                    break
        self._pyttsx.say(text)
        self._pyttsx.runAndWait()
