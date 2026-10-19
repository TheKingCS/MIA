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
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
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
 * own mic and speaker. Started from the Quick Settings tile (ListenTile),
 * the app shortcut, a headset's voice button, or a screen (MIAAndroid.listen).
 */
class Voice(private val activity: MainActivity) : RecognitionListener {
    private var recognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var token = ""
    private var waitingForPermission = false
    private val audio = activity.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    fun start(sessionToken: String) {
        token = sessionToken
        if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            waitingForPermission = true
            activity.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), VOICE_REQUEST)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(activity)) {
            say("This phone has no speech recognizer. Install Google's speech services to talk to MIA.")
            return
        }
        stop()
        useHeadset(true)
        val r = if (Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(activity))
            SpeechRecognizer.createOnDeviceSpeechRecognizer(activity)
        else SpeechRecognizer.createSpeechRecognizer(activity)
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
        Toast.makeText(activity, "MIA is listening…", Toast.LENGTH_SHORT).show()
    }

    /** Android answered the microphone question. */
    fun permissionAnswered(granted: Boolean) {
        if (!waitingForPermission) return
        waitingForPermission = false
        if (granted) start(token) else say("MIA needs the microphone to hear you.")
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
        Thread {
            val answer = try {
                ask(heard)
            } catch (e: Exception) {
                Log.w(MainActivity.TAG, "glasses voice", e)
                "I couldn't reach MIA just now."
            }
            activity.runOnUiThread { say(answer) }
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
        Toast.makeText(activity, text, Toast.LENGTH_LONG).show()
        val speaker = tts
        if (speaker != null) {
            speaker.speak(text, TextToSpeech.QUEUE_FLUSH, null, "mia")
            return
        }
        tts = TextToSpeech(activity) { status ->
            if (status == TextToSpeech.SUCCESS) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "mia")
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
