"""Mikasa ki saari settings yahin hain. Jo badalna ho, yahin badlo.

Made by Arjun Ahirwar, built on OpenJarvis (Apache-2.0).
"""

from pathlib import Path

# ── Tum ───────────────────────────────────────────────────────────────────
USER_NAME = "Arjun sir"          # Mikasa tumhe hamesha isi naam se bulayegi
CREATOR_NAME = "Arjun Ahirwar"   # "Mikasa kisne banaya?" ka jawab

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
# "auto" = GPU ho to "large-v3-turbo" (bahut accurate + tez), warna "small"
STT_MODEL = "auto"         # auto / small / medium / large-v3-turbo / large-v3
STT_LANGUAGE = "hi"        # "hi" Hinglish ke liye best. "en" sirf English ke liye
STT_DEVICE = "auto"        # auto / cpu / cuda
STT_BEAM_SIZE = 5
# Whisper ko pehle se batao kaise words aate hain -> English app names sahi likhega
STT_PROMPT = (
    "Mikasa, VS Code open करो. Chrome open करो. Gmail खोलो. WhatsApp पे Rahul को message भेजो. "
    "YouTube पर Arijit Singh के गाने चलाओ. Google पर search करो. Note बनाओ. Task add करो. "
    "Mikasa, Python का code लिखो. Mikasa, आज के tasks बताओ."
)
STT_HOTWORDS = ("Mikasa VS Code Chrome Gmail WhatsApp YouTube Google Notepad Calculator Instagram "
                "LinkedIn GitHub Spotify ChatGPT Claude Python HTML code open message")

# ── Text-to-speech ────────────────────────────────────────────────────────
# "auto" = ELEVENLABS_API_KEY set ho to ElevenLabs (sabse real insaan jaisi), warna Edge
TTS_ENGINE = "auto"        # auto / elevenlabs / edge / pyttsx3 (offline)
# Edge voices (free). Kaunsi pasand hai sunne ke liye: start_mikasa.bat --voice-test
#   en-IN-NeerjaExpressiveNeural  - natural, expressive Indian ladki (Hinglish ke liye best)
#   en-IN-NeerjaNeural            - same, thodi calm
#   hi-IN-SwaraNeural             - Hindi ladki
TTS_VOICE = "en-IN-NeerjaExpressiveNeural"
TTS_FALLBACK_VOICES = ["en-IN-NeerjaNeural", "hi-IN-SwaraNeural"]
TTS_RATE = "+4%"
TTS_PITCH = "+3Hz"         # thodi meethi/ladki jaisi. Zyada patli chahiye to "+8Hz"
# ElevenLabs: elevenlabs.io pe free account -> API key -> Windows env variable ELEVENLABS_API_KEY.
# Voice Library se koi Hindi/Indian female voice choose karo aur uska Voice ID yahan daalo.
ELEVENLABS_VOICE_ID = ""
ELEVENLABS_MODEL = "eleven_flash_v2_5"   # tez. Aur natural: "eleven_multilingual_v2"

# ── Brain (Ollama AI) ─────────────────────────────────────────────────────
BRAIN_MODEL = "qwen3:8b"   # Ollama model ka naam (ollama list se dekho)
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_KEEP_ALIVE = "60m"  # model itni der GPU/RAM mein garam rahe -> jawab tez
SMART_ROUTER = True        # galat suna ho to bhi AI se matlab samajh ke command chalao
BRAIN_AGENT = "orchestrator"
BRAIN_TOOLS = ["web_search", "calculator", "think", "get_weather"]
BRAIN_MAX_SPOKEN_CHARS = 450
HISTORY_TURNS = 6          # pichhli kitni baatein yaad rakhe

# ── Screen (HUD) ──────────────────────────────────────────────────────────
HUD_ENABLED = True         # laal rings + avatar + stats wali screen
HUD_OPEN_WINDOW = True     # start pe window khud khule (Edge app mode)
HUD_PORT = 7878

# ── WhatsApp ──────────────────────────────────────────────────────────────
WHATSAPP_MODE = "web"        # "web" = browser mein WhatsApp Web (chat/message kar sakti hai), "app" = desktop app
WHATSAPP_BROWSER = "msedge"  # "msedge" (Windows mein hamesha hota hai) / "chrome"
# Jo naam tum bologe -> WhatsApp mein saved naam ya number (91 ke saath). Zarurat ho to add karo:
CONTACTS = {
    # "honey": "Priti",
    # "rahul": "919876543210",
}

# ── Data (notes, tasks, screenshots, code) ──────────────────────────────────────
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
