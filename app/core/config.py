import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dsr_digital.db'}")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_COOKIE_NAME = "dsr_session"

STUDENT_EMAIL_DOMAIN = "@edu.kpi.ua"

CLUB_NAME_MIN_LEN = 3
CLUB_NAME_MAX_LEN = 75
FULL_NAME_MIN_LEN = 10
FULL_NAME_MAX_LEN = 50
MAX_CLUB_HEADS = 3

CLUB_CLOSED_RETENTION_DAYS = 365 * 2

ORDER_TEMPLATES_DIR = BASE_DIR / "app" / "order_templates"

# Підписанти наказів (проректор, начальник ВРСП, начальник відділу кадрів
# тощо) налаштовуються через адмінпанель (/vrsp/settings) і зберігаються
# в таблиці document_signatories -- див. app.db.models.DocumentSignatory.

