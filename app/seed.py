"""
Наповнення бази початковими довідковими даними: факультети/інститути,
кафедри та обліковий запис першого працівника ВРСП.

Запуск: python -m app.seed
Ідемпотентний -- повторний запуск нічого не дублює.
"""

from __future__ import annotations

from app.core.security import hash_password
from app.db.models import DocumentSignatory, Department, Faculty, FacultyKind, SignatoryRole, User, UserRole
from app.db.session import Base, SessionLocal, engine
from app.services.morphology import decline_headword_phrase

DEFAULT_SIGNATORIES: dict[SignatoryRole, str] = {
    SignatoryRole.CREATE_ORDER: "Проректор з навчальної роботи",
    SignatoryRole.RENAME_ORDER: "Проректор з навчальної роботи",
    SignatoryRole.CHANGE_HEAD_ORDER: "Проректор з навчальної роботи",
    SignatoryRole.CLOSE_ORDER: "Проректор з навчальної роботи",
    SignatoryRole.VRSP_CHIEF: "Начальник ВРСП",
    SignatoryRole.HR_CHIEF: "Начальник відділу кадрів",
}

FACULTIES: list[dict] = [
    {
        "name": "Факультет інформатики та обчислювальної техніки",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра автоматики та управління в технічних системах",
            "кафедра обчислювальної техніки",
            "кафедра технічної кібернетики",
        ],
    },
    {
        "name": "Факультет соціології і права",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра соціології",
            "кафедра філософії",
            "кафедра права",
        ],
    },
    {
        "name": "Навчально-науковий інститут прикладного системного аналізу",
        "kind": FacultyKind.INSTITUTE,
        "departments": [
            "кафедра математичних методів системного аналізу",
            "кафедра системного проєктування",
        ],
    },
    {
        "name": "Факультет електроенерготехніки та автоматики",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра автоматизації електромеханічних систем та електроприводу",
            "кафедра електричних мереж та систем",
        ],
    },
    {
        "name": "Факультет менеджменту та маркетингу",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра менеджменту",
            "кафедра маркетингу і комунікаційного дизайну",
        ],
    },
]

DEFAULT_STAFF_EMAIL = "vrsp.staff@edu.kpi.ua"
DEFAULT_STAFF_PASSWORD = "changeme123"


def seed() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Faculty).count() == 0:
            for entry in FACULTIES:
                name = entry["name"]
                faculty = Faculty(
                    name=name,
                    kind=entry["kind"],
                    genitive=decline_headword_phrase(name, "gent"),
                    dative=decline_headword_phrase(name, "datv"),
                    instrumental=decline_headword_phrase(name, "ablt"),
                )
                db.add(faculty)
                db.flush()
                for dept_name in entry["departments"]:
                    db.add(
                        Department(
                            faculty_id=faculty.id,
                            name=dept_name,
                            genitive=decline_headword_phrase(dept_name, "gent"),
                        )
                    )
            print(f"Додано факультетів/інститутів: {len(FACULTIES)}")
        else:
            print("Факультети вже існують -- пропускаю.")

        if db.query(User).filter(User.email == DEFAULT_STAFF_EMAIL).first() is None:
            db.add(
                User(
                    email=DEFAULT_STAFF_EMAIL,
                    full_name="Провідний фахівець ВРСП",
                    password_hash=hash_password(DEFAULT_STAFF_PASSWORD),
                    role=UserRole.STAFF,
                )
            )
            print(f"Створено обліковий запис ВРСП: {DEFAULT_STAFF_EMAIL} / {DEFAULT_STAFF_PASSWORD}")
        else:
            print("Обліковий запис ВРСП вже існує -- пропускаю.")

        for role, default_title in DEFAULT_SIGNATORIES.items():
            if db.query(DocumentSignatory).filter(DocumentSignatory.role == role).first() is None:
                db.add(DocumentSignatory(role=role, position_title=default_title, full_name=""))
        print("Перевірено налаштування підписантів.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
