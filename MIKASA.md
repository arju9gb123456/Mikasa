# Mikasa: tumhari personal voice assistant

Bas **"Mikasa"** bolo aur kaam bolo. Na Enter dabana, na kuch type karna. Mikasa laptop pe hamesha sunti rehti hai, apna naam sunte hi jaag jaati hai, kaam karti hai, aur Hinglish mein jawab bolti hai.

Made by Arjun Ahirwar. AI brain ke liye [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) (Apache-2.0) use hota hai.

---

## Kaise kaam karti hai

```
Mic hamesha on  →  awaaz aayi?  →  Whisper (offline) text banata hai
      →  "Mikasa" bola?  →  haan: command samjho  →  kaam karo + bol ke batao
                         →  nahi: ignore (TV/baatein nahi sunti)
```

- **Wake word:** "Mikasa", "Hey Mikasa", "Ok Mikasa", sab chalega. Sirf "Mikasa" bologe to wo "Haan Arjun, boliye?" bolegi.
- **Follow-up:** Jawab ke baad **12 second** tak agli baat bina "Mikasa" bole sun leti hai, jaise real baat-cheet.
- **Quick commands** (neeche list hai) turant laptop pe hote hain, AI ke bina.
- **Baaki sab** ("duniya ka sabse bada desh?", "aaj mausam kaisa hai?") OpenJarvis AI se poocha jata hai, jo web search, weather aur calculator tools use kar sakta hai.
- Bolte waqt Mikasa mic band rakhti hai, taaki apni hi awaaz na sune.

---

## Kya-kya bol sakte ho

| Bolo | Mikasa kya karegi |
|---|---|
| "Mikasa, Gmail kholo" / "mail check karo" | Gmail khulega |
| "Mikasa, WhatsApp kholo" | WhatsApp app (na ho to WhatsApp Web) |
| "Mikasa, YouTube pe Arijit Singh ke gaane chalao" | YouTube search khulega |
| "Mikasa, gaana bajao" | YouTube pe gaane |
| "Mikasa, Google pe IPL score search karo" | Google search |
| "Mikasa, Gmail mein Amazon search karo" | Gmail ke andar search |
| "Mikasa, Chrome / VS Code / Calculator / Notepad / Settings kholo" | App khulega |
| "Mikasa, Chrome band karo" | App band |
| "Mikasa, note bana lo ki kal 10 baje meeting hai" | Note save |
| "Mikasa, note banao" → "Kya likhun?" → "doodh lana hai" | Do step mein note |
| "Mikasa, mere notes sunao" / "notes kholo" | Last 3 notes bolegi / file kholegi |
| "Mikasa, task add karo assignment submit karna hai" | Task list mein add |
| "Mikasa, yaad dila dena kal 5 baje gym jana hai" | Task add |
| "Mikasa, aaj ke tasks batao" | Pending tasks bolegi |
| "Mikasa, assignment wala task ho gaya" | Wo task done |
| "Mikasa, time kya hua" / "aaj kya date hai" | Time / date |
| "Mikasa, volume badhao / kam karo / mute karo" | Volume |
| "Mikasa, screenshot lo" | Screenshot `~/Mikasa/screenshots/` mein |
| "Mikasa, so jao" / "thank you" | Wapas sirf naam pe jaagegi |
| "Mikasa, band ho jao" | Program band |
| "Mikasa, tumhe kisne banaya?" | "Mujhe Arjun Ahirwar sir ne banaya hai" |
| "Mikasa, tum kaun ho?" | Apna parichay degi |
| "Mikasa, VS Code kholo aur ek calculator ka python code likho" | AI code likhegi, file save karke VS Code mein kholegi |
| "Mikasa, ek login page ki website bana do" | HTML page likh ke VS Code mein |
| "Mikasa, code run karo" | Last likha code chalayegi (Python = naya terminal, HTML = browser) |
| "Mikasa, WhatsApp kholo" / "browser mein web WhatsApp kholo" | WhatsApp Web khulega |
| "Mikasa, Rahul ki chat kholo" | Rahul ki chat khulegi |
| "Mikasa, WhatsApp pe Rahul ko message bhejo ki main 5 baje aaunga" | Message **type** karke poochegi "Bhej dun?" → "haan" = send, "na" = hata degi |
| "Mikasa, Priti ko good morning bhej do" | Same, confirm karke |
| "Mikasa, Rahul ko WhatsApp karo" → "Kya message likhun?" → "hello bhai" → "Bhej dun?" → "haan" | Step-by-step |
| Kuch bhi aur poocho | AI jawab dega |

