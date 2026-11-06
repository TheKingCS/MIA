import java.util.Properties

// MIA on the phone (DEC-0019, the Phase 1 spike): MIA's own engine and
// screens running inside this app, no computer needed. The engine is the
// repo's Python (core/, server/), unchanged; the screens are web/,
// unchanged. Both are packed into mia.zip at build time (bundleMia below)
// and unpacked into the app's private storage on first start (Unpack.kt),
// so MIA's data folder sits beside its code just as it does on a computer.
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

// Meta's toolkit (DEC-0059): the app's id and token stay out of git, in
// local.properties here, or the environment on the build machine.
val metaKeys = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}
fun metaKey(name: String): String = metaKeys.getProperty(name) ?: System.getenv(name.uppercase()) ?: "0"

val miaRoot: File = rootProject.projectDir.parentFile
val miaAssets = layout.buildDirectory.dir("mia-assets")

val bundleMia by tasks.registering(Zip::class) {
    archiveFileName.set("mia.zip")
    destinationDirectory.set(miaAssets)
    from(miaRoot) {
        include(
            "core/**/*.py", "server/**", "modules/__init__.py", "modules/module_base.py", "web/**",
            "config/default_config.json", "data/mission_pathways.json", "data/skill_definitions.json",
            "data/model_bench_cases.json", "data/foods.tsv",
        )
        exclude("**/__pycache__/**")
    }
}

android {
    namespace = "com.mia.phone"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.mia.phone"
        minSdk = 29
        targetSdk = 34
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = "0.0.${System.getenv("GITHUB_RUN_NUMBER") ?: "0"}-spike"
        // Phones (arm64) and the CI emulator (x86_64).
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
        manifestPlaceholders["mwdat_application_id"] = metaKey("mwdat_application_id")
        manifestPlaceholders["mwdat_client_token"] = metaKey("mwdat_client_token")
        // A new bundle of MIA's files on every build, so an update unpacks it.
        buildConfigField("String", "MIA_BUNDLE", "\"${System.currentTimeMillis()}\"")
    }
    buildFeatures { buildConfig = true }

    sourceSets["main"].assets.srcDir(miaAssets)

    signingConfigs {
        // The companion app's fixed key, so a new build installs over the last.
        create("mia") {
            storeFile = file("../../android/mia-companion.keystore")
            storePassword = "mia-companion"
            keyAlias = "mia"
            keyPassword = "mia-companion"
        }
    }
    buildTypes {
        getByName("debug") { signingConfig = signingConfigs.getByName("mia") }
    }

    // llama.cpp's server (build_llama_server.sh) is a program, not a
    // library: unpacked onto the phone so MIA can start it.
    packaging { jniLibs { useLegacyPackaging = true } }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    // Meta's Device Access Toolkit: MIA on the glasses (DEC-0059).
    implementation("com.meta.wearable:mwdat-core:1.0.1")
    implementation("com.meta.wearable:mwdat-display:1.0.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")  // the sealed relay (DEC-0062)
    implementation("androidx.core:core:1.16.0")  // FileProvider, for Look's camera (already pulled in by mwdat)
}

tasks.named("preBuild") { dependsOn(bundleMia) }

chaquopy {
    defaultConfig {
        // The version CPython supports on both Android and iOS (PEP 738,
        // PEP 730): Zac moves to an iPhone later (DEC-0019).
        version = "3.13"
        pip {
            // Everything MIA's engine and server need on a phone
            // (tests/test_phone_ready.py checks nothing desktop-only sneaks in).
            // pydantic 2's core is Rust with no Android build yet; pydantic 1
            // is pure Python, and FastAPI before 0.100 runs on it. MIA's
            // server works on both (the desktop keeps the newest).
            install("fastapi<0.100")
            install("pydantic<2")
            install("uvicorn")
            install("cryptography")
            install("astral")
            install("mutagen")
            install("certifi") // HTTPS for downloading a model (core/local_model.py)
        }
    }
}
