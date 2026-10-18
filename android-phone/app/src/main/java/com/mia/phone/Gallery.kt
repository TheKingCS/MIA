package com.mia.phone

import android.Manifest
import android.content.ContentUris
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.BaseColumns
import android.provider.MediaStore
import android.webkit.JavascriptInterface
import org.json.JSONArray

/**
 * The memory vault's door to the camera roll (DEC-0030 E, core/memory_vault.py),
 * for MIA's own screens as window.MIAAndroid. MIA's engine reads the photos
 * itself once Android allows it; this only asks for that permission, and,
 * when the person chooses to free space, hands the exact files to Android's
 * own Trash dialog (Android asks them; the Trash keeps them 30 days).
 * MIA never deletes anything itself.
 */
class Gallery(private val activity: MainActivity) {

    private fun granted(permission: String) =
        activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED

    /** "granted", "partial" (Android 14: only the photos picked), or "needed". */
    @JavascriptInterface
    fun galleryAccess(): String = when {
        Build.VERSION.SDK_INT >= 33 ->
            if (granted(Manifest.permission.READ_MEDIA_IMAGES)) "granted"
            else if (Build.VERSION.SDK_INT >= 34 && granted(Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED)) "partial"
            else "needed"
        else -> if (granted(Manifest.permission.READ_EXTERNAL_STORAGE)) "granted" else "needed"
    }

    @JavascriptInterface
    fun askGallery() {
        val wanted = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= 33) {
            wanted += Manifest.permission.READ_MEDIA_IMAGES
            wanted += Manifest.permission.READ_MEDIA_VIDEO
            if (Build.VERSION.SDK_INT >= 34) wanted += Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED
        } else {
            wanted += Manifest.permission.READ_EXTERNAL_STORAGE
        }
        // Where a photo was taken is inside it; Android hides that without this.
        if (Build.VERSION.SDK_INT >= 29) wanted += Manifest.permission.ACCESS_MEDIA_LOCATION
        activity.runOnUiThread { activity.requestPermissions(wanted.toTypedArray(), GALLERY_REQUEST) }
    }

    /** Android's Trash dialog exists from Android 11. */
    @JavascriptInterface
    fun canTrash(): Boolean = Build.VERSION.SDK_INT >= 30

    /** Ask Android to move these files (a JSON list of paths) to its Trash. */
    @JavascriptInterface
    fun trash(pathsJson: String) {
        if (Build.VERSION.SDK_INT < 30) { done(false); return }
        val list = JSONArray(pathsJson)
        val paths = (0 until list.length()).map { list.getString(it) }
        val uris = mutableListOf<Uri>()
        val collections = listOf(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, MediaStore.Video.Media.EXTERNAL_CONTENT_URI)
        for (collection in collections) {
            for (chunk in paths.chunked(200)) {
                @Suppress("DEPRECATION")
                val where = MediaStore.MediaColumns.DATA + " IN (" + chunk.joinToString(",") { "?" } + ")"
                activity.contentResolver.query(collection, arrayOf(BaseColumns._ID), where, chunk.toTypedArray(), null)?.use { c ->
                    while (c.moveToNext()) uris += ContentUris.withAppendedId(collection, c.getLong(0))
                }
            }
        }
        if (uris.isEmpty()) { done(false); return }
        val ask = MediaStore.createTrashRequest(activity.contentResolver, uris, true)
        activity.runOnUiThread {
            try {
                activity.startIntentSenderForResult(ask.intentSender, TRASH_REQUEST, null, 0, 0, 0)
            } catch (e: Exception) {
                done(false)
            }
        }
    }

    /** Tell the screen how Android's dialog ended. */
    fun done(ok: Boolean) = answer("onTrashed", ok.toString())

    fun accessChanged() = answer("onAccess", "\"" + galleryAccess() + "\"")

    private fun answer(name: String, value: String) {
        activity.runOnUiThread {
            activity.webView()?.evaluateJavascript("window.MIAGallery && MIAGallery.$name($value)", null)
        }
    }

    companion object {
        const val GALLERY_REQUEST = 42
        const val TRASH_REQUEST = 43
    }
}
