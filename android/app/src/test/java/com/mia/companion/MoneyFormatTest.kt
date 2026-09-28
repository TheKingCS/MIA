package com.mia.companion

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * finance_summary.json is written by tests/test_finance_summary.py from the
 * real server code, so this checks the Android formatter against exactly
 * what MIA sends (same expectations as the web app's money.js test).
 */
class MoneyFormatTest {
    private fun fixture(): JSONObject {
        val text = javaClass.classLoader!!.getResource("finance_summary.json")!!.readText()
        return JSONObject(text)
    }

    private fun sections() = moneySections(fixture()).associateBy { it.title }

    @Test
    fun monthRows() {
        val rows = sections().getValue("This month (September 2026)").rows
        assertEquals(listOf("$3,000", "$1,949", "$1,051"), rows.map { it.value })
        assertEquals("good", rows[2].tone)
    }

    @Test
    fun comingUp() {
        val rows = sections().getValue("Coming up (next 2 weeks)").rows
        assertEquals(MoneyRow("Electric", "$120", "warn", "due in 3 days"), rows[0])
        assertEquals(MoneyRow("Paycheck", "+$2,400", "good", "expected in 5 days"), rows[1])
    }

    @Test
    fun debtsNetWorthBuildsTools() {
        val s = sections()
        assertEquals("bad", s.getValue("Budget targets").rows[0].tone)
        val debts = s.getValue("Debts: $15,000")
        assertEquals("1. Chase card", debts.rows[0].label)
        assertTrue(debts.rows[0].sub.startsWith("24.9% APR. "))
        assertTrue(debts.rows[1].sub.contains("bank-synced"))
        assertTrue(debts.note.startsWith("Minimum payments: $545/month"))
        assertTrue(s.getValue("Net worth: $130,000").note.contains("hand ($3,000) aren't subtracted here"))
        assertEquals("$3,800 left", s.getValue("Builds").rows[0].sub)
        assertEquals("$329", s.getValue("Tools & equipment").rows[0].value)
    }

    @Test
    fun formattingHelpers() {
        assertEquals("-$1,234", formatMoney(-1234.4))
        assertEquals("$20.00", formatMoney(20.0, cents = true))
        assertEquals("—", formatMoney(null))
        assertEquals("2 days overdue", whenLabel(-2, "due"))
        assertEquals("due today", whenLabel(0, "due"))
        assertEquals("expected tomorrow", whenLabel(1, "expected"))
    }

    @Test
    fun unavailable() {
        val only = moneySections(JSONObject("{\"available\": false}")).single()
        assertTrue(only.note.contains("isn't available"))
    }
}
