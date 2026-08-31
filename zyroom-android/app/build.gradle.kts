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
        manifestPlaceholders["appLabel"] = "V-RyLune"
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

    // Deux applications à partir du même code. Ce qui les sépare tient dans
    // `src/<variante>/kotlin/Diffusion.kt` : le masque du petit coffre, et la
    // faculté de se mettre à jour soi-même. On aurait pu passer par
    // BuildConfig, mais l'activer fait générer du Java, donc appelle javac, qui
    // réclame ici un jlink absent du JDK installé.
    //
    //   guilde  distribuée par la page GitHub, masque le coffre
    //   dev     la même, mais montre tout ; identifiant distinct, donc les deux
    //           s'installent côte à côte sur le même téléphone
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
            manifestPlaceholders["appLabel"] = "V-RyLune (dev) ${nomDe("dev")}"
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

        // Le `string_client.pack` du jeu -- deux megaoctets et demi de donnees
        // de Ryzom -- vit dans les deux variantes, celles qu'on distribue
        // soi-meme. Sa licence n'est pas etablie : une logitheque le
        // refuserait, et l'application sait de toute facon l'importer depuis
        // l'installation du joueur.
        //
        // Un repertoire partage plutot qu'une copie par variante : le fichier
        // est binaire, et un depot git garde chaque copie pour toujours.
        getByName("guilde").assets.srcDir("src/packAssets")
        getByName("dev").assets.srcDir("src/packAssets")

        // Les symboles des familles de matières — coquille, goutte, boucle —
        // sont eux aussi des images du jeu, reprises de Ryzom Armory : même
        // règle que le pack, et donc même partage. `src/packKotlin` porte le
        // code qui les nomme, car une ressource absente ne se compile pas :
        // une variante qui ne les embarquerait pas aurait besoin de sa propre
        // version, qui ne rend aucun symbole.
        getByName("guilde").res.srcDir("src/packRes")
        getByName("dev").res.srcDir("src/packRes")
        getByName("guilde").java.srcDir("src/packKotlin")
        getByName("dev").java.srcDir("src/packKotlin")
        // Les essais de ce qui n'existe que là : un test qui nomme la carte ne
        // se compile pas dans la variante qui ne l'embarque pas.
        getByName("testGuilde").java.srcDir("src/packTestKotlin")
        getByName("testDev").java.srcDir("src/packTestKotlin")
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.09.02")
    implementation(composeBom)
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    // Le cycle de vie côté Compose : c'est là que vit désormais
    // LocalLifecycleOwner, dont l'écran d'accueil se sert pour interroger les
    // mises à jour à chaque retour au premier plan.
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    // FileProvider, pour présenter l'APK de mise à jour au système.
    implementation("androidx.core:core-ktx:1.13.1")
    // Pas de WorkManager : il avait été ajouté pour un rafraîchissement en
    // arrière-plan qui n'a jamais été écrit, et il apportait à lui seul cinq
    // permissions — service au premier plan, démarrage du téléphone, réveil du
    // processeur — qu'un joueur voit dans la liste avant d'installer. Le jour
    // où le rafraîchissement viendra, la dépendance reviendra avec lui.
    //
    // Icônes d'items : téléchargement et cache disque.
    implementation("io.coil-kt:coil-compose:2.7.0")

    testImplementation("junit:junit:4.13.2")
    // org.json n'est qu'un squelette dans l'android.jar des tests unitaires :
    // sans une vraie implémentation, le moindre appel lève « not mocked ».
    testImplementation("org.json:json:20240303")
}
