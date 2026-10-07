package com.mia.phone

import android.content.Context
import java.io.File
import java.util.zip.ZipInputStream

/**
 * Puts MIA's files (assets/mia.zip: core/, server/, web/, the defaults)
 * in the app's private storage, where her data folder (data/, config/)
 * can sit beside them as on a computer. A new app version replaces only
 * the code and the shipped defaults; the person's data stays.
 */
object Unpack {
    private val CODE = listOf("core", "server", "modules", "web")
    private val SHIPPED = listOf("config/default_config.json", "data/mission_pathways.json", "data/skill_definitions.json")

    fun ensure(context: Context): File {
        val root = File(context.filesDir, "mia")
        val stamp = File(root, ".bundle")
        if (stamp.exists() && stamp.readText() == BuildConfig.MIA_BUNDLE) return root
        root.mkdirs()
        CODE.forEach { File(root, it).deleteRecursively() }
        SHIPPED.forEach { File(root, it).delete() }
        context.assets.open("mia.zip").use { raw ->
            ZipInputStream(raw).use { zip ->
                var entry = zip.nextEntry
                while (entry != null) {
                    val out = File(root, entry.name)
                    require(out.canonicalPath.startsWith(root.canonicalPath)) { "Bad path in bundle: ${entry.name}" }
                    if (entry.isDirectory) out.mkdirs() else {
                        out.parentFile?.mkdirs()
                        out.outputStream().use { zip.copyTo(it) }
                    }
                    entry = zip.nextEntry
                }
            }
        }
        File(root, "data").mkdirs()
        stamp.writeText(BuildConfig.MIA_BUNDLE)
        return root
    }
}
