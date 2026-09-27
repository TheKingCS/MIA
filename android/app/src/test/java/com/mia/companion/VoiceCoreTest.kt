package com.mia.companion

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.sin

class VoiceCoreTest {
    private val block = TARGET_RATE / 10 // 100 ms

    private fun silence() = ShortArray(block) { ((it % 7) - 3).toShort() } // faint noise
    private fun speech(amplitude: Int = 8000) =
        ShortArray(block) { (amplitude * sin(2 * PI * 220 * it / TARGET_RATE)).toInt().toShort() }

    @Test
    fun detectsAnUtteranceAfterTrailingSilence() {
        val detector = SpeechDetector()
        repeat(10) { assertEquals(DetectorState.IDLE, detector.feed(silence())) }
        assertEquals(DetectorState.SPEECH, detector.feed(speech()))
        repeat(9) { assertEquals(DetectorState.SPEECH, detector.feed(speech())) }
        var state = DetectorState.SPEECH
        var silentBlocks = 0
        while (state == DetectorState.SPEECH) {
            state = detector.feed(silence())
            silentBlocks++
        }
        assertEquals(DetectorState.DONE, state)
        assertEquals(12, silentBlocks) // 1200 ms of silence ends it
        val utterance = detector.takeUtterance()
        // 400 ms of pre-roll (which ends with the block where speech began),
        // the other 9 speech blocks, and the 1.2 s of trailing silence.
        assertEquals((4 + 9 + 12) * block, utterance.size)
    }

    @Test
    fun aShortNoiseIsNotSpeech() {
        val detector = SpeechDetector()
        repeat(5) { detector.feed(silence()) }
        assertEquals(DetectorState.SPEECH, detector.feed(speech())) // 100 ms: a cough
        var state = DetectorState.SPEECH
        repeat(12) { state = detector.feed(silence()) }
        assertEquals(DetectorState.IDLE, state)
    }

    @Test
    fun hardMaximumEndsALongUtterance() {
        val detector = SpeechDetector(maxUtteranceMs = 1000.0)
        detector.feed(speech())
        var state = DetectorState.SPEECH
        var blocks = 1
        while (state == DetectorState.SPEECH) {
            state = detector.feed(speech())
            blocks++
        }
        assertEquals(DetectorState.DONE, state)
        assertEquals(10, blocks)
    }

    @Test
    fun wavRoundTrips() {
        val samples = shortArrayOf(0, 1, -1, Short.MAX_VALUE, Short.MIN_VALUE, 1234)
        val wav = encodeWav(samples)
        assertEquals(44 + samples.size * 2, wav.size)
        assertEquals("RIFF", String(wav, 0, 4))
        val parsed = parseWav(wav)
        assertNotNull(parsed)
        assertEquals(TARGET_RATE, parsed!!.sampleRate)
        assertEquals(1, parsed.channels)
        assertEquals(16, parsed.bitsPerSample)
        val decoded = ShortArray(samples.size) { i ->
            ((parsed.data[i * 2].toInt() and 0xFF) or (parsed.data[i * 2 + 1].toInt() shl 8)).toShort()
        }
        assertArrayEquals(samples, decoded)
    }

    @Test
    fun parseWavSkipsExtraChunks() {
        val plain = encodeWav(shortArrayOf(5, 6, 7))
        // Insert a LIST chunk (odd size, padded) between fmt and data.
        val list = "LIST".toByteArray() + byteArrayOf(3, 0, 0, 0, 1, 2, 3, 0)
        val withList = plain.copyOfRange(0, 36) + list + plain.copyOfRange(36, plain.size)
        val parsed = parseWav(withList)
        assertNotNull(parsed)
        assertEquals(6, parsed!!.data.size)
    }

    @Test
    fun parseWavRejectsJunk() {
        assertNull(parseWav(ByteArray(0)))
        assertNull(parseWav("not a wav file at all".toByteArray()))
    }

    @Test
    fun rmsIsScaledLikeTheWebApp() {
        assertEquals(0.0, rms(ShortArray(0)), 0.0)
        assertTrue(rms(ShortArray(100) { 16384 }) in 0.49..0.51)
    }

    @Test
    fun goodbyePhrasesMatchTheWebApp() {
        for (text in listOf("Goodbye", "ok bye MIA", "stop listening", "that's all", "thats all for now", "End conversation")) {
            assertTrue(text, isGoodbye(text))
        }
        for (text in listOf("", "we said our goodbyes to the old truck", "all of that", "keep listening")) {
            assertTrue(text, !isGoodbye(text))
        }
    }
}
