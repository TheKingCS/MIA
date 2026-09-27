package com.mia.companion

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Where the app keeps its sign-in.
 *
 * MIA's server keeps sessions in memory, so every restart of MIA at home
 * ends them. A hands-free app that silently stops working after a reboot
 * is worse than useless, so the app remembers the password and signs in
 * again by itself when the server says the session is gone (HTTP 401).
 *
 * The password is encrypted with an AES-GCM key that lives in the
 * Android Keystore: the key never leaves the phone's secure hardware and
 * can't be copied out with the app's files. Server URL and name are not
 * secret and sit in plain preferences.
 */
class CredentialStore(context: Context) {
    private val prefs = context.getSharedPreferences("mia_companion", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString("server_url", "") ?: ""
        set(value) = prefs.edit().putString("server_url", value).apply()

    var name: String
        get() = prefs.getString("name", "") ?: ""
        set(value) = prefs.edit().putString("name", value).apply()

    var token: String?
        get() = prefs.getString("token", null)
        set(value) = prefs.edit().putString("token", value).apply()

    /** Whether to take the mic from a connected Bluetooth headset. */
    var useBluetoothMic: Boolean
        get() = prefs.getBoolean("bluetooth_mic", false)
        set(value) = prefs.edit().putBoolean("bluetooth_mic", value).apply()

    val hasSignIn: Boolean get() = serverUrl.isNotBlank() && name.isNotBlank() && prefs.contains("password")

    fun savePassword(password: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(password.toByteArray(Charsets.UTF_8))
        prefs.edit()
            .putString("password", Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .putString("password_iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .apply()
    }

    fun password(): String? {
        val encrypted = prefs.getString("password", null) ?: return null
        val iv = prefs.getString("password_iv", null) ?: return null
        return try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(encrypted, Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (e: Exception) {
            null // key lost (e.g. restored to a new phone): sign in again
        }
    }

    fun signOut() {
        prefs.edit().remove("password").remove("password_iv").remove("token").apply()
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "mia_companion_password"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
