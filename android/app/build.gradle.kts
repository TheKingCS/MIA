plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.mia.companion"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mia.companion"
        minSdk = 26
        targetSdk = 34
        // Each CI build counts up, so a new APK installs over the old one.
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = "0.1.${System.getenv("GITHUB_RUN_NUMBER") ?: "0"}"
    }

    signingConfigs {
        // One fixed key for this personal, sideloaded app (see android/README.md):
        // Android only installs an update signed with the same key as the
        // installed app, and CI would otherwise make a new key every run.
        create("mia") {
            storeFile = file("../mia-companion.keystore")
            storePassword = "mia-companion"
            keyAlias = "mia"
            keyPassword = "mia-companion"
        }
    }

    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("mia")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    // Real org.json for JVM unit tests (android.jar's copy is only stubs).
    testImplementation("org.json:json:20240303")
}
