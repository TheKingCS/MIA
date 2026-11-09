package com.mia.phone

import android.app.Activity
import android.os.Build
import android.os.Bundle
import android.service.autofill.Dataset
import android.text.InputType
import android.util.Log
import android.view.ViewGroup
import android.view.autofill.AutofillId
import android.view.autofill.AutofillManager
import android.view.autofill.AutofillValue
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RemoteViews
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * "Fill from MIA" (MiaAutofillService): the person's own choice of which login goes into the boxes. Asks MIA's engine
 * on the phone (127.0.0.1, the signed-in person's session) for the logins that fit the site or app, titles and
 * usernames only; with the vault locked it asks for the master password first, as the Passwords page does. Only the
 * login tapped has its password read (the same reveal the Passwords page's Show uses), once, straight into the box.
 */
class AutofillActivity : Activity() {
    private lateinit var body: LinearLayout
    private var usernameId: AutofillId? = null
    private var passwordId: AutofillId? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        usernameId = idExtra(EXTRA_USERNAME_ID)
        passwordId = idExtra(EXTRA_PASSWORD_ID)
        body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 48, 48, 48) }
        setContentView(ScrollView(this).apply { addView(body) })
        setResult(RESULT_CANCELED)
        say(getString(R.string.autofill_looking))
        load()
    }

    @Suppress("DEPRECATION")
    private fun idExtra(name: String): AutofillId? =
        if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(name, AutofillId::class.java)
        else intent.getParcelableExtra<AutofillId>(name)

    /** The fitting logins (or the unlock box when the vault is locked). */
    private fun load() {
        val domain = intent.getStringExtra(EXTRA_DOMAIN).orEmpty()
        val pkg = intent.getStringExtra(EXTRA_PACKAGE).orEmpty()
        val path = "/api/passwords/autofill?domain=" + URLEncoder.encode(domain, "UTF-8") + "&package=" + URLEncoder.encode(pkg, "UTF-8")
        call("GET", path, null) { code, answer ->
            when {
                code == 423 -> askMaster()
                code != 200 -> say(answer.optString("detail", getString(R.string.autofill_unreachable)))
                else -> choose(answer.optJSONArray("matches") ?: JSONArray(), domain.ifEmpty { pkg })
            }
        }
    }

    private fun askMaster() {
        body.removeAllViews()
        body.addView(TextView(this).apply { text = getString(R.string.autofill_locked); textSize = 18f })
        val master = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            hint = getString(R.string.autofill_master)
            importantForAutofill = android.view.View.IMPORTANT_FOR_AUTOFILL_NO  // never offer to fill MIA's own master password
        }
        body.addView(master, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        body.addView(Button(this).apply {
            text = getString(R.string.autofill_unlock)
            setOnClickListener {
                val secret = master.text.toString()
                master.setText("")
                call("POST", "/api/passwords/unlock", JSONObject().put("master", secret)) { code, answer ->
                    if (code == 200) load() else { say(answer.optString("detail", getString(R.string.autofill_wrong))); askMaster() }
                }
            }
        })
    }

    private fun choose(matches: JSONArray, where: String) {
        body.removeAllViews()
        if (matches.length() == 0) {
            say(getString(R.string.autofill_none, where))
            return
        }
        body.addView(TextView(this).apply { text = getString(R.string.autofill_pick, where); textSize = 18f })
        for (i in 0 until matches.length()) {
            val m = matches.getJSONObject(i)
            body.addView(Button(this).apply {
                text = m.optString("title") + if (m.optString("username").isNotEmpty()) "\n" + m.optString("username") else ""
                isAllCaps = false
                setOnClickListener { fill(m.optString("id"), m.optString("username"), m.optString("title")) }
            })
        }
    }

    /** Reads the one password picked and hands the boxes their values. */
    private fun fill(entryId: String, username: String, title: String) {
        call("POST", "/api/passwords/login/" + URLEncoder.encode(entryId, "UTF-8") + "/reveal", JSONObject()) { code, answer ->
            if (code != 200) { say(answer.optString("detail", getString(R.string.autofill_unreachable))); return@call }
            val presentation = RemoteViews(packageName, android.R.layout.simple_list_item_1).apply {
                setTextViewText(android.R.id.text1, title)
            }
            @Suppress("DEPRECATION")
            val dataset = Dataset.Builder(presentation).apply {
                usernameId?.let { if (username.isNotEmpty()) setValue(it, AutofillValue.forText(username)) }
                passwordId?.let { setValue(it, AutofillValue.forText(answer.optString("password"))) }
            }.build()
            setResult(RESULT_OK, android.content.Intent().putExtra(AutofillManager.EXTRA_AUTHENTICATION_RESULT, dataset))
            finish()
        }
    }

    private fun say(line: String) {
        body.removeAllViews()
        body.addView(TextView(this).apply { text = line; textSize = 16f })
    }

    /** One request to MIA's engine on this phone, off the main thread; the answer comes back on it. */
    private fun call(method: String, path: String, json: JSONObject?, then: (Int, JSONObject) -> Unit) {
        Thread {
            val (code, answer) = try {
                val token = Engine.ensure(applicationContext).optString("token")
                val connection = URL("http://127.0.0.1:${MainActivity.PORT}$path").openConnection() as HttpURLConnection
                connection.requestMethod = method
                connection.connectTimeout = 5000
                connection.readTimeout = 15000
                connection.setRequestProperty("Authorization", "Bearer $token")
                if (json != null) {
                    connection.doOutput = true
                    connection.setRequestProperty("Content-Type", "application/json")
                    connection.outputStream.use { it.write(json.toString().toByteArray()) }
                }
                val status = connection.responseCode
                val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                status to (try { JSONObject(text) } catch (e: Exception) { JSONObject() })
            } catch (e: Exception) {
                Log.w(TAG, "Couldn't reach MIA for autofill", e)
                0 to JSONObject()
            }
            runOnUiThread { if (!isFinishing) then(code, answer) }
        }.start()
    }

    companion object {
        private const val TAG = "MiaAutofill"
        const val EXTRA_USERNAME_ID = "com.mia.phone.autofill.USERNAME_ID"
        const val EXTRA_PASSWORD_ID = "com.mia.phone.autofill.PASSWORD_ID"
        const val EXTRA_DOMAIN = "com.mia.phone.autofill.DOMAIN"
        const val EXTRA_PACKAGE = "com.mia.phone.autofill.PACKAGE"
    }
}
