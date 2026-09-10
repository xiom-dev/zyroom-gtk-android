"""Mise à jour de l'application depuis l'application elle-même.

**Rien de la version GTK ne se réutilise ici.** Là-bas, l'application est en
bac à sable et ne peut pas se mettre à jour : elle passe par le portail
Flatpak, en D-Bus, qui décide lui-même quand vérifier et sait installer après
confirmation du système. Ce portail n'existe ni hors bac à sable ni sous
Windows.

Le mécanisme retenu est celui du portage Android, qui a le même problème et le
résout depuis longtemps : un `version.json` publié sur la page de
téléchargement annonce le dernier numéro et l'adresse de l'archive. C'est un
fichier de quelques centaines d'octets ; on peut le demander au lancement et
tous les quarts d'heure sans peser sur rien.

**Le numéro comparé est un entier**, `versionCode`, jamais le nom : un nom se
compare mal — « 0.10 » vient après « 0.9 » pour nous, avant pour un tri de
chaînes — et c'est exactement la règle que suit déjà `version.json`.

## Comment le remplacement se fait

Un programme ne peut pas effacer le dossier depuis lequel il tourne : sous
Windows, ses fichiers ouverts sont verrouillés. Mais **renommer** ce dossier
est permis sur les deux systèmes, et c'est le tour de main qu'emploient les
navigateurs :

1. l'archive est téléchargée dans le cache, puis extraite à côté de
   l'installation ;
2. l'installation en place est **renommée**, pas effacée ;
3. la nouvelle prend son nom ;
4. l'ancienne est effacée au prochain lancement, quand plus rien ne la tient.

Si quoi que ce soit échoue en route, l'ancienne est remise à sa place : à
aucun moment il n'existe d'état où l'application aurait disparu.

**Rien ne se passe hors paquet.** Lancée depuis les sources, l'application n'a
pas d'installation à remplacer : le module se met en sommeil et le bouton
n'apparaît jamais — c'est `git pull` qui met à jour dans ce cas.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile

from . import __version_code__

#: Le manifeste publie, celui-la meme que lit l'application Android.
MANIFESTE = "https://xiom-dev.github.io/zyroom-gtk-android/version.json"

#: La cle qui nous designe dedans.
APPLICATION = "net.ryzom.zyroomqt"

#: Le suffixe de l'installation mise de cote, effacee au lancement suivant.
SUFFIXE_ANCIEN = ".ancien"
#: Le dossier ou la nouvelle version attend, sous Windows, que l'application
#: se ferme. Voir `installer`.
SUFFIXE_NOUVEAU = ".nouveau"

#: Les suffixes que nous ajoutons au dossier d'installation, et qu'il faut
#: donc savoir lui retirer.
SUFFIXES = (SUFFIXE_NOUVEAU, SUFFIXE_ANCIEN)

_USER_AGENT = "zyroom-qt (+https://github.com/xiom-dev/zyroom-gtk-android)"

#: Le drapeau de creation du relais, sous Windows : pas de fenetre, mais une
#: console valide.
#:
#: **Et surtout pas `DETACHED_PROCESS`.** Il y etait, et c'est lui qui a tenu
#: la mise a jour en panne depuis le premier jour. Un processus detache n'a
#: pas de console du tout, donc pas de poignees standard : la premiere ligne
#: de la boucle d'attente,
#:
#:     tasklist /fi "PID eq %ZY_PID%" | find "%ZY_PID%" || goto :libre
#:
#: est un tube, et un tube sans poignees valides ne se monte pas. `cmd`
#: abandonnait la, au premier tour, sans un mot. Les redirections vers un
#: fichier passaient -- c'est pourquoi le journal ecrivait sa premiere ligne
#: avant de se taire, ce qui a permis de le voir.
#:
#: Mesure sur la machine Windows de GitHub, journal a l'appui :
#:
#:     [debut] cible=... attente=... pid=6940
#:     [attente] tour 1
#:     (plus rien)
#:
#: `CREATE_NO_WINDOW` donne ce qu'on voulait vraiment -- aucune fenetre noire
#: qui clignote -- sans rien couper. Le relais survit de toute facon a notre
#: mort : sous Windows un enfant n'appartient pas a son parent.
CREATE_NO_WINDOW = 0x08000000

#: La raison du dernier echec du relais, pour que l'ecran puisse la dire.
derniere_erreur = ""


def empaquete() -> bool:
    """Vrai si l'on tourne depuis un paquet et non depuis les sources."""
    return bool(getattr(sys, "frozen", False))


