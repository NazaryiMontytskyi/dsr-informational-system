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
    SignatoryRole.ORDER: "Проректор з навчальної роботи",
    SignatoryRole.VRSP_CHIEF: "Начальник ВРСП",
    SignatoryRole.HR_CHIEF: "Начальник відділу кадрів",
}

# Повний перелік факультетів/інститутів КПІ ім. Ігоря Сікорського --
# з FACULTIES.md. Назви навмисно з малої літери (вживання в тексті
# наказу: "закріпити його за факультетом...", "деканові факультету...").
# У списку окремих кафедр немає -- для 5 підрозділів лишено реальні
# кафедри (використовуються найчастіше в прикладах), для решти доданий
# один умовний запис-заглушка "кафедра (уточнюється)", який варто
# замінити на реальний перелік кафедр цього підрозділу.
_PLACEHOLDER_DEPARTMENT = "кафедра (уточнюється)"

FACULTIES: list[dict] = [
    {
        "name": "факультет інформатики та обчислювальної техніки",
        "abbreviation": "ФІОТ",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра інформатики та програмної інженерії",
            "кафедра обчислювальної техніки",
            "кафедра інформаційних систем і технологій",
            "кафедра інтелектуальних та ігрових систем",
        ],
    },
    {
        "name": "факультет програмних систем та прикладної математики",
        "abbreviation": "ФПСПМ",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра прикладної математики",
            "кафедра системного програмування і спеціалізованих комп'ютерних систем",
            "кафедра програмного забезпечення комп'ютерних систем",
        ],
    },
    {
        "name": "факультет автоматизації, промислової інженерії та екології",
        "abbreviation": "ФАПІЕ",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "факультет біотехнології та біотехніки",
        "abbreviation": "ФБТ",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "хіміко-технологічний факультет",
        "abbreviation": "ХТФ",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "факультет біомедичної інженерії",
        "abbreviation": "ФБМІ",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "факультет соціології і права",
        "abbreviation": "ФСП",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра інтелектуальної власності та приватного права",
            "кафедра інформаційного, господарського та адміністративного права",
            "кафедра історії",
            "кафедра психології та педагогіки",
            "кафедра соціології",
            "кафедра теорії та практики управління",
            "кафедра філософії",
        ],
    },
    {
        "name": "факультет лінгвістики",
        "abbreviation": "ФЛ",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "факультет електроніки",
        "abbreviation": "ФЕЛ",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра мікроелектроніки",
            "кафедра електронних пристроїв та систем",
            "кафедра електронної інженерії",
            "кафедра конструювання електронно-обчислювальної апаратури",
            "кафедра акустичних та мультимедійних електронних систем",
        ],
    },
    {
        "name": "радіотехнічний факультет",
        "abbreviation": "РТФ",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра прикладної радіотехніки",
            "кафедра радіоінженерії",
            "кафедра радіотехнічних систем",
        ],
    },
    {
        "name": "факультет менеджменту і маркетингу",
        "abbreviation": "ФММ",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра менеджменту",
            "кафедра маркетингу і комунікаційного дизайну",
        ],
    },
    {
        "name": "факультет електроенерготехніки та автоматики",
        "abbreviation": "ФЕА",
        "kind": FacultyKind.FACULTY,
        "departments": [
            "кафедра автоматизації електромеханічних систем та електроприводу",
            "кафедра електричних мереж та систем",
        ],
    },
    {
        "name": "факультет робототехніки та приладобудування",
        "abbreviation": "ФРП",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "фізико-математичний факультет",
        "abbreviation": "ФМФ",
        "kind": FacultyKind.FACULTY,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "навчально-науковий інститут прикладного системного аналізу",
        "abbreviation": "НН ІПСА",
        "kind": FacultyKind.INSTITUTE,
        "departments": [
            "кафедра математичних методів системного аналізу",
            "кафедра системного проєктування",
        ],
    },
    {
        "name": "навчально-науковий інститут атомної та теплової енергетики",
        "abbreviation": "НН ІАТЕ",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "навчально-науковий інститут аерокосмічних технологій",
        "abbreviation": "НН ІАТ",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "навчально-науковий фізико-технічний інститут",
        "abbreviation": "НН ФТІ",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "навчально-науковий механіко-машинобудівний інститут",
        "abbreviation": "НН ММІ",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "навчально-науковий інститут матеріалознавства і зварювання імені Є. О. Патона",
        "abbreviation": "НН ІМЗ ім. Є. О. Патона",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        # "енергозбереження" -- нейтральний іменник, у якого називний і
        # родовий відмінки збігаються (як-от "питання"), тому автоматична
        # евристика хибно відмінює цей "хвіст" у давальному/орудному --
        # форми задані вручну.
        "name": "навчально-науковий інститут енергозбереження та енергоменеджменту",
        "abbreviation": "НН ІЕЕ",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
        "dative_override": "навчально-науковому інституту енергозбереження та енергоменеджменту",
        "instrumental_override": "навчально-науковим інститутом енергозбереження та енергоменеджменту",
    },
    {
        "name": "навчально-науковий видавничо-поліграфічний інститут",
        "abbreviation": "НН ВПІ",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
    },
    {
        "name": "навчально-науковий інститут телекомунікаційних систем",
        "abbreviation": "НН ІТС",
        "kind": FacultyKind.INSTITUTE,
        "departments": [_PLACEHOLDER_DEPARTMENT],
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
                    abbreviation=entry["abbreviation"],
                    kind=entry["kind"],
                    genitive=decline_headword_phrase(name, "gent"),
                    dative=entry.get("dative_override") or decline_headword_phrase(name, "datv"),
                    instrumental=entry.get("instrumental_override") or decline_headword_phrase(name, "ablt"),
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
