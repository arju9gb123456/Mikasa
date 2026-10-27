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

## Mikasa ki screen (HUD)

Mikasa start hote hi ek window khulti hai (Edge app mode), jisme ye sab hai:

- **Beech mein:** laal animated rings aur "MIKASA" core. Sunte waqt rings tez ghoomti hain, sochte waqt arc spin karti hai, bolte waqt core dhadakta hai.
- **Neeche:** Mikasa ka apna original avatar (caramel ponytail, amber aankhein, laal-kaali jacket). Chup rahe to **shy** (nazar neeche, gaal laal), sunte waqt sir tilt karke **dhyan se**, bolte waqt **cute** smile, aur kaam ke baad **cool wink**.
- **Left:** CPU, RAM, Disk, Battery, network speed, uptime, aur speech/AI/voice ka status.
- **Right:** ghadi, quick buttons (Gmail, WhatsApp, YouTube, VS Code, Notes, Tasks...) aur poori baat-cheet ka log.
- **Neeche ka box:** bolne ki jagah type bhi kar sakte ho.

Window band ho jaye to browser mein `http://127.0.0.1:7878` kholo. Screen nahi chahiye to `start_mikasa.bat --no-hud`, ya `settings.py` mein `HUD_ENABLED = False`.

**Apni avatar photo:** koi bhi image (PNG best, transparent background wali sabse achhi lagti hai) apne Mikasa data folder `C:\Users\<aap>\Mikasa\` mein **`avatar.png`** naam se rakh do (ya `avatar.jpg` / `avatar.gif`). Mikasa restart karo, screen pe wahi dikhegi aur bolte waqt hilegi/chamkegi. Ye photo sirf aapke laptop pe rehti hai, GitHub pe nahi jaati.

**Reminders (time pe khud bolti hai):**

| Bolo | Kab yaad dilayegi |
|---|---|
| "Mikasa, 5 baje yaad dila dena gym jana hai" | Aaj shaam 5:00 |
| "Mikasa, 10 minute baad yaad dilana chai" | 10 min baad |
| "Mikasa, kal subah 7 baje yaad dila dena assignment submit karna hai" | Kal 7:00 AM |
| "Mikasa, raat 10 baje padhai yaad dilana" / "saadhe 4 baje" / "do ghante baad" / "parso 11 baje" | Wahi time |

Time aate hi Mikasa bolti hai *"Arjun sir! Yaad dila rahi hoon: gym jana hai. Bhool mat jaana, okay?"*, aur screen pe ⏰ dikhta hai. Laptop band tha aur reminder nikal gaya, to agli baar start hote hi bata deti hai.

**Yaad rakhna:** "Mikasa, yaad rakhna mera exam 10 November ko hai" bologe to Mikasa ye baat aage ki baat-cheet mein yaad rakhti hai (jaise "exam ki taiyari kaisi chal rahi hai?").

**Personality:** Mikasa ab pyaari, chulbuli, caring ladki ki tarah baat karti hai: emotions, masti, thoda nakhre aur teasing, aapki fikr (khana khaya?). Kisi aur AI ki tareef karoge to mazaak mein jealous bhi hogi, par kaam kabhi mana nahi karti. Andaaz badalna ho to `mikasa/persona.py` edit karo.

## Accuracy, speed aur awaaz

- **Smart samajh:** Whisper kuch galat sune (jaise "bs को दोपन करो"), to Mikasa AI se poochti hai ki asal mein kya bola tha ("VS Code open karo") aur wahi command chalati hai. Window mein grey `(samjha: ...)` line dikhegi.
- **GPU:** NVIDIA GPU ho to Mikasa `large-v3-turbo` speech model GPU pe chalati hai, jo bahut accurate aur tez hai. GPU files (`nvidia-cublas`, `nvidia-cudnn`) `start_mikasa.bat` khud install karta hai (pehli baar ~1.5 GB, phir naya speech model ~1.6 GB).
- **Tez jawab:** AI model GPU pe 60 minute garam rehta hai aur Qwen3 ka lamba sochna band hai. Pehla jawab 5-10 sec, baaki 1-3 sec.
- **Awaaz chuno:** `start_mikasa.bat --voice-test` chalao. 5 female voices sunao, jo pasand aaye uska naam `settings.py` mein `TTS_VOICE` mein likho. Default `en-IN-NeerjaExpressiveNeural` hai (natural Indian ladki).
- **Sabse real awaaz (ElevenLabs):** elevenlabs.io pe free account → Profile → API key. Windows mein: `setx ELEVENLABS_API_KEY "tumhari-key"` (phir PowerShell naya kholo). Voice Library se Hindi female voice ka **Voice ID** `settings.py` ke `ELEVENLABS_VOICE_ID` mein daalo. Free plan mein ~10,000 characters/month milte hain, khatam hone pe Mikasa apne aap Edge voice pe aa jaati hai.

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
  router.py     smart samajh: galat suna text -> sahi command (Ollama)
  persona.py    personality, greetings, andaaz
  reminders.py  time samajhna (5 baje, 10 min baad, kal subah) + time pe yaad dilana
  hud/          screen: server.py (live status/stats) + index.html (rings, avatar, chat)
  settings.py   saari settings
start_mikasa.bat / start_mikasa.sh
setup_autostart.bat / remove_autostart.bat   (Windows autostart on/off)
```

