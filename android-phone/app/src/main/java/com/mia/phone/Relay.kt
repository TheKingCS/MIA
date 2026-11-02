package com.mia.phone

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import android.webkit.JavascriptInterface
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.math.BigInteger
import java.nio.ByteBuffer
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.SecureRandom
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECPoint
import java.security.spec.ECPublicKeySpec
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * The phone's side of the sealed relay (DEC-0062, docs/GLASSES_RELAY_PLAN.md).
 * It connects out to the relay, opens what the glasses send, and answers
 * only what ALLOWED names. Fake data only until the plan's gate has passed.
 * Logs say why something was refused, never what it held.
 *
 * The page asks through window.MIARelay: state(), pair(), confirm(), cancel()
 * and unpair().
 */
object Relay {
    private const val TAG = "MIARelay"
    private const val URL = "wss://mia-relay.yhrhodes.workers.dev"
    private const val PREFS = "mia_relay"
    private const val WRAP_KEY = "mia_relay_wrap"
    private const val RETRY_MS = 5000L
    private const val PAGE_TO_PHONE = "page-to-phone"
    private const val PHONE_TO_PAGE = "phone-to-page"
    private val ALLOWED = mapOf("/test/hello" to """{"hello":"This is a made-up answer, sealed by your phone."}""")

    private class Keys(val room: String, val send: ByteArray, val receive: ByteArray)

    private val client = OkHttpClient()
    private val main = Handler(Looper.getMainLooper())
    private val random = SecureRandom()
    private var appContext: Context? = null
    private var keys: Keys? = null
    private var highest = 0L
    private var sent = 0L
    private var socket: WebSocket? = null

    @Volatile private var stage = "unpaired"
    @Volatile private var check = ""
    @Volatile private var connected = false
    private var pairing: WebSocket? = null
    private var ours: KeyPair? = null
    private var pending: Keys? = null

    /** Once at start: a paired phone goes straight to its room. */
    @Synchronized
    fun start(context: Context) {
        if (appContext != null) return
        appContext = context.applicationContext
        keys = load()
        if (keys != null) { stage = "paired"; connect() }
    }

    @JavascriptInterface
    fun state(): String = JSONObject().put("stage", stage).put("check", check).put("connected", connected).toString()

