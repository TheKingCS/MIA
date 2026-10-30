package com.mia.phone

import android.annotation.SuppressLint
import android.app.Activity
import android.app.ActivityManager
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.webkit.GeolocationPermissions
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import android.widget.Toast
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
    // The memory vault's door to the camera roll (Gallery.kt), window.MIAAndroid on MIA's screens.
    private val gallery = Gallery(this)
    // Location quests while MIA is closed (Places.kt). Talking through the
    // glasses is ListenService's, so it keeps working once this screen is gone.
    private val placesBridge = PlacesBridge(this)

    fun webView(): WebView? = web

    /** Listen now (the tile, the shortcut, a headset's button, or a screen asking).
     *  Asks for the microphone first; then ListenService takes over, and keeps
     *  listening for a tap on the glasses after this screen closes. */
    fun listen() {
        if (Engine.started == null) return  // still starting: onCreate's thread takes it
        runOnUiThread {
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                ListenService.listen(this)
            } else {
                val ask = mutableListOf(Manifest.permission.RECORD_AUDIO)
                // Its "MIA · Ready" notification (Android 13+ asks; saying no only hides it).
                if (Build.VERSION.SDK_INT >= 33) ask += Manifest.permission.POST_NOTIFICATIONS
                requestPermissions(ask.toTypedArray(), Voice.VOICE_REQUEST)
            }
        }
    }

    /** Where to open: a place just arrived at (its notification), a share, or Home. */
    private fun startPage(opened: Intent?, shared: Boolean): String {
        val arrive = opened?.getStringExtra("arrive")
        return when {
            arrive != null -> "index.html?arrive=" + Uri.encode(arrive)
            shared -> "inbox.html"
            else -> "index.html"
        }
    }

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
        Places.register(applicationContext)  // the watched places' alerts (after an update, too)
        Thread {
            try {
                // Once per app process (Engine.kt), shared with the listening service.
                val result = Engine.ensure(applicationContext, lastExit())
                // Spike only: the CI check reads it to call the API. Local to this phone.
                Log.d(TAG, "token=${result.optString("token")}")
                // Opened from another app's Share menu: into the inbox, then show it.
                val shared = if (Share.isShare(intent)) saveShare(intent) else false
                runOnUiThread {
                    show(result.optString("token"), startPage(intent, shared))
                    if (Voice.wanted(intent)) listen()
                }
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
        val token = Engine.started?.optString("token") ?: return  // still starting: onCreate's thread takes it
        if (Voice.wanted(newIntent)) { listen(); return }
        if (newIntent.getStringExtra("arrive") != null) { web?.loadUrl(page(startPage(newIntent, false), token)); return }
        if (!Share.isShare(newIntent)) return
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
            addJavascriptInterface(gallery, "MIAAndroid")
            addJavascriptInterface(placesBridge, "MIAPhonePlaces")
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
        if (requestCode == Gallery.GALLERY_REQUEST) { gallery.accessChanged(); return }
        if (requestCode == Voice.VOICE_REQUEST) {
            val mic = permissions.indexOf(Manifest.permission.RECORD_AUDIO)
            if (mic >= 0 && grantResults.getOrNull(mic) == PackageManager.PERMISSION_GRANTED) ListenService.listen(this)
            else Toast.makeText(this, "MIA needs the microphone to hear you.", Toast.LENGTH_LONG).show()
            return
        }
        if (requestCode == PlacesBridge.PLACES_REQUEST) { placesBridge.answered(); return }
        if (requestCode != GEO_REQUEST) return
        val ask = geoAsk ?: return
        geoAsk = null
        ask.second.invoke(ask.first, grantResults.any { it == PackageManager.PERMISSION_GRANTED }, false)
    }

    override fun onResume() {
        super.onResume()
        Places.onScreen = true  // the screen's own watch asks while MIA is showing
    }

    override fun onPause() {
        Places.onScreen = false
        super.onPause()
    }

    @Deprecated("Activity.onActivityResult is fine for this spike")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        // Android's own Trash dialog (the memory vault's Free Up Space) closed.
        if (requestCode == Gallery.TRASH_REQUEST) gallery.done(resultCode == RESULT_OK)
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
    }
}
