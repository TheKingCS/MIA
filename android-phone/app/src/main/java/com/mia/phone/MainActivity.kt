package com.mia.phone

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.view.Gravity
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
                val t0 = SystemClock.elapsedRealtime()
                val root = Unpack.ensure(this)
                val t1 = SystemClock.elapsedRealtime()
                if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                val t2 = SystemClock.elapsedRealtime()
                val result = JSONObject(Python.getInstance().getModule("mia_phone").callAttr("start", root.absolutePath, PORT, applicationInfo.nativeLibraryDir).toString())
                val t3 = SystemClock.elapsedRealtime()
                Log.i(TAG, "ready unpack_ms=${t1 - t0} python_ms=${t2 - t1} engine_ms=${result.optInt("engine_ms")} " +
                    "server_ms=${result.optInt("server_ms")} total_ms=${t3 - t0} python=${result.optString("python")}")
                // Spike only: the CI check reads it to call the API. Local to this phone.
                Log.d(TAG, "token=${result.optString("token")}")
                runOnUiThread { show(result.optString("token")) }
            } catch (e: Throwable) {
                Log.e(TAG, "failed", e)
                runOnUiThread { status.text = "MIA couldn't start on this phone:\n\n${e.message}" }
            }
        }.start()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun show(token: String) {
        val view = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            webViewClient = WebViewClient()
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
    }
}
