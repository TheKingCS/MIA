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

val miaRoot: File = rootProject.projectDir.parentFile
val miaAssets = layout.buildDirectory.dir("mia-assets")

val bundleMia by tasks.registering(Zip::class) {
    archiveFileName.set("mia.zip")
    destinationDirectory.set(miaAssets)
    from(miaRoot) {
        include(
            "core/**/*.py", "server/**", "modules/__init__.py", "modules/module_base.py", "web/**",
            "config/default_config.json", "data/mission_pathways.json", "data/skill_definitions.json",
        )
        exclude("**/__pycache__/**")
    }
}

android {
    namespace = "com.mia.phone"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mia.phone"
        minSdk = 26
        targetSdk = 34
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = "0.0.${System.getenv("GITHUB_RUN_NUMBER") ?: "0"}-spike"
        // Phones (arm64) and the CI emulator (x86_64).
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
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

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
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
        }
    }
}
