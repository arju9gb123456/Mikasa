"""WhatsApp Web automation: chat kholna, message type karna, confirm pe bhejna.

Tumhara laptop ka Edge/Chrome browser (Playwright) use hota hai, alag profile
ke saath. Pehli baar phone se QR scan karna padega, uske baad login yaad rehta hai.

Safety: message type karne ke baad Mikasa poochti hai "bhej dun?". Sirf "haan"
bolne pe Enter dabata hai.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from typing import Optional

from mikasa import settings

URL = "https://web.whatsapp.com"

# WhatsApp Web ke selectors (WhatsApp UI badle to yahan update karna)
SEARCH_BOX = (
    'div[contenteditable="true"][data-tab="3"], '
    '[aria-label="Search input textbox"], '
    'div[role="textbox"][aria-label*="Search" i], '
    'input[aria-label*="Search" i]'
)
MESSAGE_BOX = (
    '#main footer div[contenteditable="true"], '
    'footer div[role="textbox"][contenteditable="true"]'
)
CHAT_HEADER_NAME = "#main header span[dir='auto']"
LOGGED_IN = "#pane-side, div[aria-label='Chat list']"
HEADLESS = False  # tests ke liye


def _similar(a: str, b: str) -> bool:
    import difflib

    a, b = a.lower().strip(), b.lower().strip()
    return bool(a) and (a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.6)


class WhatsAppBot:
    def __init__(self) -> None:
        self._pw = None
        self._ctx = None
        self.page = None
        self.chat_name: Optional[str] = None

    # ── browser ──
    def _browser_channels(self) -> list[Optional[str]]:
        pref = settings.WHATSAPP_BROWSER
        if sys.platform.startswith("win"):
            order = [pref, "msedge", "chrome", None]
        else:
            order = [pref, "chrome", "msedge", None]
        seen, out = set(), []
        for ch in order:
            if ch not in seen:
                seen.add(ch)
                out.append(ch)
        return out

    def _alive(self) -> bool:
        try:
            return self.page is not None and not self.page.is_closed()
        except Exception:
            return False

    def open(self) -> str:
        """WhatsApp Web kholo (zarurat ho to browser launch). Status text return."""
        if self._alive():
            self.page.bring_to_front()
            return "ok"
        from playwright.sync_api import sync_playwright

        profile = settings.DATA_DIR / "whatsapp_browser"
        profile.mkdir(parents=True, exist_ok=True)
        if self._pw is None:
            self._pw = sync_playwright().start()
        last_err = None
        for channel in self._browser_channels():
            try:
                kwargs = {"headless": HEADLESS, "no_viewport": True, "args": ["--start-maximized"]}
                if channel:
                    kwargs["channel"] = channel
                self._ctx = self._pw.chromium.launch_persistent_context(str(profile), **kwargs)
                break
            except Exception as exc:
                last_err = exc
                self._ctx = None
        if self._ctx is None:
            raise RuntimeError(f"Browser nahi khula: {last_err}")
        self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        self.page.goto(URL)
        return "opened"

    def wait_login(self, timeout_s: int = 120) -> bool:
        try:
            self.page.wait_for_selector(LOGGED_IN, timeout=timeout_s * 1000)
            return True
        except Exception:
            return False

    def is_logged_in(self, quick_s: int = 20) -> bool:
        return self.wait_login(quick_s)

    # ── chat ──
    def open_chat(self, contact: str) -> Optional[str]:
        """Contact ki chat kholo. Khuli chat ka naam return (na mile to None)."""
        contact = settings.CONTACTS.get(contact.lower().strip(), contact)
        page = self.page
        if contact.replace("+", "").replace(" ", "").isdigit():
            phone = contact.replace("+", "").replace(" ", "")
            page.goto(f"{URL}/send?phone={urllib.parse.quote(phone)}")
            page.wait_for_selector(MESSAGE_BOX, timeout=30000)
        else:
            before = self._header_name()
            box = page.locator(SEARCH_BOX).first
            box.click(timeout=10000)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(contact, delay=40)
            time.sleep(2.0)
            page.keyboard.press("Enter")
            # Nayi chat khuli? (purani chat ko galti se "mil gayi" na maano)
            deadline = time.time() + 8
            while time.time() < deadline:
                name = self._header_name()
                if name and (name != before or _similar(contact, name)):
                    self.chat_name = name
                    return name
                time.sleep(0.4)
            return None
        name = self._header_name() or contact
        self.chat_name = name
        return name

    def _header_name(self) -> str:
        try:
            loc = self.page.locator(CHAT_HEADER_NAME).first
            if loc.count() == 0:
                return ""
            return loc.inner_text(timeout=1000).strip()
        except Exception:
            return ""

    def type_message(self, message: str) -> None:
        box = self.page.locator(MESSAGE_BOX).first
        box.click()
        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")
        self.page.keyboard.insert_text(message)

    def send(self) -> None:
        self.page.locator(MESSAGE_BOX).first.click()
        self.page.keyboard.press("Enter")

    def clear_message(self) -> None:
        try:
            self.page.locator(MESSAGE_BOX).first.click()
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Backspace")
        except Exception:
            pass

    def close(self) -> None:
        for obj in (self._ctx, self._pw):
            try:
                if obj is self._pw and obj is not None:
                    obj.stop()
                elif obj is not None:
                    obj.close()
            except Exception:
                pass
        self._ctx = self._pw = self.page = None
