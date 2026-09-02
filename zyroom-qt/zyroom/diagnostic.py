"""Ce que l'application voit de son installation, sans ouvrir de fenêtre.

`run.py --diagnostic` l'affiche puis quitte. Deux usages :

- **valider un paquet.** Un bundle où les données manquent démarre quand même :
  la table des fiches, les traductions et la police se chargent toutes en
  silence, et l'application se contente alors d'afficher des identifiants au
  lieu des noms. Le défaut ne se voit qu'à l'écran, plusieurs minutes plus
  tard. Ce relevé le dit tout de suite, et se lance là où l'on ne peut pas
  regarder soi-même — sur la machine Windows d'un autre, par exemple.
- **répondre à « ça ne marche pas ».** Chemins, présence des fichiers,
  nombre d'entités configurées : de quoi savoir où chercher sans faire
  décrire une arborescence par téléphone.

Aucune clé d'API n'y paraît : ce relevé est fait pour être recopié dans un
message.
"""
from __future__ import annotations

import os
import sys

from . import __version__, config, i18n, polices
from .sheetdb import SheetDb


def _etat(present: bool) -> str:
    return "OK  " if present else "MANQUE"


def _fichier(chemin: str) -> str:
    if not chemin:
        return "MANQUE  (non configuré)"
    if not os.path.isfile(chemin):
        return f"MANQUE  {chemin}"
    return f"OK      {chemin}  ({os.path.getsize(chemin):,} o)".replace(",", " ")


def rapport() -> str:
    lignes = [
        f"ZyRoom-Qt {__version__}",
        f"Python   {sys.version.split()[0]}",
    ]
    try:
        from PySide6 import __version__ as pyside
        lignes.append(f"PySide6  {pyside}")
    except Exception:                                    # noqa: BLE001
        lignes.append("PySide6  ABSENT")

    # `sys.frozen` est pose par PyInstaller : c'est ainsi qu'on sait qu'on
    # tourne depuis un paquet et non depuis les sources.
    empaquete = getattr(sys, "frozen", False)
    lignes.append(f"Paquet   {'oui' if empaquete else 'non (sources)'}")
    lignes.append(f"Système  {sys.platform}"
                  f"{'  (Windows)' if config.WINDOWS else ''}")
    lignes.append("")

    lignes.append("Données embarquées")
    sheet = SheetDb()
    charge = sheet.load(config.SHEETID_CSV)
    lignes.append(f"  sheetid.csv    {_etat(charge)}"
                  f"  {len(sheet)} fiches")
    lignes.append(f"  category.csv   {_etat(os.path.isfile(config.CATEGORY_CSV))}")
    lignes.append(f"  police         {_etat(os.path.isfile(polices.FICHIER))}"
                  f"  {polices.FAMILLE}")
    catalogues = []
    dossier_locale = os.path.join(os.path.dirname(os.path.abspath(i18n.__file__)),
                                  "locale")
    if os.path.isdir(dossier_locale):
        catalogues = sorted(os.listdir(dossier_locale))
    lignes.append(f"  traductions    {_etat(bool(catalogues))}"
                  f"  {', '.join(catalogues) or 'aucune'}")
    lignes.append("")

    lignes.append("Dossiers")
    lignes.append(f"  configuration  {config.config_dir()}")
    lignes.append(f"  cache          {config.cache_dir()}")
    lignes.append(f"  données        {config.data_dir()}")
    lignes.append("")

    lignes.append("Jeu")
    lignes.append(f"  string_client.pack  {_fichier(config.detect_pack())}")
    dossier = config.detect_save_folder()
    lignes.append(f"  dossier « save »    "
                  f"{dossier or 'MANQUE  (non trouvé)'}")
    lignes.append("")

    lignes.append("Configuration")
    personnages = config.EntityStore("characters.ini").entries()
    guildes = config.EntityStore("guilds.ini").entries()
    lignes.append(f"  personnages    {len(personnages)}")
    lignes.append(f"  guildes        {len(guildes)}")
    reglages = config.Settings()
    lignes.append(f"  langue         {reglages.language or 'système'}")
    lignes.append(f"  relevé auto    {reglages.sync_interval} min")
    lignes.append(f"  proxy          {'oui' if reglages.proxy_enabled else 'non'}")
    return "\n".join(lignes)


def main() -> int:
    print(rapport())
    return 0
