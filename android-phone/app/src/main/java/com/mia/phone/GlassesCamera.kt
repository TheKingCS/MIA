package com.mia.phone

import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import com.meta.wearable.dat.camera.Camera
import com.meta.wearable.dat.camera.addCamera
import com.meta.wearable.dat.camera.types.PhotoData
import com.meta.wearable.dat.camera.types.StreamConfiguration
import com.meta.wearable.dat.camera.types.StreamState
import com.meta.wearable.dat.camera.types.VideoQuality
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.Permission
import com.meta.wearable.dat.core.types.PermissionStatus
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import java.io.ByteArrayOutputStream

/**
 * One photo through the glasses' own camera, for Sight's "what am I looking at?" (core/sight.py; the parity gap
 * sight:glasses). DEC-0062 keeps whatever needs Meta's toolkit in this app, so a look opens a camera-only session on
 * the glasses, takes a single still through the camera stream (the toolkit's capture rides the stream), and closes it
 * all again: the camera is on only for that moment, and the photo goes to MIA on this phone (/api/sight), never kept.
 *
 * The toolkit's camera permission is granted in the Meta AI app; [askPermission] opens that request from MIA's
 * Settings. Without it, or without glasses in reach, [photo] says why in words instead.
 */
object GlassesCamera {
    private const val TAG = "GlassesCamera"
    private const val SESSION_MS = 15_000L
    private const val STREAM_MS = 10_000L
    private const val PHOTO_MS = 12_000L
    const val PERMISSION_REQUEST = 7311

    /** A photo, or why there isn't one. */
    class Result(val jpeg: ByteArray?, val why: String = "")

    /** Opens the Meta AI app's request for the glasses' camera (the result is read again at the next look). */
    fun askPermission(activity: Activity) {
        try {
            Wearables.initialize(activity.applicationContext)
            val intent = Wearables.RequestPermissionContract().createIntent(activity, Permission.CAMERA)
            activity.startActivityForResult(intent, PERMISSION_REQUEST)
        } catch (e: Exception) {
            Log.w(TAG, "Couldn't ask for the glasses' camera", e)
        }
    }

    /** Takes one photo through the glasses. Blocks for up to about half a minute: call it off the main thread. */
    fun photo(context: Context): Result = runBlocking {
        try {
            Wearables.initialize(context.applicationContext)
        } catch (e: Exception) {
            Log.d(TAG, "toolkit already set up", e)
        }
        val allowed = Wearables.checkPermissionStatus(Permission.CAMERA).fold(
            onSuccess = { status -> status == PermissionStatus.Granted },
            onFailure = { error, _ -> Log.w(TAG, "camera permission unreadable: ${error.description}"); false },
        )
        if (!allowed) {
            return@runBlocking Result(null, "I can't use the glasses' camera yet. In MIA's Settings, under Glasses, " +
                "tap Let MIA Use the Glasses' Camera.")
        }
        var session: DeviceSession? = null
        Wearables.createSession(AutoDeviceSelector()).fold(
            onSuccess = { opened -> session = opened },
            onFailure = { error, _ -> Log.w(TAG, "no session: ${error.description}") },
        )
        val opened = session ?: return@runBlocking Result(null, "I can't reach the glasses right now.")
        try {
            opened.start()
            val started = withTimeoutOrNull(SESSION_MS) { opened.state.first { it == DeviceSessionState.STARTED } }
            if (started == null) return@runBlocking Result(null, "The glasses didn't answer in time.")
            var bytes: ByteArray? = null
            var why = "The glasses' camera didn't start."
            var camera: Camera? = null
            opened.addCamera(StreamConfiguration(videoQuality = VideoQuality.LOW, frameRate = 7, compressVideo = true)).fold(
                onSuccess = { added -> camera = added },
                onFailure = { error, _ -> Log.w(TAG, "camera: ${error.description}") },
            )
            camera?.let { cam ->
                try {
                    val stream = cam.stream
                    stream.start().onFailure { error, _ -> Log.w(TAG, "stream: ${error.description}") }
                    val streaming = withTimeoutOrNull(STREAM_MS) { stream.state.first { it == StreamState.STREAMING } }
                    if (streaming != null) {
                        val result = withTimeoutOrNull(PHOTO_MS) { stream.capturePhoto() }
                        if (result == null) why = "The photo took too long to come through."
                        else result.fold(
                            onSuccess = { data -> bytes = jpegOf(data) },
                            onFailure = { error, _ -> why = "The photo didn't come through (${error.description})." },
                        )
                    }
                } finally {
                    cam.close()
                }
            }
            Result(bytes, if (bytes == null) why else "")
        } finally {
            opened.stop()
        }
    }

    /** The photo as JPEG bytes (a decoded image is compressed; one that came encoded is converted the same way). */
    private fun jpegOf(data: PhotoData): ByteArray? = when (data) {
        is PhotoData.Bitmap -> ByteArrayOutputStream().also { data.bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }.toByteArray()
        is PhotoData.HEIC -> {
            val buffer = data.data.asReadOnlyBuffer().also { it.rewind() }
            val raw = ByteArray(buffer.remaining()).also { buffer.get(it) }
            android.graphics.BitmapFactory.decodeByteArray(raw, 0, raw.size)?.let { bitmap ->
                ByteArrayOutputStream().also { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }.toByteArray()
            }
        }
    }
}
