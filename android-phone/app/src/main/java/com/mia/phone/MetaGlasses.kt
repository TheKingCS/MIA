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
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.display.Display
import com.meta.wearable.dat.display.addDisplay
import com.meta.wearable.dat.display.types.DisplayState
import com.meta.wearable.dat.display.views.ButtonStyle
import com.meta.wearable.dat.display.views.FlexBoxBackground
import com.meta.wearable.dat.display.views.TextColor
import com.meta.wearable.dat.display.views.TextStyle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
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
 * The page asks through window.MIAMetaGlasses: connect() and state().
 */
class MetaGlasses(private val activity: Activity) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var session: DeviceSession? = null
    private var display: Display? = null
    @Volatile private var state = "not connected"
    private var watching = false
    private var ready = false

    @JavascriptInterface
    fun state(): String = state

    /** From the Connect Glasses button: permission, Meta AI registration, then the session. */
    @JavascriptInterface
    fun connect() {
        activity.runOnUiThread {
            if (activity.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                state = "needs the Nearby Devices permission; tap Connect again after allowing it"
                activity.requestPermissions(arrayOf(Manifest.permission.BLUETOOTH_CONNECT), BLUETOOTH_REQUEST)
                return@runOnUiThread
            }
            // Meta: the permission comes first, then the toolkit starts, once.
            if (!ready) {
                ready = true
                Wearables.initialize(activity.applicationContext).onFailure { error, _ -> fail(error.description) }
            }
            watchRegistration()
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
                scope.launch { opened.errors.collect { error -> fail(error.description) } }
                scope.launch {
                    opened.state.collect { now ->
                        if (now == DeviceSessionState.STARTED && display == null) attach(opened)
                        if (now == DeviceSessionState.STOPPED) { session = null; display = null; state = "not connected" }
                    }
                }
                opened.start()
            },
            onFailure = { error, _ -> fail(error.description) },
        )
    }

    private fun attach(opened: DeviceSession) {
        opened.addDisplay().fold(
            onSuccess = { attached ->
                display = attached
                scope.launch {
                    attached.state.collect { now ->
                        if (now == DisplayState.STARTED) { state = "connected"; showHome() }
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

    private fun showHome() = load("/api/glasses") { data ->
        val apps = data.optJSONArray("apps") ?: JSONArray()
        val cards = (0 until minOf(apps.length(), MAX_BUTTONS)).map { apps.getJSONObject(it) }
        screen("MIA", data.optString("hint")) {
            cards.forEach { card -> it(card.optString("name"), { showApp(card) }) }
        }
    }

    private fun showApp(card: JSONObject) {
        val menu = card.optJSONArray("menu") ?: JSONArray()
        val items = (0 until menu.length()).map { menu.getJSONObject(it) }.filter { it.optString("type") == "panel" }.take(MAX_BUTTONS - 1)
        screen(card.optString("name"), card.optString("status")) { add ->
            items.forEach { item -> add(item.optString("label"), { showPanel(card, item.optString("id")) }) }
            add("Back", { showHome() })
        }
    }

    private fun showPanel(card: JSONObject, itemId: String) = load("/api/glasses/${card.optString("id")}/$itemId") { panel ->
        val lines = panel.optJSONArray("lines") ?: JSONArray()
        val shown = (0 until minOf(lines.length(), MAX_LINES)).joinToString("\n") {
            val line = lines.getJSONObject(it)
            listOf(line.optString("text"), line.optString("detail")).filter { bit -> bit.isNotEmpty() }.joinToString(": ")
        }
        screen(panel.optString("title"), shown.ifEmpty { panel.optString("empty") }) { add -> add("Back", { showApp(card) }) }
    }

    /** One screen: a title, a line of words, and buttons. Each send replaces the last. */
    private fun screen(title: String, body: String, buttons: ((String, () -> Unit) -> Unit) -> Unit) {
        val list = mutableListOf<Pair<String, () -> Unit>>()
        buttons { label, tap -> list.add(label to tap) }
        val target = display ?: return
        scope.launch {
            target.sendContent {
                flexBox(gap = 10, padding = 20, background = FlexBoxBackground.CARD) {
                    text(title, style = TextStyle.HEADING)
                    if (body.isNotEmpty()) text(body, style = TextStyle.BODY, color = TextColor.SECONDARY)
                    list.forEachIndexed { i, (label, tap) ->
                        button(label = label, style = if (i == 0) ButtonStyle.PRIMARY else ButtonStyle.SECONDARY, onClick = { tap() })
                    }
                }
            }.onFailure { error, _ -> fail(error.description) }
        }
    }

    private fun load(path: String, then: (JSONObject) -> Unit) {
        scope.launch {
            val data = withContext(Dispatchers.IO) {
                try {
                    val token = Engine.ensure(activity.applicationContext).optString("token")
                    val connection = URL("http://127.0.0.1:${MainActivity.PORT}$path").openConnection() as HttpURLConnection
                    connection.connectTimeout = 5000
                    connection.readTimeout = 15000
                    connection.setRequestProperty("Authorization", "Bearer $token")
                    JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                } catch (e: Exception) {
                    Log.w(TAG, "Couldn't read $path", e)
                    null
                }
            }
            if (data != null) then(data) else screen("MIA", "I can't reach my engine right now.") { }
        }
    }

    companion object {
        private const val TAG = "MetaGlasses"
        private const val MAX_BUTTONS = 5
        private const val MAX_LINES = 5
        const val BLUETOOTH_REQUEST = 7301
    }
}
