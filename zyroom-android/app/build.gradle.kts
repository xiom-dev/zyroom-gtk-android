import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Le magasin de clés reste hors dépôt : sans lui on construit quand même, mais
// l'APK n'est pas signé pour la distribution.
val signature = Properties().apply {
    val fichier = rootProject.file("keystore.properties")
    if (fichier.exists()) fichier.inputStream().use { load(it) }
}

android {
    namespace = "net.ryzom.zyroom"
    compileSdk = 35

    defaultConfig {
        applicationId = "net.ryzom.zyroom"
        // Android 8 : ce que fait tourner à peu près tout téléphone encore vivant.
        minSdk = 26
        targetSdk = 35
        // versionCode doit croître à CHAQUE livraison : c'est le seul numéro
        // qu'Android ordonne, et celui que la vérification de mise à jour
        // compare. versionName n'est là que pour l'affichage.
        versionCode = 2
        versionName = "0.3"
    }

    signingConfigs {
        if (signature.containsKey("storeFile")) {
            create("guilde") {
                storeFile = rootProject.file(signature.getProperty("storeFile"))
                storePassword = signature.getProperty("storePassword")
                keyAlias = signature.getProperty("keyAlias")
                keyPassword = signature.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("guilde")
        }
    }

    // Deux applications à partir du même code, comme les deux bundles Flatpak :
    // celle qu'on donne à la guilde masque le contenu du petit coffre, celle du
    // mainteneur montre tout. L'identifiant diffère, donc elles s'installent
    // côte à côte sur le même téléphone.
    flavorDimensions += "diffusion"
    productFlavors {
        create("guilde") {
            dimension = "diffusion"
        }
        create("dev") {
            dimension = "diffusion"
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-dev"
            // Le nom du lanceur est dans src/dev/res/ : une ressource de
            // variante remplace celle de src/main, là où un resValue() entrerait
            // en conflit avec elle.
            // Ce qui sépare les deux variantes est `MASQUE_COFFRES`, déclaré une
            // fois par variante dans src/<variante>/kotlin/. On aurait pu passer
            // par BuildConfig, mais l'activer fait générer du Java, donc appelle
            // javac, qui réclame ici un jlink absent du JDK installé.
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    sourceSets {
        getByName("main").java.srcDirs("src/main/kotlin")
        getByName("test").java.srcDirs("src/test/kotlin")
        getByName("guilde").java.srcDirs("src/guilde/kotlin")
        getByName("dev").java.srcDirs("src/dev/kotlin")
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.09.02")
    implementation(composeBom)
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    // FileProvider, pour présenter l'APK de mise à jour au système.
    implementation("androidx.core:core-ktx:1.13.1")
    // Rafraîchissement en arrière-plan : quinze minutes est le plancher.
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    // Icônes d'items : téléchargement et cache disque.
    implementation("io.coil-kt:coil-compose:2.7.0")

    testImplementation("junit:junit:4.13.2")
    // org.json n'est qu'un squelette dans l'android.jar des tests unitaires :
    // sans une vraie implémentation, le moindre appel lève « not mocked ».
    testImplementation("org.json:json:20240303")
}
