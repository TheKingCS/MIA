package com.mia.phone

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.OpenableColumns
import java.io.File
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

/**
 * "Share to MIA" (Zac, 2026-10-16: "the inbox for sending stuff to MIA"):
 * a file or text shared from any app goes into MIA's document inbox on this
 * phone, the same folder core/inbox_manager.py reads. Each file is written
 * whole under a hidden name and then renamed to the inbox's "sent" pattern
 * (YYYYMMDD-HHMMSS-xxxx.phone.<name>), so MIA takes it in at once. Nothing
 * leaves the phone.
 */
object Share {
    const val MAX_BYTES = 25L * 1024 * 1024

    fun isShare(intent: Intent?): Boolean =
        intent != null && (intent.action == Intent.ACTION_SEND || intent.action == Intent.ACTION_SEND_MULTIPLE)

    /** Saves what was shared into `inbox`. Returns (saved, problems). */
    fun save(context: Context, intent: Intent, inbox: File): Pair<Int, List<String>> {
        inbox.mkdirs()
        var saved = 0
        val problems = mutableListOf<String>()
        val uris = streams(intent)
        if (uris.isEmpty()) {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!text.isNullOrBlank()) {
                val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT)
                val body = if (subject.isNullOrBlank()) text else "Subject: ${subject.trim()}\n\n$text"
                write(inbox, "shared note.txt", body.toByteArray(Charsets.UTF_8))
                saved++
            }
            return Pair(saved, problems)
        }
        for ((index, uri) in uris.withIndex()) {
            val name = fileName(context, uri, intent.type, index)
            try {
                write(inbox, name, read(context, uri))
                saved++
            } catch (e: Exception) {
                problems.add("$name (${e.message ?: "couldn't read it"})")
            }
        }
        return Pair(saved, problems)
    }

    @Suppress("DEPRECATION")
    private fun streams(intent: Intent): List<Uri> = when (intent.action) {
        Intent.ACTION_SEND -> listOfNotNull(
            if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
            else intent.getParcelableExtra(Intent.EXTRA_STREAM))
        Intent.ACTION_SEND_MULTIPLE ->
            (if (Build.VERSION.SDK_INT >= 33) intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
            else intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM)) ?: emptyList()
        else -> emptyList()
    }

    private val EXTENSIONS = mapOf(
        "application/pdf" to "pdf", "image/jpeg" to "jpg", "image/png" to "png", "image/webp" to "webp",
        "image/heic" to "heic", "image/gif" to "gif", "text/plain" to "txt", "text/html" to "html",
        "message/rfc822" to "eml",
    )

    private fun fileName(context: Context, uri: Uri, intentType: String?, index: Int): String {
        val type = context.contentResolver.getType(uri) ?: intentType
        val extension = EXTENSIONS[type?.lowercase(Locale.US)?.substringBefore(';')?.trim()]
        val given = try {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0) else null
            }
        } catch (e: Exception) {
            null
        } ?: uri.lastPathSegment
        val clean = given?.substringAfterLast('/')?.trim().orEmpty()
        if (clean.isNotEmpty()) {
            val hasExtension = clean.contains('.') && clean.substringAfterLast('.').length in 1..5
            return if (hasExtension || extension == null) clean else "$clean.$extension"
        }
        return "shared${if (index > 0) "-${index + 1}" else ""}.${extension ?: "bin"}"
    }

    private fun read(context: Context, uri: Uri): ByteArray {
        val input = context.contentResolver.openInputStream(uri) ?: throw IOException("couldn't open it")
        input.use {
            val out = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(64 * 1024)
            var total = 0L
            while (true) {
                val n = it.read(buffer)
                if (n < 0) break
                total += n
                if (total > MAX_BYTES) throw IOException("it's over 25 MB")
                out.write(buffer, 0, n)
            }
            return out.toByteArray()
        }
    }

    private fun write(inbox: File, name: String, data: ByteArray) {
        val safe = name.replace(Regex("[^\\w.\\- ]"), "_").ifBlank { "shared" }
        val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
        val final = File(inbox, "$stamp-${UUID.randomUUID().toString().replace("-", "").take(4)}.phone.$safe")
        val partial = File(inbox, ".${final.name}.part")
        partial.writeBytes(data)
        if (!partial.renameTo(final)) throw IOException("couldn't save it")
    }
}
