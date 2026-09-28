package com.mia.companion

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import android.view.Gravity
import android.widget.TextView
import java.io.ByteArrayOutputStream
import java.io.IOException

/**
 * "Share to MIA": pick MIA in any app's Share menu (a receipt email's PDF,
 * a photo of a paper receipt, a manual from Files) and it goes straight
 * into MIA's document inbox at home (POST /api/inbox/upload, the same
 * endpoint as the web app's Send a file). MIA reads and classifies it
 * there; nothing is kept on the phone.
 *
 * A small dialog-style screen: "Sending…", then what happened, then it
 * closes itself. Uses the app's saved sign-in, signing in again when MIA
 * restarted (HTTP 401), like the voice service.
 */
class ShareActivity : Activity() {

    private lateinit var status: TextView
    private lateinit var store: CredentialStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = CredentialStore(this)
        status = TextView(this).apply {
            textSize = 16f
            gravity = Gravity.CENTER
            val pad = (24 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, pad)
            text = "Sending to MIA…"
        }
        setContentView(status)
        setFinishOnTouchOutside(false)

        if (!store.hasSignIn) {
            finishWith("Open the MIA app and sign in first, then share again.")
            return
        }
        val shares = collectShares(intent)
        if (shares.isEmpty()) {
            finishWith("There was nothing to send.")
            return
        }
        Thread { send(shares) }.start()
    }

    /** A file (by Uri) or shared text, with what to call it. */
    private class Share(val name: String, val uri: Uri?, val text: String?, val mimeType: String?)

    private fun collectShares(intent: Intent): List<Share> {
        val uris = when (intent.action) {
            Intent.ACTION_SEND -> listOfNotNull(streamExtra(intent))
            Intent.ACTION_SEND_MULTIPLE -> streamListExtra(intent)
            else -> emptyList()
        }
        if (uris.isNotEmpty()) {
            return uris.mapIndexed { index, uri ->
                val type = contentResolver.getType(uri) ?: intent.type
                Share(shareFileName(displayName(uri), type, index), uri, null, type)
            }
        }
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)
        if (!text.isNullOrBlank()) {
            val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT)
            return listOf(Share(shareFileName(null, "text/plain"), null, sharedTextDocument(subject, text), "text/plain"))
        }
        return emptyList()
    }

    @Suppress("DEPRECATION")
    private fun streamExtra(intent: Intent): Uri? =
        if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        else intent.getParcelableExtra(Intent.EXTRA_STREAM)

    @Suppress("DEPRECATION")
    private fun streamListExtra(intent: Intent): List<Uri> =
        (if (Build.VERSION.SDK_INT >= 33) intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
        else intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM)) ?: emptyList()

    private fun displayName(uri: Uri): String? = try {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        } ?: uri.lastPathSegment
    } catch (e: Exception) {
        uri.lastPathSegment
    }

    /** The file's bytes, refusing anything over the server's 25 MB limit. */
    private fun readBytes(uri: Uri): ByteArray {
        val input = contentResolver.openInputStream(uri) ?: throw IOException("couldn't open it")
        input.use {
            val out = ByteArrayOutputStream()
            val buffer = ByteArray(64 * 1024)
            var total = 0L
            while (true) {
                val read = it.read(buffer)
                if (read < 0) break
                total += read
                if (total > MAX_SHARE_BYTES) throw IOException("it's over 25 MB")
                out.write(buffer, 0, read)
            }
            return out.toByteArray()
        }
    }

    private fun send(shares: List<Share>) {
        val client = MiaClient(store.serverUrl)
        val sent = mutableListOf<String>()
        val failed = mutableListOf<String>()
        for ((index, share) in shares.withIndex()) {
            if (shares.size > 1) runOnUiThread { status.text = "Sending ${index + 1} of ${shares.size}…" }
            try {
                val data = share.uri?.let(::readBytes) ?: share.text!!.toByteArray(Charsets.UTF_8)
                upload(client, share.name, data, share.mimeType)
                sent.add(share.name)
            } catch (e: Exception) {
                failed.add("${share.name} (${e.message ?: "network error"})")
            }
        }
        finishWith(shareSummary(sent, failed), if (failed.isEmpty()) 1800L else 5000L)
    }

    private fun upload(client: MiaClient, name: String, data: ByteArray, mimeType: String?) {
        val token = store.token ?: signInAgain(client)
        try {
            client.uploadToInbox(token, name, data, mimeType)
        } catch (e: MiaClient.HttpError) {
            if (e.code != 401) throw e
            client.uploadToInbox(signInAgain(client), name, data, mimeType)
        }
    }

    private fun signInAgain(client: MiaClient): String {
        val password = store.password() ?: throw IOException("sign in again in the MIA app")
        return client.login(store.name, password).token.also { store.token = it }
    }

    private fun finishWith(message: String, delayMs: Long = 3000L) {
        runOnUiThread {
            status.text = message
            Handler(Looper.getMainLooper()).postDelayed({ if (!isFinishing) finish() }, delayMs)
        }
    }
}
