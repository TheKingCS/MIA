package com.mia.phone

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.util.Log
import android.view.KeyEvent

/**
 * MIA ready to listen with the app closed and the phone locked (slice 0 of
 * docs/GLASSES_FIRST_BOOT_PLAN.md; Zac 2026-10-29: "the glasses shouldn't
 * need the phone to be open").
 *
 * The first time you talk to MIA (the tile, the shortcut, a screen's mic
 * button) the app is on screen, so Android lets it start this microphone
 * service. From then on it stays, with a quiet "MIA · Ready" notification,
 * until you press Stop. A tap on the glasses (or any headset's button)
 * reaches it through a media session even with the screen off, and MIA
 * listens once (Voice.kt). If Android closed MIA's engine meanwhile, the
 * service starts it again first (Engine.kt).
 *
 * Same pattern as the companion app's VoiceService (android/), which has
 * run hands-free on Zac's phone: NOT_STICKY on purpose, because a system
 * restart of a microphone service from the background crashes on Android 14;
 * you start it from the app. While it runs, the headset's play/pause button
 * talks to MIA instead of the music player.
 */
class ListenService : Service() {
    private val main = Handler(Looper.getMainLooper())
    private var voice: Voice? = null
    private var mediaSession: MediaSession? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var state = "ready"

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
        voice = Voice(this) { s -> state = s; notifyState() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) {  // the system restarting it: never open the mic from the background
            if (!running) stopSelf()
            return START_NOT_STICKY
        }
        if (intent.action == ACTION_STOP) {
            stopEverything()
            return START_NOT_STICKY
        }
        if (!running && !goForeground()) return START_NOT_STICKY
        if (intent.action == Voice.ACTION_LISTEN) listenNow()
        return START_NOT_STICKY
    }

    private fun goForeground(): Boolean {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, buildNotification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            } else {
                startForeground(NOTIFICATION_ID, buildNotification())
            }
        } catch (e: RuntimeException) {  // Android said no (started from the background)
            Log.w(MainActivity.TAG, "listen service couldn't start", e)
            stopSelf()
            return false
        }
        startMediaSession()
        running = true
        return true
    }

    /** One turn: make sure MIA is up, then listen. */
    private fun listenNow() {
        wakeLock?.takeIf { it.isHeld }?.release()
        wakeLock = getSystemService(PowerManager::class.java)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MIA::listen")
            .apply { acquire(TURN_MS) }  // listening + her answer; released by the timeout
        Thread {
            val token = try {
                Engine.ensure(applicationContext).optString("token")
            } catch (e: Throwable) {
                Log.e(MainActivity.TAG, "engine for listening", e)
                null
            }
            main.post {
                when {
                    token == null -> { state = "MIA couldn't start"; notifyState() }
                    token.isEmpty() -> { state = "Open MIA and sign in first"; notifyState() }
                    else -> voice?.start(token)
                }
            }
        }.start()
    }

    private fun stopEverything() {
        running = false
        voice?.close()
        mediaSession?.release()
        mediaSession = null
        wakeLock?.takeIf { it.isHeld }?.release()
        wakeLock = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        if (running) stopEverything()
        voice?.close()
        super.onDestroy()
    }

    // ------------------------------------------------------------ the glasses' tap / a headset button

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
                    listenNow()
                    return true
                }
                return super.onMediaButtonEvent(mediaButtonIntent)
            }
        })
        // "Playing" so Android sends the headset's buttons here (as the companion app does).
        session.setPlaybackState(
            PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE)
                .setState(PlaybackState.STATE_PLAYING, 0, 1f)
                .build(),
        )
        session.isActive = true
        mediaSession = session
    }

    // ------------------------------------------------------------ the notification

    private fun createChannel() {
        val channel = NotificationChannel(CHANNEL_ID, "MIA ready to listen", NotificationManager.IMPORTANCE_LOW)
        channel.description = "Shown while MIA can hear a tap on your glasses or headset."
        channel.setShowBadge(false)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun notifyState() {
        if (running) getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification())
    }

    private fun buildNotification(): Notification {
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), flags)
        val talk = PendingIntent.getService(this, 1, intent(this, Voice.ACTION_LISTEN), flags)
        val stop = PendingIntent.getService(this, 2, intent(this, ACTION_STOP), flags)
        val title = when (state) {
            "listening" -> "MIA · Listening"
            "thinking" -> "MIA · Thinking"
            "speaking" -> "MIA · Speaking"
            "ready" -> "MIA · Ready"
            else -> "MIA · $state"
        }
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle(title)
            .setContentText("Tap your glasses or headset to talk.")
            .setContentIntent(open)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .addAction(Notification.Action.Builder(null, "Talk", talk).build())
            .addAction(Notification.Action.Builder(null, "Stop", stop).build())
            .build()
    }

    companion object {
        const val ACTION_STOP = "com.mia.phone.LISTEN_STOP"
        private const val CHANNEL_ID = "mia_listen"
        private const val NOTIFICATION_ID = 7
        private const val TURN_MS = 3 * 60 * 1000L
        private val HEADSET_KEYS = setOf(
            KeyEvent.KEYCODE_HEADSETHOOK,
            KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE,
            KeyEvent.KEYCODE_MEDIA_PLAY,
            KeyEvent.KEYCODE_MEDIA_PAUSE,
        )

        @Volatile var running = false
            private set

        fun intent(context: Context, action: String): Intent = Intent(context, ListenService::class.java).setAction(action)

        /** Listen now. Starts the service (only allowed while MIA's screen is showing) or asks the running one. */
        fun listen(context: Context) {
            val ask = intent(context, Voice.ACTION_LISTEN)
            if (running) context.startService(ask) else context.startForegroundService(ask)
        }
    }
}
