import groovy.json.JsonSlurper
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Labyrinth Mobile's version lives in versions.json at the repo root, next to the others.
@Suppress("UNCHECKED_CAST")
val versions = JsonSlurper().parse(rootProject.file("../versions.json")) as Map<String, String>
val mobileVersion: String = versions.getValue("mobile")
val (major, minor, patch) = mobileVersion.split(".").map { it.toInt() }

// Release signing reads android/keystore.properties, which stays out of git. Without it,
// assembleRelease still builds, but the APK is unsigned.
val keystoreProperties = Properties().apply {
    val file = rootProject.file("keystore.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

android {
    namespace = "com.bydesigninteractive.labyrinth.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.bydesigninteractive.labyrinth.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = major * 10000 + minor * 100 + patch
        versionName = mobileVersion
    }

    signingConfigs {
        if (!keystoreProperties.isEmpty) {
            create("release") {
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            signingConfig = signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation(project(":core"))
    testImplementation("junit:junit:4.13.2")
}
