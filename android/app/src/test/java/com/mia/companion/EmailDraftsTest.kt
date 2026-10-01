package com.mia.companion

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EmailDraftsTest {
    @Test
    fun readsTheDraftsAndWhetherSendingIsSetUp() {
        val json = JSONObject("""{"can_send": true, "drafts": [{"draft_id": "d1", "to": ["pat@example.com"],
            "subject": "Faucet", "body": "Hi Pat", "text": "Subject: Faucet\n\nHi Pat",
            "mailto": "mailto:pat@example.com?subject=Faucet&body=Hi%20Pat"}]}""")
        val (drafts, canSend) = parseDrafts(json)
        assertTrue(canSend)
        assertEquals(listOf("pat@example.com"), drafts[0].to)
        assertEquals("d1", drafts[0].id)
        assertTrue(drafts[0].mailto.startsWith("mailto:"))
        val (none, cannot) = parseDrafts(JSONObject("""{"drafts": []}"""))
        assertTrue(none.isEmpty())
        assertFalse(cannot)
    }
}
