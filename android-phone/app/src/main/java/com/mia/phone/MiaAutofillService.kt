package com.mia.phone

import android.app.PendingIntent
import android.app.assist.AssistStructure
import android.content.Intent
import android.os.CancellationSignal
import android.service.autofill.AutofillService
import android.service.autofill.Dataset
import android.service.autofill.FillCallback
import android.service.autofill.FillRequest
import android.service.autofill.FillResponse
import android.service.autofill.SaveCallback
import android.service.autofill.SaveRequest
import android.text.InputType
import android.view.View
import android.view.autofill.AutofillId
import android.widget.RemoteViews

/**
 * MIA as the phone's autofill service (DEC-0035's next step): when an app or a website shows a sign-in, Android asks
 * here. MIA finds the username and password boxes and offers one line, "Fill from MIA", locked behind
 * AutofillActivity: nothing is read from the vault until the person taps it, unlocks with their master password if it
 * isn't open, and picks a login. Turned on in Android's Settings: Passwords and autofill, Autofill service, MIA.
 * Nothing is saved from here (no SaveInfo): logins are added on the Passwords page.
 */
class MiaAutofillService : AutofillService() {

    /** The boxes found in a screen: the username's and the password's ids, and the site or app they're on. */
    data class Boxes(var username: AutofillId? = null, var password: AutofillId? = null, var domain: String = "")

    override fun onFillRequest(request: FillRequest, cancellationSignal: CancellationSignal, callback: FillCallback) {
        val structure = request.fillContexts.lastOrNull()?.structure
        if (structure == null) { callback.onSuccess(null); return }
        val boxes = Boxes()
        for (i in 0 until structure.windowNodeCount) walk(structure.getWindowNodeAt(i).rootViewNode, boxes)
        val ids = listOfNotNull(boxes.username, boxes.password)
        if (boxes.password == null || packageName == structure.activityComponent.packageName) {
            callback.onSuccess(null)  // no sign-in here (or it's MIA's own screen)
            return
        }
        val auth = Intent(this, AutofillActivity::class.java)
            .putExtra(AutofillActivity.EXTRA_USERNAME_ID, boxes.username)
            .putExtra(AutofillActivity.EXTRA_PASSWORD_ID, boxes.password)
            .putExtra(AutofillActivity.EXTRA_DOMAIN, boxes.domain)
            .putExtra(AutofillActivity.EXTRA_PACKAGE, structure.activityComponent.packageName)
        val sender = PendingIntent.getActivity(this, REQUEST, auth,
            PendingIntent.FLAG_CANCEL_CURRENT or PendingIntent.FLAG_MUTABLE).intentSender
        val presentation = RemoteViews(packageName, android.R.layout.simple_list_item_1).apply {
            setTextViewText(android.R.id.text1, getString(R.string.autofill_offer))
        }
        @Suppress("DEPRECATION")
        val dataset = Dataset.Builder(presentation).apply {
            ids.forEach { setValue(it, null) }
            setAuthentication(sender)
        }.build()
        callback.onSuccess(FillResponse.Builder().addDataset(dataset).build())
    }

    override fun onSaveRequest(request: SaveRequest, callback: SaveCallback) {
        callback.onSuccess()  // never asked for: the response carries no SaveInfo
    }

    /** Looks through a screen's views for the password box, the username box before it, and the website's domain. */
    private fun walk(node: AssistStructure.ViewNode, boxes: Boxes) {
        if (boxes.domain.isEmpty() && !node.webDomain.isNullOrEmpty()) boxes.domain = node.webDomain.orEmpty()
        val id = node.autofillId
        if (id != null && node.autofillType == View.AUTOFILL_TYPE_TEXT) {
            val hints = (node.autofillHints?.joinToString(" ") ?: "").lowercase()
            val words = listOfNotNull(node.hint, node.idEntry, node.htmlInfo?.attributes?.firstOrNull { it.first == "name" }?.second)
                .joinToString(" ").lowercase()
            val variation = node.inputType and InputType.TYPE_MASK_VARIATION
            val isPassword = "password" in hints || variation == InputType.TYPE_TEXT_VARIATION_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD || variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
                (node.htmlInfo?.attributes?.any { it.first == "type" && it.second == "password" } == true)
            val isUser = "username" in hints || "email" in hints || variation == InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS ||
                variation == InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS || USER_WORDS.any { it in words }
            if (isPassword && boxes.password == null) boxes.password = id
            else if (isUser && boxes.username == null && boxes.password == null) boxes.username = id
        }
        for (i in 0 until node.childCount) walk(node.getChildAt(i), boxes)
    }

    companion object {
        private const val REQUEST = 4210
        private val USER_WORDS = listOf("user", "email", "e-mail", "login", "account", "phone")
    }
}
