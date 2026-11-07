package com.mia.phone

import android.annotation.SuppressLint
import android.app.Activity
import android.app.ActivityManager
import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.view.Gravity
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.File

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
    private var fileAsk: ValueCallback<Array<Uri>>? = null  // a page's file input, waiting on Android's picker
    private var captured: Uri? = null  // where the camera is writing Look's photo, while it's open
    // The memory vault's door to the camera roll (Gallery.kt), window.MIAAndroid on MIA's screens.
    private val gallery = Gallery(this)
    // Location quests while MIA is closed (Places.kt). Talking through the
    // glasses is ListenService's, so it keeps working once this screen is gone.
    private val placesBridge = PlacesBridge(this)
    private val permissions = Permissions(this)
    // The workout's count, spoken here (DEC-0055); made when the page first needs it (after onCreate).
    private val phoneVoice = lazy { PhoneVoice(this) }

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

    /** Where to open: a place just arrived at (its notification), a share, or where you were last (Home the first
     *  time). */
    private fun startPage(opened: Intent?, shared: Boolean): String {
        val arrive = opened?.getStringExtra("arrive")
        return when {
            arrive != null -> "index.html?arrive=" + Uri.encode(arrive)
            shared -> "inbox.html"
            else -> lastPlace() ?: "index.html"
        }
    }

    /** Keeps the page MIA is showing (its name and query, never the sign-in token after the #) in the app's own
     *  preferences, so the next start opens there. Only MIA's own screens; a place-arrival page isn't kept. */
    private fun remember(url: String) {
        val prefix = "http://127.0.0.1:$PORT/web/"
        if (!url.startsWith(prefix)) return
        val page = url.removePrefix(prefix).substringBefore('#')
        if (page.isEmpty() || page.contains("arrive=")) return
        getSharedPreferences(PLACE_PREFS, MODE_PRIVATE).edit().putString(PLACE_KEY, page).apply()
    }

    /** The page MIA was showing last, or null the first time (or when what was kept isn't one of her pages). */
    private fun lastPlace(): String? {
        val page = getSharedPreferences(PLACE_PREFS, MODE_PRIVATE).getString(PLACE_KEY, null) ?: return null
        return page.takeIf { Regex("^[\\w.-]+\\.html(\\?[^#]*)?$").matches(it) }
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
        Relay.start(applicationContext)  // the glasses' way to her (DEC-0062)
        Thread {
            try {
                // Once per app process (Engine.kt), shared with the listening service.
                val result = Engine.ensure(applicationContext, lastExit())
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
            // Only MIA's own pages stay in here, with their bridges: anything
            // else opens in the browser, which has none.
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    if (request.url.toString().startsWith("http://127.0.0.1:$PORT/")) return false
                    if (request.isForMainFrame) {
                        try {
                            startActivity(Intent(Intent.ACTION_VIEW, request.url))
                        } catch (e: ActivityNotFoundException) {
                            Log.w(TAG, "Nothing can open that link")
                        }
                    }
                    return true
                }

                // Frames, scripts and form posts never reach the check above.
                // MIA's pages load nothing from outside but pictures.
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                    val own = request.url.toString().startsWith("http://127.0.0.1:$PORT/")
                    val picture = request.requestHeaders["Accept"]?.startsWith("image/") == true
                    if (own || picture || request.url.scheme !in listOf("http", "https")) return null
                    return WebResourceResponse("text/plain", "utf-8", 403, "Refused", emptyMap(), ByteArrayInputStream(ByteArray(0)))
                }

                // Every page MIA shows (and every in-page step that changes the address) is remembered, so the next
                // start opens where you were instead of Home, after the phone locks and Android closes the app.
                override fun doUpdateVisitedHistory(view: WebView, url: String, isReload: Boolean) {
                    super.doUpdateVisitedHistory(view, url, isReload)
                    remember(url)
                }
            }
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

                // A screen's mic button: yes for MIA's own pages, once Android's microphone permission is given.
                override fun onPermissionRequest(request: PermissionRequest) {
                    val own = request.origin.toString().startsWith("http://127.0.0.1:$PORT")
                    val microphone = PermissionRequest.RESOURCE_AUDIO_CAPTURE
                    if (!own || request.resources.toList() != listOf(microphone)) { request.deny(); return }
                    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                        request.grant(arrayOf(microphone))
                    } else {
                        request.deny()
                        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), Voice.VOICE_REQUEST)
                    }
                }

                // A screen's file input (Look's "choose a photo", the Inbox): Android's own picker, for MIA's
                // pages only. Without this the web view ignores the tap. An input that asks for the camera
                // (Look's "take a photo") opens the camera, which writes into MIA's own cache: never the
                // gallery, and cleared at the next look.
                override fun onShowFileChooser(view: WebView, callback: ValueCallback<Array<Uri>>,
                                               params: FileChooserParams): Boolean {
                    if (!view.url.orEmpty().startsWith("http://127.0.0.1:$PORT/")) { callback.onReceiveValue(null); return true }
                    fileAsk?.onReceiveValue(null)  // one at a time: an earlier one that never came back is cancelled
                    fileAsk = callback
                    captured = if (params.isCaptureEnabled) lookFile() else null
                    val intent = captured?.let {
                        Intent(MediaStore.ACTION_IMAGE_CAPTURE).putExtra(MediaStore.EXTRA_OUTPUT, it)
                            .addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                    } ?: params.createIntent()
                    try {
                        startActivityForResult(intent, FILE_REQUEST)
                    } catch (e: ActivityNotFoundException) {
                        fileAsk = null
                        captured = null
                        callback.onReceiveValue(null)
                    }
                    return true
                }
            }
            addJavascriptInterface(gallery, "MIAAndroid")
            addJavascriptInterface(placesBridge, "MIAPhonePlaces")
            addJavascriptInterface(phoneVoice.value, "MIAPhoneVoice")
            addJavascriptInterface(Relay, "MIARelay")
            addJavascriptInterface(permissions, "MIAPhonePermissions")
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
        if (requestCode == Permissions.ASK_REQUEST) { this.permissions.answered(); return }
        if (requestCode != GEO_REQUEST) return
        val ask = geoAsk ?: return
        geoAsk = null
        ask.second.invoke(ask.first, grantResults.any { it == PackageManager.PERMISSION_GRANTED }, false)
    }

    override fun onResume() {
        super.onResume()
        Places.onScreen = true  // the screen's own watch asks while MIA is showing
        Relay.showingOn(this)
        ListenService.ready(this)  // a tap on the glasses talks to her (DEC-0063); only allowed while showing
    }

    override fun onDestroy() {
        Relay.showingOn(null)
        if (phoneVoice.isInitialized()) phoneVoice.value.shutdown()
        super.onDestroy()
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
        if (requestCode == FILE_REQUEST) {  // the picker or the camera closed: what was picked or taken, or nothing
            val photo = captured
            fileAsk?.onReceiveValue(when {
                photo != null -> if (resultCode == RESULT_OK) arrayOf(photo) else null
                else -> WebChromeClient.FileChooserParams.parseResult(resultCode, data)
            })
            fileAsk = null
            captured = null
        }
    }

    // A fresh file for Look's camera in the app's own cache; the last look's photo is cleared first.
    private fun lookFile(): Uri? = try {
        val dir = File(cacheDir, "looks").apply { mkdirs() }
        dir.listFiles()?.forEach { it.delete() }
        FileProvider.getUriForFile(this, "$packageName.files", File(dir, "look-${System.currentTimeMillis()}.jpg"))
    } catch (e: Exception) {
        Log.w(TAG, "No file for the camera", e)
        null
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
        const val FILE_REQUEST = 47
        const val PLACE_PREFS = "mia_place"  // where you were in the app (remember / lastPlace)
        const val PLACE_KEY = "page"
    }
}
