"""Ce que l'application voit de son installation, sans ouvrir de fenêtre.

`./run.py --diagnostic`, ou `flatpak run net.ryzom.zyroomgtk --diagnostic`,
l'affiche puis quitte. Deux usages :

- **valider un paquet.** Un bundle où les données manquent démarre quand même :
  la table des fiches, les traductions et la police se chargent toutes en
  silence, et l'application se contente alors d'afficher des identifiants au
  lieu des noms. Le défaut ne se voit qu'à l'écran, plusieurs minutes plus
  tard.
- **répondre à « ça ne marche pas ».** Le bac à sable de Flatpak est
  précisément l'endroit où « le fichier est pourtant là » cesse d'être vrai :
  l'application ne voit du disque que ce que `--filesystem` lui accorde, et le
  dossier du jeu est au bout de cette permission. Ce relevé dit ce qu'elle
  atteint vraiment, et où sont passés ses réglages.

Aucune clé d'API n'y paraît : ce relevé est fait pour être recopié dans un
message.

Son équivalent Qt (`zyroom-qt/zyroom/diagnostic.py`) relève les mêmes choses ;
les deux diffèrent là où les portages diffèrent — bac à sable et rendu ici,
`%APPDATA%` et PySide là-bas. Il ne passe donc pas par `sync-noyau.sh`.
"""
from __future__ import annotations

import configparser
import os
import re
import sys

from . import config, i18n, polices
from .sheetdb import SheetDb


def _etat(present: bool) -> str:
    return "OK  " if present else "MANQUE"


def _fichier(chemin: str) -> str:
    if not chemin:
        return "MANQUE  (non configuré)"
    if not os.path.isfile(chemin):
        return f"MANQUE  {chemin}"
    taille = f"{os.path.getsize(chemin):,}".replace(",", " ")
    return f"OK      {chemin}  ({taille} o)"


def _version() -> tuple[str, bool]:
    """Le numéro affiché, et si c'est la variante du mainteneur.

    Il est lu dans le source de `window.py` plutôt qu'importé : importer ce
    module tirerait GTK et toute l'interface pour trois caractères, et le
    relevé doit pouvoir parler d'une installation dont l'interface, elle, ne
    démarre plus.
    """
    dev = (os.environ.get("FLATPAK_ID") or "").endswith(".dev")
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "window.py")
    try:
        with open(chemin, encoding="utf-8") as source:
            texte = source.read()
    except OSError:
        return "inconnue", dev
    trouve = re.search(r'^VERSION = "([^"]*)" if _DEV else "([^"]*)"$',
                       texte, re.M)
    if not trouve:
        return "inconnue", dev
    return (trouve.group(1) if dev else trouve.group(2)), dev


def _entites(fichier: str) -> str:
    """Combien d'entités dans un .ini, sans passer par EntityStore.

    EntityStore seme la configuration livree quand le fichier n'existe pas
    encore : un releve qui cree ce qu'il vient compter ne dit plus l'etat de la
    machine, il dit celui d'apres. On lit donc le fichier tel qu'il est.
    """
    chemin = os.path.join(config.config_dir(), fichier)
    if not os.path.isfile(chemin):
        return "0  (pas encore de fichier)"
    ini = configparser.ConfigParser()
    try:
        ini.read(chemin, encoding="utf-8")
    except configparser.Error as souci:
        return f"ILLISIBLE  {souci.__class__.__name__}"
    return str(len(ini.sections()))


