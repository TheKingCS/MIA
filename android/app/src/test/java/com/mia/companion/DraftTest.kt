package com.mia.companion

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DraftTest {
    @Test
    fun showsTheDraftAndWhereToSendIt() {
        val draft = JSONObject("""{"to": ["pat@example.com"], "subject": "Leaky faucet", "body": "Hi Pat"}""")
        val text = MiaClient.describeDraft(draft)
        assertTrue(text.startsWith("Email draft to pat@example.com: Leaky faucet\nHi Pat"))
        assertTrue(text.contains("Email drafts"))
        assertTrue(MiaClient.describeDraft(JSONObject("""{"to": [], "subject": "x", "body": "y"}""")).contains("(no address yet)"))
        assertEquals("", MiaClient.describeDraft(null))
    }
}