---

## 📱 Phone wali Mikasa (Android app)

Phone ki apni Mikasa: wahi rings + avatar, "Mikasa" bolo aur phone pe kaam karwao.

**Install:** phone ke browser mein ye link kholo → `Mikasa.apk` download → kholo → "Install unknown apps" allow karo → Install.
https://github.com/arju9gb123456/Mikasa/releases/download/android-latest/Mikasa.apk

Har naye update pe GitHub khud naya APK bana deta hai (wahi link). Purani app ke upar install karo, data rehta hai.

**Pehli baar:**
1. Mic aur notification permission **Allow**. Call / WhatsApp ke liye contacts permission bhi maangegi.
2. ⚙️ Settings → **Gemini API key** daalo (free): phone browser mein `aistudio.google.com/apikey` → Create API key → copy → paste → Save. Iske bina bhi commands chalenge, sirf normal baat-cheet nahi.
3. Behtar Hindi awaaz: Phone Settings → "Text-to-speech output" → Google → Hindi voice download. Phir Mikasa settings mein "Awaaz suno" se chuno.
4. (Optional) Phone Settings → Apps → Default apps → **Digital assistant app** → Mikasa. Ab home button lamba dabao to seedha Mikasa sunegi.

**Kya bol sakte ho (Hindi/Hinglish):**

| Bolo | Kya hoga |
|---|---|
| "Mikasa, Instagram kholo" / koi bhi app | App khulegi |
| "Mikasa, Rahul ko call lagao" | Call |
| "Mikasa, WhatsApp pe Rahul ko message bhejo ki main aa raha hoon" | Rahul ka chat khul ke message likha milega, aap send dabao |
| "Mikasa, YouTube pe Arijit ke gaane chalao" | YouTube |
| "Mikasa, Bhopal station ka rasta dikhao" | Google Maps navigation |
| "Mikasa, subah 6 baje ka alarm lagao" / "10 minute ka timer" | Alarm / timer |
| "Mikasa, 5 baje yaad dila dena gym jana hai" | Theek 5 baje notification + Mikasa bolegi |
| "Mikasa, torch jalao / band karo", "volume badhao", "battery kitni hai", "time kya hua" | Turant |
| "Mikasa, note banao ki..." / "yaad rakhna ki..." | Note save, baat-cheet mein yaad rakhegi |
| Kuch bhi poocho | Gemini se friendly jawab |

**Limits:** "Mikasa" wake word tab sunti hai jab app screen pe khuli ho (Android background mein lagatar mic chalane nahi deta). Band screen pe reminders phir bhi aate hain. WhatsApp message Android ke rules ki wajah se aapko khud send dabana hoga.

**Laptop ka Ollama phone se (optional, same WiFi):** laptop pe PowerShell mein `setx OLLAMA_HOST 0.0.0.0` → Ollama restart → `ipconfig` se laptop ka IPv4 dekho → Mikasa app settings mein AI = "Laptop ka Ollama", URL `http://<IP>:11434`. Windows Firewall poochhe to Private network allow karo.
