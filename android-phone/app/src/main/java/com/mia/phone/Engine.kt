package com.mia.phone

import android.content.Context
import android.os.SystemClock
import android.util.Log
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject

/**
 * MIA's engine and server inside this app (mia_phone.py), started once per
 * app process. Its own object, not MainActivity's, so the listening service
 * (ListenService) can start MIA by itself when the glasses are tapped and
 * the app isn't open: Android may have closed the screen, or the whole app,
 * since MIA last ran.
 */
object Engine {
    private val lock = Any()
    @Volatile var started: JSONObject? = null
        private set

    /** The session token, once MIA is up ("" when nobody is signed in yet). */
    fun token(): String = started?.optString("token").orEmpty()

    /** Starts MIA if she isn't running; returns her start answer. Blocks: call off the main thread.
     *  Android can recreate a screen while MIA is still starting (rotating the
     *  phone, the system), so a second caller waits for the first instead of
     *  starting Python twice. */
    fun ensure(context: Context, lastExit: String = ""): JSONObject = synchronized(lock) {
        started ?: run {
            val app = context.applicationContext
            val t0 = SystemClock.elapsedRealtime()
            val root = Unpack.ensure(app)
            val t1 = SystemClock.elapsedRealtime()
            if (!Python.isStarted()) Python.start(AndroidPlatform(app))
            val t2 = SystemClock.elapsedRealtime()
            val answer = JSONObject(Python.getInstance().getModule("mia_phone")
                .callAttr("start", root.absolutePath, MainActivity.PORT, app.applicationInfo.nativeLibraryDir, lastExit).toString())
            val t3 = SystemClock.elapsedRealtime()
            Log.i(MainActivity.TAG, "ready unpack_ms=${t1 - t0} python_ms=${t2 - t1} engine_ms=${answer.optInt("engine_ms")} " +
                "server_ms=${answer.optInt("server_ms")} total_ms=${t3 - t0} python=${answer.optString("python")}")
            answer.also { started = it }
        }
    }
}
