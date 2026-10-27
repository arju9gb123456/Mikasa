"""Mikasa main loop.

    uv run python -m mikasa          # voice mode: bas "Mikasa" bolo
    uv run python -m mikasa --text   # bina mic ke, type karke test karo
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time

import os
import warnings

# Faltu warnings chhupao (Windows symlink / HF token) - Mikasa pe asar nahi
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
warnings.filterwarnings("ignore", module="huggingface_hub")
import logging  # noqa: E402

for _name in ("openjarvis", "huggingface_hub", "faster_whisper"):
    logging.getLogger(_name).setLevel(logging.ERROR)

from mikasa import persona, settings  # noqa: E402
from mikasa.commands import Commands, Reply, detect_wake, normalize  # noqa: E402

BANNER = r"""
  __  __ _ _
 |  \/  (_) | ____ _ ___  __ _
 | |\/| | | |/ / _` / __|/ _` |
 | |  | | |   < (_| \__ \ (_| |
 |_|  |_|_|_|\_\__,_|___/\__,_|   your personal AI · made by Arjun Ahirwar
"""


class Mikasa:
    def __init__(self, text_mode: bool = False, mute: bool = False, hud: bool = True) -> None:
        from mikasa.brain import Brain
        from mikasa.router import Router

        self.text_mode = text_mode
        self.mute = mute
        self.brain = Brain()
        self.router = Router()
        self.commands = Commands(brain=self.brain)
        self.speaker = None
        self.listener = None
        self.transcriber = None
        self.awake_until = 0.0
        self.inbox: "queue.Queue[str]" = queue.Queue()  # screen (HUD) ya keyboard se aayi commands
        self.hud = None
        if hud and settings.HUD_ENABLED:
            from mikasa.hud import Hud

            h = Hud()
            if h.start():
                self.hud = h
                self.inbox = h.commands

    # ── HUD helpers ──
    def _state(self, s: str) -> None:
        if self.hud:
            self.hud.state(s)

    def _info(self, **kw) -> None:
        if self.hud:
            self.hud.emit("info", **kw)

    def _idle_state(self) -> None:
        self._state("listening" if time.time() < self.awake_until else "idle")

    def setup(self) -> None:
        if self.hud and settings.HUD_OPEN_WINDOW:
            self.hud.open_window()
        self._info(mic=not self.text_mode, stt="text mode" if self.text_mode else "load ho raha hai...",
                   ai="load ho raha hai...", voice="-" if self.mute else settings.TTS_VOICE.replace("Neural", ""))
        if not self.mute:
            from mikasa.speaker import Speaker

            self.speaker = Speaker()
            self._info(voice=self.speaker.describe())
        if not self.text_mode:
            from mikasa.listener import Listener, Transcriber

            self._state("thinking")
            self.transcriber = Transcriber()
            self._info(stt=f"{self.transcriber.model_name} · {self.transcriber.device.upper()}")
            self.listener = Listener()
            self.listener.start()
        else:
            threading.Thread(target=self._stdin_reader, daemon=True).start()

        def warm():
            ok = self.router.warmup()
            share = self.router.gpu_share
            where = f" · GPU {share:.0%}" if (ok and share is not None) else ""
            self._info(ai=f"{settings.BRAIN_MODEL} · {'ready' if ok else 'offline'}{where}")

        # Reminders: time aane pe inbox mein daalo, main loop bolega
        from mikasa.commands import load_tasks, save_tasks
        from mikasa.reminders import ReminderWatcher

        self.reminders = ReminderWatcher(load_tasks, save_tasks,
                                         lambda task, late: self.inbox.put(f"\x00REMIND:{int(late)}:{task}"))
        self.reminders.start()

        # AI model background mein GPU/RAM mein load karo taaki pehla jawab tez aaye
        threading.Thread(target=warm, daemon=True).start()
        threading.Thread(target=self.brain._get, daemon=True).start()
        self._state("idle")

    def _stdin_reader(self) -> None:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                self.inbox.put("\x00EOF")
                return
            if line:
                self.inbox.put(line)

    def say(self, text: str) -> None:
        if self.hud:
            self.hud.emit("reply", text=text)
        self._state("speaking")
        if self.listener:
            self.listener.pause()
        try:
            if self.speaker:
                self.speaker.say(text)
            else:
                print(f"\n\033[95mMikasa:\033[0m {text}\n")
        finally:
            if self.listener:
                self.listener.resume()
            self._idle_state()

    @staticmethod
    def with_title(text: str) -> str:
        return persona.with_title(text)

    def respond(self, command: str) -> Reply:
        self._state("thinking")
        # 1. seedhe commands (turant, AI ke bina)
        reply = self.commands.handle(command)
        if reply is not None:
            return reply
        # 2. smart router: galat suna ho to bhi matlab samjho (ek tez AI call)
        print("\033[2m(samajh rahi hoon...)\033[0m")
        if settings.SMART_ROUTER:
            intent = self.router.route(command)
            if intent is not None:
                reply = self.commands.execute_intent(intent, brain=self.brain)
                if reply is not None:
                    return reply
        # 3. aakhri raasta: OpenJarvis agent
        return Reply(self.brain.answer(command))

    def deliver(self, reply: Reply) -> Reply:
        """Reply bolo; agar uske baad koi kaam (then) hai to wo karo aur uska jawab bhi bolo."""
        self.say(self.with_title(reply.text))
        steps = 0
        while reply.then is not None and steps < 5:
            steps += 1
            self._state("thinking")
            try:
                reply = reply.then()
            except Exception as exc:
                print(f"[Mikasa] Kaam mein error: {exc}")
                reply = Reply("Sorry, ye kaam karte waqt error aaya.")
            self.say(reply.text)
        return reply

    def process(self, heard: str, force: bool = False) -> bool:
        """Ek suni hui line process karo. force = screen/keyboard se (wake word zaruri nahi). False = band."""
        found, rest = detect_wake(heard)
        now = time.time()
        if not force and not found and now > self.awake_until and self.commands.pending is None:
            print(f"\033[2m(suna, par Mikasa nahi bola): {heard}\033[0m")
            return True

        print(f"\033[96m{settings.USER_NAME}:\033[0m {heard}")
        if self.hud:
            self.hud.emit("heard", text=heard)
        command = rest if found else normalize(heard)
        if not command.strip():
            self.awake_until = time.time() + settings.FOLLOWUP_SECONDS
            self.say(persona.wake())
            return True

        reply = self.deliver(self.respond(command))
        if reply.quit:
            return False
        self.awake_until = 0.0 if reply.sleep else time.time() + settings.FOLLOWUP_SECONDS
        self._idle_state()
        return True

    def run(self) -> None:
        print(BANNER)
        self.setup()
        hint = "type karo (jaise: gmail kholo)" if self.text_mode else 'bas "Mikasa" bolo'
        print(f"[Mikasa] Ready! {hint}. Band karne ke liye: \"Mikasa band ho jao\" ya Ctrl+C")
        if self.hud:
            print(f"[Mikasa] Screen: {self.hud.url}")
        print()
        self.say(persona.greeting())
        try:
            while True:
                # screen / keyboard ki command pehle
                try:
                    typed = self.inbox.get_nowait()
                except queue.Empty:
                    typed = None
                if typed is not None:
                    if typed == "\x00EOF":
                        break
                    if typed.startswith("\x00REMIND:"):
                        _, late, task = typed.split(":", 2)
                        if self.hud:
                            self.hud.emit("reminder", text=task)
                        self.awake_until = time.time() + settings.FOLLOWUP_SECONDS
                        self.say(persona.reminder(task, late == "1"))
                        continue
                    if not self.process(typed, force=True):
                        break
                    continue
                if self.text_mode:
                    time.sleep(0.05)
                    continue
                audio = self.listener.next_utterance(stop_check=lambda: not self.inbox.empty())
                if audio is None:
                    continue
                heard = self.transcriber.transcribe(audio)
                if not heard:
                    continue
                if not self.process(heard):
                    break
        except KeyboardInterrupt:
            print("\n[Mikasa] Bye!")
        finally:
            if self.listener:
                self.listener.stop()
            self.commands.close()
            self.brain.close()
            if self.hud:
                self.hud.state("sleeping")
                time.sleep(0.2)
                self.hud.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="mikasa", description="Mikasa voice assistant")
    parser.add_argument("--text", action="store_true", help="mic ke bina, type karke chalao")
    parser.add_argument("--mute", action="store_true", help="awaaz mat nikalo, sirf print karo")
    parser.add_argument("--list-mics", action="store_true", help="saare mic devices dikhao")
    parser.add_argument("--voice-test", action="store_true", help="saari female voices sunao")
    parser.add_argument("--no-hud", action="store_true", help="screen (HUD) mat kholo, sirf terminal")
    args = parser.parse_args()

    if args.voice_test:
        from mikasa.speaker import voice_test

        voice_test()
        return

    if args.list_mics:
        import sounddevice as sd

        print(sd.query_devices())
        return

    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # Devanagari print ke liye
        except Exception:
            pass

    Mikasa(text_mode=args.text, mute=args.mute, hud=not args.no_hud).run()


if __name__ == "__main__":
    main()
