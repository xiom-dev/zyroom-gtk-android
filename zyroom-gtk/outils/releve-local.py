#!/usr/bin/env python3
"""Le relevé des guildes, sur cette machine, toutes les quinze minutes.

L'API de Ryzom ne rend qu'un état, jamais un historique : un mouvement se
déduit de deux relevés successifs, et personne ne voit ce qui se passe pendant
que tout le monde dort. Le relevé qui tourne sur GitHub est censé y pourvoir —
sauf qu'il ne tourne pas. Mesuré sur huit jours : **5,4 exécutions par jour**
pour un cron horaire, des retards de 5 à 58 minutes, et jusqu'à dix-huit
heures d'affilée sans rien. GitHub déprioritise les workflows planifiés, et
demander plus souvent ne fait qu'ignorer davantage de créneaux.

Ce script-ci fait donc le travail régulier, ici, où l'horloge est respectée.
Le relevé de GitHub reste le filet des heures où cette machine est éteinte.
Les deux publient sur la même branche, et la fusion des registres rapproche
les constats en double — c'est exactement le cas pour lequel elle est écrite.

    ./releve-local.py            relève et publie
    ./releve-local.py --a-blanc  relève sans rien envoyer

Il s'installe en minuteur systemd **utilisateur** — rien dans le système :

    ./releve-local.py --installer     pose le service et le minuteur
    ./releve-local.py --desinstaller  les retire

**Les clés ne sont écrites nulle part.** Elles sont lues dans les `guilds.ini`
des applications installées, là où elles sont déjà, en clair : le paquet ne
livre aucune clé, chaque joueur y met la sienne, et ce script se contente de
les relire.
"""
from __future__ import annotations

import configparser
import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

#: Le dépôt qui porte la branche `journaux`.
DEPOT = "git@github.com:xiom-dev/zyroom-gtk-android.git"

#: La copie de travail, gardée d'un relevé à l'autre.
#:
#: En cache et non en données : elle se reconstruit d'un `git clone`, et sa
#: perte ne coûte qu'un téléchargement. C'est l'état du dernier relevé qui
#: compte, et il vit sur la branche.
TRAVAIL = os.path.expanduser("~/.cache/zyroom-releve/journaux")

#: Où les applications gardent leurs clés de guilde, en clair.
#:
#: Le Flatpak dev d'abord — c'est l'installation qui sert ici —, puis les
#: autres. Un fichier absent est sauté ; les clés en double sont écartées.
GUILDES_INI = (
    "~/.var/app/net.ryzom.zyroomgtk.dev/config/zyroom-gtk/guilds.ini",
    "~/.var/app/net.ryzom.zyroomgtk/config/zyroom-gtk/guilds.ini",
    "~/.config/zyroom-qt/guilds.ini",
    "~/.config/zyroom-gtk/guilds.ini",
)

UNITE = "zyroom-releve"


def cles_de_guilde() -> list[str]:
    """Les clés d'API des guildes suivies, sans doublon, dans l'ordre trouvé."""
    vues: list[str] = []
    for chemin in GUILDES_INI:
        chemin = os.path.expanduser(chemin)
        if not os.path.isfile(chemin):
            continue
        ini = configparser.ConfigParser()
        try:
            ini.read(chemin, encoding="utf-8")
        except (configparser.Error, OSError):
            continue
        for section in ini.sections():
            cle = ini.get(section, "key", fallback="").strip()
            if cle and cle not in vues:
                vues.append(cle)
    return vues


def git(*arguments: str, dans: str = TRAVAIL) -> subprocess.CompletedProcess:
    return subprocess.run(("git",) + arguments, cwd=dans,
                          capture_output=True, text=True)


def preparer() -> bool:
    """La copie de travail, à jour sur la branche publiée.

    Repartir de la branche à chaque relevé, et non d'un dossier laissé là :
    le relevé de GitHub a pu publier entre-temps, et écrire par-dessus son
    travail le perdrait.
    """
    if not os.path.isdir(os.path.join(TRAVAIL, ".git")):
        os.makedirs(os.path.dirname(TRAVAIL), exist_ok=True)
        fait = subprocess.run(
            ["git", "clone", "--quiet", "--branch", "journaux", "--depth", "1",
             DEPOT, TRAVAIL], capture_output=True, text=True)
        return fait.returncode == 0

    if git("fetch", "--quiet", "--depth", "1", "origin", "journaux").returncode != 0:
        return False
    return git("reset", "--quiet", "--hard", "origin/journaux").returncode == 0


