package com.mia.companion

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.ToneGenerator
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.view.KeyEvent
import java.io.IOException
import java.util.concurrent.LinkedBlockingQueue

/**
 * Hands-free MIA with the screen locked: a foreground service of type
 * "microphone", the only kind Android allows to keep listening in the
 * background, shown as a persistent notification with Pause and Stop.
 *
 * One worker thread runs a half-duplex loop, so MIA never hears herself:
 *   listen (SpeechDetector) -> short beep -> send the WAV home ->
 *   play the spoken reply -> listen again.
 *
 * A headset or Bluetooth play/pause button pauses and resumes listening
 * (a MediaSession receives it even with the screen off). A partial wake
 * lock keeps the CPU awake while listening; the screen can sleep.
 *
 * If MIA at home restarted, the session token is gone (HTTP 401): the
 * service signs in again with the saved password and retries once.
 */
class VoiceService : Service() {

    enum class State(val label: String) {
        STOPPED("Stopped"),
        LISTENING("Listening"),
        HEARING("Hearing you…"),
        THINKING("Thinking…"),
        SPEAKING("Speaking"),
        PAUSED("Paused"),
        OFFLINE("Can't reach MIA at home"),
        PROBLEM("MIA had a problem"),
    }

    data class Snapshot(val state: State, val detail: String, val log: List<String>)

    companion object {
        const val ACTION_START = "com.mia.companion.START"
        const val ACTION_STOP = "com.mia.companion.STOP"
        const val ACTION_TOGGLE_PAUSE = "com.mia.companion.TOGGLE_PAUSE"
        const val ACTION_SAY_TEXT = "com.mia.companion.SAY_TEXT"
        const val EXTRA_TEXT = "text"

        private const val CHANNEL_ID = "mia_voice"
        private const val NOTIFICATION_ID = 1
        private const val BLOCK_SAMPLES = TARGET_RATE / 10 // 100 ms
        private const val MAX_LOG = 40

        private val mainHandler = Handler(Looper.getMainLooper())

        @Volatile
        var snapshot = Snapshot(State.STOPPED, "", emptyList())
            private set

        /** The screen showing status; called on the main thread. */
        var listener: ((Snapshot) -> Unit)? = null
            set(value) {
                field = value
                value?.invoke(snapshot)
            }

        fun intent(context: Context, action: String): Intent = Intent(context, VoiceService::class.java).setAction(action)
    }

    private lateinit var store: CredentialStore
    private lateinit var audioManager: AudioManager
    private var worker: Thread? = null
    private var mediaSession: MediaSession? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private val typedTexts = LinkedBlockingQueue<String>()
    private val log = ArrayDeque<String>()

