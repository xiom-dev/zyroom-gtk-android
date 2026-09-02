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

_USER_AGENT = "zyroom-qt (+https://github.com/xiom-dev/zyroom-gtk-android)"


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


def nettoyer_ancienne() -> None:
    """Efface l'installation précédente, s'il en reste une.

    Appelée au démarrage : à ce moment plus rien ne la tient, et le nettoyage
    ne peut plus gêner personne. Un échec est sans conséquence — on réessaiera
    au prochain lancement.
    """
    dossier = dossier_installe()
    if not dossier:
        return
    ancienne = dossier + SUFFIXE_ANCIEN
    if os.path.isdir(ancienne):
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
            chemin = zip_.extract(membre, dossier)
            mode = membre.external_attr >> 16
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


def installer(archive: str) -> tuple[bool, str]:
    """Met la nouvelle version à la place de l'ancienne.

    Rend `(réussi, message)`. En cas d'échec à n'importe quelle étape,
    l'installation d'origine est remise en place.
    """
    cible = dossier_installe()
    if not cible:
        return False, "Aucune installation à remplacer."

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

        # Une precedente mise de cote qui trainerait empecherait le renommage.
        if os.path.isdir(ancienne):
            shutil.rmtree(ancienne, ignore_errors=True)

        # Le tour de main : renommer, jamais effacer. Le dossier d'ou l'on
        # tourne continue d'exister sous son nouveau nom, et les fichiers
        # ouverts restent valides -- sous Windows comme ici.
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


def relancer() -> bool:
    """Relance l'application fraîchement installée. Rend vrai si c'est parti.

    Le chemin est le même qu'avant — c'est le contenu du dossier qui a changé,
    pas son nom.
    """
    if not empaquete():
        return False
    try:
        import subprocess
        subprocess.Popen([sys.executable], close_fds=True)
        return True
    except Exception:                                   # noqa: BLE001
        return False