def dossier_installe() -> str:
    """Le dossier de l'installation, ou une chaîne vide hors paquet.

    PyInstaller pose l'exécutable à la racine du dossier distribué ; c'est
    celui-là qu'on remplacera.
    """
    if not empaquete():
        return ""
    return os.path.dirname(os.path.abspath(sys.executable))


def dossier_canonique(dossier: str = "") -> str:
    """Le dossier d'installation debarrasse de nos suffixes.

    **Sans lui, les suffixes s'empilent.** Un joueur s'est retrouve avec
    `ZyRoom-Qt`, `ZyRoom-Qt.nouveau` et `ZyRoom-Qt.nouveau.nouveau` : la mise
    en place ne s'etait pas faite, il avait lance l'application depuis le
    dossier depose a cote -- ce qui est la chose la plus naturelle du monde
    quand on voit apparaitre un dossier tout frais --, et la mise a jour
    suivante a colle un second suffixe au premier. Un dossier de plus a chaque
    fois, quarante megaoctets a chaque fois, et une application qui ne
    revenait jamais chez elle.

    On retire donc les suffixes en boucle : `.nouveau.nouveau` rend le meme
    dossier de base que `.nouveau`.
    """
    dossier = dossier or dossier_installe()
    encore = True
    while encore and dossier:
        encore = False
        for suffixe in SUFFIXES:
            if dossier.endswith(suffixe):
                dossier = dossier[: -len(suffixe)]
                encore = True
    return dossier


def hors_de_chez_soi() -> bool:
    """Vrai si l'on tourne depuis un dossier depose a cote, jamais mis en place.

    C'est l'etat du joueur dont la mise a jour n'avait pas abouti. Il n'y a
    rien a telecharger dans ce cas : il y a une mise en place a terminer.
    """
    dossier = dossier_installe()
    return bool(dossier) and dossier != dossier_canonique(dossier)


def nettoyer_ancienne() -> None:
    """Efface l'installation précédente, s'il en reste une.

    Appelée au démarrage : à ce moment plus rien ne la tient, et le nettoyage
    ne peut plus gêner personne. Un échec est sans conséquence — on réessaiera
    au prochain lancement.
    """
    dossier = dossier_canonique()
    if not dossier:
        return
    ancienne = dossier + SUFFIXE_ANCIEN
    # **Jamais le dossier d'ou l'on tourne.** Quelqu'un qui aurait lance
    # l'application depuis la mise de cote se serait vu effacer sous les
    # pieds : sous Unix les fichiers ouverts survivent, la fenetre reste la,
    # mais l'application a disparu du disque et le lancement suivant ne
    # trouve plus rien. Mesure sur une installation simulee.
    if os.path.isdir(ancienne) and ancienne != dossier_installe():
        shutil.rmtree(ancienne, ignore_errors=True)


