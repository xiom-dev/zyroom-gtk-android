"""Analyse et affichage d'un fichier de log /chatLog de Ryzom.

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

from gi.repository import Gdk, GLib, Gtk

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
        # Ligne sans horodatage : continuation / message système brut
        return LogLine(is_system=True, segments=_parse_segments(line))
    y, mo, d, h, mi, s, channel, content = m.groups()
    ll = LogLine(timestamp=f"{y}-{mo}-{d} {h}:{mi}:{s}",
                 channel=(channel or "").strip())
    ll.segments = _parse_segments(content)
    # Nom de personnage : premier mot avant ':' (sur le texte sans codes couleur)
    cm = re.search(r"([\wÀ-ÿ'\-]+)\s*:", ll.plain)
    if cm:
        ll.character = cm.group(1)
    # Heuristique « système » : ni canal ni locuteur identifié
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


# --------------------------------------------------------------- Fenêtre
class LogWindow(Gtk.Window):
    def __init__(self, parent, lines: list[LogLine]):
        super().__init__(title=_("Analyse de chatlog"), transient_for=parent)
        self.set_default_size(760, 560)
        self._lines = lines
        self._tags: dict[str, Gtk.TextTag] = {}

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(box)

        # Barre d'outils
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for mgn in ("margin_top", "margin_start", "margin_end"):
            setattr(bar.props, mgn, 8)
        box.append(bar)
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(_("Filtrer les messages…"))
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda *_: self._render())
        bar.append(self._search)

        self._channel_dd = Gtk.DropDown.new_from_strings(self._channels())
        self._channel_dd.connect("notify::selected", lambda *_: self._render())
        bar.append(self._channel_dd)

        self._show_system = Gtk.CheckButton(label=_("Système"))
        self._show_system.set_active(True)
        self._show_system.connect("toggled", lambda *_: self._render())
        bar.append(self._show_system)

        # Zone de texte
        self._view = Gtk.TextView()
        self._view.set_editable(False)
        self._view.set_cursor_visible(False)
        self._view.set_monospace(True)
        self._view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._view.add_css_class("chatlog")
        self._buffer = self._view.get_buffer()
        self._install_css()
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self._view)
        box.append(scroll)

        # Export
        exp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for mgn in ("margin_bottom", "margin_start", "margin_end"):
            setattr(exp.props, mgn, 8)
        box.append(exp)
        self._status = Gtk.Label(xalign=0.0, hexpand=True)
        exp.append(self._status)
        for label, fmt in ((_("Copier HTML"), "html"), (_("Copier BBCode"), "bbcode"),
                           (_("Copier texte"), "text")):
            b = Gtk.Button(label=label)
            b.connect("clicked", self._on_export, fmt)
            exp.append(b)

        self._render()

    def _channels(self) -> list[str]:
        found = sorted({ll.channel for ll in self._lines if ll.channel})
        return [_("Tous les canaux")] + found

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(b".chatlog text { background:#40503f; color:#e8e8e8; }")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _tag(self, color: str) -> Gtk.TextTag:
        tag = self._tags.get(color)
        if tag is None:
            tag = self._buffer.create_tag(color, foreground=color)
            self._tags[color] = tag
        return tag

    def _filtered(self) -> list[LogLine]:
        needle = self._search.get_text().strip().lower()
        ch_idx = self._channel_dd.get_selected()
        channels = self._channels()
        channel = channels[ch_idx] if 0 <= ch_idx < len(channels) else _("Tous les canaux")
        show_system = self._show_system.get_active()
        out = []
        for ll in self._lines:
            if ll.is_system and not show_system:
                continue
            if channel != _("Tous les canaux") and ll.channel != channel:
                continue
            if needle and needle not in ll.plain.lower():
                continue
            out.append(ll)
        return out

    def _render(self) -> None:
        self._buffer.set_text("")
        lines = self._filtered()
        end = self._buffer.get_end_iter()
        for ll in lines:
            if ll.timestamp:
                self._buffer.insert_with_tags(
                    end, f"{ll.timestamp}  ", self._tag("#9aa79a"))
            for color, text in ll.segments:
                if color:
                    self._buffer.insert_with_tags(end, text, self._tag(color))
                else:
                    self._buffer.insert(end, text)
            self._buffer.insert(end, "\n")
        self._status.set_text(f"{len(lines)} / {len(self._lines)} messages")

    def _on_export(self, _btn, fmt: str) -> None:
        lines = self._filtered()
        if fmt == "html":
            content = to_html(lines)
        elif fmt == "bbcode":
            content = to_bbcode(lines)
        else:
            content = to_text(lines)
        clipboard = self.get_clipboard()
        clipboard.set(content)
        self._status.set_text(f"{len(lines)} messages copiés ({fmt}).")
