"""Internationalisation (gettext).

Les chaînes source sont en français (ce sont les msgid). Les catalogues
`locale/<lang>/LC_MESSAGES/zyroom.mo` fournissent les traductions ; en leur
absence, gettext retombe sur le français (le msgid).

Comme la langue est fixée au démarrage (avant construction de l'interface),
un changement de langue nécessite un redémarrage.
"""
from __future__ import annotations

import gettext as _gettext
import os

_LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")
_DOMAIN = "zyroom"

# code -> libellé affiché dans les options
LANGUAGES = {"": "Système", "fr": "Français", "en": "English", "de": "Deutsch"}

_translation = _gettext.NullTranslations()


def set_language(lang: str) -> None:
    """Charge le catalogue de la langue (code '' = langue système)."""
    global _translation
    languages = [lang] if lang else None
    _translation = _gettext.translation(_DOMAIN, _LOCALE_DIR,
                                        languages=languages, fallback=True)


def _(message: str) -> str:
    """Traduit une chaîne selon la langue courante."""
    return _translation.gettext(message)
