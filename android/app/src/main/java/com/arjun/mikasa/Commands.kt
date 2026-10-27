package com.arjun.mikasa

import android.Manifest
import android.app.SearchManager
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.os.BatteryManager
import android.provider.AlarmClock
import android.provider.ContactsContract
import android.provider.MediaStore
import android.provider.Settings
import org.json.JSONObject
import java.util.Calendar

data class Reply(val text: String, val sleep: Boolean = false)

/** Phone pe kaam: rule-based (turant) + Brain ke JSON intents. Jawab Devanagari-Hinglish mein (Hindi voice ke liye). */
class Commands(private val act: MainActivity, private val store: Store) {

    private val ctx: Context get() = act

    // ── vocab ──
    private val openStems = listOf("khol", "open", "chalu", "start", "launch", "खोल", "ओपन", "चालू", "स्टार्ट")
    private val filler = setOf(
        "pe", "par", "पर", "पे", "mein", "में", "karo", "kar", "करो", "कर", "do", "दो", "de", "दे", "please", "zara",
        "जरा", "mujhe", "मुझे", "mera", "मेरा", "meri", "मेरी", "ek", "एक", "app", "ऐप", "एप", "wala", "वाला", "ko", "को",
        "ki", "की", "ka", "का", "ke", "के", "yaar", "यार", "na", "ना", "jara", "dena", "देना", "the", "a"
    ).map { Text.normalize(it) }.toSet()

    private var appCache: List<Pair<String, String>>? = null // (label, package)

    private fun apps(): List<Pair<String, String>> {
        appCache?.let { return it }
        val pm = ctx.packageManager
        val i = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val list = pm.queryIntentActivities(i, 0).map {
            it.loadLabel(pm).toString() to it.activityInfo.packageName
        }.distinctBy { it.second }
        appCache = list
        return list
    }

    private val aliases = mapOf(
        "whatsapp" to "WhatsApp", "vatsap" to "WhatsApp", "vatsep" to "WhatsApp", "vhatsep" to "WhatsApp",
        "yutyub" to "YouTube", "yutub" to "YouTube", "youtube" to "YouTube", "insta" to "Instagram",
        "instagram" to "Instagram", "jimel" to "Gmail", "gmail" to "Gmail", "mel" to "Gmail", "email" to "Gmail",
        "kemra" to "Camera", "kaimra" to "Camera", "camera" to "Camera", "gelri" to "Gallery", "gailri" to "Gallery",
        "photos" to "Photos", "photo" to "Photos", "setting" to "Settings", "settings" to "Settings",
        "kelkuletar" to "Calculator", "kailkuletar" to "Calculator", "calculator" to "Calculator", "ghadi" to "Clock",
        "clock" to "Clock", "crom" to "Chrome", "krom" to "Chrome", "chrome" to "Chrome", "mep" to "Maps",
        "maps" to "Maps", "map" to "Maps", "plestor" to "Play Store", "playstore" to "Play Store",
        "spotifai" to "Spotify", "spotify" to "Spotify", "fesbuk" to "Facebook", "facebook" to "Facebook",
        "snepchet" to "Snapchat", "snapchat" to "Snapchat", "telegram" to "Telegram", "teligram" to "Telegram",
        "fonpe" to "PhonePe", "phonepe" to "PhonePe", "pe" to "Paytm", "paytm" to "Paytm", "gpay" to "GPay",
        "gugalpe" to "GPay", "contacts" to "Contacts", "kontekt" to "Contacts", "fon" to "Phone", "phone" to "Phone",
        "mesej" to "Messages", "messages" to "Messages", "calendar" to "Calendar", "kailendar" to "Calendar",
        "keleandar" to "Calendar", "files" to "Files", "fail" to "Files", "drive" to "Drive", "linkdin" to "LinkedIn",
        "linkedin" to "LinkedIn", "chatgpt" to "ChatGPT", "chetjipiti" to "ChatGPT", "netflix" to "Netflix",
        "netfliks" to "Netflix", "amezon" to "Amazon", "amazon" to "Amazon", "flipkart" to "Flipkart"
    )

