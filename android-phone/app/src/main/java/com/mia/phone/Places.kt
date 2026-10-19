package com.mia.phone

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.util.Log
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject

/**
 * Location quests while MIA is closed (DEC-0028 #13; Zac, 2026-10-19).
 * MIA's screens hand the places the person watches to Android
 * (window.MIAPhonePlaces.watch, from web/places-watch.js); Android's own
 * proximity alerts then wake MIA when the phone arrives at one, even with
 * MIA closed, and a notification asks ("📍 You're at Gym. Your workout's
 * ready."). Tapping it records the arrival and opens the place's screen
 * (index.html?arrive=<id>). Where you are stays on this phone: Android
 * compares it, MIA never stores or sends it. Once per place per six hours,
 * and not while MIA is on screen (its own watch asks then).
 */
object Places {
    private const val PREFS = "mia_places"
    private const val CHANNEL = "places"
    private const val QUIET_MS = 6 * 3600 * 1000L
    @Volatile var onScreen = false  // MainActivity is showing: web/places-watch.js asks itself

    fun watch(context: Context, placesJson: String) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        // Every screen hands them over; set the alerts again only when they changed.
        if (prefs.getString("places", null) == placesJson && (prefs.getInt("registered", 0) > 0) == allowed(context)) return
        prefs.edit().putString("places", placesJson).apply()
        register(context)
    }

    private fun list(context: Context): JSONArray = try {
        JSONArray(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("places", "[]"))
    } catch (e: Exception) {
        JSONArray()
    }

    private fun alert(context: Context, index: Int, id: String): PendingIntent =
        PendingIntent.getBroadcast(context, 1000 + index,
            Intent(context, PlaceReceiver::class.java).putExtra("id", id),  // matched by its number, so it can be removed
            PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0))

    /** (Re)set Android's alerts for the watched places: on a change, after a restart. */
    @SuppressLint("MissingPermission")
    fun register(context: Context) {
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        for (i in 0 until prefs.getInt("registered", 0)) {
            manager.removeProximityAlert(alert(context, i, ""))
        }
        val places = list(context)
        if (!allowed(context)) { prefs.edit().putInt("registered", 0).apply(); return }
        var n = 0
        for (i in 0 until places.length()) {
            val p = places.getJSONObject(i)
            try {
                manager.addProximityAlert(p.getDouble("lat"), p.getDouble("lon"), p.optDouble("radius", 150.0).toFloat(),
                    -1, alert(context, i, p.getString("id")))
                n = i + 1
            } catch (e: Exception) {
                Log.w(MainActivity.TAG, "place alert", e)
            }
        }
        prefs.edit().putInt("registered", n).apply()
    }

    fun allowed(context: Context): Boolean {
        val fine = context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val background = Build.VERSION.SDK_INT < 29 ||
            context.checkSelfPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED
        return fine && background
    }

    /** Arrived (Android's alert): ask with a notification, once per place per six hours. */
    fun arrived(context: Context, id: String) {
        if (onScreen) return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (now - prefs.getLong("at.$id", 0) < QUIET_MS) return
        val all = list(context)
        val place = (0 until all.length()).map { all.getJSONObject(it) }.firstOrNull { it.optString("id") == id } ?: return
        prefs.edit().putLong("at.$id", now).apply()
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(NotificationChannel(CHANNEL, "Location quests", NotificationManager.IMPORTANCE_DEFAULT))
        }
        val open = Intent(context, MainActivity::class.java).setAction("com.mia.phone.ARRIVE").setData(Uri.parse("mia-place:$id"))
            .putExtra("arrive", id).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val tap = PendingIntent.getActivity(context, id.hashCode(), open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val say = place.optString("say", "📍 You're at ${place.optString("name")}.")
        @Suppress("DEPRECATION")
        val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(context, CHANNEL) else Notification.Builder(context)
        val note = builder.setSmallIcon(android.R.drawable.ic_dialog_map)
            .setContentTitle("📍 " + place.optString("name"))
            .setContentText(say.replace(Regex("^📍 You're at [^.]*\\.\\s*"), "").ifBlank { say })
            .setContentIntent(tap)
            .setAutoCancel(true)
            .build()
        try {
            manager.notify(id.hashCode(), note)
        } catch (e: SecurityException) {
            Log.w(MainActivity.TAG, "no notification permission", e)
        }
    }
}

/** Android's proximity alert for a place. */
class PlaceReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (!intent.getBooleanExtra(LocationManager.KEY_PROXIMITY_ENTERING, false)) return
        Places.arrived(context, intent.getStringExtra("id") ?: return)
    }
}

/** After the phone restarts, Android has forgotten the alerts: set them again. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            Places.register(context)
        }
    }
}

/** MIA's screens' door to it: window.MIAPhonePlaces. */
class PlacesBridge(private val activity: MainActivity) {
    @JavascriptInterface
    fun watch(placesJson: String) = Places.watch(activity.applicationContext, placesJson)

    private fun has(permission: String) = activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    private fun notifies() = Build.VERSION.SDK_INT < 33 || has(Manifest.permission.POST_NOTIFICATIONS)

    /** "on" (alerts set and notifications allowed), "notify" (alerts set, notifications not
     *  allowed), "foreground" (location only while MIA is open), or "off". */
    @JavascriptInterface
    fun background(): String = when {
        Places.allowed(activity) -> if (notifies()) "on" else "notify"
        has(Manifest.permission.ACCESS_FINE_LOCATION) -> "foreground"
        else -> "off"
    }

    /** Ask Android for the next thing missing, one at a time (Android 11+
     *  refuses "all the time" asked together with anything else): location,
     *  then "Allow all the time" (its own settings page), then notifications. */
    @JavascriptInterface
    fun askBackground() {
        val wanted = when {
            !has(Manifest.permission.ACCESS_FINE_LOCATION) ->
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
            Build.VERSION.SDK_INT >= 29 && !has(Manifest.permission.ACCESS_BACKGROUND_LOCATION) ->
                arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
            !notifies() -> arrayOf(Manifest.permission.POST_NOTIFICATIONS)
            else -> { answered(); return }
        }
        activity.runOnUiThread { activity.requestPermissions(wanted, PLACES_REQUEST) }
    }

    fun answered() {
        Places.register(activity.applicationContext)
        activity.runOnUiThread {
            activity.webView()?.evaluateJavascript(
                "window.MIAPlaces && MIAPlaces.backgroundChanged && MIAPlaces.backgroundChanged(" +
                    JSONObject.quote(background()) + ")", null)
        }
    }

    companion object {
        const val PLACES_REQUEST = 45
    }
}
