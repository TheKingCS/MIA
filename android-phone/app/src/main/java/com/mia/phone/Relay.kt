package com.mia.phone

import android.app.Activity
import android.app.AlertDialog
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
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigInteger
import java.net.HttpURLConnection
import java.net.URL
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
import kotlin.math.abs

/**
 * The phone's side of the sealed relay (DEC-0062, docs/GLASSES_RELAY_PLAN.md).
 * It connects out to the relay, opens what the glasses send, and answers
 * only what's named below: the screens of the apps in HOME_APPS, cut down
 * here on the phone, so the glasses can't ask for more (DEC-0062). The page's
 * code is public, so it never names a change: a panel's allowed actions become
 * one-time references here, and the page can only send one back (DEC-0064).
 * Logs say why something was refused, never what it held.
 *
 * The page asks through window.MIARelay: state(), pair(), confirm(), cancel()
 * and unpair().
 */
object Relay {
    private const val TAG = "MIARelay"
    private const val URL = "wss://mia-relay.yhrhodes.workers.dev"
    private const val PREFS = "mia_relay"
    private const val LISTEN = "/voice/listen"
    private const val WRAP_KEY = "mia_relay_wrap"
    private const val RETRY_MS = 5000L
    private const val PROMISE_MS = 2000L
    private const val FRESH_MS = 30000L
    private const val PAGE_TO_PHONE = "page-to-phone"
    private const val PHONE_TO_PAGE = "phone-to-page"
    private const val ORB = "/api/glasses/orb"
    private val CARDS = Regex("/api/glasses(\\?mission=[A-Za-z0-9_-]{1,64})?")
    private val FEED = Regex("/api/glasses/feed(\\?since=[A-Za-z0-9:.%_-]{0,64})?")
    private val PANEL = Regex("/api/glasses/([a-z_]{1,32})/([a-z0-9_-]{1,32})(\\?mission=[A-Za-z0-9_-]{1,64})?")
    private val THREAD = Regex("/api/talk/thread\\?limit=[0-9]{1,2}&earlier=1")
    private val NOT_FOR_GLASSES = setOf("action", "actions", "ask", "html", "heard")
    // Meeting her: the only writes the glasses can make, each named here.
    private val FIRST_BOOT_READS = setOf("/api/first-boot", "/api/user-sync", "/api/welcome")
    private val FIRST_BOOT_WRITES = setOf("/api/user-sync", "/api/welcome")
    private val BOOT_ACTIONS = setOf("firstboot.advance", "firstboot.skip")
    private const val BOOT_STEP = "/firstboot/step"
    private const val SYNC = "/api/user-sync"
    // Everyday and undoable (DEC-0064). Nothing that pays out, spends or deletes.
    private val OFFER_KINDS = setOf("task.done", "routine.log", "grocery.check", "objective.tick", "fitness.step",
        "fitness.training_done", "fitness.food", "meal.prep_done", "maintenance.done")
    private const val OFFER_PROPOSE = "/action/propose"
    private const val OFFER_APPROVE = "/action/approve"
    private const val OFFER_REJECT = "/action/reject"
    private const val OFFER_MS = 5 * 60 * 1000L
    private const val MAX_OFFERS = 300
    private const val MAX_CHANGES_A_MINUTE = 30
    private const val PAIRED_PERSON = "person"
    // Money waits for the phone's screen, whatever the page sends (DEC-0064).
    private val SYNC_CHOICES_ON_MONEY = setOf("skip", "later", "start", "continue")
    private const val MAX_BODY = 20_000
    private const val MAX_REPLY = 200_000  // under what the relay carries
    // By name, so a new app stays off the glasses until someone adds it. No
    // budget, property or account app belongs here.
    private val HOME_APPS = listOf("missions", "calendar", "workout", "kitchen", "garage", "greenhouse")
    private val MONEY = Regex("[$€£¥]")

    private class Keys(val room: String, val send: ByteArray, val receive: ByteArray)
    private class Offer(val kind: String, val params: JSONObject, val at: Long)

