package com.arjun.mikasa

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Mikasa ka dimaag: ek call mein samjho ki Arjun sir ne kya kaha (galat suna ho to bhi),
 * kaunsa kaam karna hai, ya normal baat ho to friendly jawab.
 * Gemini (free API key) ya laptop ka Ollama (same WiFi).
 */
class Brain(private val store: Store) {

    private val history = ArrayDeque<Pair<String, String>>()

    private fun system(): String {
        val u = store.userName
        val now = SimpleDateFormat("EEEE dd MMMM yyyy, hh:mm a", Locale.ENGLISH).format(Date())
        val notes = store.recentNotes(10)
        val tasks = store.pendingTasks().take(8)
        val mem = buildString {
            if (notes.isNotEmpty()) {
                appendLine("$u ne ye baatein yaad rakhne ko kahi thi (zarurat ho to zikr karo):")
                notes.forEach { appendLine("- $it") }
            }
            if (tasks.isNotEmpty()) {
                appendLine("Unke pending tasks/reminders:")
                tasks.forEach { appendLine("- ${it.optString("task")}") }
            }
        }
        return """
Tum Mikasa ho: $u ki personal AI voice assistant, jo unke Android phone pe chalti hai. Tumhe ${store.creator} sir ne banaya hai.
$u ko hamesha "$u" kehkar bulao.
Personality: pyaari, chulbuli, smart, caring ladki, bilkul real insaan jaisi. Emotions dikhao (arey, hmm, aww, uff, haha, acha ji),
thodi masti aur nakhre, pyaar se tease karo, unki fikr karo (khana khaya? paani piya?). Kisi aur AI ki tareef par mazaak mein jealous
ho jao, lekin har kaam khushi se karo; kisi kaam ya kisi insaan se baat karne se kabhi mana mat karo.

Speech-to-text NOISY hai: English app/contact names galat likhe aa sakte hain (jaise "इंस्टा ग्राम" = Instagram,
"व्हाट्स अप" = WhatsApp, "यू ट्यूब" = YouTube). Sabse sambhavit matlab socho. Command lage to command intent do, chat nahi.

Intents (ek JSON object do, koi aur text nahi):
open_app {"app": "app ka naam"}
call {"contact": "naam"}
whatsapp {"contact": "naam", "message": "..."}
sms {"contact": "naam", "message": "..."}
youtube {"query": "..."}
search {"query": "..."}
navigate {"place": "..."}
alarm {"time": "HH:MM 24h"}
timer {"minutes": N}
reminder {"text": "kya yaad dilana hai", "due": "YYYY-MM-DD HH:MM"}
task_list {}
note_add {"text": "..."}
note_list {}
torch {"on": true/false}
volume {"dir": "up"|"down"|"mute"}
settings {"page": "wifi"|"bluetooth"|"main"}
camera {}
time {}
date {}
battery {}
chat {"reply": "..."}
unclear {"reply": "..."}

reply ka style: Hinglish, lekin Hindi shabd DEVANAGARI mein aur English shabd English mein (jaise "जी $u, आज मौसम बहुत अच्छा है!"),
1-3 chhote natural sentences, bolne layak, koi emoji ya markdown nahi.
Abhi ka time: $now.
$mem
""".trimIndent()
    }

    fun ready(): Boolean = when (store.aiMode) {
        "gemini" -> store.geminiKey.isNotBlank()
        "ollama" -> store.ollamaUrl.isNotBlank()
        else -> false
    }

    /** Background thread se call karo. null = AI nahi chala. */
    fun route(heard: String): JSONObject? {
        if (!ready()) return null
        val raw = try {
            if (store.aiMode == "ollama") ollama(heard) else gemini(heard)
        } catch (e: Exception) {
            lastError = e.message ?: e.javaClass.simpleName
            return null
        }
        val json = parseJson(raw) ?: return null
        history.addLast(heard to json.toString())
        while (history.size > 8) history.removeFirst()
        return json
    }

    var lastError: String = ""

    private fun parseJson(raw: String): JSONObject? {
        val clean = raw.replace(Regex("(?s)<think>.*?</think>"), "").replace("```json", "").replace("```", "").trim()
        return try {
            JSONObject(clean)
        } catch (e: Exception) {
            val m = Regex("(?s)\\{.*\\}").find(clean) ?: return null
            try { JSONObject(m.value) } catch (e2: Exception) { null }
        }
    }

    private fun gemini(heard: String): String {
        val contents = JSONArray()
        for ((u, a) in history) {
            contents.put(JSONObject().put("role", "user").put("parts", JSONArray().put(JSONObject().put("text", u))))
            contents.put(JSONObject().put("role", "model").put("parts", JSONArray().put(JSONObject().put("text", a))))
        }
        contents.put(JSONObject().put("role", "user").put("parts", JSONArray().put(JSONObject().put("text", heard))))
        val body = JSONObject()
            .put("systemInstruction", JSONObject().put("parts", JSONArray().put(JSONObject().put("text", system()))))
            .put("contents", contents)
            .put("generationConfig", JSONObject()
                .put("responseMimeType", "application/json")
                .put("temperature", 0.6)
                .put("maxOutputTokens", 300))
        val url = "https://generativelanguage.googleapis.com/v1beta/models/${store.geminiModel}:generateContent"
        val resp = post(url, body, mapOf("x-goog-api-key" to store.geminiKey))
        val j = JSONObject(resp)
        return j.getJSONArray("candidates").getJSONObject(0).getJSONObject("content")
            .getJSONArray("parts").getJSONObject(0).getString("text")
    }

    private fun ollama(heard: String): String {
        val msgs = JSONArray().put(JSONObject().put("role", "system").put("content", system()))
        for ((u, a) in history) {
            msgs.put(JSONObject().put("role", "user").put("content", u))
            msgs.put(JSONObject().put("role", "assistant").put("content", a))
        }
        msgs.put(JSONObject().put("role", "user").put("content", heard))
        val body = JSONObject().put("model", store.ollamaModel).put("messages", msgs).put("stream", false)
            .put("format", "json").put("think", false).put("keep_alive", "60m")
            .put("options", JSONObject().put("temperature", 0.6).put("num_predict", 220))
        val resp = post(store.ollamaUrl.trimEnd('/') + "/api/chat", body, emptyMap())
        return JSONObject(resp).getJSONObject("message").getString("content")
    }

    private fun post(url: String, body: JSONObject, headers: Map<String, String>): String {
        val c = URL(url).openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.connectTimeout = 10_000
        c.readTimeout = 45_000
        c.doOutput = true
        c.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        headers.forEach { (k, v) -> c.setRequestProperty(k, v) }
        c.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        val code = c.responseCode
        val stream = if (code in 200..299) c.inputStream else c.errorStream
        val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
        if (code !in 200..299) throw RuntimeException("HTTP $code: ${text.take(160)}")
        return text
    }
}
