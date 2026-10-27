package com.arjun.mikasa

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {

    companion object {
        @Volatile var instance: MainActivity? = null
        private const val FOLLOWUP_MS = 10_000L
        private val WAKE = listOf("mikasa", "mikasha", "mikaasa", "micasa", "meekasa", "mikassa", "mikas", "nikasa", "mekasa")
    }

    private lateinit var web: WebView
    private lateinit var store: Store
    private lateinit var commands: Commands
    private lateinit var brain: Brain
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var recognizer: SpeechRecognizer? = null
    private val ui = Handler(Looper.getMainLooper())
    private val bg = Executors.newSingleThreadExecutor()

    private var resumed = false
    private var listening = false
    private var speaking = false
    private var busy = false
    private var awakeUntil = 0L
    private var forceOnce = false
    private var muted = false
    private var greeted = false
    private var pendingAsk: String? = null // "note"

    // ── lifecycle ──
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        instance = this
        store = Store(this)
        commands = Commands(this, store)
        brain = Brain(store)
        Store.ensureChannel(this)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.statusBarColor = 0xFF0B080A.toInt()
        window.navigationBarColor = 0xFF0B080A.toInt()

        web = WebView(this)
        web.setBackgroundColor(0xFF07070A.toInt())
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.mediaPlaybackRequiresUserGesture = false
        web.webChromeClient = WebChromeClient()
        web.addJavascriptInterface(Bridge(), "Android")
        web.loadUrl("file:///android_asset/index.html")
        setContentView(web)

        val need = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) need.add(Manifest.permission.POST_NOTIFICATIONS)
        val missing = need.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) requestPermissions(missing.toTypedArray(), 1)

        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                ttsReady = true
                configureVoice()
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(id: String?) {}
                    override fun onDone(id: String?) { ui.post { afterSpeak() } }
                    @Deprecated("old api") override fun onError(id: String?) { ui.post { afterSpeak() } }
                })
                ui.postDelayed({ if (!greeted) { greeted = true; say(greeting()) } }, 600)
            }
        }
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(i: Intent?) {
        i ?: return
        i.getStringExtra("reminder")?.let { task -> ui.postDelayed({ onReminder(task) }, 900) }
        if (i.action == Intent.ACTION_ASSIST || i.action == "android.intent.action.VOICE_COMMAND") {
            awakeUntil = System.currentTimeMillis() + FOLLOWUP_MS
            forceOnce = true
            ui.postDelayed({ restartListening(0) }, 400)
        }
    }

    override fun onResume() {
        super.onResume()
        resumed = true
        restartListening(500)
    }

    override fun onPause() {
        super.onPause()
        resumed = false
        stopListening()
        setMuted(false)
    }

    override fun onDestroy() {
        instance = null
        setMuted(false)
        recognizer?.destroy()
        tts?.shutdown()
        bg.shutdownNow()
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(code: Int, perms: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, perms, results)
        restartListening(300)
    }

    fun askPermission(p: String) {
        if (checkSelfPermission(p) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(p), 2)
    }

    // ── JS bridge ──
    inner class Bridge {
        @JavascriptInterface fun listen() = ui.post {
            awakeUntil = System.currentTimeMillis() + FOLLOWUP_MS
            forceOnce = true
            if (speaking) tts?.stop()
            restartListening(0)
        }
        @JavascriptInterface fun send(text: String) = ui.post { process(text, true) }
        @JavascriptInterface fun getSettings(): String = store.settingsJson().toString()
        @JavascriptInterface fun saveSettings(json: String) = ui.post {
            try { store.saveSettings(JSONObject(json)) } catch (e: Exception) {}
            configureVoice()
            js("onInfo(${info()})")
            restartListening(200)
        }
        @JavascriptInterface fun voices(): String {
            val arr = JSONArray()
            tts?.voices?.filter { it.locale.language == "hi" || (it.locale.language == "en" && it.locale.country == "IN") }
                ?.sortedBy { it.name }?.forEach { arr.put(it.name) }
            return arr.toString()
        }
        @JavascriptInterface fun testVoice(name: String) = ui.post {
            store.voice = name
            configureVoice()
            say("नमस्ते ${store.userName}, मैं Mikasa हूँ। ये मेरी आवाज़ कैसी लगी?", title = false)
        }
        @JavascriptInterface fun stopSpeaking() = ui.post { tts?.stop(); afterSpeak() }
        @JavascriptInterface fun info(): String = this@MainActivity.info()
    }

    private fun info(): String = JSONObject()
        .put("ai", when {
            !brain.ready() -> "off (settings mein key daalo)"
            store.aiMode == "ollama" -> "Ollama · ${store.ollamaModel}"
            else -> "Gemini · ${store.geminiModel}"
        })
        .put("wake", store.wakeWord)
        .put("user", store.userName)
        .toString()

    private fun js(code: String) = ui.post { web.evaluateJavascript(code, null) }
    private fun q(s: String) = JSONObject.quote(s)

    private fun state(s: String) = js("onState(${q(s)})")

    // ── voice out ──
    private fun configureVoice() {
        val t = tts ?: return
        if (!ttsReady) return
        t.setLanguage(Locale("hi", "IN"))
        val all = t.voices ?: emptySet()
        val chosen = all.firstOrNull { it.name == store.voice }
            ?: all.filter { it.locale.language == "hi" && !it.isNetworkConnectionRequired }
                .sortedBy { v -> listOf("hia", "hic", "hie", "hib").indexOfFirst { v.name.contains(it) }.let { if (it < 0) 99 else it } }
                .firstOrNull()
            ?: all.firstOrNull { it.locale.language == "hi" }
        if (chosen != null) t.setVoice(chosen)
        t.setPitch(store.pitch)
        t.setSpeechRate(store.rate)
    }

    fun say(text: String, title: Boolean = true) {
        val line = if (title) withTitle(text) else text
        js("onReply(${q(line)})")
        stopListening()
        setMuted(false)
        speaking = true
        state("speaking")
        val t = tts
        if (t == null || !ttsReady) { afterSpeak(); return }
        val spoken = line.replace(Regex("https?://\\S+"), "link").replace(Regex("[*_#`>|]"), "")
        t.speak(spoken, TextToSpeech.QUEUE_FLUSH, null, "m" + System.currentTimeMillis())
    }

    private fun afterSpeak() {
        if (!speaking) return
        speaking = false
        busy = false
        state("idle")
        restartListening(250)
    }

    // ── voice in ──
    private fun setMuted(on: Boolean) {
        if (on == muted) return
        if (on && !store.muteBeep) return
        val am = getSystemService(AUDIO_SERVICE) as AudioManager
        val dir = if (on) AudioManager.ADJUST_MUTE else AudioManager.ADJUST_UNMUTE
        for (s in listOf(AudioManager.STREAM_MUSIC, AudioManager.STREAM_NOTIFICATION, AudioManager.STREAM_SYSTEM)) {
            try { am.adjustStreamVolume(s, dir, 0) } catch (e: Exception) {}
        }
        muted = on
    }

    private fun stopListening() {
        listening = false
        try { recognizer?.cancel() } catch (e: Exception) {}
    }

    private fun shouldListen(): Boolean =
        resumed && !speaking && !busy &&
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED &&
            (store.wakeWord || forceOnce || System.currentTimeMillis() < awakeUntil)

    private fun restartListening(delayMs: Long) {
        ui.removeCallbacks(listenRunnable)
        ui.postDelayed(listenRunnable, delayMs)
    }

    private val listenRunnable = Runnable { startListening() }

    private fun startListening() {
        if (!shouldListen()) {
            if (!speaking && !busy) state(if (store.wakeWord) "idle" else "sleeping")
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            js("onReply(${q("Is phone mein speech recognition nahi mila. Google app install/update kijiye.")})")
            return
        }
        if (recognizer == null) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this).also { it.setRecognitionListener(listener) }
        }
        val i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "hi-IN")
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            .putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 900)
            .putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
        setMuted(true)
        listening = true
        state(if (forceOnce || System.currentTimeMillis() < awakeUntil) "listening" else "idle")
        try { recognizer?.startListening(i) } catch (e: Exception) { listening = false; restartListening(800) }
    }

    private val listener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rms: Float) { if (listening) js("onLevel($rms)") }
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onPartialResults(partial: Bundle?) {
            val t = partial?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: return
            if (t.isNotBlank()) js("onPartial(${q(t)})")
        }
        override fun onEvent(eventType: Int, params: Bundle?) {}
        override fun onError(error: Int) {
            listening = false
            when (error) {
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY, SpeechRecognizer.ERROR_CLIENT -> {
                    recognizer?.destroy(); recognizer = null; restartListening(600)
                }
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> askPermission(Manifest.permission.RECORD_AUDIO)
                SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT, SpeechRecognizer.ERROR_SERVER -> restartListening(2500)
                else -> { forceOnce = false; restartListening(150) }
            }
        }
        override fun onResults(results: Bundle?) {
            listening = false
            val alts = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: arrayListOf()
            val heard = alts.firstOrNull { detectWake(it).first } ?: alts.firstOrNull() ?: ""
            val force = forceOnce
            forceOnce = false
            if (heard.isBlank()) { restartListening(150); return }
            process(heard, force)
        }
    }

    // ── samajhna ──
    private fun detectWake(text: String): Pair<Boolean, String> {
        val tk = Text.tokens(text)
        var best = 0.0; var bi = -1; var bs = 1
        for (i in 0 until minOf(4, tk.size)) {
            for (span in 1..2) {
                if (i + span > tk.size) continue
                val k = Text.key(tk.subList(i, i + span).joinToString(""))
                for (w in WAKE) {
                    var sc = if (k == w) 1.0 else Text.similarity(k, w)
                    if (span == 2) sc -= 0.02
                    if (sc > best) { best = sc; bi = i; bs = span }
                }
            }
        }
        return if (best >= 0.72 && bi >= 0) true to tk.drop(bi + bs).joinToString(" ") else false to text
    }

    fun process(heard: String, force: Boolean) {
        val (found, rest) = detectWake(heard)
        val now = System.currentTimeMillis()
        if (!force && !found && now > awakeUntil && pendingAsk == null) {
            js("onIgnored(${q(heard)})")
            restartListening(150)
            return
        }
        js("onHeard(${q(heard)})")
        val cmd = if (found) rest else heard
        if (cmd.isBlank()) {
            awakeUntil = now + FOLLOWUP_MS
            say(wakeReply(), title = false)
            return
        }
        if (pendingAsk == "note") {
            pendingAsk = null
            store.addNote(cmd)
            awakeUntil = now + FOLLOWUP_MS
            say("Note save कर दिया।")
            return
        }
        val r = try { commands.handle(cmd) } catch (e: Exception) { Reply("सॉरी, ये करते वक़्त error आया।") }
        if (r != null) { deliver(r); return }
        if (!brain.ready()) {
            deliver(Reply("ये समझने के लिए मुझे AI चाहिए। Settings में Gemini की free key डाल दीजिए ना, फिर मैं हर बात का जवाब दूँगी।"))
            return
        }
        busy = true
        state("thinking")
        bg.execute {
            val j = brain.route(cmd)
            ui.post {
                val intentName = j?.optString("intent") ?: ""
                val rr: Reply = if (j == null) {
                    Reply(if (brain.lastError.isNotBlank()) "AI से जवाब नहीं आया। Internet या key check कीजिए।" else "सॉरी, समझ नहीं आया। एक बार फिर बोलिए?")
                } else {
                    val ex: Reply? = try { commands.execute(j) } catch (e: Exception) { null }
                    ex ?: Reply("हम्म, ये मैं अभी नहीं कर पाऊँगी।")
                }
                if (intentName == "note_add" && (j?.optString("text") ?: "").isBlank()) pendingAsk = "note"
                busy = false
                deliver(rr, isChat = intentName == "chat" || intentName == "unclear")
            }
        }
    }

    private fun deliver(r: Reply, isChat: Boolean = false) {
        awakeUntil = if (r.sleep) 0L else System.currentTimeMillis() + FOLLOWUP_MS
        say(r.text, title = !isChat)
    }

    fun onReminder(task: String) = ui.post {
        js("onReminder(${q(task)})")
        awakeUntil = System.currentTimeMillis() + FOLLOWUP_MS
        say(listOf(
            "${store.userName}! याद दिला रही हूँ: $task। भूल मत जाना, okay?",
            "ओए ${store.userName}, time हो गया! $task। चलिए, जल्दी कीजिए!",
            "${store.userName}, आपने कहा था याद दिलाऊँ: $task। मैं हूँ ना, भूलने नहीं दूँगी!"
        ).random(), title = false)
    }

    // ── personality ──
    private fun withTitle(text: String): String {
        val u = store.userName
        if (text.contains(u, ignoreCase = true)) return text
        return listOf("$u, ", "जी $u, ", "Okay $u! ", "लीजिए $u, ", "हाँ जी $u, ").random() + text
    }

    private fun wakeReply(): String {
        val u = store.userName
        return listOf("हाँ $u, बोलिए ना?", "जी $u, मैं सुन रही हूँ!", "हाँ जी $u, हुकुम कीजिए!", "बोलिए बोलिए $u, Mikasa हाज़िर है!").random()
    }

    private fun greeting(): String {
        val u = store.userName
        val h = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        val ai = if (brain.ready()) "" else " और हाँ, settings में Gemini key डाल दोगे तो मैं हर बात का जवाब दूँगी।"
        return when (h) {
            in 5..11 -> "Good morning $u! उठ गए आप? चलिए, आज का दिन मस्त बनाते हैं।$ai"
            in 12..16 -> "नमस्ते $u! Lunch किया या नहीं? मैं आ गई हूँ, बस Mikasa बोलिए।$ai"
            in 17..21 -> "Good evening $u! दिन कैसा गया? बताइए, मैं क्या मदद करूँ?$ai"
            else -> "$u, इतनी रात को भी जाग रहे हो? ठीक है, मैं हूँ ना साथ में।$ai"
        }
    }
}
