package com.mia.companion

import android.util.Base64
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * Talks to MIA at home: the same endpoints the phone web app uses
 * (server/app.py), so the server needs no changes for the native app.
 *
 *   POST /api/login        {profile_id, password} -> {token, name, ...}
 *   GET  /api/voice/status -> {speech_to_text, text_to_speech, assistant}
 *   POST /api/voice/turn   raw 16 kHz mono WAV body -> a TurnResult
 *   POST /api/voice/text   {text} -> a TurnResult
 *   POST /api/voice/reset  start a fresh conversation
 *   GET  /api/finance/summary  read-only money summary (Money view)
 *   POST /api/inbox/upload  raw file body + X-Filename -> the document inbox (Share to MIA)
 *
 * Plain HttpURLConnection and the platform's org.json: no third-party
 * libraries to go stale. Blocking calls; callers run them off the main
 * thread.
 */
class MiaClient(baseUrl: String) {
    private val base = normalizeBaseUrl(baseUrl)

    class HttpError(val code: Int, message: String) : IOException(message)

    data class LoginResult(val token: String, val name: String)

    data class TurnResult(val transcript: String, val replyText: String, val audioWav: ByteArray?, val timings: String = "")

    data class Status(val speechToText: Boolean, val textToSpeech: Boolean, val assistant: Boolean)

    fun login(name: String, password: String): LoginResult {
        val body = JSONObject().put("profile_id", name).put("password", password)
        val json = request("POST", "/api/login", null, body.toString().toByteArray(), "application/json")
        return LoginResult(json.getString("token"), json.optString("name", name))
    }

    fun status(token: String): Status {
        val json = request("GET", "/api/voice/status", token, null, null)
        return Status(json.optBoolean("speech_to_text"), json.optBoolean("text_to_speech"), json.optBoolean("assistant"))
    }

    fun voiceTurn(token: String, wav: ByteArray): TurnResult =
        parseTurn(request("POST", "/api/voice/turn", token, wav, "audio/wav"))

    fun textTurn(token: String, text: String): TurnResult =
        parseTurn(request("POST", "/api/voice/text", token, JSONObject().put("text", text).toString().toByteArray(), "application/json"))

    /** Finance #4: the read-only money summary (core/finance_summary.py). */
    fun financeSummary(token: String): JSONObject = request("GET", "/api/finance/summary", token, null, null)

    /** Share to MIA: a file for the document inbox (core/inbox_manager.py). */
    fun uploadToInbox(token: String, fileName: String, data: ByteArray, mimeType: String?) {
        request("POST", "/api/inbox/upload", token, data, mimeType ?: "application/octet-stream",
            mapOf("X-Filename" to encodeFileNameHeader(fileName)))
    }

    fun reset(token: String) {
        request("POST", "/api/voice/reset", token, ByteArray(0), "application/json")
    }

    private fun request(
        method: String, path: String, token: String?, body: ByteArray?, contentType: String?,
        headers: Map<String, String> = emptyMap(),
    ): JSONObject {
        val connection = URL(base + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = 10_000
            // A reply can take a while: speech-to-text, the model, then the voice.
            connection.readTimeout = 120_000
            token?.let { connection.setRequestProperty("Authorization", "Bearer $it") }
            headers.forEach { (name, value) -> connection.setRequestProperty(name, value) }
            if (body != null) {
                connection.doOutput = true
                contentType?.let { connection.setRequestProperty("Content-Type", it) }
                connection.setFixedLengthStreamingMode(body.size)
                connection.outputStream.use { it.write(body) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() } ?: ""
            if (code !in 200..299) throw HttpError(code, errorDetail(text) ?: "MIA answered with error $code.")
            return if (text.isBlank()) JSONObject() else JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        /** "mia-home.tail1234.ts.net" -> "https://mia-home.tail1234.ts.net", trailing slash dropped. */
        fun normalizeBaseUrl(raw: String): String {
            var url = raw.trim().trimEnd('/')
            if (url.isNotEmpty() && !url.startsWith("http://") && !url.startsWith("https://")) url = "https://$url"
            return url
        }

        /** FastAPI errors look like {"detail": "..."}. */
        fun errorDetail(body: String): String? = try {
            JSONObject(body).optString("detail").takeIf { it.isNotBlank() }
        } catch (e: Exception) {
            null
        }

        fun parseTurn(json: JSONObject): TurnResult {
            val audio = json.optString("audio_wav_base64").takeIf { it.isNotBlank() && it != "null" }
            return TurnResult(
                transcript = json.optString("transcript"),
                replyText = json.optString("reply_text"),
                audioWav = audio?.let { Base64.decode(it, Base64.DEFAULT) },
                timings = describeTimings(json.optJSONObject("timings")),
            )
        }

        /** "heard 1.2s · thought 3.4s · spoke 0.8s": where a turn's time went (server/app.py turn_timings). */
        fun describeTimings(timings: JSONObject?): String {
            if (timings == null) return ""
            val words = listOf("hearing" to "heard", "thinking" to "thought", "speaking" to "spoke")
            return words.filter { timings.has(it.first) }
                .joinToString(" · ") { (key, word) -> "$word ${String.format(java.util.Locale.US, "%.1f", timings.getDouble(key))}s" }
        }
    }
}