    // What the glasses were offered, and which proposal came from which offer.
    private val offers = HashMap<String, Offer>()
    private val proposed = HashMap<String, String>()
    private val changes = ArrayDeque<Long>()

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
    private var ourNonce: ByteArray? = null
    private var transcript: ByteArray? = null
    private var confirmPhone: ByteArray? = null
    private var confirmPage: ByteArray? = null
    private var screen: Activity? = null
    private var dialog: AlertDialog? = null

    /** The screen a pairing's question can show on. */
    fun showingOn(activity: Activity?) { screen = activity }

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

    /** The six digits the glasses are showing. Our key is only promised at first
     *  (commit-then-reveal): nobody can pick theirs to match it. */
    @JavascriptInterface
    @Synchronized
    fun pair(code: String) {
        if (!Regex("[0-9]{6}").matches(code) || keys != null) return
        cancel()
        stage = "pairing"
        val pair = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        ours = pair
        val nonce = ByteArray(32).also { random.nextBytes(it) }
        ourNonce = nonce
        val promise = encode(MessageDigest.getInstance("SHA-256").digest(raw(pair.public as ECPublicKey) + nonce))
        val request = Request.Builder().url("$URL/pair-$code?role=phone").build()
        val opened = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) = promiseUntilAnswered(webSocket, promise)
            override fun onMessage(webSocket: WebSocket, text: String) = onPairing(webSocket, text)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "Pairing connection failed")
                failPairing(webSocket)
            }
        })
        pairing = opened
    }

    @Synchronized
    private fun failPairing(webSocket: WebSocket) {
        if (pairing === webSocket) { cancel(); webSocket.cancel() }
    }

    /** The relay keeps nothing, so the glasses may not be there yet. */
    @Synchronized
    private fun promiseUntilAnswered(webSocket: WebSocket, promise: String) {
        if (webSocket !== pairing || pending != null) return
        webSocket.send(JSONObject().put("t", "commit").put("c", promise).toString())
        main.postDelayed({ promiseUntilAnswered(webSocket, promise) }, PROMISE_MS)
    }

    @Synchronized
    private fun onPairing(webSocket: WebSocket, text: String) {
        if (webSocket !== pairing) return
        try {
            val message = JSONObject(text)
            when (message.optString("t")) {
                "hello" -> if (pending == null) answerHello(webSocket, message)
                "ok" -> finishPairing(webSocket, message)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Refused a bad pairing message")
            failPairing(webSocket)
        }
    }

    private fun answerHello(webSocket: WebSocket, message: JSONObject) {
        val pair = ours ?: return
        val nonce = ourNonce ?: return
        val pagePub = decode(message.getString("pub"))
        val pageNonce = decode(message.getString("nonce"))
        require(pageNonce.size == 32)
        val phonePub = raw(pair.public as ECPublicKey)
        val agreement = KeyAgreement.getInstance("ECDH")
        agreement.init(pair.private)
        agreement.doPhase(publicKey(pagePub, pair.public as ECPublicKey), true)
        val shared = agreement.generateSecret()
        val salt = MessageDigest.getInstance("SHA-256")
            .digest("mia-relay-v2".toByteArray() + pagePub + phonePub + pageNonce + nonce)
        val number = ByteBuffer.wrap(expand(shared, salt, "check")).int.toLong() and 0xffffffffL
        check = (number % 100000000).toString().padStart(8, '0')
        pending = Keys(
            expand(shared, salt, "room").joinToString("") { "%02x".format(it) },
            expand(shared, salt, PHONE_TO_PAGE),
            expand(shared, salt, PAGE_TO_PHONE),
        )
        transcript = salt
        confirmPhone = expand(shared, salt, "confirm-phone")
        confirmPage = expand(shared, salt, "confirm-page")
        webSocket.send(JSONObject().put("t", "reveal").put("pub", encode(phonePub)).put("nonce", encode(nonce)).toString())
        stage = "check"
    }

    /** They Match opens this. Android's own dialog, so no page can answer it,
     *  and it only ever answers the pairing whose digits it shows. */
    @JavascriptInterface
    @Synchronized
    fun confirm() {
        val here = screen ?: return
        val shown = transcript ?: return
        if (stage != "check") return
        val showing = check
        here.runOnUiThread {
            synchronized(this) {
                if (dialog != null || transcript !== shown) return@runOnUiThread
                dialog = AlertDialog.Builder(here)
                    .setTitle("Pair your glasses?")
                    .setMessage("Only say yes if your glasses show ${showing.take(4)} ${showing.drop(4)}.")
                    .setCancelable(false)
                    .setPositiveButton("They Match") { _, _ -> matched(shown) }
                    .setNegativeButton("They Don't") { _, _ -> cancel() }
                    .setOnDismissListener { dialog = null }
                    .show()
            }
        }
    }

    /** The person has seen the same digits on both: prove it to the glasses. */
    @Synchronized
    private fun matched(shown: ByteArray) {
        val socket = pairing ?: return
        val key = confirmPhone ?: return
        if (stage != "check" || transcript !== shown) return
        socket.send(JSONObject().put("t", "ok").put("mac", encode(mac(key, shown))).toString())
        stage = "confirming"
    }

    /** Only keeps the key once the glasses have proved they hold it too. */
    private fun finishPairing(webSocket: WebSocket, message: JSONObject) {
        if (stage != "confirming") return
        val chosen = pending ?: return
        val key = confirmPage ?: return
        val said = transcript ?: return
        if (!MessageDigest.isEqual(mac(key, said), decode(message.getString("mac")))) {
            Log.w(TAG, "Refused: the glasses' proof didn't match")
            failPairing(webSocket)
            return
        }
        webSocket.close(1000, null)
        pairing = null
        clearPairing()
        highest = 0
        forgetOffers()
        keys = chosen
        save(chosen)
        stage = "paired"
        connect()
    }

    private fun clearPairing() {
        pending = null
        ours = null
        ourNonce = null
        transcript = null
        confirmPhone = null
        confirmPage = null
        check = ""
        dialog?.let { open -> main.post { open.dismiss() } }
    }

    @JavascriptInterface
    @Synchronized
    fun cancel() {
        pairing?.close(1000, null)
        pairing = null
        clearPairing()
        stage = if (keys != null) "paired" else "unpaired"
    }

    /** Forget the glasses: their key reaches nothing from now on. */
    @JavascriptInterface
    @Synchronized
    fun unpair() {
        forgetOffers()
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

        val path = message.optString("path")
        val id = message.opt("id")
        val fresh = abs(System.currentTimeMillis() - number) <= FRESH_MS
        if (message.has("body") || path == BOOT_STEP) {
            val body = message.optJSONObject("body")
            val allowed = fresh && body != null && body.toString().length <= MAX_BODY
            Thread { answer(webSocket, id, if (allowed) write(path, body!!) else null) }.start()
            return
        }
        if (path != LISTEN) {
            Thread { answer(webSocket, id, read(path)) }.start()  // the engine can take a moment
            return
        }
        // Held back on the way: an old press never opens the mic.
        answer(webSocket, id, if (fresh) listen() else null)
    }

    @Synchronized
    private fun answer(webSocket: WebSocket, id: Any?, body: String?) {
        val paired = keys ?: return
        val reply = JSONObject().put("id", id).put("status", if (body == null) 403 else 200)
        if (body != null) reply.put("body", JSONObject(body))
        sent = maxOf(sent + 1, System.currentTimeMillis())
        webSocket.send(seal(paired.send, reply.put("n", sent).toString().toByteArray()))
    }

    /** What the glasses may read. Only these shapes, only approved apps, and
     *  the answer is cut down again in clean(). Anything else stays refused. */
    private fun read(path: String): String? {
        val panel = PANEL.matchEntire(path)
        val allowed = path == ORB || path in FIRST_BOOT_READS || FEED.matches(path) || CARDS.matches(path) || THREAD.matches(path) ||
            (panel != null && panel.groupValues[1] in HOME_APPS)
        if (!allowed) {
            Log.w(TAG, "Refused: a path that isn't allowed")
            return null
        }
        return try {
            val data = engine(path, null) ?: return null
            if (panel != null) offer(data)
            val out = if (CARDS.matches(path)) cards(data) else clean(data) as JSONObject
            if (path == SYNC) money(out as JSONObject)
            out.toString().takeIf { it.length <= MAX_REPLY }
        } catch (e: Exception) {
            Log.w(TAG, "Couldn't read for the glasses")
            null
        }
    }

    /** The writes of meeting her: User Sync and the tours, and first boot's own
     *  two steps, which are approved here as her screen's second gesture. */
    private fun write(path: String, body: JSONObject): String? {
        return try {
            if (path == BOOT_STEP) {
                val kind = body.optString("kind")
                if (kind !in BOOT_ACTIONS) return null
                val proposal = engine("/api/actions/propose", JSONObject().put("kind", kind).put("params", body.optJSONObject("params") ?: JSONObject()))
                    ?: return null
                engine("/api/actions/${proposal.getString("proposal_id")}/approve", JSONObject()) ?: return null
                return "{}"
            }
            if (path == OFFER_PROPOSE) return propose(body)
            if (path == OFFER_APPROVE) return decide(body, true)
            if (path == OFFER_REJECT) return decide(body, false)
            if (path !in FIRST_BOOT_WRITES) return null
            if (path == SYNC && !syncAllowed(body)) return null
            val out = clean(engine(path, body) ?: return null) as JSONObject
            if (path == SYNC) money(out)
            out.toString()
        } catch (e: Exception) {
            Log.w(TAG, "Couldn't save for the glasses")
            null
        }
    }

    /** User Sync's Money topic is for the phone: its screen says so, and only moving on passes. */
    private fun money(sync: JSONObject) {
        if (sync.optString("topic") == "money" && sync.optString("step") != "next") sync.put("phone_only", true)
    }

    private fun syncAllowed(body: JSONObject): Boolean {
        val now = engine(SYNC, null) ?: return false
        return now.optString("topic") != "money" || body.optString("choice") in SYNC_CHOICES_ON_MONEY
    }

    /** Swaps each allowed action in a panel for a reference. The rest stay out (clean()). */
    @Synchronized
    private fun offer(panel: JSONObject) {
        val now = System.currentTimeMillis()
        offers.entries.removeAll { now - it.value.at > OFFER_MS }
        val lines = panel.optJSONArray("lines") ?: return
        for (i in 0 until lines.length()) {
            val line = lines.optJSONObject(i) ?: continue
            val action = line.optJSONObject("action") ?: continue
            val kind = action.optString("kind")
            if (kind !in OFFER_KINDS || offers.size >= MAX_OFFERS) continue
            val ref = ByteArray(16).also { random.nextBytes(it) }.joinToString("") { "%02x".format(it) }
            offers[ref] = Offer(kind, action.optJSONObject("params") ?: JSONObject(), now)
            line.put("offered", JSONObject().put("kind", "offer").put("label", action.optString("label"))
                .put("params", JSONObject().put("ref", ref)))
        }
    }

    @Synchronized
    private fun offerFor(ref: String): Offer? = offers[ref]?.takeIf { System.currentTimeMillis() - it.at <= OFFER_MS }

    @Synchronized
    private fun roomForChange(): Boolean {
        val now = System.currentTimeMillis()
        while (changes.isNotEmpty() && now - changes.first() > 60_000L) changes.removeFirst()
        if (changes.size >= MAX_CHANGES_A_MINUTE) return false
        changes.addLast(now)
        return true
    }

    /** A pairing acts for one person: whoever made its first change. */
    private fun samePerson(proposal: JSONObject): Boolean {
        val who = proposal.optString("profile_id")
        val saved = prefs()?.getString(PAIRED_PERSON, null)
        if (saved == null) prefs()?.edit()?.putString(PAIRED_PERSON, who)?.apply()
        return who.isNotEmpty() && (saved == null || saved == who)
    }

    /** Only what the screen shows and nothing of the params. */
    private fun shown(proposal: JSONObject): String {
        val out = JSONObject()
        for (key in listOf("proposal_id", "status", "summary", "result", "reward")) {
            if (proposal.has(key)) out.put(key, proposal.get(key))
        }
        return (clean(out) as JSONObject).toString()
    }

    private fun propose(body: JSONObject): String? {
        val ref = body.optString("ref")
        val offered = offerFor(ref) ?: return null
        if (!roomForChange()) return null
        val proposal = engine("/api/actions/propose", JSONObject().put("kind", offered.kind).put("params", offered.params)) ?: return null
        val id = proposal.getString("proposal_id")
        if (!samePerson(proposal)) {
            engine("/api/actions/$id/reject", JSONObject())
            return null
        }
        synchronized(this) { proposed[id] = ref }
        return shown(proposal)
    }

    /** Yes or no to a proposal from this pairing. A yes spends its reference. */
    private fun decide(body: JSONObject, yes: Boolean): String? {
        val id = body.optString("id")
        val ref = synchronized(this) { proposed.remove(id) } ?: return null
        if (!yes) return shown(engine("/api/actions/$id/reject", JSONObject()) ?: return null)
        val spent = synchronized(this) { offers.remove(ref) }
        if (spent == null) {
            engine("/api/actions/$id/reject", JSONObject())
            return null
        }
        return shown(engine("/api/actions/$id/approve", JSONObject()) ?: return null)
    }

    @Synchronized
    private fun forgetOffers() {
        offers.clear()
        proposed.clear()
        changes.clear()
        prefs()?.edit()?.remove(PAIRED_PERSON)?.apply()
    }

    private fun engine(path: String, body: JSONObject?): JSONObject? {
        val context = appContext ?: return null
        val token = Engine.ensure(context).optString("token")
        val connection = URL("http://127.0.0.1:${MainActivity.PORT}$path").openConnection() as HttpURLConnection
        connection.connectTimeout = 5000
        connection.readTimeout = if (body == null) 7000 else 90000
        connection.setRequestProperty("Authorization", "Bearer $token")
        if (body != null) {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.use { it.write(body.toString().toByteArray()) }
        }
        return JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
    }

    /** Her app cards: approved apps only, their panels only. */
    private fun cards(data: JSONObject): Any {
        val out = JSONObject().put("hint", data.optString("hint")).put("pinned", data.optBoolean("pinned"))
            .put("priority", data.optString("priority"))
        for (list in listOf("apps", "others")) {
            val all = data.optJSONArray(list) ?: JSONArray()
            val kept = JSONArray()
            (0 until all.length()).map { all.getJSONObject(it) }.filter { it.optString("id") in HOME_APPS }.forEach { app ->
                val menu = app.optJSONArray("menu") ?: JSONArray()
                val panels = JSONArray()
                (0 until menu.length()).map { menu.getJSONObject(it) }
                    .filter { it.optString("type") == "panel" }.forEach { panels.put(it) }
                app.put("menu", panels)
                kept.put(app)
            }
            out.put(list, kept)
        }
        return clean(out) ?: out
    }

    /** Whatever the engine sends: no actions, and no line with money in it. */
    private fun clean(value: Any?): Any? = when (value) {
        is JSONObject -> JSONObject().also { out ->
            value.keys().forEach { key -> if (key !in NOT_FOR_GLASSES) out.put(key, clean(value.get(key))) }
        }
        is JSONArray -> JSONArray().also { out -> (0 until value.length()).forEach { out.put(clean(value.get(it))) } }
        is String -> if (MONEY.containsMatchIn(value)) "" else value
        else -> value
    }

    /** Her Listen button: she hears and answers through the glasses, not this relay. */
    private fun listen(): String? {
        val context = appContext ?: return null
        if (!ListenService.running) return null
        main.post { ListenService.listen(context) }
        return "{}"
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

    private fun mac(key: ByteArray, data: ByteArray): ByteArray =
        Mac.getInstance("HmacSHA256").apply { init(SecretKeySpec(key, "HmacSHA256")) }.doFinal(data)

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