    /** Spoken naam -> installed app (label, package). */
    fun findApp(spoken: String): Pair<String, String>? {
        val k = Text.key(spoken)
        if (k.isBlank()) return null
        val target = aliases[k]?.let { Text.key(it) } ?: k
        var best: Pair<String, String>? = null
        var bestScore = 0.0
        for (app in apps()) {
            val lk = Text.key(app.first)
            if (lk.isBlank()) continue
            val score = when {
                lk == target -> 1.0
                lk.startsWith(target) || target.startsWith(lk) -> 0.9
                else -> Text.similarity(lk, target)
            }
            if (score > bestScore) { bestScore = score; best = app }
        }
        return if (bestScore >= 0.62) best else null
    }

    private fun stripWords(tokens: List<String>, drop: Collection<String>): List<String> =
        tokens.filter { t -> t !in filler && drop.none { d -> t.startsWith(Text.normalize(d)) } }

    // ── contacts ──
    fun hasPerm(p: String) = ctx.checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED

    fun findContact(spoken: String): Pair<String, String>? {
        if (!hasPerm(Manifest.permission.READ_CONTACTS)) {
            act.askPermission(Manifest.permission.READ_CONTACTS)
            return null
        }
        val target = Text.key(spoken)
        if (target.isBlank()) return null
        var best: Pair<String, String>? = null
        var bestScore = 0.0
        val cur = ctx.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            arrayOf(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME, ContactsContract.CommonDataKinds.Phone.NUMBER),
            null, null, null
        ) ?: return null
        cur.use {
            while (it.moveToNext()) {
                val name = it.getString(0) ?: continue
                val num = it.getString(1) ?: continue
                val nk = Text.key(name)
                val first = Text.key(name.split(" ").first())
                val score = maxOf(
                    if (nk == target) 1.0 else Text.similarity(nk, target),
                    if (first == target) 0.97 else Text.similarity(first, target) * 0.95,
                    if (nk.startsWith(target) && target.length >= 3) 0.9 else 0.0
                )
                if (score > bestScore) { bestScore = score; best = name to num }
            }
        }
        return if (bestScore >= 0.6) best else null
    }

    private fun digits(num: String): String {
        var d = num.filter { it.isDigit() }
        if (d.length == 10) d = "91$d"
        if (d.startsWith("0") && d.length == 11) d = "91" + d.drop(1)
        return d
    }

    // ── actions (sab Devanagari-Hinglish jawab dete hain) ──
    private fun start(i: Intent): Boolean = try {
        act.startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); true
    } catch (e: ActivityNotFoundException) { false } catch (e: SecurityException) { false }

    fun openApp(spoken: String): Reply {
        val app = findApp(spoken) ?: return Reply("सॉरी, \"$spoken\" नाम का app phone में नहीं मिला।")
        val i = ctx.packageManager.getLaunchIntentForPackage(app.second)
            ?: return Reply("${app.first} खुल नहीं पाया।")
        start(i)
        return Reply("${app.first} खोल रही हूँ।")
    }

    fun call(name: String): Reply {
        if (name.isBlank()) return Reply("किसको call लगाऊँ?")
        if (!hasPerm(Manifest.permission.READ_CONTACTS)) {
            act.askPermission(Manifest.permission.READ_CONTACTS)
            return Reply("पहले contacts की permission दे दीजिए, फिर दोबारा बोलिए।")
        }
        val c = findContact(name) ?: return Reply("\"$name\" नाम का contact नहीं मिला।")
        val uri = Uri.parse("tel:" + c.second.filter { it.isDigit() || it == '+' })
        if (hasPerm(Manifest.permission.CALL_PHONE)) start(Intent(Intent.ACTION_CALL, uri))
        else { act.askPermission(Manifest.permission.CALL_PHONE); start(Intent(Intent.ACTION_DIAL, uri)) }
        return Reply("${c.first} को call लगा रही हूँ।")
    }

    fun whatsapp(name: String, message: String): Reply {
        val pkg = listOf("com.whatsapp", "com.whatsapp.w4b").firstOrNull {
            ctx.packageManager.getLaunchIntentForPackage(it) != null
        }
        if (name.isBlank()) {
            if (pkg != null) start(ctx.packageManager.getLaunchIntentForPackage(pkg)!!)
            return Reply("WhatsApp खोल रही हूँ।")
        }
        if (!hasPerm(Manifest.permission.READ_CONTACTS)) {
            act.askPermission(Manifest.permission.READ_CONTACTS)
            return Reply("पहले contacts की permission दे दीजिए, फिर दोबारा बोलिए।")
        }
        val c = findContact(name) ?: return Reply("\"$name\" नाम का contact नहीं मिला।")
        val url = "https://api.whatsapp.com/send?phone=${digits(c.second)}" +
            if (message.isNotBlank()) "&text=" + Uri.encode(message) else ""
        val i = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        if (pkg != null) i.setPackage(pkg)
        start(i)
        return if (message.isNotBlank()) Reply("${c.first} का WhatsApp chat खोल के message लिख दिया है। बस send दबाइए।")
        else Reply("${c.first} का WhatsApp chat खोल दिया।")
    }

    fun sms(name: String, message: String): Reply {
        if (!hasPerm(Manifest.permission.READ_CONTACTS)) {
            act.askPermission(Manifest.permission.READ_CONTACTS)
            return Reply("पहले contacts की permission दे दीजिए।")
        }
        val c = findContact(name) ?: return Reply("\"$name\" नाम का contact नहीं मिला।")
        start(Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:" + c.second)).putExtra("sms_body", message))
        return Reply("${c.first} के लिए SMS लिख दिया है, बस send दबाइए।")
    }

    fun youtube(q: String): Reply {
        val i = Intent(Intent.ACTION_SEARCH).setPackage("com.google.android.youtube").putExtra("query", q)
        if (!start(i)) start(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/results?search_query=" + Uri.encode(q))))
        return Reply("YouTube पे $q लगा रही हूँ।")
    }

    fun search(q: String): Reply {
        if (!start(Intent(Intent.ACTION_WEB_SEARCH).putExtra(SearchManager.QUERY, q)))
            start(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=" + Uri.encode(q))))
        return Reply("Google पे $q search कर रही हूँ।")
    }

    fun navigate(place: String): Reply {
        if (!start(Intent(Intent.ACTION_VIEW, Uri.parse("google.navigation:q=" + Uri.encode(place)))))
            start(Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=" + Uri.encode(place))))
        return Reply("$place का रास्ता दिखा रही हूँ, safe जाइएगा!")
    }

    fun alarm(hour: Int, minute: Int): Reply {
        val i = Intent(AlarmClock.ACTION_SET_ALARM)
            .putExtra(AlarmClock.EXTRA_HOUR, hour).putExtra(AlarmClock.EXTRA_MINUTES, minute)
            .putExtra(AlarmClock.EXTRA_MESSAGE, "Mikasa").putExtra(AlarmClock.EXTRA_SKIP_UI, true)
        start(i)
        val h12 = if (hour % 12 == 0) 12 else hour % 12
        return Reply("$h12:${String.format("%02d", minute)} ${if (hour < 12) "AM" else "PM"} का alarm लगा दिया।")
    }

    fun timer(minutes: Int): Reply {
        val i = Intent(AlarmClock.ACTION_SET_TIMER).putExtra(AlarmClock.EXTRA_LENGTH, minutes * 60)
            .putExtra(AlarmClock.EXTRA_MESSAGE, "Mikasa").putExtra(AlarmClock.EXTRA_SKIP_UI, true)
        start(i)
        return Reply("$minutes मिनट का timer चालू कर दिया।")
    }

    fun torch(on: Boolean): Reply = try {
        val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val id = cm.cameraIdList.first { cm.getCameraCharacteristics(it).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true }
        cm.setTorchMode(id, on)
        Reply(if (on) "Torch जला दी।" else "Torch बंद कर दी।")
    } catch (e: Exception) { Reply("Torch नहीं चल पाई।") }

    fun volume(dir: String): Reply {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        when (dir) {
            "mute" -> am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_TOGGLE_MUTE, AudioManager.FLAG_SHOW_UI)
            "down" -> repeat(3) { am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI) }
            else -> repeat(3) { am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI) }
        }
        return Reply("हो गया।")
    }

    fun settingsPage(page: String): Reply {
        val action = when (page) {
            "wifi" -> Settings.ACTION_WIFI_SETTINGS
            "bluetooth" -> Settings.ACTION_BLUETOOTH_SETTINGS
            else -> Settings.ACTION_SETTINGS
        }
        start(Intent(action))
        return Reply(when (page) { "wifi" -> "WiFi settings खोल दी।"; "bluetooth" -> "Bluetooth settings खोल दी।"; else -> "Settings खोल दी।" })
    }

    fun camera(): Reply {
        start(Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA))
        return Reply("Camera खोल रही हूँ, smile कीजिए!")
    }

    fun battery(): Reply {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val p = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val extra = if (p < 20) " Charge पे लगा दीजिए ना, please!" else ""
        return Reply("Battery $p परसेंट है।$extra")
    }

    fun timeNow(): Reply {
        val c = Calendar.getInstance()
        val h = c.get(Calendar.HOUR).let { if (it == 0) 12 else it }
        return Reply("अभी $h बजकर ${c.get(Calendar.MINUTE)} मिनट हुए हैं।")
    }

    fun dateNow(): Reply {
        val days = listOf("रविवार", "सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार")
        val months = listOf("जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर")
        val c = Calendar.getInstance()
        return Reply("आज ${days[c.get(Calendar.DAY_OF_WEEK) - 1]}, ${c.get(Calendar.DAY_OF_MONTH)} ${months[c.get(Calendar.MONTH)]} ${c.get(Calendar.YEAR)} है।")
    }

    fun reminder(text: String, source: String, dueHint: String = ""): Reply {
        var due: Long? = null
        if (dueHint.isNotBlank()) {
            try {
                val p = Regex("(\\d{4})-(\\d{2})-(\\d{2})[ T](\\d{1,2}):(\\d{2})").find(dueHint)
                if (p != null) {
                    val c = Calendar.getInstance()
                    c.set(p.groupValues[1].toInt(), p.groupValues[2].toInt() - 1, p.groupValues[3].toInt(),
                        p.groupValues[4].toInt(), p.groupValues[5].toInt(), 0)
                    if (c.timeInMillis > System.currentTimeMillis()) due = c.timeInMillis
                }
            } catch (e: Exception) { due = null }
        }
        if (due == null) due = TimeParse.parse(source)
        val task = if (due != null) TimeParse.stripTime(text) else text
        if (task.isBlank()) return Reply("क्या याद दिलाऊँ?")
        store.addTask(task, due)
        return if (due != null) Reply("पक्का! ${TimeParse.spoken(due)} याद दिला दूँगी: $task।")
        else Reply("Task add कर दिया: $task।")
    }

    fun taskList(): Reply {
        val p = store.pendingTasks()
        if (p.isEmpty()) return Reply("कोई pending task नहीं है। सब clear!")
        val items = p.take(7).mapIndexed { i, t ->
            val d = t.optLong("due", 0L)
            "${i + 1}, ${t.optString("task")}" + if (d > 0) " (${TimeParse.spoken(d)})" else ""
        }.joinToString("। ")
        return Reply("आपके ${p.size} pending tasks हैं। $items")
    }

    fun noteAdd(text: String, remember: Boolean): Reply {
        if (text.isBlank()) return Reply("हाँ, क्या लिखूँ?")
        store.addNote(text)
        return Reply(if (remember) "पक्का याद रखूँगी: $text।" else "Note save कर दिया: $text।")
    }

    fun noteList(): Reply {
        val n = store.recentNotes(3)
        return if (n.isEmpty()) Reply("अभी कोई note नहीं है।") else Reply("आपके last notes: " + n.joinToString("। "))
    }

    // ── rule-based (bina AI, turant) ──
    fun handle(raw: String): Reply? {
        val t = Text.normalize(raw)
        val tk = t.split(" ").filter { it.isNotBlank() }
        if (tk.isEmpty()) return null
        val u = store.userName

        // pehchaan
        if (Text.hasStem(tk, listOf("kisne", "किसने")) &&
            Text.hasStem(tk, listOf("banaya", "बनाया", "bana", "बना", "tumh", "तुम्ह", "aapk", "आपक", "mikasa", "मिकासा"))
        ) return Reply("मुझे ${store.creator} sir ने बनाया है। मैं $u की personal AI assistant Mikasa हूँ।")
        if (tk.size <= 6 && Text.hasPhrase(t, listOf("kaun ho", "कौन हो", "who are you", "tumhara naam", "तुम्हारा नाम", "आपका नाम")))
            return Reply("मैं Mikasa हूँ, $u की personal AI assistant। मुझे ${store.creator} sir ने बनाया है।")

        // so jao / thanks
        if (tk.size <= 4 && Text.hasPhrase(t, listOf("so jao", "सो जाओ", "so ja", "सो जा", "bas", "बस", "chup", "चुप", "rehne do", "रहने दो", "cancel")))
            return Reply("ठीक है।", sleep = true)
        if (tk.size <= 4 && Text.hasPhrase(t, listOf("thank you", "thanks", "shukriya", "शुक्रिया", "धन्यवाद", "थैंक यू", "थैंक्यू")))
            return Reply("Welcome! ज़रूरत हो तो बस Mikasa बोलिए।", sleep = true)

        // torch
        if (Text.hasStem(tk, listOf("torch", "टॉर्च", "flash", "फ्लैश", "टोर्च"))) {
            val off = Text.hasStem(tk, listOf("band", "बंद", "off", "ऑफ", "bujha", "बुझा"))
            return torch(!off)
        }
        // volume
        if (Text.hasStem(tk, listOf("volume", "वॉल्यूम", "वोल्यूम", "awaz", "awaaz", "आवाज"))) {
            return volume(when {
                Text.hasStem(tk, listOf("mute", "म्यूट", "band", "बंद")) -> "mute"
                Text.hasStem(tk, listOf("kam", "कम", "down", "धीर", "dheer", "low")) -> "down"
                else -> "up"
            })
        }
        if (Text.hasStem(tk, listOf("battery", "बैटरी", "charge", "चार्ज"))) return battery()
        val asking = Text.hasStem(tk, listOf("kya", "क्या", "kitn", "कितन", "bata", "बता", "what", "कौन"))
        if (asking && Text.hasStem(tk, listOf("time", "टाइम", "samay", "समय", "baj", "बज")) && !Text.hasStem(tk, listOf("yaad", "याद")))
            return timeNow()
        if (asking && Text.hasStem(tk, listOf("date", "डेट", "tarikh", "तारीख", "din", "दिन")))
            return dateNow()
        if (Text.hasStem(tk, listOf("wifi", "वाईफाई", "वाई", "wi"))) return settingsPage("wifi")
        if (Text.hasStem(tk, listOf("bluetooth", "ब्लूटूथ"))) return settingsPage("bluetooth")

        // reminder / alarm / timer / tasks
        if (Text.hasStem(tk, listOf("alarm", "अलार्म", "अलार्म"))) {
            val due = TimeParse.parse(raw) ?: return Reply("कितने बजे का alarm लगाऊँ?")
            val c = Calendar.getInstance().apply { timeInMillis = due }
            return alarm(c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE))
        }
        if (Text.hasStem(tk, listOf("timer", "टाइमर"))) {
            val m = Regex("(\\d+)").find(TimeParse.prep(raw))?.value?.toInt() ?: return Reply("कितने मिनट का timer?")
            return timer(m)
        }
        val taskWord = Text.hasPhrase(t, listOf("yaad dila", "याद दिला", "yaad dilana", "याद दिलाना", "reminder", "रिमाइंडर", "task", "टास्क", "tasks", "टास्क्स"))
        if (taskWord) {
            if (Text.hasStem(tk, listOf("bata", "बता", "suna", "सुना", "dikha", "दिखा", "list", "लिस्ट")) ||
                Text.hasPhrase(t, listOf("kya hai", "क्या है", "kitne", "कितने", "pending", "baki", "बाकी")))
                return taskList()
            val drop = listOf("yaad", "याद", "dila", "दिला", "reminder", "रिमाइंडर", "task", "टास्क", "add", "एड", "jod", "जोड़", "जोड", "daal", "डाल", "laga", "लगा", "set", "सेट")
            val content = stripWords(tk, drop).joinToString(" ")
            return reminder(content, raw)
        }

        // notes
        val remember = Text.hasPhrase(t, listOf("yaad rakhna", "याद रखना", "yaad rakh", "याद रख"))
        if (remember || Text.hasStem(tk, listOf("note", "नोट"))) {
            if (!remember && Text.hasStem(tk, listOf("suna", "सुना", "bata", "बता", "padh", "पढ", "dikha", "दिखा")) &&
                !Text.hasStem(tk, listOf("likh", "लिख", "bana", "बना")))
                return noteList()
            val content = stripWords(tk, listOf("note", "नोट", "yaad", "याद", "rakh", "रख", "likh", "लिख", "bana", "बना", "save", "सेव", "lo", "लो", "le", "ले", "kar", "कर"))
            return noteAdd(content.joinToString(" "), remember)
        }

        // call
        if (Text.hasStem(tk, listOf("call", "कॉल", "कोल", "phone", "फोन", "फ़ोन")) &&
            Text.hasStem(tk, listOf("laga", "लगा", "kar", "कर", "mila", "मिला", "lagao", "लगाओ", "do", "दो", "करो"))) {
            val koIdx = tk.indexOfFirst { it == "ko" || it == "को" }
            val nameToks = if (koIdx > 0) tk.subList(0, koIdx) else tk
            val name = stripWords(nameToks, listOf("call", "कॉल", "कोल", "phone", "फोन", "laga", "लगा", "kar", "कर", "mila", "मिला")).joinToString(" ")
            return call(name)
        }

        // whatsapp / message
        val waApp = Text.hasStem(tk, listOf("whatsapp", "व्हाट्सएप", "व्हाट्सऐप", "वॉट्सऐप", "वाट्सएप", "व्हाट्सअप", "वाट्सअप", "watsapp"))
        val msgWord = Text.hasStem(tk, listOf("message", "msg", "मैसेज", "मेसेज", "sms", "एसएमएस"))
        val sendWord = Text.hasStem(tk, listOf("bhej", "भेज", "send", "सेंड", "bol", "बोल", "likh", "लिख"))
        val koIdx = tk.indexOfFirst { it == "ko" || it == "को" }
        if ((waApp || msgWord) && koIdx > 0 && (sendWord || msgWord)) {
            val seps = setOf("pe", "पे", "par", "पर", "aur", "और")
            var s = 0
            for (i in koIdx - 1 downTo 0) {
                val w = tk[i]
                if (w in seps || Text.hasStem(listOf(w), listOf("whatsapp", "व्हाट्स", "वॉट्स", "वाट्स", "message", "मैसेज", "मेसेज", "sms"))) { s = i + 1; break }
            }
            val name = tk.subList(s, koIdx).joinToString(" ")
            var after = tk.subList(koIdx + 1, tk.size)
            val ki = after.indexOfFirst { it == "ki" || it == "कि" || it == "that" }
            if (ki >= 0) after = after.subList(ki + 1, after.size)
            val edge = setOf("message", "msg", "मैसेज", "मेसेज", "bhejo", "bhej", "भेजो", "भेज", "send", "karo", "करो", "kar", "कर",
                "do", "दो", "de", "दे", "bolo", "बोलो", "likho", "लिखो", "ye", "यह", "ये", "whatsapp", "व्हाट्सएप", "pe", "पे", "par", "पर", "dena", "देना", "ki", "कि")
            val msg = after.dropWhile { it in edge }.dropLastWhile { it in edge }.joinToString(" ")
            return if (Text.hasStem(tk, listOf("sms", "एसएमएस"))) sms(name, msg) else whatsapp(name, msg)
        }
        if (waApp && tk.size <= 3) return whatsapp("", "")

        // youtube / search / navigate
        val yt = Text.hasStem(tk, listOf("youtube", "यूट्यूब", "यूट्यूब", "युट्यूब", "यू"))
        val play = Text.hasStem(tk, listOf("chala", "चला", "baja", "बजा", "play", "प्ले", "laga", "लगा", "suna", "सुना"))
        val srch = Text.hasStem(tk, listOf("search", "सर्च", "dhund", "ढूंढ", "ढूँढ", "khoj", "खोज"))
        val drops = listOf("youtube", "यूट्यूब", "युट्यूब", "यू", "ट्यूब", "google", "गूगल", "search", "सर्च", "chala", "चला", "baja", "बजा",
            "play", "प्ले", "laga", "लगा", "suna", "सुना", "dhund", "ढूंढ", "khoj", "खोज", "kholo", "खोलो")
        if (Text.hasStem(tk, listOf("rasta", "रास्ता", "navigate", "नेविगेट", "direction", "डायरेक्शन")) || Text.hasPhrase(t, listOf("le chalo", "ले चलो"))) {
            val place = stripWords(tk, listOf("rasta", "रास्ता", "navigate", "नेविगेट", "direction", "le", "ले", "chalo", "चलो", "dikha", "दिखा", "tak", "तक", "jana", "जाना", "hai", "है"))
            if (place.isNotEmpty()) return navigate(place.joinToString(" "))
        }
        if ((yt && (play || srch)) || (play && Text.hasStem(tk, listOf("gaana", "gana", "गाना", "गाने", "song", "सॉन्ग", "video", "वीडियो")))) {
            val q = stripWords(tk, drops).joinToString(" ")
            if (q.isNotBlank()) return youtube(q)
        }
        if (srch) {
            val q = stripWords(tk, drops).joinToString(" ")
            if (q.isNotBlank()) return search(q)
        }

        // camera
        if (Text.hasStem(tk, listOf("camera", "कैमरा", "कैमरा")) && Text.hasStem(tk, openStems + listOf("photo", "फोटो", "selfie", "सेल्फी"))) return camera()

        // open app
        if (Text.hasStem(tk, openStems)) {
            val name = stripWords(tk, openStems).joinToString(" ")
            if (name.isNotBlank()) {
                val app = findApp(name)
                if (app != null) return openApp(name)
            }
        }
        return null
    }

    // ── Brain ke JSON intent -> kaam ──
    fun execute(j: JSONObject): Reply? {
        fun s(k: String) = j.optString(k, "").trim()
        return when (j.optString("intent").lowercase()) {
            "open_app" -> if (s("app").isNotBlank()) openApp(s("app")) else null
            "call" -> call(s("contact"))
            "whatsapp" -> whatsapp(s("contact"), s("message"))
            "sms" -> sms(s("contact"), s("message"))
            "youtube" -> youtube(s("query"))
            "search" -> search(s("query"))
            "navigate" -> navigate(s("place"))
            "alarm" -> Regex("(\\d{1,2}):(\\d{2})").find(s("time"))?.let { alarm(it.groupValues[1].toInt(), it.groupValues[2].toInt()) }
            "timer" -> timer(j.optInt("minutes", 5))
            "reminder" -> reminder(s("text"), s("text"), s("due"))
            "task_list" -> taskList()
            "note_add" -> noteAdd(s("text"), false)
            "note_list" -> noteList()
            "torch" -> torch(j.optBoolean("on", true))
            "volume" -> volume(s("dir"))
            "settings" -> settingsPage(s("page"))
            "camera" -> camera()
            "time" -> timeNow()
            "date" -> dateNow()
            "battery" -> battery()
            "chat", "unclear" -> if (s("reply").isNotBlank()) Reply(s("reply")) else null
            else -> null
        }
    }
}