    @Volatile private var running = false
    @Volatile private var paused = false
    private var usingBluetooth = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        store = CredentialStore(this)
        audioManager = getSystemService(AudioManager::class.java)
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // NOT_STICKY on purpose: a system restart of this service would open
        // the microphone from the background, which Android 14 forbids for
        // a microphone service (it would crash). You start it from the app.
        if (intent == null) {
            if (!running) stopSelf()
            return START_NOT_STICKY
        }
        when (intent.action) {
            ACTION_STOP -> {
                stopEverything()
                return START_NOT_STICKY
            }
            ACTION_TOGGLE_PAUSE -> if (running) setPaused(!paused)
            ACTION_SAY_TEXT -> {
                intent.getStringExtra(EXTRA_TEXT)?.takeIf { it.isNotBlank() }?.let { typedTexts.put(it) }
                if (!running) start(startPaused = true)
            }
            else -> if (!running) start(startPaused = false) else if (paused) setPaused(false)
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        stopEverything()
        super.onDestroy()
    }

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    private fun start(startPaused: Boolean) {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            publish(State.STOPPED, "Microphone permission is needed.")
            stopSelf()
            return
        }
        paused = startPaused
        val notification = buildNotification(if (paused) State.PAUSED else State.LISTENING, "")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
        wakeLock = getSystemService(PowerManager::class.java)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MIA::voice")
            .apply { acquire() }
        startMediaSession()
        running = true
        worker = Thread(::runLoop, "mia-voice").apply { start() }
        publish(if (paused) State.PAUSED else State.LISTENING, "")
    }

    private fun stopEverything() {
        running = false
        worker?.interrupt()
        worker = null
        mediaSession?.release()
        mediaSession = null
        wakeLock?.takeIf { it.isHeld }?.release()
        wakeLock = null
        routeBluetooth(false)
        publish(State.STOPPED, "")
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun setPaused(value: Boolean) {
        paused = value
        publish(if (paused) State.PAUSED else State.LISTENING, "")
    }

    // ------------------------------------------------------------------
    // The loop (worker thread)
    // ------------------------------------------------------------------

    private fun runLoop() {
        val detector = SpeechDetector()
        var recorder: AudioRecord? = null
        val block = ShortArray(BLOCK_SAMPLES)
        try {
            while (running) {
                typedTexts.poll()?.let { text ->
                    recorder?.release(); recorder = null
                    handleTurn { client, token -> client.textTurn(token, text) }
                    detector.reset()
                }
                if (paused) {
                    recorder?.release(); recorder = null
                    routeBluetooth(false)
                    Thread.sleep(150)
                    continue
                }
                if (recorder == null) {
                    routeBluetooth(store.useBluetoothMic)
                    recorder = openRecorder() ?: run {
                        publish(State.PAUSED, "The microphone is busy (a call?). Tap Resume to try again.")
                        paused = true
                        null
                    }
                    detector.reset()
                    continue
                }
                val read = recorder!!.read(block, 0, block.size)
                if (read <= 0) continue
                when (detector.feed(if (read == block.size) block.copyOf() else block.copyOf(read))) {
                    DetectorState.IDLE -> if (snapshot.state == State.HEARING) publish(State.LISTENING, "")
                    DetectorState.SPEECH -> if (snapshot.state != State.HEARING) publish(State.HEARING, "")
                    DetectorState.DONE -> {
                        val wav = encodeWav(detector.takeUtterance())
                        recorder?.release(); recorder = null
                        beep(ToneGenerator.TONE_PROP_BEEP)
                        handleTurn { client, token -> client.voiceTurn(token, wav) }
                    }
                }
            }
        } catch (e: InterruptedException) {
            // stopping
        } finally {
            recorder?.release()
        }
    }

    private fun openRecorder(): AudioRecord? {
        val minBuffer = AudioRecord.getMinBufferSize(TARGET_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val source = if (usingBluetooth) MediaRecorder.AudioSource.VOICE_COMMUNICATION else MediaRecorder.AudioSource.VOICE_RECOGNITION
        return try {
            val recorder = AudioRecord(source, TARGET_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minBuffer, BLOCK_SAMPLES * 4))
            if (recorder.state != AudioRecord.STATE_INITIALIZED) {
                recorder.release()
                return null
            }
            recorder.startRecording()
            recorder
        } catch (e: SecurityException) {
            null
        }
    }

    /** Send one turn home, signing in again once if MIA restarted, then speak the reply. */
    private fun handleTurn(send: (MiaClient, String) -> MiaClient.TurnResult) {
        publish(State.THINKING, "")
        val client = MiaClient(store.serverUrl)
        val result = try {
            val token = store.token ?: signIn(client)
            try {
                send(client, token)
            } catch (e: MiaClient.HttpError) {
                if (e.code != 401) throw e
                send(client, signIn(client))
            }
        } catch (e: IOException) {
            beep(ToneGenerator.TONE_PROP_NACK)
            // An HTTP error means home answered (e.g. speech-to-text missing);
            // anything else means the phone couldn't reach home at all.
            publish(if (e is MiaClient.HttpError) State.PROBLEM else State.OFFLINE, e.message ?: "Network error")
            Thread.sleep(3_000)
            publish(if (paused) State.PAUSED else State.LISTENING, "")
            return
        }
        if (result.transcript.isNotBlank()) addLog("You: ${result.transcript}")
        if (result.replyText.isNotBlank()) addLog("MIA: ${result.replyText}")
        if (result.timings.isNotBlank()) addLog("   (${result.timings})")
        result.audioWav?.let { wav ->
            publish(State.SPEAKING, "")
            play(wav)
        }
        // "Goodbye" pauses rather than stops, so the headset button can resume.
        if (isGoodbye(result.transcript)) paused = true
        publish(if (paused) State.PAUSED else State.LISTENING, "")
    }

    private fun signIn(client: MiaClient): String {
        val password = store.password() ?: throw IOException("Sign in again in the MIA app.")
        val token = client.login(store.name, password).token
        store.token = token
        return token
    }

    // ------------------------------------------------------------------
    // Audio out
    // ------------------------------------------------------------------

    private fun play(wav: ByteArray) {
        val audio = parseWav(wav) ?: return
        if (audio.bitsPerSample != 16 || audio.channels !in 1..2) return
        val attributes = AudioAttributes.Builder()
            .setUsage(if (usingBluetooth) AudioAttributes.USAGE_VOICE_COMMUNICATION else AudioAttributes.USAGE_ASSISTANT)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()
        val focus = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
            .setAudioAttributes(attributes)
            .build()
        audioManager.requestAudioFocus(focus)
        val channelMask = if (audio.channels == 2) AudioFormat.CHANNEL_OUT_STEREO else AudioFormat.CHANNEL_OUT_MONO
        val format = AudioFormat.Builder()
            .setSampleRate(audio.sampleRate)
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setChannelMask(channelMask)
            .build()
        val minBuffer = AudioTrack.getMinBufferSize(audio.sampleRate, channelMask, AudioFormat.ENCODING_PCM_16BIT)
        val track = AudioTrack.Builder()
            .setAudioAttributes(attributes)
            .setAudioFormat(format)
            .setBufferSizeInBytes(maxOf(minBuffer, 8192))
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()
        try {
            track.play()
            var offset = 0
            while (offset < audio.data.size && running) {
                val written = track.write(audio.data, offset, minOf(8192, audio.data.size - offset))
                if (written <= 0) break
                offset += written
            }
            // Let the buffer drain before the mic opens again.
            val totalFrames = audio.data.size / (2 * audio.channels)
            val deadline = System.currentTimeMillis() + 2_000 + totalFrames * 1000L / audio.sampleRate
            track.stop()
            while (running && track.playbackHeadPosition < totalFrames && System.currentTimeMillis() < deadline) {
                Thread.sleep(50)
            }
        } finally {
            track.release()
            audioManager.abandonAudioFocusRequest(focus)
        }
    }

    private fun beep(tone: Int) {
        try {
            val generator = ToneGenerator(AudioManager.STREAM_MUSIC, 60)
            generator.startTone(tone, 150)
            Thread.sleep(180)
            generator.release()
        } catch (e: RuntimeException) {
            // no tone on this device; not worth failing a turn over
        }
    }

    /** Take (or give back) the mic of a connected Bluetooth headset. */
    @Suppress("DEPRECATION")
    private fun routeBluetooth(wanted: Boolean) {
        if (wanted == usingBluetooth) return
        if (wanted) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val headset = audioManager.availableCommunicationDevices.firstOrNull { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                    ?: return
                audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
                usingBluetooth = audioManager.setCommunicationDevice(headset)
            } else {
                audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
                audioManager.startBluetoothSco()
                audioManager.isBluetoothScoOn = true
                usingBluetooth = true
            }
        } else {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                audioManager.clearCommunicationDevice()
            } else {
                audioManager.isBluetoothScoOn = false
                audioManager.stopBluetoothSco()
            }
            audioManager.mode = AudioManager.MODE_NORMAL
            usingBluetooth = false
        }
    }

    // ------------------------------------------------------------------
    // Headset button
    // ------------------------------------------------------------------

    private fun startMediaSession() {
        val session = MediaSession(this, "MIA")
        session.setCallback(object : MediaSession.Callback() {
            override fun onMediaButtonEvent(mediaButtonIntent: Intent): Boolean {
                val event = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT, KeyEvent::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT)
                }
                if (event?.action == KeyEvent.ACTION_UP && event.keyCode in HEADSET_KEYS) {
                    setPaused(!paused)
                    return true
                }
                return super.onMediaButtonEvent(mediaButtonIntent)
            }
        })
        session.setPlaybackState(
            PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE)
                .setState(PlaybackState.STATE_PLAYING, 0, 1f)
                .build(),
        )
        session.isActive = true
        mediaSession = session
    }

    private val HEADSET_KEYS = setOf(
        KeyEvent.KEYCODE_HEADSETHOOK,
        KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE,
        KeyEvent.KEYCODE_MEDIA_PLAY,
        KeyEvent.KEYCODE_MEDIA_PAUSE,
    )

    // ------------------------------------------------------------------
    // Status: notification + the app screen
    // ------------------------------------------------------------------

    private fun addLog(line: String) {
        synchronized(log) {
            log.addLast(line)
            while (log.size > MAX_LOG) log.removeFirst()
        }
    }

    private fun publish(state: State, detail: String) {
        val lines = synchronized(log) { log.toList() }
        snapshot = Snapshot(state, detail, lines)
        if (running || state == State.STOPPED) {
            if (state != State.STOPPED) {
                getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification(state, detail))
            }
        }
        val current = snapshot
        mainHandler.post { listener?.invoke(current) }
    }

    private fun createChannel() {
        val channel = NotificationChannel(CHANNEL_ID, "MIA listening", NotificationManager.IMPORTANCE_LOW)
        channel.description = "Shown while MIA is listening hands-free."
        channel.setShowBadge(false)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun buildNotification(state: State, detail: String): Notification {
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), flags)
        val toggle = PendingIntent.getService(this, 1, intent(this, ACTION_TOGGLE_PAUSE), flags)
        val stop = PendingIntent.getService(this, 2, intent(this, ACTION_STOP), flags)
        val toggleLabel = if (state == State.PAUSED) "Resume" else "Pause"
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("MIA · ${state.label}")
            .setContentText(detail.ifBlank { snapshot.log.lastOrNull() ?: "Say something, or press your headset button to pause." })
            .setContentIntent(open)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .addAction(Notification.Action.Builder(null, toggleLabel, toggle).build())
            .addAction(Notification.Action.Builder(null, "Stop", stop).build())
            .build()
    }
}
