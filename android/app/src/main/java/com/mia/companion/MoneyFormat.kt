package com.mia.companion

import org.json.JSONArray
import org.json.JSONObject
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs

/**
 * The Money view (Finance #4): /api/finance/summary (core/finance_summary.py)
 * turned into titled sections of rows. A straight port of
 * server/static/money.js so the Android app and the web app show the same
 * thing; pure, so it's unit-tested on the JVM.
 */
data class MoneyRow(val label: String, val value: String, val tone: String = "", val sub: String = "")

data class MoneySection(val title: String, val rows: List<MoneyRow>, val note: String = "")

fun formatMoney(value: Double?, cents: Boolean = false): String {
    if (value == null) return "—"
    val format = NumberFormat.getNumberInstance(Locale.US).apply {
        minimumFractionDigits = if (cents) 2 else 0
        maximumFractionDigits = if (cents) 2 else 0
    }
    return (if (value < 0) "-$" else "$") + format.format(abs(value))
}

fun whenLabel(days: Int, verb: String): String = when {
    days < 0 -> "${-days} day${if (days == -1) "" else "s"} overdue"
    days == 0 -> "$verb today"
    days == 1 -> "$verb tomorrow"
    else -> "$verb in $days days"
}

private fun JSONObject.num(key: String): Double? = if (isNull(key) || !has(key)) null else getDouble(key)

private fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }

private fun aprText(value: Double): String =
    if (value == Math.floor(value)) value.toLong().toString() else value.toString()

fun moneySections(s: JSONObject): List<MoneySection> {
    if (!s.optBoolean("available")) {
        return listOf(MoneySection("Money", emptyList(), "Budget isn't available on MIA's computer right now."))
    }
    val sections = mutableListOf<MoneySection>()

    val m = s.getJSONObject("month")
    val net = m.getDouble("net")
    sections += MoneySection(
        "This month (${m.getString("label")})",
        listOf(
            MoneyRow("Money in", formatMoney(m.getDouble("income"))),
            MoneyRow("Money out", formatMoney(m.getDouble("expenses"))),
            MoneyRow("Net", formatMoney(net), if (net < 0) "bad" else "good"),
        ),
    )

    val coming = mutableListOf<MoneyRow>()
    for (b in s.getJSONArray("bills_due").objects()) {
        val days = b.getInt("days")
        coming += MoneyRow(b.getString("name"), formatMoney(b.getDouble("amount")),
            if (days < 0) "bad" else if (days <= 3) "warn" else "", whenLabel(days, "due"))
    }
    for (p in s.getJSONArray("income_expected").objects()) {
        coming += MoneyRow(p.getString("name"), "+" + formatMoney(p.getDouble("amount")), "good", whenLabel(p.getInt("days"), "expected"))
    }
    sections += MoneySection("Coming up (next 2 weeks)", coming, if (coming.isEmpty()) "No bills or paydays in the next two weeks." else "")

    val targets = s.getJSONArray("budget_targets").objects()
    if (targets.isNotEmpty()) {
        sections += MoneySection("Budget targets", targets.map { t ->
            val budget = t.getDouble("budget")
            val spent = t.getDouble("spent")
            val pct = if (budget > 0) spent / budget else 0.0
            MoneyRow(t.getString("category"), "${formatMoney(spent)} of ${formatMoney(budget)}",
                if (pct > 1) "bad" else if (pct >= 0.9) "warn" else "")
        })
    }

    val d = s.getJSONObject("debts")
    val ranked = d.getJSONArray("ranked").objects()
    sections += MoneySection(
        "Debts: ${formatMoney(d.getDouble("total"))}",
        ranked.mapIndexed { i, debt ->
            MoneyRow("${i + 1}. ${debt.getString("name")}", formatMoney(debt.getDouble("balance")), if (i == 0) "warn" else "",
                "${aprText(debt.getDouble("apr"))}% APR${if (debt.optBoolean("bank_synced")) " · bank-synced" else ""}. ${debt.getString("reason")}")
        },
        if (ranked.isNotEmpty()) "Minimum payments: ${formatMoney(d.getDouble("minimum_payments"))}/month. Pay #1 first." else "No debts tracked.",
    )

    val nw = s.getJSONObject("net_worth")
    val total = nw.num("total")
    var note = if (total == null) "Nothing to total yet: no bank sync or properties." else ""
    val manual = nw.optDouble("manual_debts_not_in_net_worth", 0.0)
    if (manual > 0) {
        note = (if (note.isNotEmpty()) "$note " else "") +
            "Debts you entered by hand (${formatMoney(manual)}) aren't subtracted here; bank-synced ones already are."
    }
    sections += MoneySection(
        "Net worth: ${formatMoney(total)}",
        nw.getJSONArray("sources").objects().map { src ->
            val v = src.getDouble("value")
            MoneyRow(src.getString("label"), formatMoney(v), if (v < 0) "bad" else "")
        },
        note,
    )

    val builds = s.getJSONArray("builds").objects()
    if (builds.isNotEmpty()) {
        sections += MoneySection("Builds", builds.map { b ->
            val spent = b.getDouble("spent")
            val budget = b.getDouble("budget")
            if (budget <= 0) {
                MoneyRow(b.getString("name"), formatMoney(spent) + " spent")
            } else {
                val remaining = b.num("remaining") ?: 0.0
                MoneyRow(b.getString("name"), "${formatMoney(spent)} of ${formatMoney(budget)}", if (remaining < 0) "bad" else "",
                    if (remaining < 0) "${formatMoney(-remaining)} over budget" else "${formatMoney(remaining)} left")
            }
        })
    }
    val tools = s.getJSONArray("tools").objects()
    if (tools.isNotEmpty()) {
        sections += MoneySection("Tools & equipment", tools.map { t ->
            val perHour = t.num("per_hour")
            MoneyRow(t.getString("name"), formatMoney(t.getDouble("total")), "",
                "${formatMoney(t.getDouble("purchase"))} to buy + ${formatMoney(t.getDouble("upkeep"))} since" +
                    (if (perHour != null) " · ${formatMoney(perHour, cents = true)}/hr" else ""))
        })
    }
    return sections
}
