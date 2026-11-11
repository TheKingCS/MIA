package com.mia.phone

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.net.Uri
import android.os.PowerManager
import android.util.Log
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject

/**
 * Music from MIA's library, played on the phone, so it comes out wherever the
 * phone's sound goes, the glasses included. The glasses choose what plays
 * (Relay.kt); only library tracks can play, by id, from this phone's engine.
 * While she listens the music pauses, and it comes back when she's done.
 */
object Music {
    private const val TAG = "MIAMusic"
    val TRACK = Regex("[A-Za-z0-9_-]{1,64}")
    const val MAX_QUEUE = 200

    private var appContext: Context? = null
    private var player: MediaPlayer? = null
    private var queue: List<String> = emptyList()
    private var at = 0
    private var preparing = false
    private var heldForVoice = false
    private var focus: AudioFocusRequest? = null

    @Synchronized
    fun play(context: Context, ids: List<String>, start: Int) {
        appContext = context.applicationContext
        queue = ids.take(MAX_QUEUE)
        at = start.coerceIn(0, (queue.size - 1).coerceAtLeast(0))
        heldForVoice = false
        startTrack()
    }

    @Synchronized
    fun control(what: String) {
        val now = player
        when (what) {
            "pause" -> if (now != null && !preparing && now.isPlaying) now.pause()
            "resume" -> if (now != null && !preparing) { takeFocus(); now.start() }
            "next" -> step(1)
            "previous" -> step(-1)
            "stop" -> stop()
        }
    }

    @Synchronized
    fun now(): String {
        val out = JSONObject().put("track", queue.getOrNull(at) ?: "").put("number", at + 1).put("total", queue.size)
        val current = player
        val ready = current != null && !preparing
        out.put("playing", preparing || (ready && current!!.isPlaying))
        out.put("seconds", if (ready) current!!.currentPosition / 1000 else 0)
        out.put("length", if (ready) current!!.duration / 1000 else 0)
        return out.toString()
    }

    /** She's listening: the microphone needs the headset's call audio. */
    @Synchronized
    fun holdForVoice() {
        val current = player ?: return
        if (!preparing && current.isPlaying) {
            current.pause()
            heldForVoice = true
        }
    }

    @Synchronized
    fun voiceDone() {
        if (heldForVoice) player?.start()
        heldForVoice = false
    }

    private fun step(by: Int) {
        val next = at + by
        if (next < 0 || next >= queue.size) { stop(); return }
        at = next
        startTrack()
    }

    private fun stop() {
        release()
        queue = emptyList()
        at = 0
        val request = focus ?: return
        (appContext?.getSystemService(Context.AUDIO_SERVICE) as? AudioManager)?.abandonAudioFocusRequest(request)
        focus = null
    }

    private fun release() {
        player?.release()
        player = null
        preparing = false
    }

    private fun takeFocus() {
        if (focus != null) return
        val manager = appContext?.getSystemService(Context.AUDIO_SERVICE) as? AudioManager ?: return
        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
            .setAudioAttributes(attributes())
            .setOnAudioFocusChangeListener { change -> if (change < 0) control("pause") }
            .build()
        manager.requestAudioFocus(request)
        focus = request
    }

    private fun attributes() = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build()

    private fun startTrack() {
        release()
        val context = appContext ?: return
        val id = queue.getOrNull(at) ?: return
        takeFocus()
        val token = Engine.ensure(context).optString("token")
        val uri = Uri.parse("http://127.0.0.1:${MainActivity.PORT}/api/music/track/$id/audio")
        val next = MediaPlayer()
        try {
            next.setAudioAttributes(attributes())
            next.setWakeMode(context, PowerManager.PARTIAL_WAKE_LOCK)
            next.setDataSource(context, uri, mapOf("Authorization" to "Bearer $token"))
            next.setOnPreparedListener { ready -> synchronized(this) { if (ready === player) { preparing = false; ready.start() } } }
            next.setOnCompletionListener { done -> synchronized(this) { if (done === player) step(1) } }
            next.setOnErrorListener { failed, _, _ ->
                Log.w(TAG, "A track couldn't play")
                synchronized(this) { if (failed === player) step(1) }
                true
            }
            player = next
            preparing = true
            next.prepareAsync()
        } catch (e: Exception) {
            Log.w(TAG, "A track couldn't start")
            next.release()
            player = null
            preparing = false
        }
    }
}

/**
 * The pages' way to this phone's player (web/player.js, as MIAPhoneMusic): a
 * song picked on the Music page is played here, not by the page, so it keeps
 * playing from page to page and with the screen off. Library tracks only, by
 * id; each call answers with what's playing now.
 */
class MusicBridge(private val context: Context) {
    /** Play these tracks (a JSON list of ids), starting at this one. "" when it isn't a list of track ids. */
    @JavascriptInterface
    fun play(idsJson: String, at: Int): String = try {
        val list = JSONArray(idsJson)
        val ids = (0 until minOf(list.length(), Music.MAX_QUEUE)).map { list.optString(it) }
        if (ids.isEmpty() || !ids.all { Music.TRACK.matches(it) }) "" else {
            Music.play(context, ids, at)
            Music.now()
        }
    } catch (e: Exception) {
        ""
    }

    /** pause, resume, next, previous or stop; any other word changes nothing. */
    @JavascriptInterface
    fun control(what: String): String {
        Music.control(what)
        return Music.now()
    }

    @JavascriptInterface
    fun now(): String = Music.now()
}
