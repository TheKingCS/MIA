package com.mia.phone

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.widget.Toast
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Talking to MIA through the glasses (core/glasses_voice.py). The Display
 * glasses are this phone's Bluetooth headset, so: listen through their
 * microphone with Android's own speech recognizer (on the phone, offline
 * when the phone can), send the words to MIA on this phone
 * (/api/glasses/voice: "open Kitchen" switches the glasses, anything else
 * is a Talk turn; a phone linked to the home computer asks it there), and
 * say her answer through their speakers. Without glasses it's the phone's
 * own mic and speaker.
 *
 * Owned by ListenService, not a screen, so it works with the app closed
 * and the phone locked (slice 0 of docs/GLASSES_FIRST_BOOT_PLAN.md). The
 * microphone permission is asked by MainActivity before the service starts.
 * `onState` reports what she's doing: "listening", "thinking", "speaking", "ready".
 */
class Voice(private val context: Context, private val onState: (String) -> Unit = {}) : RecognitionListener {
    private var recognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var token = ""
    private val main = Handler(Looper.getMainLooper())
    private val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    /** Listen once. Call on the main thread (Android's recognizer needs it). */
    fun start(sessionToken: String) {
        token = sessionToken
        if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            say("MIA needs the microphone. Open MIA once and allow it.")
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            say("This phone has no speech recognizer. Install Google's speech services to talk to MIA.")
            return
        }
        stop()
        tts?.stop()  // a tap while she's talking interrupts her
        useHeadset(true)
        val r = if (Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(context))
            SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
        else SpeechRecognizer.createSpeechRecognizer(context)
        recognizer = r
        r.setRecognitionListener(this)
        val ask = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            .putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        try {
            ToneGenerator(AudioManager.STREAM_MUSIC, 60).startTone(ToneGenerator.TONE_PROP_BEEP, 120)
        } catch (e: RuntimeException) { /* no beep: fine */ }
        r.startListening(ask)
        onState("listening")
    }

    fun stop() {
        recognizer?.destroy()
        recognizer = null
        useHeadset(false)
    }

    // The glasses' microphone: Android's communication device (12+), or Bluetooth SCO before.
    @Suppress("DEPRECATION")
    private fun useHeadset(on: Boolean) {
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                if (on) {
                    val glasses = audio.availableCommunicationDevices.firstOrNull { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                    if (glasses != null) audio.setCommunicationDevice(glasses)
                } else {
                    audio.clearCommunicationDevice()
                }
            } else if (on) {
                audio.startBluetoothSco()
            } else {
                audio.stopBluetoothSco()
            }
        } catch (e: RuntimeException) {
            Log.w(MainActivity.TAG, "headset mic", e)
        }
    }

    override fun onResults(results: Bundle) {
        val heard = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
        stop()
        if (heard.isBlank()) { say("I didn't catch that."); return }
        onState("thinking")
        Thread {
            val answer = try {
                ask(heard)
            } catch (e: Exception) {
                Log.w(MainActivity.TAG, "glasses voice", e)
                "I couldn't reach MIA just now."
            }
            main.post { say(answer) }
        }.start()
    }

    /** The words to MIA on this phone; her answer back. */
    private fun ask(heard: String): String {
        val connection = URL("http://127.0.0.1:${MainActivity.PORT}/api/glasses/voice").openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 5000
        connection.readTimeout = 120000
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json")
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.outputStream.use { it.write(JSONObject().put("text", heard).toString().toByteArray()) }
        val ok = connection.responseCode in 200..299
        val body = (if (ok) connection.inputStream else connection.errorStream)?.bufferedReader()?.use { it.readText() }.orEmpty()
        val json = try { JSONObject(body) } catch (e: Exception) { JSONObject() }
        return if (ok) json.optString("say", "Done.") else json.optString("detail", "MIA couldn't do that.")
    }

    private fun say(text: String) {
        Toast.makeText(context, text, Toast.LENGTH_LONG).show()
        onState("speaking")
        val speaker = tts
        if (speaker != null) {
            speaker.speak(text, TextToSpeech.QUEUE_FLUSH, null, "mia")
            return
        }
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) { main.post { onState("ready") } }
                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) { main.post { onState("ready") } }
                })
                tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "mia")
            } else {
                onState("ready")
            }
        }
    }

    fun close() {
        stop()
        tts?.shutdown()
        tts = null
    }

    override fun onError(error: Int) {
        stop()
        say(if (error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT)
            "I didn't catch that." else "I couldn't listen just now.")
    }

    override fun onReadyForSpeech(params: Bundle?) {}
    override fun onBeginningOfSpeech() {}
    override fun onRmsChanged(rmsdB: Float) {}
    override fun onBufferReceived(buffer: ByteArray?) {}
    override fun onEndOfSpeech() {}
    override fun onPartialResults(partialResults: Bundle?) {}
    override fun onEvent(eventType: Int, params: Bundle?) {}

    companion object {
        const val VOICE_REQUEST = 44
        const val ACTION_LISTEN = "com.mia.phone.LISTEN"

        /** Opened to listen: the tile, the shortcut, a headset's voice button. */
        fun wanted(intent: Intent?): Boolean =
            intent?.action == ACTION_LISTEN || intent?.action == Intent.ACTION_VOICE_COMMAND
    }
}