def rapport() -> str:
    version, dev = _version()
    lignes = [
        f"ZyRoom-GTK {version}" + ("  (variante dev)" if dev else ""),
        f"Python     {sys.version.split()[0]}",
    ]

    # GTK et PyGObject s'importent ici et nulle part ailleurs dans ce module :
    # importer Gtk ne pose aucune fenetre tant qu'on n'ouvre pas d'application,
    # et leur absence est elle-meme une reponse.
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        lignes.append(f"PyGObject  {gi.__version__}")
        lignes.append("GTK        "
                      f"{Gtk.get_major_version()}."
                      f"{Gtk.get_minor_version()}."
                      f"{Gtk.get_micro_version()}")
    except Exception as souci:                           # noqa: BLE001
        lignes.append(f"PyGObject  ABSENT  ({souci.__class__.__name__})")

    # /.flatpak-info n'existe que dans le bac a sable : c'est Flatpak qui l'y
    # pose. FLATPAK_ID dit sous quel nom, et donc laquelle des deux variantes.
    bac = os.path.isfile("/.flatpak-info")
    identifiant = os.environ.get("FLATPAK_ID") or "net.ryzom.zyroomgtk"
    lignes.append(f"Paquet     {'Flatpak (bac à sable)' if bac else 'sources'}"
                  f"  {identifiant}")
    lignes.append(f"Session    {os.environ.get('XDG_SESSION_TYPE') or 'inconnue'}"
                  f"  rendu {os.environ.get('GSK_RENDERER') or 'par défaut'}")
    lignes.append("")

    lignes.append("Données embarquées")
    sheet = SheetDb()
    lignes.append(f"  sheetid.csv    {_etat(sheet.load(config.SHEETID_CSV))}"
                  f"  {len(sheet)} fiches")
    lignes.append(f"  category.csv   {_etat(os.path.isfile(config.CATEGORY_CSV))}")
    # Present, pas charge : `polices.charger()` inscrit la police dans
    # fontconfig, et un releve ne change rien a la machine qu'il decrit.
    lignes.append(f"  police         {_etat(os.path.isfile(polices.FICHIER))}"
                  f"  {polices.FAMILLE}")
    dossier_locale = os.path.join(os.path.dirname(os.path.abspath(i18n.__file__)),
                                  "locale")
    catalogues = sorted(os.listdir(dossier_locale)) \
        if os.path.isdir(dossier_locale) else []
    lignes.append(f"  traductions    {_etat(bool(catalogues))}"
                  f"  {', '.join(catalogues) or 'aucune'}")
    lignes.append("")

    lignes.append("Dossiers")
    lignes.append(f"  configuration  {config.config_dir()}")
    lignes.append(f"  cache          {config.cache_dir()}")
    lignes.append(f"  données        {config.data_dir()}")
    lignes.append(f"  sauvegardes    {config.backup_dir()}")
    journal = config.journal_erreurs()
    if os.path.isfile(journal):
        taille = f"{os.path.getsize(journal):,}".replace(",", " ")
        lignes.append(f"  journal        {journal}  ({taille} o — il a servi)")
    else:
        lignes.append(f"  journal        {journal}  (vide, rien n'a cassé)")
    lignes.append("")

    lignes.append("Jeu")
    # Le point ou le bac a sable se fait sentir : sans --filesystem=home:ro,
    # les deux lignes suivantes disent MANQUE alors que les fichiers sont bien
    # la. La troisieme repond d'avance a la question que cela poserait.
    lignes.append(f"  string_client.pack  {_fichier(config.detect_pack())}")
    dossier = config.detect_save_folder()
    lignes.append(f"  dossier « save »    {dossier or 'MANQUE  (non trouvé)'}")
    maison = os.path.expanduser("~")
    lignes.append(f"  accès au dossier personnel  "
                  f"{_etat(os.access(maison, os.R_OK))}  {maison}")
    lignes.append("")

    lignes.append("Configuration")
    lignes.append(f"  personnages    {_entites('characters.ini')}")
    lignes.append(f"  guildes        {_entites('guilds.ini')}")
    reglages = config.Settings()
    lignes.append(f"  langue         {reglages.language or 'système'}")
    lignes.append(f"  relevé auto    {reglages.sync_interval} min")
    lignes.append(f"  notifications  {'oui' if reglages.notifications else 'non'}")
    lignes.append(f"  proxy          {'oui' if reglages.proxy_enabled else 'non'}")
    # Coupees a droite : "OK  " est cale sur "MANQUE", et le blanc de calage se
    # voit des qu'on colle le releve dans un message.
    return "\n".join(ligne.rstrip() for ligne in lignes)


def main() -> int:
    print(rapport())
    return 0
