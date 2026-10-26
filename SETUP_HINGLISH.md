# OpenJarvis Setup Guide (Hinglish)

> **Mikasa voice assistant** (bas "Mikasa" bolo, laptop kaam karega) ka setup [`MIKASA.md`](MIKASA.md) mein hai.

Ye repo **OpenJarvis** ka source code hai. OpenJarvis Stanford (Hazy Research + Scaling Intelligence Lab) ka open-source personal AI hai, jo tumhare laptop pe locally chalta hai. Cloud APIs optional hain.

- Original repo: https://github.com/open-jarvis/OpenJarvis
- Docs: https://open-jarvis.github.io/OpenJarvis/
- License: Apache 2.0 (`LICENSE` file dekho). Original authors ka credit isi license ke under rehna chahiye.

> Upstream ke changes: original repo se copy kiya gaya (commit `0583901`, 26 Oct 2026). Do cheezein hata di gayi hain:
> 1. `desktop/src-tauri/binaries/ollama-aarch64-apple-darwin` (77 MB ka Ollama binary). Repo halka rakhne ke liye hataya. Sirf Mac desktop app build karna ho tab chahiye.
> 2. `.github/workflows/`, taaki upstream ke release/docs CI workflows tumhare GitHub account pe na chalein.

---

## 1. Requirements

| Cheez | Version |
|---|---|
| Python | 3.10+ |
| [uv](https://docs.astral.sh/uv/) | latest (Python package manager) |
| [Ollama](https://ollama.com/download) | local models chalane ke liye |
| Node.js | 22+ (sirf `jarvis gui` ke liye) |

Windows pe ho to **WSL2** use karo, ya niche diya native Windows installer.

---

## 2. Sabse aasaan tareeka: one-line installer

Ye official installer hai. uv, venv, Ollama aur ek starter model sab khud setup kar deta hai (broadband pe ~3 min):

```bash
# macOS / Linux / WSL2
curl -fsSL https://open-jarvis.github.io/OpenJarvis/install.sh | bash
```

```powershell
# Native Windows (PowerShell)
irm https://open-jarvis.github.io/OpenJarvis/install.ps1 | iex
```

Phir bas `jarvis` chalao.

---

## 3. Is repo se (source se) setup

```bash
# 1. Repo clone karo
git clone https://github.com/arju9gb123456/beanssite.git
cd beanssite

# 2. uv install karo (agar nahi hai)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Dependencies install karo (.venv ban jayega)
uv sync

# 4. Check karo
uv run jarvis --help
uv run jarvis doctor
```

> Har command ke aage `uv run` lagao, ya pehle `source .venv/bin/activate` kar lo. Uske baad seedha `jarvis` likh sakte ho.

### Local model (Ollama)

```bash
# Ollama install: https://ollama.com/download
ollama serve            # alag terminal mein chalu rakho
ollama pull qwen3:8b    # ya koi bhi chhota model, jaise llama3.2:3b
```

---

## 4. Chalao

```bash
jarvis                 # chat start (default preset: chat-simple)
jarvis gui             # browser wala graphical interface (Node 22+ chahiye)
jarvis ask "Aaj ka plan banao"
```

### Presets

```bash
jarvis init --preset <name> --force
```

| Preset | Kya karta hai |
|---|---|
| `chat-simple` | Simple chat, koi tool nahi |
| `morning-digest-linux` / `-mac` / `-minimal` | Email, calendar, news se roz subah ka spoken briefing |
| `deep-research` | Docs pe multi-step research, citations ke saath |
| `code-assistant` | Code chalana, files padhna, shell access |
| `scheduled-monitor` | Schedule pe chalne wala agent, memory ke saath |

---

## 5. Video wala setup: Voice (ElevenLabs) + Inbox/Calendar

### Voice key (ElevenLabs)

1. https://elevenlabs.io pe sign up karo → **Profile → API Keys** se key banao.
2. **Voice Library** se apni pasand ki voice choose karo aur uska **Voice ID** copy karo.
3. Key environment variable mein daalo (code yahi naam padhta hai):

```bash
export ELEVENLABS_API_KEY="tumhari-key-yahan"
```

Hamesha ke liye ise `~/.bashrc` / `~/.zshrc` mein daal do. **Key kabhi GitHub pe commit mat karna.**

4. Config file (`~/.openjarvis/config.toml`) mein voice set karo:

```toml
[speech]
tts_backend = "elevenlabs"
voice_id = "YAHAN_ELEVENLABS_VOICE_ID"

[digest]
tts_backend = "elevenlabs"
voice_id = "YAHAN_ELEVENLABS_VOICE_ID"
timezone = "Asia/Kolkata"
```

> Free option: ElevenLabs ki jagah `kokoro` backend (default) bhi kaam karta hai, bina kisi API key ke.

### Apps connect karo (Gmail, Calendar, Tasks)

```bash
jarvis init --preset morning-digest-linux --force   # Mac pe: morning-digest-mac
jarvis connect gdrive      # ek Google OAuth se Gmail + Calendar + Tasks
jarvis digest --fresh      # pehla morning brief generate + play
```

Isse Jarvis bata dega: kaunse emails pending hain, kaunse important hain, kisko reply nahi kiya.

---

## 6. Developer setup (code mein changes karne ke liye)

```bash
uv sync --extra dev
uv run pre-commit install
uv run pytest tests/ -v
```

Structure:

| Folder | Kya hai |
|---|---|
| `src/openjarvis/` | Main Python package (agents, tools, speech, connectors, CLI) |
| `configs/openjarvis/examples/` | Preset config files |
| `frontend/` | `jarvis gui` wala web UI |
| `desktop/` | Tauri desktop app |
| `rust/` | Rust extension (fast paths) |
| `docs/` | MkDocs documentation |
| `tests/` | Test suite |

---

## 7. Problem aaye to

- `jarvis doctor` chalao, ye bata dega kya missing hai.
- Ollama connect nahi ho raha → check karo `ollama serve` chal raha hai (port 11434).
- `jarvis: command not found` → `uv run jarvis` use karo ya `.venv` activate karo.
- Official docs: https://open-jarvis.github.io/OpenJarvis/getting-started/install/
