package com.mia.phone

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.webkit.JavascriptInterface
import org.json.JSONObject

/**
 * User Sync's phone step (core/user_sync.py, docs/GLASSES_FIRST_BOOT_PLAN.md):
 * window.MIAPhonePermissions. Only the phone can ask Android, so `status()`
 * says what's allowed, the screen sends that to the engine, and the glasses
 * show it. Only what MIA already uses; each is also asked again where it's
 * needed, so saying no here costs nothing.
 */
class Permissions(private val activity: MainActivity) {
    private fun has(permission: String) = activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED

    private fun wanted(id: String): Array<String> = when (id) {
        "microphone" -> arrayOf(Manifest.permission.RECORD_AUDIO)
        "notifications" -> if (Build.VERSION.SDK_INT >= 33) arrayOf(Manifest.permission.POST_NOTIFICATIONS) else emptyArray()
        "location" -> arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        "photos" -> if (Build.VERSION.SDK_INT >= 33) arrayOf(Manifest.permission.READ_MEDIA_IMAGES)
                    else arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
        "glasses" -> if (Build.VERSION.SDK_INT >= 31) arrayOf(Manifest.permission.BLUETOOTH_CONNECT) else emptyArray()
        else -> emptyArray()
    }

    @JavascriptInterface
    fun status(): String = JSONObject().apply {
        for (id in IDS) put(id, wanted(id).any { has(it) } || wanted(id).isEmpty())
    }.toString()

    @JavascriptInterface
    fun ask(id: String) {
        val asking = wanted(id).filterNot { has(it) }.toTypedArray()
        if (asking.isEmpty()) answered()
        else activity.runOnUiThread { activity.requestPermissions(asking, ASK_REQUEST) }
    }

    fun answered() {
        activity.runOnUiThread {
            activity.webView()?.evaluateJavascript("window.MIAPermissions && MIAPermissions.changed()", null)
        }
    }

    companion object {
        const val ASK_REQUEST = 46
        private val IDS = listOf("microphone", "notifications", "location", "photos", "glasses")
    }
}
