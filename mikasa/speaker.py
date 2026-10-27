"""Mikasa ki awaaz.

Engines (settings.TTS_ENGINE):
  elevenlabs - sabse real insaan jaisi awaaz (free account + API key chahiye)
  edge       - Microsoft neural voices, free, natural (internet chahiye)
  pyttsx3    - offline, robotic (backup)
  auto       - ELEVENLABS_API_KEY ho to elevenlabs, warna edge
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import re

from mikasa import settings

_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)


def _clean_for_speech(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```.*?```", " code diya hai screen pe. ", text, flags=re.S)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[*_#`>|]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _play_mp3(mp3: bytes) -> None:
    import miniaudio
    import numpy as np
    import sounddevice as sd

    decoded = miniaudio.decode(mp3, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=24000)
    samples = np.frombuffer(decoded.samples, dtype=np.int16)
    sd.play(samples, 24000)
    sd.wait()


def edge_mp3(text: str, voice: str, rate: str) -> bytes:
    import edge_tts

    async def fetch() -> bytes:
        com = edge_tts.Communicate(text, voice, rate=rate)
        buf = bytearray()
        async for chunk in com.stream():
            if chunk.get("type") == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    # alag thread mein, taaki browser automation (Playwright) ke event loop se na takraye
    mp3 = _POOL.submit(lambda: asyncio.run(fetch())).result(timeout=30)
    if not mp3:
        raise RuntimeError("empty audio")
    return mp3


def elevenlabs_mp3(text: str) -> bytes:
    import httpx

    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice = settings.ELEVENLABS_VOICE_ID.strip() or "21m00Tcm4TlvDq8ikWAM"
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY set nahi hai")
    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        headers={"xi-api-key": key, "accept": "audio/mpeg"},
        json={"text": text, "model_id": settings.ELEVENLABS_MODEL,
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3}},
        timeout=30,
    )
    r.raise_for_status()
    return r.content


class Speaker:
    def __init__(self) -> None:
        engine = settings.TTS_ENGINE
        if engine == "auto":
            engine = "elevenlabs" if os.environ.get("ELEVENLABS_API_KEY") else "edge"
        self._engine = engine
        self._voices = [settings.TTS_VOICE] + [v for v in settings.TTS_FALLBACK_VOICES if v != settings.TTS_VOICE]
        self._pyttsx = None
        self._warned: set[str] = set()

    def _warn(self, key: str, msg: str) -> None:
        if key not in self._warned:
            self._warned.add(key)
            print(msg)

    def say(self, text: str) -> None:
        print(f"\n\033[95mMikasa:\033[0m {text}\n")
        spoken = _clean_for_speech(text)
        if not spoken:
            return
        if self._engine == "elevenlabs":
            try:
                _play_mp3(elevenlabs_mp3(spoken))
                return
            except Exception as exc:
                self._warn("eleven", f"[Mikasa] ElevenLabs nahi chali ({type(exc).__name__}: {str(exc)[:80]}), Edge voice use kar rahi hoon.")
        if self._engine in ("elevenlabs", "edge"):
            for voice in list(self._voices):
                try:
                    _play_mp3(edge_mp3(spoken, voice, settings.TTS_RATE))
                    return
                except Exception as exc:
                    # voice hi galat ho (NoAudioReceived) to agli voice; internet na ho to seedha offline
                    if "NoAudio" in type(exc).__name__ and len(self._voices) > 1:
                        self._warn(voice, f"[Mikasa] Voice {voice} nahi chali, agli try kar rahi hoon.")
                        self._voices.remove(voice)
                        continue
                    self._warn("edge", f"[Mikasa] Edge voice nahi chali ({type(exc).__name__}), is baar offline voice.")
                    break
        try:
            self._say_pyttsx3(spoken)
        except Exception as exc:
            print(f"[Mikasa] Voice output fail: {exc}")

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


VOICE_TEST_LINE = "Namaste Arjun sir, main Mikasa hoon. Aaj aapke liye kya kar sakti hoon? Gmail khol dun ya koi gaana lagaun?"
VOICE_TEST = [
    "en-IN-NeerjaExpressiveNeural",
    "en-IN-NeerjaNeural",
    "hi-IN-SwaraNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-EmmaMultilingualNeural",
]


def voice_test() -> None:
    """Saari female voices ek-ek karke sunao, taaki pasand wali chun sako."""
    print("\nMikasa voice test: har voice ek line bolegi.\n")
    for i, voice in enumerate(VOICE_TEST, 1):
        print(f"  {i}. {voice}")
        try:
            _play_mp3(edge_mp3(VOICE_TEST_LINE, voice, "+0%"))
        except Exception as exc:
            print(f"     (nahi chali: {type(exc).__name__})")
    if os.environ.get("ELEVENLABS_API_KEY"):
        print(f"  {len(VOICE_TEST) + 1}. ElevenLabs ({settings.ELEVENLABS_VOICE_ID or 'default voice'})")
        try:
            _play_mp3(elevenlabs_mp3(VOICE_TEST_LINE))
        except Exception as exc:
            print(f"     (nahi chali: {exc})")
    print("\nJo pasand aaye uska naam mikasa\\settings.py mein TTS_VOICE = \"...\" mein likh do.\n")
