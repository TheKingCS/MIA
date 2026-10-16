package com.mia.phone

import android.annotation.SuppressLint
import android.app.Activity
import android.app.ActivityManager
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.view.Gravity
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject

/**
 * MIA on the phone (DEC-0019, the Phase 1 spike): starts MIA's own engine
 * and server inside this app (mia_phone.py) and shows her web screens
 * from it, so no computer is needed. Timings go to logcat as MIA_SPIKE.
 */
class MainActivity : Activity() {
    private var web: WebView? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val status = TextView(this).apply {
            text = "Starting MIA on this phone…"
            textSize = 18f
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }
        setContentView(status)
        Thread {
            try {
                // Once per app process: Android can recreate this screen while MIA
                // is still starting (rotating the phone, the system); the second
                // start waits for the first instead of starting Python twice.
                val result = synchronized(START_LOCK) {
                    started ?: run {
                        val t0 = SystemClock.elapsedRealtime()
                        val root = Unpack.ensure(applicationContext)
                        val t1 = SystemClock.elapsedRealtime()
                        if (!Python.isStarted()) Python.start(AndroidPlatform(applicationContext))
                        val t2 = SystemClock.elapsedRealtime()
                        val answer = JSONObject(Python.getInstance().getModule("mia_phone").callAttr("start", root.absolutePath, PORT, applicationInfo.nativeLibraryDir, lastExit()).toString())
                        val t3 = SystemClock.elapsedRealtime()
                        Log.i(TAG, "ready unpack_ms=${t1 - t0} python_ms=${t2 - t1} engine_ms=${answer.optInt("engine_ms")} " +
                            "server_ms=${answer.optInt("server_ms")} total_ms=${t3 - t0} python=${answer.optString("python")}")
                        answer.also { started = it }
                    }
                }
                // Spike only: the CI check reads it to call the API. Local to this phone.
                Log.d(TAG, "token=${result.optString("token")}")
                runOnUiThread { show(result.optString("token")) }
            } catch (e: Throwable) {
                Log.e(TAG, "failed", e)
                runOnUiThread { status.text = "MIA couldn't start on this phone:\n\n${e.message}" }
            }
        }.start()
    }

    /** Why Android last closed MIA (Android 11+), so the phone can say so:
     *  a person with only a phone has no other way to see a crash. */
    private fun lastExit(): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return ""
        return try {
            val info = getSystemService(ActivityManager::class.java)
                .getHistoricalProcessExitReasons(packageName, 0, 1).firstOrNull() ?: return ""
            JSONObject().put("reason", info.reason).put("importance", info.importance)
                .put("pss_kb", info.pss).put("when", info.timestamp)
                .put("description", info.description ?: "").toString()
        } catch (e: Exception) {
            ""
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun show(token: String) {
        val view = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            // Every screen comes from MIA on this phone, so never show a saved
            // copy: after an update the web view kept showing the old screens.
            settings.cacheMode = WebSettings.LOAD_NO_CACHE
            clearCache(true)
            webViewClient = WebViewClient()
            // Without this, the web view silently answers "no" to any
            // confirm/alert dialog a screen asks (the Model test's Delete did).
            webChromeClient = WebChromeClient()
            // Signed in: straight to Home. Not yet: the screen asks to make an
            // account (first start) or to sign in (after logging out).
            loadUrl("http://127.0.0.1:$PORT/web/index.html" + if (token.isNotEmpty()) "#token=$token" else "")
        }
        web = view
        setContentView(view)
    }

    @Deprecated("Activity.onBackPressed is fine for this spike")
    override fun onBackPressed() {
        val view = web
        if (view != null && view.canGoBack()) view.goBack() else super.onBackPressed()
    }

    companion object {
        const val TAG = "MIA_SPIKE"
        const val PORT = 8765
        private val START_LOCK = Any()
        @Volatile private var started: JSONObject? = null
    }
}
