"""Sauvegarde automatique du dossier « save » de Ryzom.

Copie le contenu du dossier save vers une sauvegarde horodatée, avec rotation
(on garde les N plus récentes, 30 par défaut comme l'original).
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from .config import backup_dir

_LIMIT = 30


def list_backups() -> list[str]:
    root = backup_dir()
    return sorted((d for d in os.listdir(root)
                   if os.path.isdir(os.path.join(root, d))), reverse=True)


def _rotate(limit: int) -> None:
    root = backup_dir()
    dirs = sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)))
    while len(dirs) > limit:
        shutil.rmtree(os.path.join(root, dirs.pop(0)), ignore_errors=True)


def run_backup(save_folder: str, limit: int = _LIMIT) -> tuple[bool, str]:
    """Copie le dossier save dans une sauvegarde horodatée. (ok, message)."""
    if not save_folder or not os.path.isdir(save_folder):
        return False, "Dossier « save » introuvable."
    ts = datetime.now().strftime("%Y-%m-%d %H%M%S")
    dest = os.path.join(backup_dir(), ts)
    try:
        shutil.copytree(save_folder, dest, dirs_exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        return False, f"Échec : {exc}"
    _rotate(limit)
    count = sum(len(files) for _, _, files in os.walk(dest))
    return True, f"{count} fichiers sauvegardés ({ts})"
