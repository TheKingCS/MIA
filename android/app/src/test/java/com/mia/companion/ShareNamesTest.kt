package com.mia.companion

import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Calendar

class ShareNamesTest {
    private val when_ = Calendar.getInstance().apply { set(2026, Calendar.SEPTEMBER, 28, 14, 5, 9) }.time

    @Test
    fun keepsTheSharingAppsName() {
        assertEquals("Z315E Manual.pdf", shareFileName("Z315E Manual.pdf", "application/pdf"))
        assertEquals("IMG_2041.jpg", shareFileName("/storage/DCIM/IMG_2041.jpg", "image/jpeg"))
    }

    @Test
    fun addsAMissingExtensionFromTheType() {
        // MIA picks how to read a file by its extension.
        assertEquals("receipt.pdf", shareFileName("receipt", "application/pdf"))
        assertEquals("1000012345.jpg", shareFileName("1000012345", "image/jpeg"))
        assertEquals("notes", shareFileName("notes", "application/x-unknown"))
    }

    @Test
    fun namesUnnamedShares() {
        assertEquals("shared-20260928-140509.txt", shareFileName(null, "text/plain", now = when_))
        assertEquals("shared-20260928-140509-2.png", shareFileName("", "image/png", 1, when_))
        assertEquals("shared-20260928-140509.bin", shareFileName(null, null, now = when_))
    }

    @Test
    fun headerIsPercentEncodedNotPlusEncoded() {
        assertEquals("Lowe%27s%20receipt.pdf", encodeFileNameHeader("Lowe's receipt.pdf"))
        assertEquals("a%2Bb.txt", encodeFileNameHeader("a+b.txt"))
    }

    @Test
    fun sharedText() {
        assertEquals("Subject: Your order\n\nTotal 12.50", sharedTextDocument("Your order", "Total 12.50"))
        assertEquals("Total 12.50", sharedTextDocument(null, "Total 12.50"))
    }

    @Test
    fun summary() {
        assertEquals("Sent a.pdf to MIA's inbox; MIA will read it within a minute.", shareSummary(listOf("a.pdf"), emptyList()))
        assertEquals("Couldn't send: b.jpg (it's over 25 MB).", shareSummary(emptyList(), listOf("b.jpg (it's over 25 MB)")))
        assertEquals(
            "Sent 2 files to MIA's inbox; MIA will read them within a minute. Couldn't send: c.pdf (timeout).",
            shareSummary(listOf("a", "b"), listOf("c.pdf (timeout)")),
        )
    }
}
