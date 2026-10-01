package com.mia.companion

import org.json.JSONObject

/** An email MIA drafted (core/email_drafts.py): sent only when Send is tapped. */
data class DraftView(
    val id: String,
    val to: List<String>,
    val subject: String,
    val body: String,
    val text: String,
    val mailto: String,
)

/** GET /api/email/drafts -> the open drafts, newest first, and whether this person can send from MIA. */
fun parseDrafts(json: JSONObject): Pair<List<DraftView>, Boolean> {
    val list = json.optJSONArray("drafts")
    val drafts = (0 until (list?.length() ?: 0)).map { i ->
        val d = list!!.getJSONObject(i)
        val to = d.optJSONArray("to")
        DraftView(
            id = d.getString("draft_id"),
            to = (0 until (to?.length() ?: 0)).map { to!!.getString(it) },
            subject = d.optString("subject"),
            body = d.optString("body"),
            text = d.optString("text"),
            mailto = d.optString("mailto"),
        )
    }
    return drafts to json.optBoolean("can_send", false)
}
