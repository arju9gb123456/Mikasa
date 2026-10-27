package com.arjun.mikasa

/** Text helpers: normalize, fuzzy match, Devanagari -> Roman (rough) transliteration. */
object Text {

    private val punct = Regex("[.,!?।॥|\"'“”‘’:;()\\[\\]{}\\-–—/\\\\]")

    fun normalize(s: String): String {
        var t = s.lowercase().replace(punct, " ")
        t = t.replace("़", "").replace("ँ", "ं") // nukta, chandrabindu
        return t.split(Regex("\\s+")).filter { it.isNotBlank() }.joinToString(" ")
    }

    fun tokens(s: String): List<String> = normalize(s).split(" ").filter { it.isNotBlank() }

    fun hasPhrase(t: String, phrases: Collection<String>): Boolean {
        val padded = " $t "
        return phrases.any { padded.contains(" ${normalize(it)} ") }
    }

    fun hasStem(tokens: List<String>, stems: Collection<String>): Boolean =
        tokens.any { tok -> stems.any { st -> tok.startsWith(normalize(st)) } }

    fun levenshtein(a: String, b: String): Int {
        if (a == b) return 0
        if (a.isEmpty()) return b.length
        if (b.isEmpty()) return a.length
        var prev = IntArray(b.length + 1) { it }
        var cur = IntArray(b.length + 1)
        for (i in 1..a.length) {
            cur[0] = i
            for (j in 1..b.length) {
                val cost = if (a[i - 1] == b[j - 1]) 0 else 1
                cur[j] = minOf(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            }
            val tmp = prev; prev = cur; cur = tmp
        }
        return prev[b.length]
    }

    fun similarity(a: String, b: String): Double {
        if (a.isEmpty() || b.isEmpty()) return 0.0
        val d = levenshtein(a, b)
        return 1.0 - d.toDouble() / maxOf(a.length, b.length)
    }

    // ── Devanagari -> Roman (bas matching ke liye, perfect nahi) ──
    private val consonants = mapOf(
        'क' to "k", 'ख' to "kh", 'ग' to "g", 'घ' to "gh", 'ङ' to "n",
        'च' to "ch", 'छ' to "chh", 'ज' to "j", 'झ' to "jh", 'ञ' to "n",
        'ट' to "t", 'ठ' to "th", 'ड' to "d", 'ढ' to "dh", 'ण' to "n",
        'त' to "t", 'थ' to "th", 'द' to "d", 'ध' to "dh", 'न' to "n",
        'प' to "p", 'फ' to "f", 'ब' to "b", 'भ' to "bh", 'म' to "m",
        'य' to "y", 'र' to "r", 'ल' to "l", 'व' to "v", 'श' to "sh",
        'ष' to "sh", 'स' to "s", 'ह' to "h", 'ळ' to "l"
    )
    private val vowels = mapOf(
        'अ' to "a", 'आ' to "a", 'इ' to "i", 'ई' to "i", 'उ' to "u", 'ऊ' to "u",
        'ए' to "e", 'ऐ' to "ai", 'ओ' to "o", 'औ' to "au", 'ऋ' to "ri", 'ऑ' to "o"
    )
    private val matras = mapOf(
        'ा' to "a", 'ि' to "i", 'ी' to "i", 'ु' to "u", 'ू' to "u", 'े' to "e",
        'ै' to "ai", 'ो' to "o", 'ौ' to "au", 'ृ' to "ri", 'ॉ' to "o"
    )

    fun romanize(s: String): String {
        val out = StringBuilder()
        val chars = s.toCharArray()
        var i = 0
        while (i < chars.size) {
            val c = chars[i]
            val cons = consonants[c]
            when {
                cons != null -> {
                    out.append(cons)
                    val next = chars.getOrNull(i + 1)
                    when {
                        next == '्' -> i++ // halant: no vowel
                        next != null && matras.containsKey(next) -> { out.append(matras[next]); i++ }
                        next == null || next == ' ' -> {}
                        else -> out.append("a")
                    }
                }
                vowels.containsKey(c) -> out.append(vowels[c])
                matras.containsKey(c) -> out.append(matras[c])
                c == 'ं' -> out.append("n")
                c == 'ः' -> out.append("h")
                c == '़' || c == '्' -> {}
                else -> out.append(c)
            }
            i++
        }
        // "intagraam" jaise rough output ko halka sa saaf karo
        return out.toString().replace("aa", "a").replace("ee", "i").replace("oo", "u")
    }

    /** Matching ke liye: lowercase roman, sirf letters/digits. */
    fun key(s: String): String =
        romanize(normalize(s)).lowercase().replace(Regex("[^a-z0-9]"), "")
            .replace("w", "v").replace("ph", "f").replace("aa", "a")
}