def relever(cles: list[str]) -> int:
    """Lance le relevé partagé avec GitHub, sur la copie de travail."""
    environnement = dict(os.environ)
    environnement["CLES_GUILDES"] = ",".join(cles)
    environnement["DOSSIER_JOURNAUX"] = TRAVAIL
    fait = subprocess.run(
        [sys.executable, os.path.join(RACINE, "outils", "releve-guildes.py")],
        env=environnement, capture_output=True, text=True)
    print(fait.stdout.strip() or fait.stderr.strip())
    return fait.returncode


def publier() -> int:
    """Pousse ce qui a bougé, et se tait quand rien n'a bougé.

    La branche est orpheline et poussée en force par GitHub comme par ici :
    l'historique ne s'accumule pas, il n'y a jamais qu'un état, celui du
    dernier relevé.
    """
    if git("add", "-A").returncode != 0:
        return 1
    if git("diff", "--cached", "--quiet").returncode == 0:
        print("Rien de neuf : la guilde n'a pas bougé.")
        return 0
    from datetime import datetime, timezone
    quand = datetime.now(timezone.utc).strftime("%d/%m/%Y %Hh%M UTC")
    if git("-c", "user.name=Relevé local",
           "-c", "user.email=noreply@localhost",
           "commit", "--quiet", "-m",
           f"Relevé des guildes : {quand}").returncode != 0:
        return 1
    envoi = git("push", "--quiet", "--force", "origin", "journaux")
    if envoi.returncode != 0:
        print(f"Envoi impossible : {envoi.stderr.strip()}", file=sys.stderr)
        return 1
    print("Publié sur la branche journaux.")
    return 0


SERVICE = """[Unit]
Description=Relevé des guildes Ryzom (ZyRoom)
Documentation=file://{script}
After=network-online.target

[Service]
Type=oneshot
ExecStart={python} {script}
"""

MINUTEUR = """[Unit]
Description=Relevé des guildes Ryzom, toutes les quinze minutes

[Timer]
# Deux minutes après l'ouverture de session : le temps que le réseau soit là.
OnBootSec=2min
OnUnitActiveSec=15min
# Rattrape le relevé manqué quand la machine était éteinte, au lieu
# d'attendre le prochain quart d'heure.
Persistent=true
Unit={unite}.service

[Install]
WantedBy=timers.target
"""


def dossier_unites() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "systemd", "user")


def installer() -> int:
    dossier = dossier_unites()
    os.makedirs(dossier, exist_ok=True)
    script = os.path.abspath(__file__)
    with open(os.path.join(dossier, f"{UNITE}.service"), "w", encoding="utf-8") as fh:
        fh.write(SERVICE.format(python=sys.executable, script=script))
    with open(os.path.join(dossier, f"{UNITE}.timer"), "w", encoding="utf-8") as fh:
        fh.write(MINUTEUR.format(unite=UNITE))
    for commande in (["systemctl", "--user", "daemon-reload"],
                     ["systemctl", "--user", "enable", "--now", f"{UNITE}.timer"]):
        fait = subprocess.run(commande, capture_output=True, text=True)
        if fait.returncode != 0:
            print(fait.stderr.strip(), file=sys.stderr)
            return 1
    print(f"Minuteur posé : {dossier}/{UNITE}.timer")
    print("  systemctl --user list-timers zyroom-releve   pour le voir passer")
    print("  journalctl --user -u zyroom-releve -f        pour le suivre")
    return 0


def desinstaller() -> int:
    subprocess.run(["systemctl", "--user", "disable", "--now", f"{UNITE}.timer"],
                   capture_output=True, text=True)
    dossier = dossier_unites()
    for nom in (f"{UNITE}.timer", f"{UNITE}.service"):
        chemin = os.path.join(dossier, nom)
        if os.path.isfile(chemin):
            os.remove(chemin)
    subprocess.run(["systemctl", "--user", "daemon-reload"],
                   capture_output=True, text=True)
    print("Minuteur retiré.")
    return 0


def main() -> int:
    if "--installer" in sys.argv[1:]:
        return installer()
    if "--desinstaller" in sys.argv[1:]:
        return desinstaller()

    cles = cles_de_guilde()
    if not cles:
        print("Aucune clé de guilde trouvée dans les applications installées.",
              file=sys.stderr)
        return 1
    if not preparer():
        print("Impossible de lire la branche « journaux ».", file=sys.stderr)
        return 1
    if relever(cles) != 0:
        return 1
    if "--a-blanc" in sys.argv[1:]:
        etat = git("status", "--short")
        print("À blanc — rien n'a été envoyé."
              + (f"\n{etat.stdout.strip()}" if etat.stdout.strip() else ""))
        return 0
    return publier()


if __name__ == "__main__":
    raise SystemExit(main())
