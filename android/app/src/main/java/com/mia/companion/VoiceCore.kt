package com.mia.companion

import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Pure voice logic, no Android APIs, so it runs in plain JVM unit tests.
 *
 * A straight port of server/static/voice.js (the phone web app): the same
 * end-of-speech detector and the same 16 kHz mono 16-bit WAV the home
 * computer's offline Vosk model wants. Keeping the numbers identical means
 * the native app and the web app feel the same and the server needs no
 * changes.
 */
const val TARGET_RATE = 16_000

enum class DetectorState { IDLE, SPEECH, DONE }

// Same phrases as the web app (server/static/app.js GOODBYE).
private val GOODBYE = Regex("""\b(goodbye|bye mia|good bye|stop listening|that'?s all|end conversation)\b""", RegexOption.IGNORE_CASE)

/** "Goodbye" / "stop listening" / "that's all": pause after MIA answers. */
fun isGoodbye(transcript: String): Boolean = GOODBYE.containsMatchIn(transcript)

class SpeechDetector(
    private val sampleRate: Int = TARGET_RATE,
    private val minThreshold: Double = 0.012,
    private val noiseMultiplier: Double = 3.0,
    private val silenceMs: Double = 1200.0,
    private val minSpeechMs: Double = 300.0,
    private val maxUtteranceMs: Double = 30_000.0,
    private val preRollMs: Double = 400.0,
) {
    private var noiseFloor: Double? = null
    private var inSpeech = false
    private var speechMs = 0.0
    private var silenceRunMs = 0.0
    private var totalMs = 0.0
    private val preRoll = ArrayDeque<ShortArray>()
    private var preRollMsHeld = 0.0
    private val chunks = mutableListOf<ShortArray>()

    fun reset() {
        noiseFloor = null
        inSpeech = false
        speechMs = 0.0
        silenceRunMs = 0.0
        totalMs = 0.0
        preRoll.clear()
        preRollMsHeld = 0.0
        chunks.clear()
    }

    fun threshold(): Double = max(minThreshold, (noiseFloor ?: 0.0) * noiseMultiplier)

    private fun blockMs(block: ShortArray): Double = block.size * 1000.0 / sampleRate

    /** Feed one block of 16-bit samples; returns what the detector now thinks. */
    fun feed(block: ShortArray): DetectorState {
        val ms = blockMs(block)
        val level = rms(block)
        val loud = level > threshold()

        if (!inSpeech) {
            // Track background noise only while nobody is talking.
            noiseFloor = noiseFloor?.let { it * 0.95 + level * 0.05 } ?: level
            preRoll.addLast(block)
            preRollMsHeld += ms
            while (preRoll.size > 1 && preRollMsHeld - blockMs(preRoll.first()) >= preRollMs) {
                preRollMsHeld -= blockMs(preRoll.removeFirst())
            }
            if (!loud) return DetectorState.IDLE
            inSpeech = true
            chunks.clear()
            chunks.addAll(preRoll)
            totalMs = preRollMsHeld
            preRoll.clear()
            preRollMsHeld = 0.0
            speechMs = ms
            silenceRunMs = 0.0
            return DetectorState.SPEECH
        }

        chunks.add(block)
        totalMs += ms
        if (loud) {
            speechMs += ms
            silenceRunMs = 0.0
        } else {
            silenceRunMs += ms
        }
        if (totalMs >= maxUtteranceMs) return DetectorState.DONE
        if (silenceRunMs >= silenceMs) {
            if (speechMs >= minSpeechMs) return DetectorState.DONE
            // A cough or a door slam, not speech: go back to waiting.
            reset()
            return DetectorState.IDLE
        }
        return DetectorState.SPEECH
    }

    /** The finished utterance, pre-roll included. Resets the detector. */
    fun takeUtterance(): ShortArray {
        val out = ShortArray(chunks.sumOf { it.size })
        var offset = 0
        for (chunk in chunks) {
            chunk.copyInto(out, offset)
            offset += chunk.size
        }
        reset()
        return out
    }
}

/** Root-mean-square level of 16-bit samples, scaled to 0..1 like the web app's Float32 math. */
fun rms(samples: ShortArray): Double {
    if (samples.isEmpty()) return 0.0
    var sum = 0.0
    for (s in samples) {
        val v = s / 32768.0
        sum += v * v
    }
    return sqrt(sum / samples.size)
}

/** Mono 16-bit PCM samples -> WAV file bytes. */
fun encodeWav(samples: ShortArray, sampleRate: Int = TARGET_RATE): ByteArray {
    val dataBytes = samples.size * 2
    val out = ByteArray(44 + dataBytes)
    fun putString(offset: Int, text: String) = text.forEachIndexed { i, c -> out[offset + i] = c.code.toByte() }
    fun putInt(offset: Int, value: Int) {
        for (i in 0 until 4) out[offset + i] = (value shr (8 * i) and 0xFF).toByte()
    }
    fun putShort(offset: Int, value: Int) {
        out[offset] = (value and 0xFF).toByte()
        out[offset + 1] = (value shr 8 and 0xFF).toByte()
    }
    putString(0, "RIFF")
    putInt(4, 36 + dataBytes)
    putString(8, "WAVE")
    putString(12, "fmt ")
    putInt(16, 16)
    putShort(20, 1) // PCM
    putShort(22, 1) // mono
    putInt(24, sampleRate)
    putInt(28, sampleRate * 2)
    putShort(32, 2)
    putShort(34, 16)
    putString(36, "data")
    putInt(40, dataBytes)
    for (i in samples.indices) putShort(44 + i * 2, samples[i].toInt())
    return out
}

/** What a WAV reply needs for playback. */
data class PcmAudio(val sampleRate: Int, val channels: Int, val bitsPerSample: Int, val data: ByteArray)

/**
 * Finds the fmt and data chunks of a PCM WAV (the home computer's Piper
 * voice replies). Walks chunks instead of assuming a 44-byte header,
 * because WAV writers may add LIST/fact chunks. Null if it isn't PCM WAV.
 */
fun parseWav(bytes: ByteArray): PcmAudio? {
    fun int(offset: Int): Int =
        (bytes[offset].toInt() and 0xFF) or
            ((bytes[offset + 1].toInt() and 0xFF) shl 8) or
            ((bytes[offset + 2].toInt() and 0xFF) shl 16) or
            ((bytes[offset + 3].toInt() and 0xFF) shl 24)
    fun short(offset: Int): Int = (bytes[offset].toInt() and 0xFF) or ((bytes[offset + 1].toInt() and 0xFF) shl 8)
    fun tag(offset: Int): String = String(bytes, offset, 4, Charsets.US_ASCII)

    if (bytes.size < 12 || tag(0) != "RIFF" || tag(8) != "WAVE") return null
    var offset = 12
    var rate = 0
    var channels = 0
    var bits = 0
    var sawFormat = false
    while (offset + 8 <= bytes.size) {
        val id = tag(offset)
        val size = int(offset + 4)
        val body = offset + 8
        if (size < 0 || body > bytes.size) return null
        when (id) {
            "fmt " -> {
                if (body + 16 > bytes.size || short(body) != 1) return null // PCM only
                channels = short(body + 2)
                rate = int(body + 4)
                bits = short(body + 14)
                sawFormat = true
            }
            "data" -> {
                if (!sawFormat) return null
                val end = min(bytes.size, body + size)
                return PcmAudio(rate, channels, bits, bytes.copyOfRange(body, end))
            }
        }
        offset = body + size + (size and 1) // chunks are word-aligned
    }
    return null
}
