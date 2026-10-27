"""Bol ke code likhwao: AI code likhta hai, file save hoti hai, VS Code mein khulti hai."""

from __future__ import annotations

import datetime as _dt
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from mikasa import settings

EXT = {
    "python": "py", "py": "py", "html": "html", "javascript": "js", "js": "js", "css": "css",
    "java": "java", "c": "c", "cpp": "cpp", "c++": "cpp", "typescript": "ts", "ts": "ts",
    "jsx": "jsx", "tsx": "tsx", "bash": "sh", "sh": "sh", "shell": "sh", "sql": "sql",
    "php": "php", "go": "go", "rust": "rs", "kotlin": "kt", "dart": "dart", "json": "json",
    "powershell": "ps1", "batch": "bat", "bat": "bat", "react": "jsx",
}

PROMPT = (
    "You are an expert programmer. Write complete, working, well-structured code for this request "
    "from Arjun sir (it may be in Hinglish): \"{task}\".\n"
    "Rules: reply with ONLY ONE markdown code block that starts with the language name "
    "(like ```python or ```html). For a web page, put HTML, CSS and JS in one single html file. "
    "Add short helpful comments. No explanation outside the code block."
)


def _code_dir() -> Path:
    d = settings.DATA_DIR / "code"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(task: str) -> str:
    words = re.findall(r"[a-z0-9]+", task.lower())
    skip = {"ek", "ka", "ki", "ke", "code", "likho", "likh", "banao", "bana", "karo", "kar", "do",
            "mujhe", "mere", "liye", "aur", "vs", "kholo", "khol", "please", "write", "make", "a", "the"}
    words = [w for w in words if w not in skip][:4]
    return "_".join(words) or "code"


def extract_code(answer: str) -> tuple[str, str]:
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S)
    m = re.search(r"```([\w+#-]*)[^\n]*\n(.*?)```", answer, flags=re.S)
    if m:
        lang = (m.group(1) or "").lower()
        return EXT.get(lang, "txt" if lang else "py"), m.group(2).rstrip() + "\n"
    return "txt", answer.strip() + "\n"


def find_vscode() -> Optional[str]:
    exe = shutil.which("code")
    if exe:
        return exe
    candidates = []
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidates = [
            Path(local) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd",
            Path(local) / "Programs" / "Microsoft VS Code" / "Code.exe",
            Path(pf) / "Microsoft VS Code" / "bin" / "code.cmd",
        ]
    elif sys.platform == "darwin":
        candidates = [Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def open_in_vscode(path: Path) -> bool:
    exe = find_vscode()
    try:
        if exe:
            if exe.lower().endswith(".cmd"):
                subprocess.Popen(f'"{exe}" "{path.parent}" -g "{path}"', shell=True)
            else:
                subprocess.Popen([exe, str(path.parent), "-g", str(path)])
            return True
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


class Coder:
    def __init__(self, brain) -> None:
        self.brain = brain
        self.last_file: Optional[Path] = None

    def write(self, task: str) -> str:
        j = self.brain._get()
        if j is None:
            return "AI connect nahi hai, isliye code nahi likh paayi. Ollama chalu karo."
        try:
            answer = j.ask(PROMPT.format(task=task), agent="simple")
        except Exception as exc:
            print(f"[Mikasa] Code error: {exc}")
            return "Code likhte waqt error aaya. Ollama check karo."
        ext, code = extract_code(answer or "")
        if len(code.strip()) < 10:
            return "Code theek se nahi bana, ek baar phir boliye."
        path = _code_dir() / f"{_slug(task)}_{_dt.datetime.now():%H%M%S}.{ext}"
        path.write_text(code, encoding="utf-8")
        self.last_file = path
        print(f"[Mikasa] Code save: {path}")
        opened = open_in_vscode(path)
        where = "VS Code mein khol diya hai" if opened else f"file {path.name} mein save hai"
        return f"Code likh diya, {where}. Chalana ho to boliye, Mikasa code run karo."

    def run_last(self) -> str:
        path = self.last_file
        if path is None:
            files = sorted(_code_dir().glob("*.*"), key=lambda p: p.stat().st_mtime)
            path = files[-1] if files else None
        if path is None or not path.exists():
            return "Abhi koi code nahi likha hai."
        if path.suffix in (".html", ".htm"):
            webbrowser.open(path.resolve().as_uri())
            return "Page browser mein khol diya."
        if path.suffix == ".py":
            py = sys.executable
            if sys.platform.startswith("win"):
                subprocess.Popen(f'start "Mikasa code" cmd /k ""{py}" "{path}""', shell=True, cwd=path.parent)
            elif sys.platform == "darwin":
                subprocess.Popen(["osascript", "-e", f'tell app "Terminal" to do script "\\"{py}\\" \\"{path}\\""'])
            else:
                subprocess.Popen([py, str(path)], cwd=path.parent)
            return "Code naye terminal mein chala diya."
        return f"{path.suffix} file main khud nahi chala sakti, VS Code se chalaiye."
