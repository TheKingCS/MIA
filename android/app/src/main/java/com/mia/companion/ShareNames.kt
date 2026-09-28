package com.mia.companion

import java.net.URLEncoder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Pure helpers for "Share to MIA" (ShareActivity): what to call a shared
 * file, and how to send its name. No Android classes, so they're tested
 * on the JVM (ShareNamesTest).
 */

/** Same limit as the server (core/inbox_manager.MAX_UPLOAD_BYTES). */
const val MAX_SHARE_BYTES = 25L * 1024 * 1024

private val EXTENSIONS = mapOf(
    "application/pdf" to "pdf",
    "image/jpeg" to "jpg",
    "image/png" to "png",
    "image/webp" to "webp",
    "image/heic" to "heic",
    "image/heif" to "heif",
    "image/gif" to "gif",
    "text/plain" to "txt",
    "text/html" to "html",
    "text/csv" to "csv",
    "message/rfc822" to "eml",
)

/**
 * The name MIA files it under: the sharing app's own name when it gave
 * one (with an extension added from the type if it's missing, since MIA
 * decides how to read a file by its extension), else "shared-<time>".
 */
fun shareFileName(displayName: String?, mimeType: String?, index: Int = 0, now: Date = Date()): String {
    val extension = EXTENSIONS[mimeType?.lowercase(Locale.US)?.substringBefore(';')?.trim()]
    val given = displayName?.substringAfterLast('/')?.trim().orEmpty()
    if (given.isNotEmpty()) {
        val hasExtension = given.contains('.') && given.substringAfterLast('.').length in 1..5
        return if (hasExtension || extension == null) given else "$given.$extension"
    }
    val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(now)
    val suffix = if (index > 0) "-${index + 1}" else ""
    return "shared-$stamp$suffix.${extension ?: "bin"}"
}

/** The X-Filename header: percent-encoded (the server url-decodes it; "+" would stay a plus). */
fun encodeFileNameHeader(name: String): String = URLEncoder.encode(name, "UTF-8").replace("+", "%20")

/** Shared text (no file), e.g. an order confirmation copied from a store's app. */
fun sharedTextDocument(subject: String?, text: String): String =
    if (subject.isNullOrBlank()) text else "Subject: ${subject.trim()}\n\n$text"

/** What the share screen says when it's done. */
fun shareSummary(sent: List<String>, failed: List<String>): String {
    val parts = mutableListOf<String>()
    if (sent.size == 1) parts.add("Sent ${sent[0]} to MIA's inbox; MIA will read it within a minute.")
    else if (sent.isNotEmpty()) parts.add("Sent ${sent.size} files to MIA's inbox; MIA will read them within a minute.")
    if (failed.isNotEmpty()) parts.add("Couldn't send: ${failed.joinToString("; ")}.")
    return parts.joinToString(" ")
}
