"""
Конвертація .docx у .pdf через headless LibreOffice (soffice) -- дає
візуально ідентичний до .docx результат (той самий рушій верстки), на
відміну від будь-якого незалежного/самописного PDF-рендера.

У продакшн-контейнері (Linux) soffice запускається як звичайний
headless-процес без потреби в інтерактивному робочому столі -- на
відміну від Windows, де GUI-підсистема iноді вимагає доступу до
window station навіть у headless-режимі.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from app.core.config import BASE_DIR

_SOFFICE_CANDIDATES = [
    "soffice",
    "soffice.exe",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/opt/libreoffice/program/soffice",
]

_PROFILE_DIR = BASE_DIR / ".soffice_profile"
_convert_lock = threading.Lock()

_FAILURE_COOLDOWN = 300  # 5 хв -- щоб не чекати повний таймаут повторно, якщо soffice щойно вже впав
_last_failure_time: float | None = None
_last_failure_reason: str | None = None


def _find_soffice() -> str | None:
    env_path = os.environ.get("SOFFICE_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    for candidate in _SOFFICE_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
        if Path(candidate).exists():
            return candidate
    return None


def is_available() -> bool:
    return _find_soffice() is not None


def _convert_once(soffice: str, docx_bytes: bytes, timeout: int) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        src_path = tmp_dir / "document.docx"
        src_path.write_bytes(docx_bytes)

        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--norestore",
                f"-env:UserInstallation=file:///{_PROFILE_DIR.as_posix()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_dir),
                str(src_path),
            ],
            capture_output=True,
            timeout=timeout,
        )
        pdf_path = tmp_dir / "document.pdf"
        if result.returncode != 0 or not pdf_path.exists():
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"Помилка конвертації .docx у .pdf (код {result.returncode}): {stderr}")
        return pdf_path.read_bytes()


def convert_docx_bytes_to_pdf(docx_bytes: bytes) -> bytes:
    global _last_failure_time, _last_failure_reason

    soffice = _find_soffice()
    if soffice is None:
        raise RuntimeError(
            "Не знайдено LibreOffice (soffice). Встановіть LibreOffice або вкажіть "
            "шлях до soffice через змінну середовища SOFFICE_PATH."
        )

    if _last_failure_time is not None and (time.time() - _last_failure_time) < _FAILURE_COOLDOWN:
        raise RuntimeError(f"LibreOffice нещодавно вже не спрацював, повторна спроба відкладена: {_last_failure_reason}")

    with _convert_lock:
        try:
            result = _convert_once(soffice, docx_bytes, timeout=60)
            _last_failure_time = None
            return result
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            _last_failure_time = time.time()
            _last_failure_reason = str(exc)
            raise RuntimeError(f"Не вдалося конвертувати .docx у .pdf: {exc}") from exc
