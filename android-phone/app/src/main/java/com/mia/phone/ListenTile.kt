package com.mia.phone

import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import android.service.quicksettings.TileService

/** The Quick Settings tile "Talk to MIA". With MIA ready (ListenService
 *  running) she listens right away, even on the lock screen; otherwise it
 *  opens MIA listening (Voice.kt), which starts the service. */
class ListenTile : TileService() {
    override fun onClick() {
        super.onClick()
        if (ListenService.running) {
            ListenService.listen(this)
            return
        }
        val listen = Intent(this, MainActivity::class.java).setAction(Voice.ACTION_LISTEN)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (Build.VERSION.SDK_INT >= 34) {
            startActivityAndCollapse(PendingIntent.getActivity(this, 0, listen,
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT))
        } else {
            @Suppress("DEPRECATION", "StartActivityAndCollapseDeprecated")
            startActivityAndCollapse(listen)
        }
    }
}
