package com.mia.phone

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import android.os.PowerManager
import android.util.Log

/**
 * Keeps MIA awake while the glasses are connected (MetaGlasses.kt). The
 * glasses only ever talk to the phone, so a phone that froze MIA's engine
 * would leave them on a screen that can't answer. Ends with the session.
 */
class GlassesService : Service() {
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, "MIA on your glasses", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val notice = Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("MIA")
            .setContentText("On your glasses")
            .setContentIntent(open)
            .setOngoing(true)
            .build()
        startForeground(NOTICE, notice, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE)
        wakeLock = getSystemService(PowerManager::class.java)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "mia:glasses").apply { acquire(MAX_AWAKE_MS) }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_NOT_STICKY

    override fun onDestroy() {
        wakeLock?.let { if (it.isHeld) it.release() }
        super.onDestroy()
    }

    companion object {
        private const val TAG = "GlassesService"
        private const val CHANNEL = "mia_glasses"
        private const val NOTICE = 7302
        private const val MAX_AWAKE_MS = 4 * 60 * 60 * 1000L

        fun begin(context: Context) {
            try {
                context.startForegroundService(Intent(context, GlassesService::class.java))
            } catch (e: Exception) {  // Android refuses it from the background: she still works, just less surely
                Log.w(TAG, "Couldn't stay awake for the glasses", e)
            }
        }

        fun end(context: Context) {
            context.stopService(Intent(context, GlassesService::class.java))
        }
    }
}
