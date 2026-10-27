package com.arjun.mikasa

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Settings + notes + tasks/reminders (phone ke andar hi save). */
class Store(private val ctx: Context) {
    private val prefs = ctx.getSharedPreferences("mikasa", Context.MODE_PRIVATE)

    // ── settings ──
    var userName: String
        get() = prefs.getString("userName", "Arjun sir") ?: "Arjun sir"
        set(v) = prefs.edit().putString("userName", v).apply()
    var creator: String
        get() = prefs.getString("creator", "Arjun Ahirwar") ?: "Arjun Ahirwar"
        set(v) = prefs.edit().putString("creator", v).apply()
    var aiMode: String // "gemini" | "ollama" | "off"
        get() = prefs.getString("aiMode", "gemini") ?: "gemini"
        set(v) = prefs.edit().putString("aiMode", v).apply()
    var geminiKey: String
        get() = prefs.getString("geminiKey", "") ?: ""
        set(v) = prefs.edit().putString("geminiKey", v.trim()).apply()
    var geminiModel: String
        get() = prefs.getString("geminiModel", "gemini-2.5-flash") ?: "gemini-2.5-flash"
        set(v) = prefs.edit().putString("geminiModel", v.trim()).apply()
    var ollamaUrl: String
        get() = prefs.getString("ollamaUrl", "http://192.168.1.10:11434") ?: ""
        set(v) = prefs.edit().putString("ollamaUrl", v.trim()).apply()
    var ollamaModel: String
        get() = prefs.getString("ollamaModel", "qwen3:4b") ?: "qwen3:4b"
        set(v) = prefs.edit().putString("ollamaModel", v.trim()).apply()
    var wakeWord: Boolean
        get() = prefs.getBoolean("wakeWord", true)
        set(v) = prefs.edit().putBoolean("wakeWord", v).apply()
    var muteBeep: Boolean
        get() = prefs.getBoolean("muteBeep", true)
        set(v) = prefs.edit().putBoolean("muteBeep", v).apply()
    var voice: String
        get() = prefs.getString("voice", "") ?: ""
        set(v) = prefs.edit().putString("voice", v).apply()
    var pitch: Float
        get() = prefs.getFloat("pitch", 1.12f)
        set(v) = prefs.edit().putFloat("pitch", v).apply()
    var rate: Float
        get() = prefs.getFloat("rate", 1.05f)
        set(v) = prefs.edit().putFloat("rate", v).apply()

    fun settingsJson(): JSONObject = JSONObject()
        .put("userName", userName).put("creator", creator).put("aiMode", aiMode)
        .put("geminiKey", geminiKey).put("geminiModel", geminiModel)
        .put("ollamaUrl", ollamaUrl).put("ollamaModel", ollamaModel)
        .put("wakeWord", wakeWord).put("muteBeep", muteBeep).put("voice", voice)
        .put("pitch", pitch.toDouble()).put("rate", rate.toDouble())

    fun saveSettings(j: JSONObject) {
        if (j.has("userName")) userName = j.getString("userName").ifBlank { "Arjun sir" }
        if (j.has("creator")) creator = j.getString("creator")
        if (j.has("aiMode")) aiMode = j.getString("aiMode")
        if (j.has("geminiKey")) geminiKey = j.getString("geminiKey")
        if (j.has("geminiModel")) geminiModel = j.getString("geminiModel").ifBlank { "gemini-2.5-flash" }
        if (j.has("ollamaUrl")) ollamaUrl = j.getString("ollamaUrl")
        if (j.has("ollamaModel")) ollamaModel = j.getString("ollamaModel")
        if (j.has("wakeWord")) wakeWord = j.getBoolean("wakeWord")
        if (j.has("muteBeep")) muteBeep = j.getBoolean("muteBeep")
        if (j.has("voice")) voice = j.getString("voice")
        if (j.has("pitch")) pitch = j.getDouble("pitch").toFloat()
        if (j.has("rate")) rate = j.getDouble("rate").toFloat()
    }

