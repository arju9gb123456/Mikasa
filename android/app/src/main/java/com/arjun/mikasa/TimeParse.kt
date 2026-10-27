package com.arjun.mikasa

import java.util.Calendar

/** "5 baje", "10 minute baad", "kal subah 7 baje", "saadhe 4" -> time (millis). Laptop wali Mikasa jaisa. */
object TimeParse {

    private val devDigits = mapOf('०' to '0', '१' to '1', '२' to '2', '३' to '3', '४' to '4',
        '५' to '5', '६' to '6', '७' to '7', '८' to '8', '९' to '9')
    private val wordNum = linkedMapOf(
        "ek" to 1, "एक" to 1, "do" to 2, "दो" to 2, "teen" to 3, "तीन" to 3, "char" to 4, "chaar" to 4, "चार" to 4,
        "paanch" to 5, "panch" to 5, "पांच" to 5, "chhe" to 6, "छह" to 6, "saat" to 7, "सात" to 7, "aath" to 8,
        "आठ" to 8, "nau" to 9, "नौ" to 9, "das" to 10, "दस" to 10, "gyarah" to 11, "ग्यारह" to 11, "barah" to 12,
        "बारह" to 12, "pandrah" to 15, "पंद्रह" to 15, "bees" to 20, "बीस" to 20, "tees" to 30, "तीस" to 30,
        "पैंतालीस" to 45
    )
    private const val B = "(?<![\\p{L}\\p{M}\\d])"
    private const val E = "(?![\\p{L}\\p{M}\\d])"

    fun prep(text: String): String {
        var t = text.lowercase().map { devDigits[it] ?: it }.joinToString("").replace("़", "")
        for ((w, n) in wordNum) t = t.replace(Regex("$B${Regex.escape(w)}$E"), n.toString())
        return t
    }

    fun parse(text: String, nowMs: Long = System.currentTimeMillis()): Long? {
        val t = prep(text)
        val now = Calendar.getInstance().apply { timeInMillis = nowMs }

        if (Regex("(aadh|aadhe|आध)\\S*\\s*(ghant|घंट)").containsMatchIn(t)) return nowMs + 30 * 60_000L
        Regex("(\\d+)\\s*(minute|minutes|min|mins|मिनट|ghante|ghanta|hour|hours|घंटे|घंटा|second|seconds|sec|सेकंड)")
            .find(t)?.let { m ->
                if (Regex("(baad|बाद|mein|में|later|after)").containsMatchIn(t)) {
                    val n = m.groupValues[1].toLong()
                    val u = m.groupValues[2]
                    return nowMs + when {
                        u.startsWith("min") || u.startsWith("मिनट") -> n * 60_000L
                        u.startsWith("sec") || u.startsWith("सेकंड") -> n * 1000L
                        else -> n * 3_600_000L
                    }
                }
            }

        var day = 0
        if (Regex("(parso|parson|परसों|परसो)").containsMatchIn(t)) day = 2
        else if (Regex("$B(kal|कल|tomorrow)$E").containsMatchIn(t)) day = 1

        var period: String? = null
        when {
            Regex("(subah|सुबह|morning|savere|सवेरे)").containsMatchIn(t) -> period = "am"
            Regex("(dopahar|dopehar|दोपहर|afternoon)").containsMatchIn(t) -> period = "noon"
            Regex("(shaam|sham|शाम|evening)").containsMatchIn(t) -> period = "pm"
            Regex("(raat|रात|night)").containsMatchIn(t) -> period = "night"
        }

        var hour: Int? = null
        var minute = 0
        val hm = Regex("(\\d{1,2})\\s*[:.]\\s*(\\d{2})").find(t)
        if (hm != null) {
            hour = hm.groupValues[1].toInt(); minute = hm.groupValues[2].toInt()
        } else {
            val bm = Regex("(\\d{1,2})\\s*(baje|बजे|baj|बज|o'?clock)").find(t)
            if (bm != null) {
                hour = bm.groupValues[1].toInt()
                val h = hour.toString()
                when {
                    Regex("(sava|सवा)\\s*$h").containsMatchIn(t) -> minute = 15
                    Regex("(saadhe|sadhe|साढ़े|साढे)\\s*$h").containsMatchIn(t) -> minute = 30
                    Regex("(paune|pone|पौने)\\s*$h").containsMatchIn(t) -> { hour -= 1; minute = 45 }
                }
            } else if (day > 0) {
                hour = when (period) { "am" -> 8; "noon" -> 13; "pm" -> 18; "night" -> 21; else -> 9 }
            }
        }
        var hr = hour ?: return null
        if (hr !in 0..23 || minute !in 0..59) return null
        if (hr < 12) {
            if (period == "pm" || period == "noon" || (period == "night" && hr >= 6)) hr += 12
            else if (period == null && hr in 1..7) hr += 12 // "5 baje" = shaam
        }
        val cal = (now.clone() as Calendar).apply {
            add(Calendar.DAY_OF_YEAR, day)
            set(Calendar.HOUR_OF_DAY, hr); set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
        }
        if (cal.timeInMillis <= nowMs) cal.add(Calendar.DAY_OF_YEAR, 1)
        return cal.timeInMillis
    }

