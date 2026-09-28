package com.mia.companion

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test

class TimingsTest {
    @Test
    fun describesWhereTheTimeWent() {
        val timings = JSONObject("""{"hearing": 1.2, "thinking": 3.4, "speaking": 0.8}""")
        assertEquals("heard 1.2s · thought 3.4s · spoke 0.8s", MiaClient.describeTimings(timings))
        assertEquals("thought 2.0s · spoke 0.5s", MiaClient.describeTimings(JSONObject("""{"thinking": 2, "speaking": 0.5}""")))
        assertEquals("", MiaClient.describeTimings(null))
    }
}
