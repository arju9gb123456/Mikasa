"""Mic hamesha on: speech aate hi record, chup hote hi utterance return.

Energy-based VAD with an adaptive noise floor, so fans/AC ki awaaz ko speech
nahi maanta. Bolte waqt (TTS) mic pause ho jata hai taaki Mikasa khud ki
awaaz na sune.
"""

from __future__ import annotations

import collections
import queue
import threading
from typing import Optional

import numpy as np

from mikasa import settings


class Listener:
    def __init__(self) -> None:
        import sounddevice as sd

        self._sd = sd
        self._q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._paused = threading.Event()
        self._block = int(settings.SAMPLE_RATE * settings.BLOCK_SECONDS)
        self._noise = float(settings.MIN_SPEECH_RMS) / settings.NOISE_MULTIPLIER
        self._stream = sd.InputStream(
            samplerate=settings.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=self._block,
            device=settings.MIC_DEVICE,
            callback=self._callback,
        )

    # sounddevice audio thread
    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        if not self._paused.is_set():
            self._q.put(indata[:, 0].copy())

    def start(self) -> None:
        self._stream.start()

    def stop(self) -> None:
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        # Bolte waqt jo audio aaya use phenk do
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        self._paused.clear()

    @staticmethod
    def _rms(block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(block.astype(np.float32) ** 2))) if block.size else 0.0

    def next_utterance(self) -> Optional[np.ndarray]:
        """Block until someone speaks and stops. Returns float32 mono @16 kHz."""
        bps = 1.0 / settings.BLOCK_SECONDS
        preroll = collections.deque(maxlen=int(0.35 * bps))
        end_blocks = int(settings.END_SILENCE_SECONDS * bps)
        max_blocks = int(settings.MAX_UTTERANCE_SECONDS * bps)
        min_blocks = int(settings.MIN_UTTERANCE_SECONDS * bps)
        start_needed = 3  # itne loud blocks lagatar = speech shuru

        frames: list[np.ndarray] = []
        speaking = False
        loud_run = 0
        silent_run = 0
        voiced = 0

        while True:
            try:
                block = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            level = self._rms(block)
            threshold = max(settings.MIN_SPEECH_RMS, self._noise * settings.NOISE_MULTIPLIER)

            if not speaking:
                preroll.append(block)
                if level > threshold:
                    loud_run += 1
                    if loud_run >= start_needed:
                        speaking = True
                        frames = list(preroll)
                        voiced = loud_run
                        silent_run = 0
                else:
                    loud_run = 0
                    # noise floor dheere-dheere adjust
                    self._noise = 0.95 * self._noise + 0.05 * level
                continue

            frames.append(block)
            if level > threshold * 0.7:
                silent_run = 0
                voiced += 1
            else:
                silent_run += 1

            if silent_run >= end_blocks or len(frames) >= max_blocks:
                if voiced < min_blocks:
                    # chhoti si awaaz (khaansi, click) - ignore
                    speaking, loud_run, frames, voiced = False, 0, [], 0
                    preroll.clear()
                    continue
                audio = np.concatenate(frames).astype(np.float32) / 32768.0
                return audio


class Transcriber:
    """faster-whisper wrapper (offline, laptop pe chalta hai)."""

    # Whisper khaali/noise audio pe ye sab "sunn" leta hai - inhe ignore karo
    _HALLUCINATIONS = {
        "धन्यवाद", "शुक्रिया", "thank you", "thanks for watching", "subscribe",
        "सब्सक्राइब", "please subscribe", "you", "बाय", "ok", "hmm", "हम्म",
    }

    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        device, compute = self._pick_device()
        print(f"[Mikasa] Speech model load ho raha hai ({settings.STT_MODEL}, {device})... "
              "pehli baar download hoga, thoda time lagega.")
        self._model = WhisperModel(settings.STT_MODEL, device=device, compute_type=compute)

    @staticmethod
    def _pick_device() -> tuple[str, str]:
        if settings.STT_DEVICE == "cpu":
            return "cpu", "int8"
        if settings.STT_DEVICE in ("cuda", "auto"):
            try:
                import ctranslate2

                if ctranslate2.get_cuda_device_count() > 0:
                    return "cuda", "float16"
            except Exception:
                pass
        return "cpu", "int8"

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _info = self._model.transcribe(
            audio,
            language=settings.STT_LANGUAGE or None,
            initial_prompt=settings.STT_PROMPT,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        parts = [s.text for s in segments if getattr(s, "no_speech_prob", 0.0) < 0.6]
        text = " ".join(p.strip() for p in parts).strip()
        cleaned = text.strip(" .,!?।").lower()
        if not cleaned or cleaned in self._HALLUCINATIONS:
            return ""
        return text