    /** The six digits the glasses are showing. */
    @JavascriptInterface
    @Synchronized
    fun pair(code: String) {
        if (!Regex("[0-9]{6}").matches(code)) return
        cancel()
        stage = "pairing"
        ours = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        val request = Request.Builder().url("$URL/pair-$code?role=phone").build()
        pairing = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) = sendHello(webSocket)
            override fun onMessage(webSocket: WebSocket, text: String) = onPairing(webSocket, text)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "Pairing connection failed")
                if (pairing === webSocket) { stage = "unpaired"; check = "" }
            }
        })
    }

    private fun sendHello(webSocket: WebSocket) {
        val pub = ours?.public as? ECPublicKey ?: return
        webSocket.send(JSONObject().put("t", "hello").put("pub", encode(raw(pub))).toString())
    }

    @Synchronized
    private fun onPairing(webSocket: WebSocket, text: String) {
        if (webSocket !== pairing || pending != null) return
        try {
            val message = JSONObject(text)
            if (message.optString("t") != "hello") return
            sendHello(webSocket)
            val pair = ours ?: return
            val pagePub = decode(message.getString("pub"))
            val phonePub = raw(pair.public as ECPublicKey)
            val agreement = KeyAgreement.getInstance("ECDH")
            agreement.init(pair.private)
            agreement.doPhase(publicKey(pagePub, pair.public as ECPublicKey), true)
            val shared = agreement.generateSecret()
            val salt = MessageDigest.getInstance("SHA-256").digest("mia-relay-v1".toByteArray() + pagePub + phonePub)
            val number = ByteBuffer.wrap(expand(shared, salt, "check")).int.toLong() and 0xffffffffL
            check = (number % 1000000).toString().padStart(6, '0')
            pending = Keys(
                expand(shared, salt, "room").joinToString("") { "%02x".format(it) },
                expand(shared, salt, PHONE_TO_PAGE),
                expand(shared, salt, PAGE_TO_PHONE),
            )
            stage = "check"
        } catch (e: Exception) {
            Log.w(TAG, "Refused a bad hello")
        }
    }

    /** The person has seen the same six digits on both. Only now is the key kept. */
    @JavascriptInterface
    @Synchronized
    fun confirm() {
        val chosen = pending ?: return
        pairing?.send(JSONObject().put("t", "ok").toString())
        pairing?.close(1000, null)
        pairing = null
        pending = null
        ours = null
        check = ""
        highest = 0
        keys = chosen
        save(chosen)
        stage = "paired"
        connect()
    }

    @JavascriptInterface
    @Synchronized
    fun cancel() {
        pairing?.close(1000, null)
        pairing = null
        pending = null
        ours = null
        check = ""
        if (stage != "paired") stage = "unpaired"
    }

    /** Forget the glasses: their key reaches nothing from now on. */
    @JavascriptInterface
    @Synchronized
    fun unpair() {
        cancel()
        keys = null
        stage = "unpaired"
        socket?.close(1000, null)
        socket = null
        connected = false
        prefs()?.edit()?.clear()?.apply()
    }

    @Synchronized
    private fun connect() {
        val paired = keys ?: return
        if (socket != null) return
        val request = Request.Builder().url("$URL/${paired.room}?role=phone").build()
        socket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) { connected = true }
            override fun onMessage(webSocket: WebSocket, text: String) = onFrame(webSocket, text)
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = dropped(webSocket)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) = dropped(webSocket)
        })
    }

    @Synchronized
    private fun dropped(webSocket: WebSocket) {
        if (socket !== webSocket) return
        socket = null
        connected = false
        main.postDelayed({ connect() }, RETRY_MS)
    }

    @Synchronized
    private fun onFrame(webSocket: WebSocket, frame: String) {
        val paired = keys ?: return
        val message = try {
            JSONObject(String(open(paired.receive, frame), Charsets.UTF_8))
        } catch (e: Exception) {
            Log.w(TAG, "Refused: couldn't open a message")
            return
        }
        val number = message.optLong("n")
        if (number <= highest) {
            Log.w(TAG, "Refused: a replayed message")
            return
        }
        highest = number
        prefs()?.edit()?.putLong("highest", highest)?.apply()

        val answer = ALLOWED[message.optString("path")]
        if (answer == null) Log.w(TAG, "Refused: a path that isn't allowed")
        val reply = JSONObject().put("id", message.opt("id")).put("status", if (answer == null) 403 else 200)
        if (answer != null) reply.put("body", JSONObject(answer))
        sent = maxOf(sent + 1, System.currentTimeMillis())
        webSocket.send(seal(paired.send, reply.put("n", sent).toString().toByteArray()))
    }

    // ---------------------------------------------------------------- crypto

    private fun encode(bytes: ByteArray): String = Base64.encodeToString(bytes, Base64.NO_WRAP)
    private fun decode(text: String): ByteArray = Base64.decode(text, Base64.NO_WRAP)

    private fun raw(key: ECPublicKey): ByteArray = byteArrayOf(4) + fixed(key.w.affineX) + fixed(key.w.affineY)

    private fun fixed(number: BigInteger): ByteArray {
        val bytes = number.toByteArray().takeLast(32).toByteArray()
        return ByteArray(32 - bytes.size) + bytes
    }

    private fun publicKey(bytes: ByteArray, like: ECPublicKey): java.security.PublicKey {
        require(bytes.size == 65 && bytes[0] == 4.toByte())
        val point = ECPoint(BigInteger(1, bytes.copyOfRange(1, 33)), BigInteger(1, bytes.copyOfRange(33, 65)))
        return KeyFactory.getInstance("EC").generatePublic(ECPublicKeySpec(point, like.params))
    }

    /** HKDF-SHA-256 for one 32-byte block. */
    private fun expand(ikm: ByteArray, salt: ByteArray, info: String): ByteArray {
        val extract = Mac.getInstance("HmacSHA256").apply { init(SecretKeySpec(salt, "HmacSHA256")) }.doFinal(ikm)
        return Mac.getInstance("HmacSHA256").apply { init(SecretKeySpec(extract, "HmacSHA256")) }
            .doFinal(info.toByteArray() + byteArrayOf(1))
    }

    private fun seal(key: ByteArray, plain: ByteArray): String {
        val nonce = ByteArray(12).also { random.nextBytes(it) }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        cipher.updateAAD(PHONE_TO_PAGE.toByteArray())
        return encode(nonce + cipher.doFinal(plain))
    }

    private fun open(key: ByteArray, frame: String): ByteArray {
        val all = decode(frame)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, all, 0, 12))
        cipher.updateAAD(PAGE_TO_PHONE.toByteArray())
        return cipher.doFinal(all, 12, all.size - 12)
    }

    // ---------------------------------------------------------------- keeping the key

    private fun prefs() = appContext?.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** Android's keystore holds the key that seals ours, so it can't be copied off the phone. */
    private fun wrapKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(WRAP_KEY, null) as? SecretKey)?.let { return it }
        val spec = KeyGenParameterSpec.Builder(WRAP_KEY, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply { init(spec) }.generateKey()
    }

    private fun save(chosen: Keys) {
        val plain = JSONObject().put("room", chosen.room).put("send", encode(chosen.send)).put("receive", encode(chosen.receive))
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, wrapKey()) }
        val sealed = cipher.doFinal(plain.toString().toByteArray())
        prefs()?.edit()?.putString("keys", encode(cipher.iv + sealed))?.putLong("highest", 0)?.apply()
    }

    private fun load(): Keys? {
        val stored = prefs()?.getString("keys", null) ?: return null
        return try {
            val all = decode(stored)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, wrapKey(), GCMParameterSpec(128, all, 0, 12))
            val plain = JSONObject(String(cipher.doFinal(all, 12, all.size - 12), Charsets.UTF_8))
            highest = prefs()?.getLong("highest", 0) ?: 0
            Keys(plain.getString("room"), decode(plain.getString("send")), decode(plain.getString("receive")))
        } catch (e: Exception) {
            Log.w(TAG, "Couldn't read the glasses' key")
            null
        }
    }
}
