package com.mia.phone

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.util.Log
import android.webkit.JavascriptInterface
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.DeviceSessionError
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.core.voiceinvocations.VoiceInvocationsStream
import com.meta.wearable.dat.core.voiceinvocations.startVoiceInvocationsStream
import com.meta.wearable.dat.core.voiceinvocations.types.actions.LaunchApp
import com.meta.wearable.dat.display.Display
import com.meta.wearable.dat.display.addDisplay
import com.meta.wearable.dat.display.types.DisplayState
import com.meta.wearable.dat.display.views.ButtonStyle
import com.meta.wearable.dat.display.views.CornerRadius
import com.meta.wearable.dat.display.views.Direction
import com.meta.wearable.dat.display.views.FlexBoxBackground
import com.meta.wearable.dat.display.views.IconName
import com.meta.wearable.dat.display.views.IconStyle
import com.meta.wearable.dat.display.views.ImageSize
import com.meta.wearable.dat.display.views.TextColor
import com.meta.wearable.dat.display.views.TextStyle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * MIA on the glasses through Meta's Device Access Toolkit (DEC-0059). The
 * engine decides what's shown (core/glasses.py, the same /api/glasses data
 * every surface uses); this only draws it with the toolkit's display views
 * and sends the taps back. First slice: her status, the person's apps, each
 * app's menu and readouts. Changes (an item's action) come next, through
 * /api/actions, with the second gesture the rules ask for.
 *
 * Not in use since DEC-0063: what you see on the glasses is the Web App, and
 * nothing here may draw on them, so she stays one app. It's kept for the
 * toolkit's camera. The page asks through window.MIAMetaGlasses: connect() and state(). There
 * is one per app process, so a session outlives the screen that started it
 * (GlassesService.kt keeps her awake meanwhile).
 */
