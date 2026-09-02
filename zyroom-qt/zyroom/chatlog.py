"""Analyse et affichage d'un fichier de log /chatLog de Ryzom.

**La moitié haute de ce fichier est celle de ZyRoom-GTK, mot pour mot** :
l'analyse d'une ligne et les trois exports ne dépendent d'aucune boîte à
outils. Elle n'est pas dans le noyau partagé parce que, là-bas, elle cohabite
dans le même fichier avec une fenêtre GTK — c'est ce voisinage, et lui seul,
qui l'en exclut.

Format d'une ligne (cf. ParseLogFile du Delphi) :
    AAAA/MM/JJ HH:MM:SS (CANAL) * <contenu>
Le contenu contient des codes couleur `@{RGBA}` (4 chiffres hexa, chaque
composante étant un demi-octet multiplié par 17 pour obtenir 0-255).

Export possible en HTML, BBCode et texte brut.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QTextEdit,
                               QVBoxLayout)

from .i18n import _

_LINE_RE = re.compile(r"^(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2}) "
                      r"(?:\((.*?)\) )?\* (.*)$")
_COLOR_RE = re.compile(r"@\{([0-9A-Fa-f]{4})\}")


def log_color(code: str) -> str:
    """Code couleur '@{RGBA}' (les 4 hexa) -> '#RRGGBB'."""
    r, g, b = code[0], code[1], code[2]
    return f"#{int(r, 16) * 17:02x}{int(g, 16) * 17:02x}{int(b, 16) * 17:02x}"


@dataclass
class LogLine:
    timestamp: str = ""
    channel: str = ""
    character: str = ""
    is_system: bool = False
    segments: list = field(default_factory=list)  # [(couleur|None, texte), ...]

    @property
    def plain(self) -> str:
        return "".join(text for _, text in self.segments)


def _parse_segments(content: str) -> list:
    segments = []
    pos = 0
    current = None
    for m in _COLOR_RE.finditer(content):
        if m.start() > pos:
            segments.append((current, content[pos:m.start()]))
        current = log_color(m.group(1))
        pos = m.end()
    if pos < len(content):
        segments.append((current, content[pos:]))
    return segments or [(None, content)]


def parse_line(line: str) -> LogLine | None:
    line = line.rstrip("\r\n")
    if not line.strip():
        return None
    m = _LINE_RE.match(line)
    if not m:
        # Ligne sans horodatage : continuation / message systeme brut
        return LogLine(is_system=True, segments=_parse_segments(line))
    y, mo, d, h, mi, s, channel, content = m.groups()
    ll = LogLine(timestamp=f"{y}-{mo}-{d} {h}:{mi}:{s}",
                 channel=(channel or "").strip())
    ll.segments = _parse_segments(content)
    # Nom de personnage : premier mot avant ':' (sur le texte sans codes couleur)
    cm = re.search(r"([\wÀ-ÿ'\-]+)\s*:", ll.plain)
    if cm:
        ll.character = cm.group(1)
    # Heuristique "systeme" : ni canal ni locuteur identifie
    ll.is_system = not ll.channel and not ll.character
    return ll


def parse_log(text: str) -> list[LogLine]:
    out = []
    for line in text.splitlines():
        ll = parse_line(line)
        if ll is not None:
            out.append(ll)
    return out


# ------------------------------------------------------------------ Exports
def to_text(lines: list[LogLine], show_date: bool = False) -> str:
    rows = []
    for ll in lines:
        prefix = f"{ll.timestamp} * " if show_date and ll.timestamp else ""
        rows.append(prefix + ll.plain)
    return "\n".join(rows)


def to_html(lines: list[LogLine], show_date: bool = False) -> str:
    rows = ['<html><head><meta charset="utf-8"></head>'
            '<body style="background:#505E42;font-family:sans-serif;">']
    for ll in lines:
        parts = []
        if show_date and ll.timestamp:
            parts.append(f'<span style="color:#aaa">{ll.timestamp} * </span>')
        for color, text in ll.segments:
            esc = html.escape(text)
            if color:
                parts.append(f'<span style="color:{color}">{esc}</span>')
            else:
                parts.append(esc)
        rows.append("".join(parts) + "<br>")
    rows.append("</body></html>")
    return "\n".join(rows)


def to_bbcode(lines: list[LogLine], show_date: bool = False) -> str:
    rows = []
    for ll in lines:
        parts = []
        if show_date and ll.timestamp:
            parts.append(f"{ll.timestamp} * ")
        for color, text in ll.segments:
            if color:
                parts.append(f"[color={color}]{text}[/color]")
            else:
                parts.append(text)
        rows.append("".join(parts))
    return "\n".join(rows)


# --------------------------------------------------------------- Fenetre
class FenetreChatlog(QDialog):
    """Le journal de discussion, filtrable et recopiable.

    **Le texte est posé en une fois, en HTML.** GTK insère segment par segment
    dans son tampon, avec une étiquette par couleur ; Qt sait lire un document
    HTML entier, et le construire coûte moins cher que des milliers
    d'insertions au curseur. Le fond vert sombre du jeu est conservé — c'est
    celui du chat dans Ryzom, et le relire ailleurs qu'à cette couleur trouble
    la lecture.
    """

    #: Au-dela, on n'affiche que les premieres : un chatlog d'un an fait des
    #: centaines de milliers de lignes, et le document HTML ne se construirait
    #: pas en un temps raisonnable. Le filtre sert a chercher plus loin.
    MAX_LIGNES = 20000

    def __init__(self, parent, lignes: list) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Analyse de chatlog"))
        self.resize(760, 560)
        self._lignes = lignes

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(8, 8, 8, 8)
        colonne.setSpacing(6)

        barre = QHBoxLayout()
        barre.setSpacing(6)
        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText(_("Filtrer les messages…"))
        self._recherche.setClearButtonEnabled(True)
        self._recherche.textChanged.connect(self._afficher)
        barre.addWidget(self._recherche, 1)

        self._dd_canal = QComboBox()
        self._dd_canal.addItems(self._canaux())
        self._dd_canal.currentIndexChanged.connect(self._afficher)
        barre.addWidget(self._dd_canal)

        self._systeme = QCheckBox(_("Système"))
        self._systeme.setChecked(True)
        self._systeme.toggled.connect(self._afficher)
        barre.addWidget(self._systeme)
        colonne.addLayout(barre)

        self._vue = QTextEdit()
        self._vue.setReadOnly(True)
        self._vue.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        # Le vert sombre du chat de Ryzom, comme cote GTK.
        self._vue.setStyleSheet(
            "QTextEdit { background:#40503f; color:#e8e8e8; }")
        police = QFont("monospace")
        police.setStyleHint(QFont.StyleHint.Monospace)
        self._vue.setFont(police)
        colonne.addWidget(self._vue, 1)

        pied = QHBoxLayout()
        pied.setSpacing(6)
        self._statut = QLabel()
        self._statut.setObjectName("discret")
        pied.addWidget(self._statut, 1)
        for libelle, forme in ((_("Copier HTML"), "html"),
                               (_("Copier BBCode"), "bbcode"),
                               (_("Copier texte"), "text")):
            bouton = QPushButton(libelle)
            bouton.clicked.connect(
                lambda _c=False, f=forme: self._copier(f))
            pied.addWidget(bouton)
        fermer = QPushButton(_("Fermer"))
        fermer.clicked.connect(self.accept)
        pied.addWidget(fermer)
        colonne.addLayout(pied)

        self._afficher()

    def _canaux(self) -> list[str]:
        trouves = sorted({ll.channel for ll in self._lignes if ll.channel})
        return [_("Tous les canaux")] + trouves

    def _filtrees(self) -> list:
        motif = self._recherche.text().strip().lower()
        canaux = self._canaux()
        rang = self._dd_canal.currentIndex()
        canal = canaux[rang] if 0 <= rang < len(canaux) else canaux[0]
        systeme = self._systeme.isChecked()
        sortie = []
        for ll in self._lignes:
            if ll.is_system and not systeme:
                continue
            if canal != canaux[0] and ll.channel != canal:
                continue
            if motif and motif not in ll.plain.lower():
                continue
            sortie.append(ll)
        return sortie

    def _afficher(self) -> None:
        lignes = self._filtrees()
        montrees = lignes[:self.MAX_LIGNES]
        morceaux = []
        for ll in montrees:
            bout = []
            if ll.timestamp:
                bout.append(f'<span style="color:#9aa79a">'
                            f'{html.escape(ll.timestamp)}&nbsp;&nbsp;</span>')
            for couleur, texte in ll.segments:
                echappe = html.escape(texte)
                if couleur:
                    bout.append(f'<span style="color:{couleur}">{echappe}</span>')
                else:
                    bout.append(echappe)
            morceaux.append("".join(bout))
        self._vue.setHtml("<br>".join(morceaux))

        if len(lignes) > len(montrees):
            self._statut.setText(
                _("{} / {} messages — {} affichés, affinez le filtre").format(
                    len(lignes), len(self._lignes), len(montrees)))
        else:
            self._statut.setText(
                _("{} / {} messages").format(len(lignes), len(self._lignes)))

    def _copier(self, forme: str) -> None:
        lignes = self._filtrees()
        if forme == "html":
            contenu = to_html(lignes)
        elif forme == "bbcode":
            contenu = to_bbcode(lignes)
        else:
            contenu = to_text(lignes)
        QGuiApplication.clipboard().setText(contenu)
        self._statut.setText(
            _("{} messages copiés ({}).").format(len(lignes), forme))


def ouvrir(parent, chemin: str) -> str:
    """Lit un fichier de chatlog et ouvre sa fenêtre. Rend un message d'état.

    Le fichier est lu en tolérant les octets illisibles : un chatlog est écrit
    par le jeu au fil de l'eau, et une session coupée net y laisse volontiers
    une ligne tronquée. Refuser tout le fichier pour un octet serait absurde.
    """
    try:
        with open(chemin, encoding="utf-8", errors="replace") as fh:
            lignes = parse_log(fh.read())
    except OSError as exc:
        return _("Lecture impossible : {}").format(exc)
    if not lignes:
        return _("Ce fichier ne contient aucun message lisible.")
    FenetreChatlog(parent, lignes).exec()
    return _("{} messages analysés.").format(len(lignes))
