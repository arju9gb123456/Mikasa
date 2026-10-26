"""Mikasa ki saari settings yahin hain. Jo badalna ho, yahin badlo.

Made by Arjun Ahirwar, built on OpenJarvis (Apache-2.0).
"""

from pathlib import Path

# ── Tum ───────────────────────────────────────────────────────────────────
USER_NAME = "Arjun"

# ── Wake word ─────────────────────────────────────────────────────────────
# Whisper "Mikasa" ko kabhi Roman mein, kabhi Devanagari mein likhta hai,
# isliye dono tarah ke spellings rakhe hain. Naye spellings yahan add kar do.
WAKE_WORDS = [
    "mikasa", "mikaasa", "meekasa", "mikasha", "mikaasha", "mikassa", "micasa",
    "मिकासा", "मीकासा", "मिकाशा", "मीकाशा", "मिकसा", "मिकास", "मिकासाह",
]
WAKE_FUZZY = 0.75          # 0-1, kam karoge to zyada aasaani se jaagegi (false trigger bhi badhenge)
FOLLOWUP_SECONDS = 12      # jawab ke baad itne second tak bina "Mikasa" bole agli baat sun legi

# ── Mic / listening ───────────────────────────────────────────────────────
SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.03
MIN_SPEECH_RMS = 350       # isse dheemi awaaz ko speech nahi maanega
NOISE_MULTIPLIER = 2.8     # background noise se kitna zyada loud ho to speech maane
END_SILENCE_SECONDS = 0.9  # itni der chup = baat khatam
MIN_UTTERANCE_SECONDS = 0.35
MAX_UTTERANCE_SECONDS = 15
MIC_DEVICE = None          # None = default mic. Specific mic ke liye uska number/naam do

# ── Speech-to-text (faster-whisper, laptop pe offline) ────────────────────
STT_MODEL = "small"        # tiny / base / small / medium / large-v3 (bada = accurate, slow)
STT_LANGUAGE = "hi"        # "hi" Hinglish ke liye best. "en" sirf English ke liye
STT_DEVICE = "auto"        # auto / cpu / cuda
STT_PROMPT = (
    "Mikasa, Gmail खोलो. WhatsApp खोलो. YouTube पर गाने चलाओ. Google पर search करो. "
    "Note बनाओ. Task add करो. Mikasa, आज के tasks बताओ."
)

# ── Text-to-speech ────────────────────────────────────────────────────────
TTS_ENGINE = "edge"        # "edge" (natural voice, internet chahiye) / "pyttsx3" (offline)
TTS_VOICE = "hi-IN-SwaraNeural"   # female Hindi voice. Male: "hi-IN-MadhurNeural"
TTS_RATE = "+8%"

# ── Brain (OpenJarvis AI) ─────────────────────────────────────────────────
BRAIN_MODEL = None         # None = ~/.openjarvis/config.toml wala model. Jaise "qwen3:8b"
BRAIN_AGENT = "orchestrator"
BRAIN_TOOLS = ["web_search", "calculator", "think", "get_weather"]
BRAIN_MAX_SPOKEN_CHARS = 450
HISTORY_TURNS = 6          # pichhli kitni baatein yaad rakhe

# ── Data (notes, tasks, screenshots) ──────────────────────────────────────
DATA_DIR = Path.home() / "Mikasa"

# ── Apps / websites jo "khol" bolne pe khulenge ───────────────────────────
# label = Mikasa kya bolegi, names = jo tum bologe (Roman + Devanagari), url = browser link,
# win/mac/linux = desktop app kholne ki command (na mile to url khulega).
APPS = {
    "gmail": {
        "label": "Gmail",
        "names": ["gmail", "g mail", "mail", "email", "जीमेल", "मेल", "ईमेल"],
        "url": "https://mail.google.com",
    },
    "whatsapp": {
        "label": "WhatsApp",
        "names": ["whatsapp", "whats app", "watsapp", "wp", "व्हाट्सएप", "व्हाट्सऐप", "वॉट्सऐप", "वाट्सएप", "व्हाट्सप"],
        "url": "https://web.whatsapp.com",
        "win": "whatsapp:",
        "mac": "WhatsApp",
    },
    "youtube": {
        "label": "YouTube",
        "names": ["youtube", "you tube", "यूट्यूब", "यू ट्यूब", "युट्यूब"],
        "url": "https://www.youtube.com",
    },
    "google": {
        "label": "Google",
        "names": ["google", "गूगल"],
        "url": "https://www.google.com",
    },
    "chrome": {
        "label": "Chrome",
        "names": ["chrome", "browser", "क्रोम", "ब्राउज़र", "ब्राउजर"],
        "url": "https://www.google.com",
        "win": "chrome",
        "mac": "Google Chrome",
        "linux": "google-chrome",
    },
    "calendar": {
        "label": "Calendar",
        "names": ["calendar", "कैलेंडर", "कैलेण्डर"],
        "url": "https://calendar.google.com",
    },
    "drive": {
        "label": "Google Drive",
        "names": ["google drive", "drive", "ड्राइव"],
        "url": "https://drive.google.com",
    },
    "instagram": {
        "label": "Instagram",
        "names": ["instagram", "insta", "इंस्टाग्राम", "इंस्टा"],
        "url": "https://www.instagram.com",
    },
    "linkedin": {
        "label": "LinkedIn",
        "names": ["linkedin", "लिंक्डइन", "लिंकडइन"],
        "url": "https://www.linkedin.com",
    },
    "github": {
        "label": "GitHub",
        "names": ["github", "git hub", "गिटहब", "गिट हब"],
        "url": "https://github.com",
    },
    "chatgpt": {
        "label": "ChatGPT",
        "names": ["chatgpt", "chat gpt", "चैटजीपीटी", "चैट जीपीटी"],
        "url": "https://chatgpt.com",
    },
    "claude": {
        "label": "Claude",
        "names": ["claude", "क्लॉड", "क्लाउड"],
        "url": "https://claude.ai",
    },
    "maps": {
        "label": "Google Maps",
        "names": ["maps", "map", "मैप", "मैप्स", "नक्शा"],
        "url": "https://maps.google.com",
    },
    "spotify": {
        "label": "Spotify",
        "names": ["spotify", "स्पॉटिफाई", "स्पोटिफाई"],
        "url": "https://open.spotify.com",
        "win": "spotify:",
        "mac": "Spotify",
    },
    "vscode": {
        "label": "VS Code",
        "names": ["vs code", "vscode", "visual studio code", "code editor", "वीएस कोड", "वी एस कोड"],
        "win": "code",
        "mac": "Visual Studio Code",
        "linux": "code",
    },
    "notepad": {
        "label": "Notepad",
        "names": ["notepad", "नोटपैड"],
        "win": "notepad",
        "mac": "TextEdit",
        "linux": "gedit",
    },
    "calculator": {
        "label": "Calculator",
        "names": ["calculator", "calc", "कैलकुलेटर", "कैलक्युलेटर"],
        "win": "calc",
        "mac": "Calculator",
        "linux": "gnome-calculator",
    },
    "files": {
        "label": "File Explorer",
        "names": ["file explorer", "explorer", "files", "फाइल", "फ़ाइल", "फाइल्स"],
        "win": "explorer",
        "mac": "Finder",
        "linux": "nautilus",
    },
    "settings": {
        "label": "Settings",
        "names": ["settings", "setting", "सेटिंग", "सेटिंग्स"],
        "win": "ms-settings:",
        "mac": "System Settings",
        "linux": "gnome-control-center",
    },
}
