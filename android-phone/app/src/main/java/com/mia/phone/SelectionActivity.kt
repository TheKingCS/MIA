package com.mia.phone

import android.annotation.SuppressLint
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject
import java.io.ByteArrayInputStream

/**
 * "MIA" on any selection (the Universal Action Layer, phase U2, DEC-0165): text selected in any app has "MIA" in its
 * selection menu (Android's PROCESS_TEXT), and text or a link shared with "Do with MIA" comes here too. A card opens
 * over the app you're in, shows what MIA can do with it (selection.html, the same offer as the PC's Ctrl+K), and
 * closes back to that app.
 *
 * What's selected stays on this phone: it's handed to the page through the `MIASelection` bridge (never in an
 * address), and the engine decides what's offered and runs it (core/ual.py). A change is only ever a proposal, made
 * only on the person's yes. The text in the other app is never replaced.
 */
class SelectionActivity : Activity() {
    private var capture: JSONObject = JSONObject()
    private var web: WebView? = null

    /** What the page may ask of the phone: the capture, copying a result, opening MIA, and closing the card. */
    private val bridge = object {
        @JavascriptInterface
        fun capture(): String = capture.toString()

        @JavascriptInterface
        fun copy(text: String) {
            runOnUiThread {
                getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText("MIA", text))
                Toast.makeText(this@SelectionActivity, "Copied.", Toast.LENGTH_SHORT).show()
            }
        }

        @JavascriptInterface
        fun openInMia(page: String) {
            if (!OWN_PAGE.matches(page)) return  // only MIA's own pages
            runOnUiThread {
                startActivity(Intent(this@SelectionActivity, MainActivity::class.java)
                    .putExtra(EXTRA_OPEN, page).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                finish()
            }
        }

        @JavascriptInterface
        fun done() { runOnUiThread { finish() } }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, (resources.displayMetrics.heightPixels * 0.82).toInt())
        window.setGravity(Gravity.BOTTOM)
        window.addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND)
        val status = TextView(this).apply {
            text = getString(R.string.selection_starting)
            textSize = 17f
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }
        setContentView(status)
        capture = captureOf(intent)
        if (!capture.has("text")) { status.text = getString(R.string.selection_nothing); return }
        Thread {
            try {
                val token = Engine.ensure(applicationContext).optString("token")
                runOnUiThread {
                    if (token.isEmpty()) status.text = getString(R.string.selection_sign_in) else show(token)
                }
            } catch (e: Throwable) {
                Log.e(TAG, "couldn't start", e)
                runOnUiThread { status.text = getString(R.string.selection_failed, e.message ?: "") }
            }
        }.start()
    }

    /** The selection as core/ual.Capture's JSON: the text (a share's subject goes in front), the app it came from
     *  and that app's name, and that it came from the phone. Nothing when there's no text. */
    private fun captureOf(given: Intent?): JSONObject {
        val got = JSONObject()
        val text = when (given?.action) {
            Intent.ACTION_PROCESS_TEXT -> given?.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()
            Intent.ACTION_SEND -> given?.getStringExtra(Intent.EXTRA_TEXT)
            else -> null
        }?.trim().orEmpty()
        if (text.isEmpty()) return got
        val from = callingPackage ?: callingActivity?.packageName ?: referrer?.host.orEmpty()
        got.put("text", text).put("device", "phone").put("source_app", if (from.isEmpty()) "android" else "android:$from")
        val subject = given?.getStringExtra(Intent.EXTRA_SUBJECT)?.trim().orEmpty()
        val label = try {
            if (from.isEmpty()) "" else packageManager.getApplicationLabel(packageManager.getApplicationInfo(from, 0)).toString()
        } catch (e: Exception) {
            ""
        }
        val title = subject.ifEmpty { label }
        if (title.isNotEmpty()) got.put("title", title)
        if (Regex("^https?://\\S+$").matches(text)) got.put("url", text)
        return got
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun show(token: String) {
        val view = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = WebSettings.LOAD_NO_CACHE
            webViewClient = object : WebViewClient() {
                // Only MIA's own card stays here; a link out opens in the browser, which has no bridge.
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    if (request.url.toString().startsWith("http://127.0.0.1:${MainActivity.PORT}/")) return false
                    try { startActivity(Intent(Intent.ACTION_VIEW, request.url)) } catch (e: Exception) { /* nothing opens it */ }
                    return true
                }

                // The card loads nothing from outside the phone.
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                    if (request.url.toString().startsWith("http://127.0.0.1:${MainActivity.PORT}/")) return null
                    return WebResourceResponse("text/plain", "utf-8", 403, "Refused", emptyMap(), ByteArrayInputStream(ByteArray(0)))
                }
            }
            addJavascriptInterface(bridge, "MIASelection")
        }
        web = view
        setContentView(view)
        view.loadUrl("http://127.0.0.1:${MainActivity.PORT}/web/selection.html#token=" + Uri.encode(token))
    }

    override fun onDestroy() {
        web?.destroy()
        web = null
        super.onDestroy()
    }

    companion object {
        private const val TAG = "MIASelection"
        /** MainActivity opens this page instead of where it was (a result's "Open in MIA"). */
        const val EXTRA_OPEN = "open"
        /** One of MIA's own pages, with a query at most (the sign-in token is MainActivity's to add). */
        val OWN_PAGE = Regex("^[\\w.-]+\\.html(\\?[^\\s#]*)?$")
    }
}