    // ── notes ──
    private val notesFile get() = File(ctx.filesDir, "notes.json")
    private val tasksFile get() = File(ctx.filesDir, "tasks.json")

    private fun readArr(f: File): JSONArray = try {
        if (f.exists()) JSONArray(f.readText()) else JSONArray()
    } catch (e: Exception) { JSONArray() }

    fun addNote(text: String) {
        val a = readArr(notesFile)
        val stamp = SimpleDateFormat("dd MMM, hh:mm a", Locale.ENGLISH).format(Date())
        a.put(JSONObject().put("text", text).put("at", stamp))
        notesFile.writeText(a.toString())
    }

    fun recentNotes(n: Int): List<String> {
        val a = readArr(notesFile)
        return (maxOf(0, a.length() - n) until a.length()).map { a.getJSONObject(it).getString("text") }
    }

    // ── tasks / reminders ──
    fun tasks(): JSONArray = readArr(tasksFile)
    fun saveTasks(a: JSONArray) = tasksFile.writeText(a.toString())

    fun addTask(text: String, dueMs: Long?): Int {
        val a = tasks()
        val id = (System.currentTimeMillis() % 1_000_000_000L).toInt()
        val o = JSONObject().put("id", id).put("task", text).put("done", false)
        if (dueMs != null) o.put("due", dueMs)
        a.put(o)
        saveTasks(a)
        if (dueMs != null) schedule(ctx, id, text, dueMs)
        return id
    }

    fun pendingTasks(): List<JSONObject> {
        val a = tasks()
        return (0 until a.length()).map { a.getJSONObject(it) }.filter { !it.optBoolean("done") }
    }

    fun markDone(id: Int) {
        val a = tasks()
        for (i in 0 until a.length()) if (a.getJSONObject(i).optInt("id") == id) a.getJSONObject(i).put("done", true)
        saveTasks(a)
    }

    companion object {
        const val CHANNEL = "mikasa_reminders"

        fun schedule(ctx: Context, id: Int, text: String, dueMs: Long) {
            val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val i = Intent(ctx, ReminderReceiver::class.java).putExtra("id", id).putExtra("task", text)
            val pi = PendingIntent.getBroadcast(ctx, id, i, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            try {
                if (Build.VERSION.SDK_INT >= 31 && !am.canScheduleExactAlarms()) {
                    am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, dueMs, pi)
                } else {
                    am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, dueMs, pi)
                }
            } catch (e: SecurityException) {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, dueMs, pi)
            }
        }

        fun ensureChannel(ctx: Context) {
            val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(CHANNEL, "Mikasa reminders", NotificationManager.IMPORTANCE_HIGH)
                        .apply { description = "Mikasa ke reminders"; enableVibration(true) }
                )
            }
        }
    }
}

/** Reminder ka time aaya: notification + (app khuli ho to) Mikasa bolegi. */
class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        val task = intent.getStringExtra("task") ?: return
        val id = intent.getIntExtra("id", 0)
        Store.ensureChannel(ctx)
        val open = PendingIntent.getActivity(
            ctx, id, Intent(ctx, MainActivity::class.java).putExtra("reminder", task)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val n = android.app.Notification.Builder(ctx, Store.CHANNEL)
            .setSmallIcon(android.R.drawable.ic_popup_reminder)
            .setContentTitle("Mikasa: yaad dila rahi hoon ⏰")
            .setContentText(task)
            .setStyle(android.app.Notification.BigTextStyle().bigText(task))
            .setAutoCancel(true)
            .setContentIntent(open)
            .build()
        try {
            (ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(id, n)
        } catch (e: SecurityException) { /* notification permission nahi */ }
        MainActivity.instance?.onReminder(task)
    }
}

/** Phone restart ke baad pending reminders dobara lagao. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val now = System.currentTimeMillis()
        for (t in Store(ctx).pendingTasks()) {
            val due = t.optLong("due", 0L)
            if (due > now) Store.schedule(ctx, t.optInt("id"), t.optString("task"), due)
        }
    }
}
