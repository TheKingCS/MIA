package com.mia.phone

import android.annotation.SuppressLint
import android.app.Activity
import android.app.ActivityManager
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.view.Gravity
import android.webkit.GeolocationPermissions
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import android.widget.Toast
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
    // A screen asked where the phone is (World Map's I'm Here, location
    // quests, DEC-0028): answered once Android's own permission is.
    private var geoAsk: Pair<String, GeolocationPermissions.Callback>? = null

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
                // Opened from another app's Share menu: into the inbox, then show it.
                val shared = if (Share.isShare(intent)) saveShare(intent) else false
                runOnUiThread { show(result.optString("token"), if (shared) "inbox.html" else "index.html") }
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

    /** Shared again while MIA is already open (singleTask): same thing. */
    override fun onNewIntent(newIntent: Intent) {
        super.onNewIntent(newIntent)
        setIntent(newIntent)
        if (!Share.isShare(newIntent)) return
        val token = started?.optString("token") ?: return  // still starting: onCreate's thread takes it
        Thread {
            if (saveShare(newIntent)) runOnUiThread { web?.loadUrl(page("inbox.html", token)) }
        }.start()
    }

    /** Saves a share into MIA's inbox folder; says what happened. */
    private fun saveShare(shared: Intent): Boolean {
        val (saved, problems) = try {
            Share.save(this, shared, java.io.File(Unpack.ensure(applicationContext), "inbox"))
        } catch (e: Exception) {
            Log.e(TAG, "share failed", e)
            Pair(0, listOf(e.message ?: "couldn't save it"))
        }
        val message = when {
            saved == 1 && problems.isEmpty() -> "Sent to MIA's inbox."
            saved > 1 && problems.isEmpty() -> "Sent $saved files to MIA's inbox."
            saved == 0 && problems.isEmpty() -> "There was nothing to send."
            else -> "Couldn't send: ${problems.joinToString("; ")}"
        }
        runOnUiThread { Toast.makeText(this, message, Toast.LENGTH_LONG).show() }
        return saved > 0
    }

    private fun page(name: String, token: String) =
        "http://127.0.0.1:$PORT/web/$name" + if (token.isNotEmpty()) "#token=$token" else ""

    @SuppressLint("SetJavaScriptEnabled")
    private fun show(token: String, start: String = "index.html") {
        val view = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            // Every screen comes from MIA on this phone, so never show a saved
            // copy: after an update the web view kept showing the old screens.
            settings.cacheMode = WebSettings.LOAD_NO_CACHE
            settings.setGeolocationEnabled(true)
            clearCache(true)
            webViewClient = WebViewClient()
            // Without this, the web view silently answers "no" to any
            // confirm/alert dialog a screen asks (the Model test's Delete did).
            // It also answers a screen asking where the phone is: yes only for
            // MIA's own pages, and only once Android's location permission is given.
            webChromeClient = object : WebChromeClient() {
                override fun onGeolocationPermissionsShowPrompt(origin: String, callback: GeolocationPermissions.Callback) {
                    if (!origin.startsWith("http://127.0.0.1:$PORT")) { callback.invoke(origin, false, false); return }
                    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                        callback.invoke(origin, true, false)
                    } else {
                        geoAsk = origin to callback
                        requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION), GEO_REQUEST)
                    }
                }
            }
            // Signed in: straight to Home (or the Inbox, after a share). Not
            // yet: the screen asks to make an account (first start) or to
            // sign in (after logging out).
            loadUrl(page(if (token.isNotEmpty()) start else "index.html", token))
        }
        web = view
        setContentView(view)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != GEO_REQUEST) return
        val ask = geoAsk ?: return
        geoAsk = null
        ask.second.invoke(ask.first, grantResults.any { it == PackageManager.PERMISSION_GRANTED }, false)
    }

    @Deprecated("Activity.onBackPressed is fine for this spike")
    override fun onBackPressed() {
        val view = web
        if (view != null && view.canGoBack()) view.goBack() else super.onBackPressed()
    }

    companion object {
        const val TAG = "MIA_SPIKE"
        const val PORT = 8765
        const val GEO_REQUEST = 41
        private val START_LOCK = Any()
        @Volatile private var started: JSONObject? = null
    }
}