    private val timeBits = listOf(
        "(aadh|aadhe|आध)\\S*\\s*(ghant|घंट)\\S*\\s*(baad|बाद)?",
        "\\d+\\s*(minute|minutes|min|mins|मिनट|ghante|ghanta|hour|hours|घंटे|घंटा|second|seconds|sec|सेकंड)\\s*(baad|बाद|mein|में|later)?",
        "(sava|सवा|saadhe|sadhe|साढ़े|साढे|paune|pone|पौने)\\s*(?=\\d)",
        "\\d{1,2}\\s*[:.]\\s*\\d{2}\\s*(baje|बजे|pe|पे|par|पर|ko|को)?",
        "\\d{1,2}\\s*(baje|बजे|baj|बज|o'?clock)\\s*(pe|पे|par|पर|ko|को)?",
        "$B(kal|कल|parso|परसों|tomorrow|aaj|आज)$E",
        "(subah|सुबह|savere|सवेरे|dopahar|दोपहर|shaam|sham|शाम|raat|रात)\\s*(ko|को)?"
    )

    fun stripTime(text: String): String {
        var t = prep(text)
        for (p in timeBits) t = t.replace(Regex(p), " ")
        t = t.replace(Regex("\\s+"), " ").trim(' ', ',', '.', '-')
        return t.ifBlank { text }
    }

    fun spoken(ms: Long, nowMs: Long = System.currentTimeMillis()): String {
        val c = Calendar.getInstance().apply { timeInMillis = ms }
        val n = Calendar.getInstance().apply { timeInMillis = nowMs }
        val h12 = c.get(Calendar.HOUR).let { if (it == 0) 12 else it }
        val mm = String.format("%02d", c.get(Calendar.MINUTE))
        val ampm = if (c.get(Calendar.AM_PM) == Calendar.AM) "AM" else "PM"
        val clock = "$h12:$mm $ampm"
        val mins = (ms - nowMs) / 60_000L
        val sameDay = c.get(Calendar.DAY_OF_YEAR) == n.get(Calendar.DAY_OF_YEAR) && c.get(Calendar.YEAR) == n.get(Calendar.YEAR)
        n.add(Calendar.DAY_OF_YEAR, 1)
        val tomorrow = c.get(Calendar.DAY_OF_YEAR) == n.get(Calendar.DAY_OF_YEAR)
        return when {
            sameDay && mins < 1 -> "थोड़ी देर में"
            sameDay && mins < 60 -> "$mins मिनट बाद"
            sameDay -> "आज $clock पे"
            tomorrow -> "कल $clock पे"
            else -> "${c.get(Calendar.DAY_OF_MONTH)}/${c.get(Calendar.MONTH) + 1} को $clock पे"
        }
    }
}
