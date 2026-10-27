"""Mic hamesha on: speech aate hi record, chup hote hi utterance return.

Energy-based VAD with an adaptive noise floor, so fans/AC ki awaaz ko speech
nahi maanta. Bolte waqt (TTS) mic pause ho jata hai taaki Mikasa khud ki
awaaz na sune.
"""

from __future__ import annotations

import collections
import os
import queue
import sys
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

    def next_utterance(self, stop_check=None) -> Optional[np.ndarray]:
        """Block until someone speaks and stops. Returns float32 mono @16 kHz.

        stop_check() True ho (jaise screen se command aayi) aur koi bol nahi raha, to None.
        """
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
            if not speaking and stop_check is not None and stop_check():
                return None
            try:
                block = self._q.get(timeout=0.2)
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


def _add_cuda_dlls() -> None:
    """Windows: pip wale NVIDIA packages (cublas, cudnn) ki DLLs ko dhoondne layak banao."""
    if not sys.platform.startswith("win"):
        return
    import glob
    import site

    roots = list(site.getsitepackages())
    try:
        roots.append(site.getusersitepackages())
    except Exception:
        pass
    for root in roots:
        for d in glob.glob(os.path.join(root, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(d)  # type: ignore[attr-defined]
            except Exception:
                pass
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


class Transcriber:
    """faster-whisper wrapper (offline, laptop pe chalta hai)."""

    # Whisper khaali/noise audio pe ye sab "sunn" leta hai - inhe ignore karo
    _HALLUCINATIONS = {
        "धन्यवाद", "शुक्रिया", "thank you", "thanks for watching", "subscribe",
        "सब्सक्राइब", "please subscribe", "you", "बाय", "ok", "hmm", "हम्म",
    }

    def __init__(self) -> None:
        _add_cuda_dlls()
        device, compute = self._pick_device()
        self._load(device, compute)
        if device == "cuda":
            # GPU libraries (cublas/cudnn) missing ho to error pehli transcription pe aata hai.
            # Abhi test karo, fail ho to CPU.
            try:
                segs, _ = self._model.transcribe(np.zeros(16000, dtype=np.float32), language="hi",
                                                 vad_filter=False, beam_size=1)
                list(segs)
                print("[Mikasa] GPU se speech chal rahi hai (tez + accurate).")
            except Exception as exc:
                self._to_cpu(exc)

    @staticmethod
    def _model_for(device: str) -> str:
        if settings.STT_MODEL != "auto":
            return settings.STT_MODEL
        return "large-v3-turbo" if device == "cuda" else "small"

    def _load(self, device: str, compute: str) -> None:
        from faster_whisper import WhisperModel

        name = self._model_for(device)
        print(f"[Mikasa] Speech model load ho raha hai ({name}, {device})... "
              "naya model pehli baar download hoga, thoda time lagega.")
        self.device = device
        self.model_name = name
        self._model = WhisperModel(name, device=device, compute_type=compute)

    def _to_cpu(self, exc: Exception) -> None:
        print(f"[Mikasa] GPU se speech nahi chali ({type(exc).__name__}: {str(exc)[:120]}).\n"
              "         CPU pe chala rahi hoon. GPU ke liye: start_mikasa.bat dobara chalao (wo GPU files install karega).")
        self._load("cpu", "int8")

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

    def _run(self, audio: np.ndarray) -> list:
        segments, _info = self._model.transcribe(
            audio,
            language=settings.STT_LANGUAGE or None,
            initial_prompt=settings.STT_PROMPT,
            hotwords=settings.STT_HOTWORDS or None,
            beam_size=settings.STT_BEAM_SIZE if self.device == "cuda" else min(settings.STT_BEAM_SIZE, 3),
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        return list(segments)  # generator - error yahin aata hai

    def transcribe(self, audio: np.ndarray) -> str:
        try:
            segments = self._run(audio)
        except Exception as exc:
            if self.device != "cuda":
                print(f"[Mikasa] Speech error: {exc}")
                return ""
            self._to_cpu(exc)
            segments = self._run(audio)
        parts = [s.text for s in segments if getattr(s, "no_speech_prob", 0.0) < 0.6]
        text = " ".join(p.strip() for p in parts).strip()
        cleaned = text.strip(" .,!?।").lower()
        if not cleaned or cleaned in self._HALLUCINATIONS:
            return ""
        # Whisper kabhi prompt hi wapas likh deta hai - use ignore karo
        if cleaned and cleaned in settings.STT_PROMPT.lower() and len(cleaned) > 40:
            return ""
        return text