class MetaGlasses private constructor(private var activity: Activity) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var session: DeviceSession? = null
    private var display: Display? = null
    @Volatile private var state = "not connected"
    private var watching = false
    private var ready = false
    private var glassesAppOutdated = false
    private var retries = 0
    private val sessionJobs = mutableListOf<Job>()
    private var voice: VoiceInvocationsStream? = null
    private val voiceJobs = mutableListOf<Job>()
    private var voiceState = ""
    private var voiceRetried = false
    private var closedByPerson = false
    private var lastHome: JSONObject? = null
    private var onHome = false

    @JavascriptInterface
    fun state(): String = state

    /** Opening MIA, or "Hey Meta, start MIA": connect if everything's already set up. */
    fun autoConnect() {
        if (activity.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) return
        prepare()
        retries = 0
        closedByPerson = false
        if (Wearables.registrationState.value == RegistrationState.REGISTERED) startSession()
    }

    /** Her Close button: the glasses go back to the person, and she stays away until asked. */
    private fun close() {
        closedByPerson = true
        session?.stop()
        state = "closed"
        GlassesService.end(activity.applicationContext)
        ListenService.ready(activity.applicationContext)  // the next tap brings her back
    }

    /** Meta: the permission comes first, then the toolkit starts, once. */
    private fun prepare() {
        if (!ready) {
            ready = true
            Wearables.initialize(activity.applicationContext).onFailure { error, _ -> fail(error.description) }
            listenForVoice()
        }
        watchRegistration()
    }

    /** "Hey Meta, start MIA": Meta AI brings the app up and asks here too. */
    private fun listenForVoice() {
        voiceJobs.toList().also { voiceJobs.clear() }.forEach { it.cancel() }
        voice?.close()
        val stream = Wearables.startVoiceInvocationsStream(AutoDeviceSelector())
        voice = stream
        voiceJobs += scope.launch {
            stream.invocations.collect { invocation ->
                Log.i(TAG, "Voice: $invocation")
                if (invocation is LaunchApp) {
                    autoConnect()
                    invocation.responseHandle.sendSuccess(null)
                }
            }
        }
        voiceJobs += scope.launch {
            stream.errors.collect { error ->
                Log.w(TAG, "Voice: ${error.description}")
                if (!voiceRetried) {  // once: it can fail if it opens while the glasses are still connecting
                    voiceRetried = true
                    delay(VOICE_RETRY_MS)
                    listenForVoice()
                }
            }
        }
        voiceJobs += scope.launch {
            stream.state.collect { now ->
                Log.i(TAG, "Voice stream: $now")
                voiceState = now.toString()
            }
        }
    }

    /** From the Connect Glasses button: permission, Meta AI registration, then the session. */
    @JavascriptInterface
    fun connect() {
        activity.runOnUiThread {
            if (glassesAppOutdated) {
                glassesAppOutdated = false
                state = "finish the update, then tap Connect again"
                Wearables.openDATGlassesAppUpdate(activity).onFailure { error, _ -> fail(error.description) }
                return@runOnUiThread
            }
            if (activity.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                state = "needs the Nearby Devices permission; tap Connect again after allowing it"
                activity.requestPermissions(arrayOf(Manifest.permission.BLUETOOTH_CONNECT), BLUETOOTH_REQUEST)
                return@runOnUiThread
            }
            prepare()
            retries = 0
            closedByPerson = false
            if (Wearables.registrationState.value == RegistrationState.REGISTERED) startSession()
            else {
                state = "finish connecting in the Meta AI app"
                Wearables.startRegistration(activity)
            }
        }
    }

    private fun watchRegistration() {
        if (watching) return
        watching = true
        scope.launch { Wearables.registrationErrorStream.collect { error -> fail(error.description) } }
        scope.launch {
            Wearables.registrationState.collect { registered ->
                if (registered == RegistrationState.REGISTERED && session == null) startSession()
            }
        }
    }

    private fun startSession() {
        if (session != null) return
        state = "looking for the glasses"
        Wearables.createSession(AutoDeviceSelector(filter = { device -> device.isDisplayCapable() })).fold(
            onSuccess = { opened ->
                session = opened
                sessionJobs += scope.launch { opened.errors.collect { error -> sessionFailed(error) } }
                sessionJobs += scope.launch {
                    opened.state.collect { now ->
                        if (now == DeviceSessionState.STARTED && display == null) attach(opened)
                        if (now == DeviceSessionState.STOPPED) stopped()
                    }
                }
                opened.start()
            },
            onFailure = { error, _ ->
                sessionFailed(error)
                retrySoon()
            },
        )
    }

    private fun stopped() {
        sessionJobs.toList().also { sessionJobs.clear() }.forEach { it.cancel() }
        session = null
        display = null
        retrySoon()
    }

    /** The glasses come and go (taken off, a moment out of range): try a few times, then wait to be asked. */
    private fun retrySoon() {
        if (glassesAppOutdated || closedByPerson) return
        if (retries >= MAX_RETRIES) {
            state = "not connected"
            GlassesService.end(activity.applicationContext)
            return
        }
        retries++
        state = "reconnecting"
        scope.launch {
            delay(RETRY_MS)
            if (session == null) startSession()
        }
    }

    /** Meta's own app on the glasses can fall behind the toolkit; only it can fix that. */
    private fun sessionFailed(error: DeviceSessionError) {
        if (error != DeviceSessionError.DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED) return fail(error.description)
        glassesAppOutdated = true
        fail("the toolkit's app on the glasses needs an update; tap Connect to update it")
    }

    private fun attach(opened: DeviceSession) {
        opened.addDisplay().fold(
            onSuccess = { attached ->
                display = attached
                sessionJobs += scope.launch {
                    attached.state.collect { now ->
                        if (now == DisplayState.STARTED) {
                            state = "connected"
                            retries = 0
                            GlassesService.begin(activity.applicationContext)
                            ListenService.ready(activity.applicationContext)
                            if (voiceState != "STARTED") listenForVoice()  // it doesn't come back by itself after Meta AI restarts
                            arrive()
                        }
                    }
                }
            },
            onFailure = { error, _ -> fail(error.description) },
        )
    }

    private fun fail(why: String) {
        Log.w(TAG, why)
        state = why
    }

    // ---------------------------------------------------------------- what's shown

    /** Her orb for a moment, then Home. */
    private fun arrive() {
        val target = display ?: return
        scope.launch {
            target.sendContent {
                flexBox(padding = 20, background = FlexBoxBackground.CARD) {
                    image(uri = "$ART/orb-speaking.png", sizePreset = ImageSize.FILL, cornerRadius = CornerRadius.NONE)
                }
            }.onFailure { error, _ -> Log.w(TAG, error.description) }
            delay(ARRIVE_MS)
            showHome()
        }
    }

    /** The last Home right away, so Back never waits on the engine; fresh when it arrives. */
    private fun showHome() {
        onHome = true
        lastHome?.let { drawHome(it) }
        load("/api/glasses", quietly = lastHome != null, retry = { showHome() }) { data ->
            lastHome = data
            if (onHome) drawHome(data)
        }
    }

    private fun drawHome(data: JSONObject) {
        val apps = data.optJSONArray("apps") ?: JSONArray()
        val cards = (0 until minOf(apps.length(), MAX_BUTTONS - 1)).map { apps.getJSONObject(it) }
        screen("MIA", null, listOf(data.optString("hint") to "")) {
            cards.forEach { card -> add(card.optString("name"), appIcon(card)) { showApp(card) } }
            add("Close MIA", quiet = true) { close() }
        }
    }

    private fun showApp(card: JSONObject) {
        onHome = false
        val menu = card.optJSONArray("menu") ?: JSONArray()
        val items = (0 until menu.length()).map { menu.getJSONObject(it) }.filter { it.optString("type") == "panel" }.take(MAX_BUTTONS - 1)
        screen(card.optString("name"), appIcon(card), listOf(card.optString("status") to "")) {
            items.forEach { item -> add(item.optString("label"), IconName.CARET_RIGHT) { showPanel(card, item.optString("id")) } }
            add("Back", IconName.ARROW_LEFT, quiet = true) { showHome() }
        }
    }

    private fun showPanel(card: JSONObject, itemId: String): Unit = load("/api/glasses/${card.optString("id")}/$itemId", retry = { showPanel(card, itemId) }) { panel ->
        val lines = panel.optJSONArray("lines") ?: JSONArray()
        val rows = (0 until minOf(lines.length(), MAX_LINES)).map { lines.getJSONObject(it).let { line -> line.optString("text") to line.optString("detail") } }
        screen(panel.optString("title"), appIcon(card), rows.ifEmpty { listOf(panel.optString("empty") to "") }) {
            add("Back", IconName.ARROW_LEFT, quiet = true) { showApp(card) }
        }
    }

    private fun appIcon(card: JSONObject): IconName = APP_ICONS[card.optString("id")] ?: IconName.CARET_RIGHT

    private class Choice(val label: String, val icon: IconName?, val quiet: Boolean, val tap: () -> Unit)

    private class Choices {
        val list = mutableListOf<Choice>()
        fun add(label: String, icon: IconName? = null, quiet: Boolean = false, tap: () -> Unit) {
            list.add(Choice(label, icon, quiet, tap))
        }
    }

    /** One screen: its icon (no icon: her orb) and title, rows of words (with a smaller detail), and buttons. Each send replaces the last. */
    private fun screen(title: String, mark: IconName?, rows: List<Pair<String, String>>, buttons: Choices.() -> Unit) {
        val choices = Choices().apply(buttons).list
        val shown = rows.filter { (text, _) -> text.isNotEmpty() }
        val target = display ?: return
        scope.launch {
            target.sendContent {
                flexBox(gap = 10, padding = 20, background = FlexBoxBackground.CARD) {
                    flexBox(direction = Direction.ROW, gap = 10) {
                        if (mark == null) image(uri = "$ART/orb-idle.png", sizePreset = ImageSize.ICON, cornerRadius = CornerRadius.NONE)
                        else icon(name = mark, style = IconStyle.FILLED)
                        text(title, style = TextStyle.HEADING)
                    }
                    shown.forEach { (text, detail) ->
                        text(text, style = TextStyle.BODY, color = TextColor.SECONDARY)
                        if (detail.isNotEmpty()) text(detail, style = TextStyle.META, color = TextColor.SECONDARY)
                    }
                    choices.forEachIndexed { i, choice ->
                        val style = when {
                            choice.quiet -> ButtonStyle.OUTLINE
                            i == 0 -> ButtonStyle.PRIMARY
                            else -> ButtonStyle.SECONDARY
                        }
                        if (choice.icon != null) button(label = choice.label, style = style, iconName = choice.icon, onClick = { choice.tap() })
                        else button(label = choice.label, style = style, onClick = { choice.tap() })
                    }
                }
            }.onFailure { error, _ -> Log.d(TAG, error.description) }  // usually just replaced by a newer screen
        }
    }

    private fun load(path: String, quietly: Boolean = false, retry: () -> Unit, then: (JSONObject) -> Unit) {
        scope.launch {
            val data = withContext(Dispatchers.IO) {
                try {
                    val token = Engine.ensure(activity.applicationContext).optString("token")
                    val connection = URL("http://127.0.0.1:${MainActivity.PORT}$path").openConnection() as HttpURLConnection
                    connection.connectTimeout = 5000
                    connection.readTimeout = READ_TIMEOUT_MS
                    connection.setRequestProperty("Authorization", "Bearer $token")
                    JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                } catch (e: Exception) {
                    Log.w(TAG, "Couldn't read $path", e)
                    null
                }
            }
            if (data != null) then(data)
            else if (!quietly) screen("MIA", IconName.EXCLAMATION_CIRCLE, listOf("I can't reach my engine right now." to "")) {
                add("Try Again", IconName.TWO_ARROWS_CLOCKWISE, tap = retry)
                add("Home", IconName.HOUSE, quiet = true) { showHome() }
            }
        }
    }

    companion object {
        private const val TAG = "MetaGlasses"
        private const val MAX_BUTTONS = 5
        private const val MAX_LINES = 5
        private const val MAX_RETRIES = 4
        private const val RETRY_MS = 6000L
        private const val ARRIVE_MS = 1800L
        private const val ART = "https://raw.githubusercontent.com/TheKingCS/mia-art/main"  // DEC-0061: artwork only
        private const val VOICE_RETRY_MS = 8000L
        private const val READ_TIMEOUT_MS = 30000
        const val BLUETOOTH_REQUEST = 7301
        private val APP_ICONS = mapOf(
            "assistant" to IconName.SPEECH_BUBBLE, "budget" to IconName.SHOPPING_BAG, "calendar" to IconName.CALENDAR,
            "character" to IconName.PERSON_CIRCLE, "classroom" to IconName.GRADUATION_CAP, "dashboard" to IconName.CLOCK,
            "garage" to IconName.CAR_FRONT_VIEW, "greenhouse" to IconName.TREE, "household" to IconName.HOUSE,
            "inbox" to IconName.ENVELOPE_OPEN, "kitchen" to IconName.FORK_KNIFE, "knowledge" to IconName.LIGHT_BULB,
            "maintenance" to IconName.GEAR, "maps" to IconName.COMPASS_NORTH_UP_RED, "memories" to IconName.MOUNTAIN_SQUARE_STACKED,
            "missions" to IconName.STAR, "music" to IconName.MUSIC_NOTE, "navigation" to IconName.COMPASS_NORTH_UP_RED,
            "notes" to IconName.PENCIL_SQUARE, "power" to IconName.LIGHT_BULB, "property" to IconName.HOUSE,
            "real_estate" to IconName.HOUSE, "relationships" to IconName.THREE_PEOPLE_OVERLAPPING, "settings" to IconName.SLIDERS_HORIZONTAL,
            "skills" to IconName.GRADUATION_CAP, "toolbox" to IconName.GEAR, "workout" to IconName.HEART,
        )
        private var only: MetaGlasses? = null

        /** A tap on the glasses with MIA not showing on them. False: she's there, or never set up. */
        fun wake(): Boolean {
            val glasses = only ?: return false
            if (glasses.display != null) return false
            Log.i(TAG, "Woken by a tap")
            glasses.autoConnect()
            return true
        }

        fun attach(activity: Activity): MetaGlasses =
            (only ?: MetaGlasses(activity).also { only = it }).also { it.activity = activity }
    }
}
