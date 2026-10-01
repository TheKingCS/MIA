package com.mia.companion

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.IOException

/**
 * The app's one screen, built in code (no XML resources to keep in sync):
 * sign in to MIA at home, start/stop hands-free listening, see what was
 * said, and type when talking isn't possible.
 */
class MainActivity : Activity() {

    private lateinit var store: CredentialStore
    private lateinit var signInSection: LinearLayout
    private lateinit var talkSection: LinearLayout
    private lateinit var serverField: EditText
    private lateinit var nameField: EditText
    private lateinit var passwordField: EditText
    private lateinit var signInStatus: TextView
    private lateinit var stateLabel: TextView
    private lateinit var detailLabel: TextView
    private lateinit var startStopButton: Button
    private lateinit var pauseButton: Button
    private lateinit var logView: TextView
    private lateinit var typeField: EditText
    private lateinit var moneyButton: Button
    private lateinit var moneySection: LinearLayout
    private lateinit var draftsButton: Button
    private lateinit var draftsSection: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = CredentialStore(this)
        setContentView(buildLayout())
        showSection()
    }

    override fun onResume() {
        super.onResume()
        VoiceService.listener = ::render
    }

    override fun onPause() {
        VoiceService.listener = null
        super.onPause()
    }

    // ------------------------------------------------------------------
    // Layout
    // ------------------------------------------------------------------

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun label(text: String, size: Float = 15f, bold: Boolean = false): TextView = TextView(this).apply {
        this.text = text
        textSize = size
        if (bold) typeface = Typeface.DEFAULT_BOLD
        setPadding(0, dp(6), 0, dp(6))
    }

    private fun field(hint: String, type: Int): EditText = EditText(this).apply {
        this.hint = hint
        inputType = type
        setSingleLine()
    }

    private fun button(text: String, onClick: () -> Unit): Button = Button(this).apply {
        this.text = text
        isAllCaps = false
        setOnClickListener { onClick() }
    }

    private fun buildLayout(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(20))
        }
        root.addView(label("MIA", 28f, bold = true))

        signInSection = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        signInSection.addView(label("Sign in to MIA at home. Use the Tailscale address from docs/PHONE_VOICE_SETUP.md, e.g. mia-home.your-tailnet.ts.net"))
        serverField = field("MIA's address", InputType.TYPE_TEXT_VARIATION_URI).apply { setText(store.serverUrl) }
        nameField = field("Your email (or your MIA name)", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS).apply { setText(store.name) }
        passwordField = field("Password", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        signInStatus = label("")
        signInSection.addView(serverField)
        signInSection.addView(nameField)
        signInSection.addView(passwordField)
        signInSection.addView(button("Sign in") { signIn() })
        signInSection.addView(signInStatus)
        root.addView(signInSection)

        talkSection = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        stateLabel = label("Stopped", 22f, bold = true)
        detailLabel = label("", 14f).apply { setTextColor(Color.GRAY) }
        startStopButton = button("Start hands-free") { toggleListening() }
        pauseButton = button("Pause") { startService(VoiceService.intent(this, VoiceService.ACTION_TOGGLE_PAUSE)) }
        val buttons = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(startStopButton, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(pauseButton, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
        talkSection.addView(stateLabel)
        talkSection.addView(detailLabel)
        talkSection.addView(buttons)

        // Finance #4: read-only money summary, same numbers as the desktop.
        moneyButton = button("Show money") { toggleMoney() }
        talkSection.addView(moneyButton)
        moneySection = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        talkSection.addView(moneySection)

        // Email drafts MIA wrote: Send (only when tapped), Copy, or the mail app.
        draftsButton = button("Email drafts") { toggleDrafts() }
        talkSection.addView(draftsButton)
        draftsSection = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        talkSection.addView(draftsSection)

        typeField = field("Or type to MIA…", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES).apply {
            imeOptions = EditorInfo.IME_ACTION_SEND
            setOnEditorActionListener { _, actionId, _ ->
                if (actionId == EditorInfo.IME_ACTION_SEND) { sendTyped(); true } else false
            }
        }
        talkSection.addView(typeField)

        val bluetooth = CheckBox(this).apply {
            text = "Use my Bluetooth headset's microphone (call-quality sound)"
            isChecked = store.useBluetoothMic
            setOnCheckedChangeListener { _, checked -> store.useBluetoothMic = checked }
        }
        talkSection.addView(bluetooth)
        talkSection.addView(button("Let MIA run in the background (battery setting)") { askBatteryExemption() })
        talkSection.addView(button("Sign out") { signOut() })

        logView = label("", 15f).apply { gravity = Gravity.TOP }
        talkSection.addView(label("Conversation", 16f, bold = true))
        talkSection.addView(logView)
        root.addView(talkSection)

        return ScrollView(this).apply { addView(root) }
    }

    private fun showSection() {
        val signedIn = store.hasSignIn
        signInSection.visibility = if (signedIn) View.GONE else View.VISIBLE
        talkSection.visibility = if (signedIn) View.VISIBLE else View.GONE
    }

    // ------------------------------------------------------------------
    // Actions
    // ------------------------------------------------------------------

    private fun signIn() {
        val server = MiaClient.normalizeBaseUrl(serverField.text.toString())
        val name = nameField.text.toString().trim()
        val password = passwordField.text.toString()
        if (server.isBlank() || name.isBlank() || password.isBlank()) {
            signInStatus.text = "Fill in all three."
            return
        }
        signInStatus.text = "Signing in…"
        Thread {
            val message = try {
                val result = MiaClient(server).login(name, password)
                store.serverUrl = server
                store.name = name
                store.savePassword(password)
                store.token = result.token
                null
            } catch (e: IOException) {
                e.message ?: "Couldn't reach MIA."
            }
            runOnUiThread {
                if (message == null) {
                    passwordField.text.clear()
                    signInStatus.text = ""
                    showSection()
                } else {
                    signInStatus.text = message
                }
            }
        }.start()
    }

    // ------------------------------------------------------------------
    // Money (Finance #4)
    // ------------------------------------------------------------------

    private fun toggleMoney() {
        if (moneySection.visibility == View.VISIBLE) {
            moneySection.visibility = View.GONE
            moneyButton.text = "Show money"
            return
        }
        moneySection.visibility = View.VISIBLE
        moneyButton.text = "Hide money"
        loadMoney()
    }

    private fun loadMoney() {
        moneySection.removeAllViews()
        moneySection.addView(label("Loading…", 14f))
        Thread {
            val result = try {
                val client = MiaClient(store.serverUrl)
                val summary = try {
                    client.financeSummary(store.token ?: signInAgain(client))
                } catch (e: MiaClient.HttpError) {
                    if (e.code != 401) throw e
                    client.financeSummary(signInAgain(client))
                }
                Result.success(moneySections(summary))
            } catch (e: Exception) {
                Result.failure<List<MoneySection>>(e)
            }
            runOnUiThread {
                result.onSuccess(::renderMoney).onFailure {
                    moneySection.removeAllViews()
                    moneySection.addView(label("Couldn't load money: ${it.message ?: "network error"}", 14f))
                }
            }
        }.start()
    }

    // ------------------------------------------------------------------
    // Email drafts (core/email_drafts.py)
    // ------------------------------------------------------------------

    private fun toggleDrafts() {
        if (draftsSection.visibility == View.VISIBLE) {
            draftsSection.visibility = View.GONE
            draftsButton.text = "Email drafts"
            return
        }
        draftsSection.visibility = View.VISIBLE
        draftsButton.text = "Hide email drafts"
        loadDrafts()
    }

    /** Runs a call home off the screen's thread, signing in again once if MIA restarted. */
    private fun <T> callHome(work: (MiaClient, String) -> T, done: (Result<T>) -> Unit) {
        Thread {
            val result = try {
                val client = MiaClient(store.serverUrl)
                Result.success(try {
                    work(client, store.token ?: signInAgain(client))
                } catch (e: MiaClient.HttpError) {
                    if (e.code != 401) throw e
                    work(client, signInAgain(client))
                })
            } catch (e: Exception) {
                Result.failure(e)
            }
            runOnUiThread { done(result) }
        }.start()
    }

    private fun loadDrafts() {
        draftsSection.removeAllViews()
        draftsSection.addView(label("Loading…", 14f))
        callHome({ client, token -> parseDrafts(client.emailDrafts(token)) }) { result ->
            draftsSection.removeAllViews()
            result.onSuccess { (drafts, canSend) -> renderDrafts(drafts, canSend) }.onFailure {
                draftsSection.addView(label("Couldn't load drafts: ${it.message ?: "network error"}", 14f))
            }
        }
    }

    private fun renderDrafts(drafts: List<DraftView>, canSend: Boolean) {
        draftsSection.addView(button("Refresh") { loadDrafts() })
        if (drafts.isEmpty()) {
            draftsSection.addView(label("No drafts. Ask MIA to write an email.", 14f))
            return
        }
        for (draft in drafts) {
            draftsSection.addView(label("To: ${draft.to.joinToString(", ").ifBlank { "(add an address)" }}\n${draft.subject}", 15f, bold = true)
                .apply { setPadding(0, dp(14), 0, dp(4)) })
            draftsSection.addView(label(draft.body, 15f))
            val status = label("MIA only sends when you tap Send.", 13f).apply { setTextColor(Color.GRAY) }
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            val send = button("Send") {}
            send.isEnabled = canSend && draft.to.isNotEmpty()
            send.setOnClickListener {
                send.isEnabled = false
                status.text = "Sending…"
                callHome({ client, token -> client.sendDraft(token, draft.id) }) { result ->
                    result.onSuccess { status.text = it; send.text = "Sent" }
                        .onFailure { status.text = it.message ?: "Couldn't send."; send.isEnabled = true }
                }
            }
            val copy = button("Copy") {
                val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("Email draft", draft.text))
                status.text = "Copied."
            }
            val mailApp = button("Mail app") {
                try {
                    startActivity(Intent(Intent.ACTION_SENDTO, Uri.parse(draft.mailto)))
                } catch (e: Exception) {
                    status.text = "No mail app found; use Copy."
                }
            }
            val discard = button("Discard") {
                callHome({ client, token -> client.discardDraft(token, draft.id) }) { loadDrafts() }
            }
            for (b in listOf(send, copy, mailApp, discard)) {
                row.addView(b, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            }
            draftsSection.addView(row)
            draftsSection.addView(status)
            if (!canSend) draftsSection.addView(label("To send from MIA, set up Sending Email in MIA's Settings on the computer.", 13f))
        }
    }

    private fun signInAgain(client: MiaClient): String {
        val password = store.password() ?: throw IOException("Sign in again.")
        return client.login(store.name, password).token.also { store.token = it }
    }

    private fun renderMoney(sections: List<MoneySection>) {
        moneySection.removeAllViews()
        moneySection.addView(button("Refresh") { loadMoney() })
        for (section in sections) {
            moneySection.addView(label(section.title, 17f, bold = true).apply { setPadding(0, dp(14), 0, dp(4)) })
            for (row in section.rows) {
                val line = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
                val left = label(if (row.sub.isEmpty()) row.label else "${row.label}\n${row.sub}", 15f)
                val right = label(row.value, 15f, bold = true).apply {
                    gravity = Gravity.END
                    toneColor(row.tone)?.let { setTextColor(it) }
                }
                line.addView(left, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
                line.addView(right, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT))
                moneySection.addView(line)
            }
            if (section.note.isNotEmpty()) {
                moneySection.addView(label(section.note, 13f).apply { setTextColor(Color.GRAY) })
            }
        }
        moneySection.addView(label("Read-only. Tell MIA to change anything.", 13f).apply { setTextColor(Color.GRAY) })
    }

    private fun toneColor(tone: String): Int? = when (tone) {
        "good" -> Color.rgb(13, 148, 136)
        "warn" -> Color.rgb(202, 138, 4)
        "bad" -> Color.rgb(220, 38, 38)
        else -> null
    }

    private fun signOut() {
        startService(VoiceService.intent(this, VoiceService.ACTION_STOP))
        store.signOut()
        showSection()
    }

    private fun toggleListening() {
        if (VoiceService.snapshot.state != VoiceService.State.STOPPED) {
            startService(VoiceService.intent(this, VoiceService.ACTION_STOP))
            return
        }
        val needed = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) needed += Manifest.permission.POST_NOTIFICATIONS
        val missing = needed.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) {
            requestPermissions(missing.toTypedArray(), REQUEST_PERMISSIONS)
            return
        }
        startForegroundService(VoiceService.intent(this, VoiceService.ACTION_START))
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQUEST_PERMISSIONS) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startForegroundService(VoiceService.intent(this, VoiceService.ACTION_START))
        } else {
            detailLabel.text = "MIA needs the microphone to hear you."
        }
    }

    private fun sendTyped() {
        val text = typeField.text.toString().trim()
        if (text.isEmpty()) return
        typeField.text.clear()
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            detailLabel.text = "Start hands-free once first (MIA needs the microphone permission)."
            return
        }
        val intent = VoiceService.intent(this, VoiceService.ACTION_SAY_TEXT).putExtra(VoiceService.EXTRA_TEXT, text)
        // startForegroundService() obliges the service to (re)enter the
        // foreground; only use it when the service isn't running yet.
        if (VoiceService.snapshot.state == VoiceService.State.STOPPED) startForegroundService(intent) else startService(intent)
    }

    @SuppressLint("BatteryLife") // a personal, always-listening assistant is exactly the allowed case
    private fun askBatteryExemption() {
        val power = getSystemService(PowerManager::class.java)
        if (power.isIgnoringBatteryOptimizations(packageName)) {
            detailLabel.text = "Already allowed to run in the background."
            return
        }
        startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")))
    }

    private fun render(snapshot: VoiceService.Snapshot) {
        stateLabel.text = snapshot.state.label
        detailLabel.text = snapshot.detail
        val running = snapshot.state != VoiceService.State.STOPPED
        startStopButton.text = if (running) "Stop" else "Start hands-free"
        pauseButton.isEnabled = running
        pauseButton.text = if (snapshot.state == VoiceService.State.PAUSED) "Resume" else "Pause"
        logView.text = snapshot.log.asReversed().joinToString("\n\n")
    }

    private companion object {
        const val REQUEST_PERMISSIONS = 7
    }
}
