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

// Les numéros de version, eux, sont dans le dépôt : c'est `livraison.sh` qui
// les fait croître, et lui seul, pour que l'APK construit et le version.json
// que les téléphones interrogent ne puissent pas divorcer.
val versions = Properties().apply {
    val fichier = rootProject.file("version.properties")
    if (!fichier.exists()) error("version.properties manquant à la racine du projet Android")
    fichier.inputStream().use { load(it) }
}

fun codeDe(variante: String): Int =
    versions.getProperty("$variante.versionCode")?.trim()?.toIntOrNull()
        ?: error("$variante.versionCode absent ou illisible dans version.properties")

fun nomDe(variante: String): String =
    versions.getProperty("$variante.versionName")?.trim()
        ?: error("$variante.versionName absent de version.properties")

android {
    namespace = "net.ryzom.zyroom"
    compileSdk = 35

    defaultConfig {
        applicationId = "net.ryzom.zyroom"
        // Android 8 : ce que fait tourner à peu près tout téléphone encore vivant.
        minSdk = 26
        targetSdk = 35
        // Numéros de la variante des joueurs ; la variante dev surcharge plus
        // bas. Voir version.properties pour la règle qui les gouverne.
        versionCode = codeDe("guilde")
        versionName = nomDe("guilde")
        // Nom au lanceur. Celui des joueurs reste nu : ils n'ont pas à lire un
        // numéro pour lancer leur application, et le bandeau de mise à jour le
        // leur dit quand il compte.
        manifestPlaceholders["appLabel"] = "ZyRoom"
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
            // La variante dev avance plus vite que celle de la guilde : elle a
            // son propre numéro, sans quoi publier un essai obligerait à faire
            // croître aussi celui que reçoivent les joueurs.
            versionCode = codeDe("dev")
            versionName = nomDe("dev")
            // Le nom du lanceur porte le numéro : sur un téléphone où les deux
            // applications sont installées, c'est le seul endroit qui dise du
            // premier coup d'œil quelle version d'essai est en place. Il se
            // déduit de version.properties, donc il suit tout seul — un nom
            // écrit à la main aurait été un troisième endroit à tenir d'accord,
            // et il serait faux au premier oubli. Passe par le manifeste et non
            // par une ressource : une ressource de variante et un resValue()
            // sur le même nom entrent en conflit.
            manifestPlaceholders["appLabel"] = "ZyRoom (dev) ${nomDe("dev")}"
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
