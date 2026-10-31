package com.mia.phone

import android.content.Context
import android.speech.tts.TextToSpeech
import android.webkit.JavascriptInterface

/**
 * The workout's count, spoken by the phone itself (DEC-0055, Active
 * Training: "MIA counts the pace"). The Workout screen calls
 * `window.MIAPhoneVoice.say("7")` on each beat; speaking it here, not on
 * the computer, keeps the count on time (no round trip), and it comes out
 * wherever the phone's sound goes, the glasses included. Only short lines
 * (a number, "Rest's over"); MIA's answers still go through Voice.
 */
class PhoneVoice(context: Context) {
    @Volatile private var ready = false
    private val tts: TextToSpeech = TextToSpeech(context.applicationContext) { status ->
        ready = status == TextToSpeech.SUCCESS
    }

    @JavascriptInterface
    fun say(text: String) {
        if (ready) tts.speak(text.take(120), TextToSpeech.QUEUE_FLUSH, null, "mia-count")
    }

    fun shutdown() {
        tts.shutdown()
    }
}