class Veilleur:
    """Regarde ce que le manifeste publié annonce."""

    def __init__(self) -> None:
        self.version_publiee = ""
        self.url = ""

    @property
    def possible(self) -> bool:
        """Y a-t-il seulement une installation à mettre à jour ?"""
        return bool(dossier_installe())

    def mise_a_jour_disponible(self, timeout: int = 15) -> str:
        """Le nom de la version qui attend, ou une chaîne vide s'il n'y a rien.

        Une panne de réseau ne doit rien casser : sans réponse, on s'en tient à
        ce qu'on a, et on redemandera au prochain quart d'heure.
        """
        if not self.possible:
            return ""
        try:
            requete = urllib.request.Request(
                MANIFESTE, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(requete, timeout=timeout) as reponse:
                manifeste = json.loads(reponse.read(64_000).decode("utf-8"))
        except Exception:                               # noqa: BLE001
            return ""
        entree = manifeste.get(APPLICATION)
        if not isinstance(entree, dict):
            return ""                # le manifeste ne nous connait pas encore
        entree = _annonce_pour_ici(entree)
        try:
            code = int(entree.get("versionCode", 0))
        except (TypeError, ValueError):
            return ""
        if code <= __version_code__:
            return ""
        self.url = _url_pour_ici(entree)
        self.version_publiee = str(entree.get("versionName", code))
        # Sans archive pour ce systeme-la, on se tait : annoncer une version
        # qu'on ne saurait pas aller chercher ne servirait qu'a agacer.
        return self.version_publiee if self.url else ""


def cle_systeme() -> str:
    """« windows » ou « linux » : le nom du système sous lequel on tourne."""
    return "windows" if os.name == "nt" else "linux"


def _annonce_pour_ici(entree: dict) -> dict:
    """Le numéro qui vaut pour ce système-là, à défaut celui de la racine.

    **Un manifeste, deux paquets, et longtemps un seul numéro.** Les archives
    Linux et Windows ne se construisent pas au même endroit — celle de Windows
    sort d'une machine que le mainteneur n'a pas —, et rien n'oblige les deux à
    paraître ensemble. Or l'application comparait le numéro de la racine, celui
    du dernier paquet livré, quel que soit le système : sous Windows, elle se
    trouvait donc en retard, téléchargeait une archive plus ancienne que ce que
    la racine annonçait, s'installait, se retrouvait en retard, recommençait.
    Une boucle sans fin, et deux joueurs l'ont vécue.

    Le manifeste porte désormais, à côté, ce que chaque système a réellement en
    ligne. Les versions déjà installées ne connaissent pas ce bloc et
    continuent de lire la racine : elle reste donc écrite, et c'est pourquoi
    l'on ne peut pas se contenter de la remplacer.
    """
    systemes = entree.get("systemes")
    if isinstance(systemes, dict):
        propre = systemes.get(cle_systeme())
        if isinstance(propre, dict) and "versionCode" in propre:
            # L'adresse reste celle de la racine : elle ne change jamais.
            return dict(entree, **propre)
    return entree


def _url_pour_ici(entree: dict) -> str:
    """L'archive qui convient au système où l'on tourne.

    Le manifeste d'Android n'a qu'une `url` : un APK vaut pour tous les
    téléphones. Ici il en faut une par système — un bundle Linux ne se lance
    pas sous Windows. Le manifeste porte donc un objet `urls`, et l'on retombe
    sur `url` si jamais il n'en portait qu'une.
    """
    urls = entree.get("urls")
    if isinstance(urls, dict):
        cle = "windows" if os.name == "nt" else "linux"
        choisie = urls.get(cle)
        if choisie:
            return str(choisie)
        return ""
    return str(entree.get("url", ""))


def telecharger(url: str, avancement=None, timeout: int = 60) -> str:
    """Rapporte l'archive dans un fichier temporaire, et rend son chemin.

    `avancement(octets, total)` est appelé au fil de l'eau — depuis le fil de
    travail, à l'appelant de le ramener vers l'interface.
    """
    requete = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        total = int(reponse.headers.get("Content-Length") or 0)
        fichier = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        recu = 0
        try:
            while True:
                bloc = reponse.read(65_536)
                if not bloc:
                    break
                fichier.write(bloc)
                recu += len(bloc)
                if avancement is not None:
                    avancement(recu, total)
        finally:
            fichier.close()
    return fichier.name


def _extraire(archive: str, dossier: str) -> None:
    """Extrait l'archive **en rendant leurs droits aux fichiers**.

    `zipfile.extractall` ne restaure pas les permissions Unix : tout ressort en
    lecture seule, exécutable compris. Une mise à jour installée de la sorte
    donnerait un dossier complet et une application qui refuse de démarrer —
    vérifié, le bit `+x` disparaît bel et bien.

    Le format ZIP les garde pourtant, dans les seize bits hauts de
    `external_attr`, quand l'archive a été faite par un outil Unix. On les
    remet donc à la main. Une archive faite sous Windows n'en a pas : les
    fichiers gardent alors le mode par défaut, ce qui est sans conséquence
    là-bas puisque Windows ne s'en sert pas.
    """
    with zipfile.ZipFile(archive) as zip_:
        for membre in zip_.infolist():
            mode = membre.external_attr >> 16
            # **Les liens symboliques d'abord.** Qt en pose des dizaines --
            # libQt6Core.so.6 pointe sur libQt6Core.so.6.11.2 -- et le format
            # ZIP les garde, comme un fichier dont le contenu est la cible et
            # dont le mode porte S_IFLNK. `extract` les ecrit tels quels : des
            # fichiers de trente octets a la place de bibliotheques, et
            # l'application refuse de demarrer sur un "file too short".
            if stat.S_ISLNK(mode):
                cible = zip_.read(membre).decode("utf-8")
                lien = os.path.join(dossier, membre.filename)
                os.makedirs(os.path.dirname(lien), exist_ok=True)
                if os.path.lexists(lien):
                    os.unlink(lien)
                os.symlink(cible, lien)
                continue
            chemin = zip_.extract(membre, dossier)
            if mode:
                os.chmod(chemin, mode & 0o777)


def _racine_de_l_archive(dossier: str) -> str:
    """Le dossier utile de l'archive extraite.

    Nos archives portent un dossier unique — `ZyRoom-Qt/` — plutôt que d'y
    déverser leurs fichiers en vrac. On le traverse ; si l'archive était
    faite autrement, on prend le dossier d'extraction tel quel.
    """
    contenu = [nom for nom in os.listdir(dossier)
               if not nom.startswith(".")]
    if len(contenu) == 1:
        seul = os.path.join(dossier, contenu[0])
        if os.path.isdir(seul):
            return seul
    return dossier


#: Les lanceurs de la variante du chef de guilde. Ils ne sont dans aucune
#: archive publique -- c'est tout leur interet -- et une mise a jour les
#: emporterait donc avec l'ancien dossier.
LANCEURS_CHEF = ("ZyRoom-Qt-dev.bat", "ZyRoom-Qt-dev.sh")


def _reporter_lanceurs(ancien: str, neuf: str) -> None:
    """Fait passer les lanceurs du chef dans la nouvelle installation.

    Le manifeste n'annonce qu'une archive par systeme, la publique : c'est
    elle que le bouton telecharge, chef ou pas. Sans ce report, le chef
    perdait son lanceur a chaque mise a jour, et avec lui les coffres
    reserves -- sans le moindre message, ce qui est la pire facon de perdre
    quelque chose.
    """
    for nom in LANCEURS_CHEF:
        source = os.path.join(ancien, nom)
        if not os.path.isfile(source):
            continue
        try:
            shutil.copy2(source, os.path.join(neuf, nom))
            if os.name != "nt":
                os.chmod(os.path.join(neuf, nom), 0o755)
        except OSError:
            # Tant pis : mieux vaut une mise a jour sans le lanceur qu'une
            # mise a jour qui echoue. Il se recopie depuis l'archive du chef.
            pass


def installer(archive: str) -> tuple[bool, str]:
    """Met la nouvelle version à la place de l'ancienne.

    Rend `(réussi, message)`. En cas d'échec à n'importe quelle étape,
    l'installation d'origine est remise en place.

    **Les deux systèmes ne s'y prennent pas pareil.** Unix laisse renommer un
    dossier d'où tourne un programme : le processus garde ses fichiers ouverts
    par leur inode, le nom n'a plus d'importance une fois l'ouverture faite.
    Windows, lui, verrouille l'exécutable et les DLL chargées, et refuse de
    renommer le dossier qui les contient — c'est le `[WinError 32] Le processus
    ne peut pas accéder au fichier car ce fichier est utilisé par un autre
    processus` qu'a rencontré le premier joueur à mettre à jour depuis
    Windows. Là-bas, la nouvelle version est donc déposée à côté, sous
    `SUFFIXE_NOUVEAU`, et c'est `relancer` qui la met en place une fois
    l'application fermée.
    """
    cible = dossier_installe()
    if not cible:
        return False, "Aucune installation à remplacer."
    # **On ne met pas a jour depuis un dossier qui n'est pas le sien.** Sinon
    # le suffixe s'ajoute au suffixe : c'est ainsi qu'un joueur s'est retrouve
    # avec un `ZyRoom-Qt.nouveau.nouveau`. Il y a une mise en place a
    # terminer, et c'est elle qu'il faut proposer.
    #
    # **Windows seulement.** La-bas le redemarrage repare, puisque le relais
    # remet le dossier a sa place. Unix n'a pas de relais -- il n'en a pas
    # besoin, la permutation s'y fait tout de suite --, et refuser la mise a
    # jour y enfermerait le joueur dans un cul-de-sac : plus de mise a jour
    # possible, et rien pour le ramener chez lui. Mesure sur une installation
    # simulee : trois refus d'affilee, sans issue.
    if os.name == "nt" and hors_de_chez_soi():
        return False, ("Une mise à jour précédente n'a pas été mise en "
                       "place. Redémarrez l'application pour la terminer.")

    extraction = tempfile.mkdtemp(prefix="zyroom-qt-maj-")
    ancienne = cible + SUFFIXE_ANCIEN
    try:
        try:
            _extraire(archive, extraction)
        except (OSError, zipfile.BadZipFile) as exc:
            return False, f"Archive illisible : {exc}"

        neuve = _racine_de_l_archive(extraction)
        binaire = os.path.join(neuve, os.path.basename(sys.executable))
        if not os.path.isfile(binaire):
            return False, "L'archive ne contient pas l'application attendue."
        # Ceinture et bretelles : meme si l'archive ne portait aucun mode --
        # faite sous Windows, ou par un outil qui les oublie --, l'executable
        # doit pouvoir se lancer.
        if os.name != "nt" and not os.access(binaire, os.X_OK):
            os.chmod(binaire, 0o755)

        # Ce que l'archive publique ne contient pas et qu'il faut garder.
        _reporter_lanceurs(cible, neuve)

        if os.name == "nt":
            # Windows tient l'executable en cours : on ne touche a rien, on
            # depose. `relancer` fera le remplacement quand plus personne
            # n'aura le dossier en main.
            attente = dossier_canonique(cible) + SUFFIXE_NOUVEAU
            if os.path.isdir(attente):
                shutil.rmtree(attente, ignore_errors=True)
            shutil.move(neuve, attente)
            return True, ("Mise à jour prête. Elle se mettra en place à la "
                          "fermeture de l'application.")

        # Une precedente mise de cote qui trainerait empecherait le renommage.
        if os.path.isdir(ancienne):
            shutil.rmtree(ancienne, ignore_errors=True)

        # Le tour de main : renommer, jamais effacer. Le dossier d'ou l'on
        # tourne continue d'exister sous son nouveau nom, et les fichiers
        # ouverts restent valides.
        os.rename(cible, ancienne)
        try:
            shutil.move(neuve, cible)
        except OSError as exc:
            # Remise en place : a aucun moment l'application ne doit manquer.
            os.rename(ancienne, cible)
            return False, f"Installation impossible : {exc}"
    finally:
        shutil.rmtree(extraction, ignore_errors=True)
        try:
            os.unlink(archive)
        except OSError:
            pass
    return True, "Mise à jour installée."


def maj_en_attente() -> bool:
    """Vrai si une nouvelle version attend d'être mise en place (Windows)."""
    dossier = dossier_canonique()
    return bool(dossier) and os.path.isdir(dossier + SUFFIXE_NOUVEAU)


def _relais_windows(relancer_apres: bool = True, journal: str = "") -> bool:
    """Confie le remplacement à un script qui nous survivra.

    `relancer_apres` faux permute et s'arrête là. C'est ce qu'il faut quand
    l'application se ferme pour de bon : rouvrir une fenêtre sous les doigts
    de quelqu'un qui vient de cliquer sur la croix serait pris pour une panne.

    Windows ne laisse pas un programme remplacer le dossier d'où il tourne.
    Le seul moment sûr est donc après notre mort, et il faut quelqu'un pour
    agir à ce moment-là : un fichier de commandes, lancé détaché, qui attend
    notre disparition avant de permuter les dossiers et de relancer.

    Il est écrit dans le dossier temporaire et non à côté de l'application :
    il doit pouvoir s'effacer lui-même à la fin, et rien ne dit que
    l'installation soit accessible en écriture.
    """
    import subprocess
    # **Le meme relais sert a poser une mise a jour et a rentrer chez soi.**
    # Dans les deux cas il s'agit de mettre un dossier a la place d'un autre
    # une fois l'application fermee : ou bien celui qui attend a cote, ou bien
    # celui d'ou nous tournons quand la mise en place precedente a echoue.
    cible = dossier_canonique()
    attente = (dossier_installe() if hors_de_chez_soi()
               else cible + SUFFIXE_NOUVEAU)
    ancienne = cible + SUFFIXE_ANCIEN
    # L'executable de destination, et non le notre : apres la permutation nous
    # ne serons plus la ou nous sommes, et relancer notre propre chemin
    # rouvrait le dossier qu'on vient de mettre de cote.
    exe = os.path.join(cible, os.path.basename(sys.executable))

    script = os.path.join(tempfile.gettempdir(), "zyroom-qt-maj.bat")
    # **Les chemins passent par l'environnement, jamais par le script.**
    #
    # Ils y étaient écrits en toutes lettres, et le fichier ouvert en ASCII :
    # un joueur dont l'installation passe par « C:\Users\Frédéric » ou par
    # « Téléchargements » faisait lever UnicodeEncodeError, que le `except`
    # d'en dessous avalait — le bouton « Relancer » ne relançait rien, et
    # n'en disait pas grand-chose. Un prénom accentué suffisait.
    #
    # L'écrire en UTF-8 n'aurait fait que déplacer la panne : `cmd` lit les
    # fichiers de commandes dans la codepage OEM, et l'accent y serait devenu
    # un autre caractère, donc un chemin qui n'existe pas. Les variables
    # d'environnement, elles, voyagent en UTF-16 jusqu'à `cmd` : le script
    # reste en ASCII pur quels que soient les chemins, et il n'y a plus rien
    # à encoder.
    environnement = dict(os.environ)
    environnement["ZY_CIBLE"] = cible
    environnement["ZY_ANCIENNE"] = ancienne
    environnement["ZY_ATTENTE"] = attente
    environnement["ZY_EXE"] = exe
    # **De quoi relancer quelque chose meme si la permutation echoue.** L'exe
    # de destination n'existe que si la cible existe ; un joueur qui voit
    # quatre dossiers en fait le menage, et supprime parfois le bon. Sans ce
    # recours, le relais lancait un chemin vide et le joueur se retrouvait
    # sans rien -- l'application n'etait plus nulle part.
    environnement["ZY_SECOURS"] = os.path.abspath(sys.executable)
    environnement["ZY_PID"] = str(os.getpid())
    environnement["ZY_RELANCER"] = "1" if relancer_apres else "0"
    if journal:
        environnement["ZY_JOURNAL"] = journal

    # `tasklist` plutot qu'une attente fixe : la duree de fermeture depend de
    # la machine, et une seconde de trop ou de moins deciderait du succes.
    # Trente essais d'une seconde laissent le temps a Qt de rendre la main,
    # puis on tente quand meme -- au pire le renommage echoue et l'ancienne
    # version reste, ce qui est le cas sur lequel on sait revenir.
    contenu = """@echo off
setlocal
rem **Un journal, quand on le demande.** Ce script est le seul morceau de
rem l'application qui tourne apres sa mort : quand il ne fait rien, il ne
rem reste aucune trace, et l'on en est reduit a deviner. `ZY_JOURNAL` dit ou
rem ecrire ; sans elle, rien n'est ecrit.
if defined ZY_JOURNAL echo [debut] cible=%ZY_CIBLE% attente=%ZY_ATTENTE% pid=%ZY_PID%>>"%ZY_JOURNAL%"
for /l %%i in (1,1,30) do (
    if defined ZY_JOURNAL echo [attente] tour %%i>>"%ZY_JOURNAL%"
    tasklist /fi "PID eq %ZY_PID%" 2>nul | find "%ZY_PID%" >nul || goto :libre
    ping -n 2 127.0.0.1 >nul
)
if defined ZY_JOURNAL echo [attente] les trente tours sont passes>>"%ZY_JOURNAL%"
:libre
if defined ZY_JOURNAL echo [libre] le processus est parti>>"%ZY_JOURNAL%"
if exist "%ZY_ANCIENNE%" rmdir /s /q "%ZY_ANCIENNE%"
rem La cible peut manquer, et ce n'est pas une panne : un joueur qui decouvre
rem trois dossiers presque identiques en supprime, et parfois le bon. Il n'y
rem a alors rien a mettre de cote -- on pose directement.
if not exist "%ZY_CIBLE%" goto :poser
move "%ZY_CIBLE%" "%ZY_ANCIENNE%" >nul 2>&1
if defined ZY_JOURNAL echo [mise de cote] errorlevel=%errorlevel%>>"%ZY_JOURNAL%"
if errorlevel 1 goto :echec
:poser
move "%ZY_ATTENTE%" "%ZY_CIBLE%" >nul 2>&1
if defined ZY_JOURNAL echo [pose] errorlevel=%errorlevel%>>"%ZY_JOURNAL%"
if errorlevel 1 (
    rem Le remplacement a echoue a mi-chemin : l'application doit exister.
    if exist "%ZY_ANCIENNE%" move "%ZY_ANCIENNE%" "%ZY_CIBLE%" >nul 2>&1
    goto :echec
)
rem Plus aucun dossier suffixe n'a de raison d'etre : celui qui comptait
rem vient de prendre la place. Sans ce menage, un `.nouveau` oublie serait
rem repris pour une mise a jour en attente au lancement suivant -- et
rem remettrait en place une version plus ancienne.
for /d %%d in ("%ZY_CIBLE%.nouveau*") do rmdir /s /q "%%d"
if defined ZY_JOURNAL echo [fini] la permutation a eu lieu>>"%ZY_JOURNAL%"
if not "%ZY_RELANCER%"=="1" goto :fin
start "" "%ZY_EXE%"
goto :fin
:echec
if defined ZY_JOURNAL echo [echec] rien n'a pu etre deplace>>"%ZY_JOURNAL%"
if not "%ZY_RELANCER%"=="1" goto :fin
rem Relancer ce qui existe, et non ce qui devrait exister : apres un echec la
rem cible peut n'avoir jamais ete la, et son executable non plus. Le dossier
rem d'ou nous venons, lui, est encore la.
if exist "%ZY_EXE%" (
    start "" "%ZY_EXE%"
) else (
    if exist "%ZY_SECOURS%" start "" "%ZY_SECOURS%"
)
:fin
rem Le script s'efface lui-meme : `del` sur le fichier en cours fonctionne
rem sous cmd, la derniere ligne ayant deja ete lue.
del "%~f0"
"""
    try:
        with open(script, "w", encoding="ascii", newline="\r\n") as f:
            f.write(contenu)
        # Les trois poignees vers le neant, et non celles que nous laissons
        # derriere nous : nous allons mourir, et un tube branche sur les
        # poignees d'un mort ne vaut pas mieux que pas de poignees du tout.
        subprocess.Popen(["cmd", "/c", script], close_fds=True,
                         env=environnement,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=CREATE_NO_WINDOW)
        return True
    except Exception as exc:                            # noqa: BLE001
        # **Ne plus avaler la raison.** Elle etait perdue ici, et le joueur
        # n'avait qu'un bouton qui ne faisait rien : c'est ce silence qui a
        # coute le plus cher: le relais ne partait pas, et rien ne le disait.
        global derniere_erreur
        derniere_erreur = str(exc)
        return False


def poser_a_la_fermeture() -> bool:
    """Met en place la mise à jour qui attend, sans rouvrir de fenêtre.

    **Le défaut que ceci corrige, et il est la cause de tout le reste.** La
    permutation ne se faisait qu'en cliquant « Relancer » dans la boîte qui la
    propose. Répondre « Plus tard », ou fermer par la croix, laissait la
    nouvelle version attendre à côté indéfiniment — et l'application relancée
    plus tard était l'ancienne, qui reproposait la mise à jour, qui en
    déposait une deuxième, puis une troisième. C'est ainsi qu'un joueur se
    retrouve avec `ZyRoom-Qt.nouveau.nouveau.nouveau` : non parce que le
    calcul des noms était faux, mais parce que rien ne finissait jamais le
    travail.

    Fermer l'application est justement le moment où le remplacement devient
    possible : plus personne ne tient le dossier. On le fait donc là, sans
    rien demander et sans rien rouvrir — c'est ce que fait n'importe quel
    logiciel qui se met à jour sous Windows.

    Rend vrai si le relais est parti ; faux s'il n'y avait rien à poser.
    """
    if os.name != "nt" or not empaquete():
        return False
    if not (maj_en_attente() or hors_de_chez_soi()):
        return False
    return _relais_windows(relancer_apres=False)


def relancer() -> bool:
    """Relance l'application fraîchement installée. Rend vrai si c'est parti.

    Le chemin est le même qu'avant — c'est le contenu du dossier qui a changé,
    pas son nom. Sous Windows le contenu ne change qu'après notre départ :
    voir `_relais_windows`.
    """
    if not empaquete():
        return False

    # Sous Windows, la nouvelle version attend a cote : c'est le relais qui la
    # met en place, puisque nous ne pouvons pas remplacer le dossier d'ou nous
    # tournons. Il relance l'application lui-meme.
    if os.name == "nt" and (maj_en_attente() or hors_de_chez_soi()):
        return _relais_windows()

    try:
        import subprocess
        # **Detache de nous.** Sans `start_new_session`, le nouveau processus
        # reste dans notre groupe : la fenetre se ferme, le bureau range le
        # groupe entier, et l'application relancee meurt avec celle qui vient
        # de la lancer. C'est ce qui donnait l'impression qu'elle ne se
        # relancait pas du tout.
        subprocess.Popen([sys.executable], close_fds=True,
                         start_new_session=True,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except Exception:                                   # noqa: BLE001
        return False
