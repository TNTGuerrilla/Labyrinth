plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

// Code shared by Labyrinth TV (:app) and Labyrinth Mobile (:phone): the maze and game rules,
// the GL maze drawing, the updater and the game's settings store.
android {
    namespace = "com.bydesigninteractive.labyrinth.core"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
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
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