Mikasa tumhe hamesha **"Arjun sir"** bulati hai (naam `mikasa/settings.py` mein `USER_NAME` se badal sakte ho).

Hindi mein bolo ya Hinglish mein, dono chalega ("मिकासा, यूट्यूब पर गाने चलाओ").

Notes aur tasks yahan save hote hain: `~/Mikasa/notes.md` aur `~/Mikasa/tasks.json` (Windows pe `C:\Users\<tum>\Mikasa\`).

---

## Setup (ek baar)

### 1. Repo aur uv

```bash
git clone https://github.com/arju9gb123456/Mikasa.git
cd Mikasa
```

uv install (agar nahi hai):
- **Windows (PowerShell):** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Mac/Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. AI brain: Ollama + model

1. https://ollama.com/download se Ollama install karo (ye background mein chalta rehta hai).
2. Model download karo:

```bash
ollama pull qwen3:8b        # 16GB+ RAM ke liye achha. GPU ho to aur fast
# kam RAM ho to:  ollama pull qwen3:4b
```

3. `mikasa/settings.py` mein `BRAIN_MODEL = "qwen3:8b"` pehle se set hai. Dusra model liya ho to wahan uska naam likh do.

> Ollama ke bina bhi Mikasa chalegi: apps kholna, search, notes, tasks, time sab kaam karega. Sirf general sawaalon ke jawab nahi aayenge.

### 3. Chalao

- **Windows:** `start_mikasa.bat` pe double-click
- **Mac/Linux:** `./start_mikasa.sh`
- Ya seedha: `uv run --extra mikasa python -m mikasa`

**Pehli baar** speech model (~500 MB, `small`) download hoga, 1-2 minute lagenge. Uske baad offline chalta hai.

**Mac pe:** pehli baar Terminal ko **Microphone** permission dena (System Settings → Privacy & Security → Microphone). Volume/screenshot ke liye **Accessibility** aur **Screen Recording** bhi.

### 4. Laptop on hote hi Mikasa khud start ho

- **Windows:** Mikasa folder mein **`setup_autostart.bat`** pe ek baar double-click karo. Bas. Ab har login pe Mikasa minimized window mein khud start hogi:
  - Ollama ready hone tak intezaar karti hai (max ~1 min).
  - Crash ho to 10 second mein khud restart hoti hai.
  - Internet late aaye to bhi kaam karti hai (us waqt offline voice).
  - Band karna ho: **`remove_autostart.bat`**.
- **Mac:** System Settings → General → Login Items → `+` → `start_mikasa.sh` choose karo.

---

## WhatsApp Web setup (ek baar)

1. Bolo **"Mikasa, WhatsApp kholo"**. Microsoft Edge ki ek alag window mein WhatsApp Web khulega.
2. Phone mein WhatsApp → **Linked devices** → **Link a device** → screen ka QR scan karo.
3. Login yaad rehta hai (`~/Mikasa/whatsapp_browser` folder mein). Agli baar QR nahi maangega.

- Mikasa **kabhi bina poochhe message nahi bhejti.** Pehle bolti hai kisko kya type kiya, phir tumhare "haan" pe hi Enter dabati hai.
- Chat ka naam dhyan se suno. Galat chat khuli ho to "na" bolo.
- Naam aur WhatsApp ka saved naam alag ho, to `settings.py` mein `CONTACTS` add karo, jaise `"honey": "Priti"`, ya seedha number `"rahul": "919876543210"`.
- Edge nahi hai to `WHATSAPP_BROWSER = "chrome"` karo. Dono na hon to: `uv run playwright install chromium`.
- WhatsApp apni website badalta rehta hai. Kabhi chat/message box na mile, to error mujhe bhejna, selectors update karne padenge (`mikasa/whatsapp.py` ke upar).

## Code likhwana

- Code `~/Mikasa/code/` folder mein save hota hai aur VS Code mein khulta hai.
- Code `qwen3:8b` likhta hai. Chhote programs (calculator, to-do app, login page) achhe banenge. Bade projects ke liye usse thoda-thoda karke bolo.
- "Mikasa code run karo" sirf Python aur HTML chalata hai, aur wo bhi tumhare bolne pe hi.

## Test / debug

```bash
uv run --extra mikasa python -m mikasa --text     # bina mic, type karke test
uv run --extra mikasa python -m mikasa --list-mics  # saare mic dekho
```

Terminal mein dikhta hai Mikasa ne kya suna. Jo "Mikasa" ke bina suna, wo grey mein `(suna, par Mikasa nahi bola)` likha aata hai.

---

## Apne hisaab se badlo: `mikasa/settings.py`

| Setting | Kya karta hai |
|---|---|
| `WAKE_WORDS` | Agar Mikasa tumhara naam galat sun rahi hai (terminal mein dekho kya likha), wo spelling yahan add kar do |
| `WAKE_FUZZY` | Kam karo (0.7) = aasaani se jaagegi. Zyada (0.85) = galti se kam jaagegi |
| `FOLLOWUP_SECONDS` | Jawab ke baad kitni der bina naam ke sune |
| `MIN_SPEECH_RMS` | Shor wali jagah ho to badhao (500-800) |
| `STT_MODEL` | `small` (default). GPU / tez laptop ho to `medium` = Hindi aur accurate |
| `TTS_VOICE` | `hi-IN-SwaraNeural` (female) / `hi-IN-MadhurNeural` (male) |
| `TTS_ENGINE` | `edge` (natural, internet chahiye) / `pyttsx3` (offline, robotic) |
| `BRAIN_MODEL` | Ollama model ka naam |
| `APPS` | Naye apps/websites add karo: `names` (jo bologe), `url`, aur `win`/`mac`/`linux` command |

Naya app add karne ka example (Amazon):

```python
"amazon": {
    "label": "Amazon",
    "names": ["amazon", "अमेज़न", "अमेजन"],
    "url": "https://www.amazon.in",
},
```

---

## Abhi kya nahi kar sakti (next version mein)

- **Mail likh ke bhejna:** Gmail abhi sirf khulta/search hota hai.
- **Reminder ka alarm:** "yaad dila dena" abhi task list mein jaata hai, time pe khud nahi bolti.
- **Gmail padh ke sunana** (kaunse mail pending hain): iske liye OpenJarvis ka `jarvis connect gdrive` + digest chahiye (`SETUP_HINGLISH.md` dekho), Mikasa mein jodna baaki hai.
- **Shell commands:** safety ke liye Mikasa ka AI laptop pe koi bhi command khud nahi chala sakta. Sirf upar wale fixed kaam karta hai.

## Files

```
mikasa/
  app.py        main loop (wake word, follow-up, sab jodta hai)
  listener.py   mic + speech detection + Whisper speech-to-text
  commands.py   quick commands (apps, search, notes, tasks, volume...)
  brain.py      OpenJarvis AI se baat
  speaker.py    awaaz (Edge neural voice / offline pyttsx3)
  whatsapp.py   WhatsApp Web automation (chat, type, confirm pe send)
  coder.py      bol ke code likhwana + VS Code / run
  settings.py   saari settings
start_mikasa.bat / start_mikasa.sh
setup_autostart.bat / remove_autostart.bat   (Windows autostart on/off)
```
