"""Mikasa HUD: MYRA jaisi screen (laal animated rings, avatar, stats, chat log).

Ek chhota local web server (sirf 127.0.0.1, bahar se koi access nahi):
  GET  /         -> HUD page
  GET  /events   -> live status (Server-Sent Events)
  GET  /stats    -> CPU / RAM / battery / disk / network
  POST /command  -> screen se type ki hui ya button wali command
Window Edge ke "app mode" mein khulti hai, isliye normal app jaisi dikhti hai.
"""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from mikasa import settings

_HERE = Path(__file__).parent


def find_avatar() -> Optional[Path]:
    """Apni avatar image: settings.AVATAR_IMAGE, ya Mikasa folder mein avatar.png/jpg/gif/webp."""
    if settings.AVATAR_IMAGE:
        p = Path(settings.AVATAR_IMAGE).expanduser()
        return p if p.is_file() else None
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        p = settings.DATA_DIR / f"avatar{ext}"
        if p.is_file():
            return p
    return None


class Hud:
    def __init__(self) -> None:
        self.commands: "queue.Queue[str]" = queue.Queue()
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._state = {"state": "idle", "info": {}}
        self._log: list[dict] = []
        self._server: Optional[ThreadingHTTPServer] = None
        self._net = None
        self.started = time.time()

    # ── events ──
    def emit(self, kind: str, **data) -> None:
        msg = {"type": kind, "t": time.time(), **data}
        if kind == "state":
            self._state["state"] = data.get("state", "idle")
        elif kind == "info":
            self._state["info"].update(data)
        elif kind in ("heard", "reply"):
            self._log.append(msg)
            self._log = self._log[-60:]
        with self._lock:
            for q in list(self._clients):
                q.put(msg)

    def state(self, s: str) -> None:
        self.emit("state", state=s)

    # ── stats ──
    def stats(self) -> dict:
        import psutil

        out = {
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
            "ram_gb": round(psutil.virtual_memory().used / 2**30, 1),
            "ram_total": round(psutil.virtual_memory().total / 2**30, 1),
            "uptime": int(time.time() - psutil.boot_time()),
            "mikasa_uptime": int(time.time() - self.started),
            "cores": psutil.cpu_count(),
        }
        try:
            out["disk"] = psutil.disk_usage(str(Path.home().anchor or "/")).percent
        except Exception:
            out["disk"] = None
        try:
            b = psutil.sensors_battery()
            out["battery"] = round(b.percent) if b else None
            out["charging"] = bool(b.power_plugged) if b else None
        except Exception:
            out["battery"] = None
        try:
            n = psutil.net_io_counters()
            now = time.time()
            if self._net:
                dt = max(0.5, now - self._net[0])
                out["down_kbps"] = round((n.bytes_recv - self._net[1]) / dt / 1024)
                out["up_kbps"] = round((n.bytes_sent - self._net[2]) / dt / 1024)
            self._net = (now, n.bytes_recv, n.bytes_sent)
        except Exception:
            pass
        return out

    # ── server ──
    def start(self) -> bool:
        hud = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # chup
                pass

            def _send(self, code: int, body: bytes, ctype: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    html = (_HERE / "index.html").read_text(encoding="utf-8")
                    html = html.replace("{{USER}}", settings.USER_NAME).replace("{{CREATOR}}", settings.CREATOR_NAME)
                    return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
                if self.path.startswith("/avatar"):
                    img = find_avatar()
                    if img is None:
                        return self._send(404, b"no avatar", "text/plain")
                    ctype = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                             ".webp": "image/webp"}.get(img.suffix.lower(), "application/octet-stream")
                    return self._send(200, img.read_bytes(), ctype)
                if self.path == "/stats":
                    return self._send(200, json.dumps(hud.stats()).encode(), "application/json")
                if self.path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    q: queue.Queue = queue.Queue()
                    with hud._lock:
                        hud._clients.append(q)
                    try:
                        hello = {"type": "hello", "state": hud._state["state"], "info": hud._state["info"],
                                 "log": hud._log[-30:], "avatar": find_avatar() is not None}
                        self.wfile.write(f"data: {json.dumps(hello, ensure_ascii=False)}\n\n".encode())
                        self.wfile.flush()
                        while True:
                            try:
                                msg = q.get(timeout=15)
                                line = f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                            except queue.Empty:
                                line = ": ping\n\n"
                            self.wfile.write(line.encode())
                            self.wfile.flush()
                    except Exception:
                        pass
                    finally:
                        with hud._lock:
                            if q in hud._clients:
                                hud._clients.remove(q)
                    return None
                return self._send(404, b"not found", "text/plain")

            def do_POST(self):
                if self.path != "/command":
                    return self._send(404, b"not found", "text/plain")
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                    data = json.loads(self.rfile.read(n) or b"{}")
                    text = str(data.get("text", "")).strip()[:500]
                except Exception:
                    text = ""
                if text:
                    hud.commands.put(text)
                return self._send(200, b'{"ok":true}', "application/json")

        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", settings.HUD_PORT), Handler)
        except OSError as exc:
            print(f"[Mikasa] HUD port {settings.HUD_PORT} busy ({exc}). Shayad Mikasa pehle se chal rahi hai.")
            return False
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return True

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{settings.HUD_PORT}/"

    def open_window(self) -> None:
        """Edge/Chrome app mode (bina address bar), na mile to normal browser."""
        url = self.url
        size = "--window-size=1280,760"
        try:
            if sys.platform.startswith("win"):
                for exe in ("msedge", "chrome"):
                    try:
                        subprocess.Popen(f'start "" {exe} --app={url} {size}', shell=True)
                        return
                    except Exception:
                        continue
            elif sys.platform == "darwin":
                for app in ("Microsoft Edge", "Google Chrome"):
                    if subprocess.run(["open", "-na", app, "--args", f"--app={url}", size]).returncode == 0:
                        return
            else:
                for exe in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
                    path = shutil.which(exe)
                    if path:
                        subprocess.Popen([path, f"--app={url}", size], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
        except Exception:
            pass
        webbrowser.open(url)

    def stop(self) -> None:
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
