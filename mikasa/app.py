"""Mikasa main loop.

    uv run python -m mikasa          # voice mode: bas "Mikasa" bolo
    uv run python -m mikasa --text   # bina mic ke, type karke test karo
"""

from __future__ import annotations

import argparse
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

from mikasa import settings  # noqa: E402
from mikasa.commands import Commands, Reply, detect_wake, normalize  # noqa: E402

BANNER = r"""
  __  __ _ _
 |  \/  (_) | ____ _ ___  __ _
 | |\/| | | |/ / _` / __|/ _` |
 | |  | | |   < (_| \__ \ (_| |
 |_|  |_|_|_|\_\__,_|___/\__,_|   your personal AI · made by Arjun Ahirwar
"""


class Mikasa:
    def __init__(self, text_mode: bool = False, mute: bool = False) -> None:
        from mikasa.brain import Brain

        self.text_mode = text_mode
        self.mute = mute
        self.brain = Brain()
        self.commands = Commands(brain=self.brain)
        self.speaker = None
        self.listener = None
        self.transcriber = None
        self.awake_until = 0.0

    def setup(self) -> None:
        if not self.mute:
            from mikasa.speaker import Speaker

            self.speaker = Speaker()
        if not self.text_mode:
            from mikasa.listener import Listener, Transcriber

            self.transcriber = Transcriber()
            self.listener = Listener()
            self.listener.start()
        # AI brain background mein load karo taaki pehla sawaal fast ho
        threading.Thread(target=self.brain._get, daemon=True).start()

    def say(self, text: str) -> None:
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

    @staticmethod
    def with_title(text: str) -> str:
        """Har jawab mein "Arjun sir" - agar pehle se nahi hai to shuru mein jodo."""
        title = settings.USER_NAME
        if not text or title.lower() in text.lower():
            return text
        return f"{title}, {text}"

    def respond(self, command: str) -> Reply:
        reply = self.commands.handle(command)
        if reply is None:
            print("\033[2m(soch rahi hoon...)\033[0m")
            reply = Reply(self.brain.answer(command))
        return reply

    def deliver(self, reply: Reply) -> Reply:
        """Reply bolo; agar uske baad koi kaam (then) hai to wo karo aur uska jawab bhi bolo."""
        self.say(self.with_title(reply.text))
        steps = 0
        while reply.then is not None and steps < 5:
            steps += 1
            try:
                reply = reply.then()
            except Exception as exc:
                print(f"[Mikasa] Kaam mein error: {exc}")
                reply = Reply("Sorry, ye kaam karte waqt error aaya.")
            self.say(reply.text)
        return reply

    def process(self, heard: str) -> bool:
        """Ek suni hui line process karo. False = program band."""
        found, rest = detect_wake(heard)
        now = time.time()
        if not found and now > self.awake_until and self.commands.pending is None:
            if not self.text_mode:
                print(f"\033[2m(suna, par Mikasa nahi bola): {heard}\033[0m")
            return True

        print(f"\033[96m{settings.USER_NAME}:\033[0m {heard}")
        command = rest if found else normalize(heard)
        if not command.strip():
            self.say(f"Haan {settings.USER_NAME}, boliye?")
            self.awake_until = time.time() + settings.FOLLOWUP_SECONDS
            return True

        reply = self.deliver(self.respond(command))
        if reply.quit:
            return False
        self.awake_until = 0.0 if reply.sleep else time.time() + settings.FOLLOWUP_SECONDS
        return True

    def run(self) -> None:
        print(BANNER)
        self.setup()
        hint = "type karo (jaise: Mikasa gmail kholo)" if self.text_mode else 'bas "Mikasa" bolo'
        print(f"[Mikasa] Ready! {hint}. Band karne ke liye: \"Mikasa band ho jao\" ya Ctrl+C\n")
        self.say(f"Namaste {settings.USER_NAME}, main Mikasa hoon. Jab bhi zarurat ho, bas Mikasa boliye.")
        try:
            while True:
                if self.text_mode:
                    try:
                        heard = input("> ").strip()
                    except EOFError:
                        break
                    if not heard:
                        continue
                    # text mode mein wake word zaruri nahi
                    if not detect_wake(heard)[0]:
                        self.awake_until = time.time() + 3600
                else:
                    audio = self.listener.next_utterance()
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="mikasa", description="Mikasa voice assistant")
    parser.add_argument("--text", action="store_true", help="mic ke bina, type karke chalao")
    parser.add_argument("--mute", action="store_true", help="awaaz mat nikalo, sirf print karo")
    parser.add_argument("--list-mics", action="store_true", help="saare mic devices dikhao")
    args = parser.parse_args()

    if args.list_mics:
        import sounddevice as sd

        print(sd.query_devices())
        return

    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # Devanagari print ke liye
        except Exception:
            pass

    Mikasa(text_mode=args.text, mute=args.mute).run()


if __name__ == "__main__":
    main()
