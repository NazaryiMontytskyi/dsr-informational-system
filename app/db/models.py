import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserRole(str, enum.Enum):
    STAFF = "staff"   # працівник ВРСП
    HEAD = "head"     # керівник гуртка


class SignatoryRole(str, enum.Enum):
    """Особи, відповідальні за підписання/погодження наказів -- налаштовуються в адмінпанелі."""

    ORDER = "order"              # підписант усіх наказів про гуртки (створення/зміна назви/зміна керівника/закриття)
    VRSP_CHIEF = "vrsp_chief"     # Начальник ВРСП (погодження)
    HR_CHIEF = "hr_chief"          # Начальник відділу кадрів (погодження)


SIGNATORY_ROLE_LABELS: dict[SignatoryRole, str] = {
    SignatoryRole.ORDER: "Підписант наказів про гуртки",
    SignatoryRole.VRSP_CHIEF: "Начальник ВРСП (погодження)",
    SignatoryRole.HR_CHIEF: "Начальник відділу кадрів (погодження)",
}


class FacultyKind(str, enum.Enum):
    FACULTY = "faculty"       # факультет -> декан
    INSTITUTE = "institute"   # навчально-науковий інститут -> директор


class ClubDirection(str, enum.Enum):
    SCIENTIFIC = "scientific"
    ENGINEERING = "engineering"
    SOCIOHUMANITARIAN = "sociohumanitarian"
    SPORTS = "sports"


DIRECTION_LABELS: dict[ClubDirection, dict[str, str]] = {
    ClubDirection.SCIENTIFIC: {"nomn": "наукове", "gent": "наукового", "plur_gent": "наукових"},
    ClubDirection.ENGINEERING: {"nomn": "інженерне", "gent": "інженерного", "plur_gent": "інженерних"},
    ClubDirection.SOCIOHUMANITARIAN: {
        "nomn": "соціогуманітарне",
        "gent": "соціогуманітарного",
        "plur_gent": "соціогуманітарних",
    },
    ClubDirection.SPORTS: {"nomn": "спортивне", "gent": "спортивного", "plur_gent": "спортивних"},
}


class PositionType(str, enum.Enum):
    ASSISTANT = "assistant"
    SENIOR_LECTURER = "senior_lecturer"
    ASSOC_PROFESSOR = "assoc_professor"
    PROFESSOR = "professor"
    OTHER = "other"   # "не є педагогічним або науково-педагогічним працівником"


POSITION_LABELS: dict[PositionType, str] = {
    PositionType.ASSISTANT: "асистент",
    PositionType.SENIOR_LECTURER: "старший викладач",
    PositionType.ASSOC_PROFESSOR: "доцент",
    PositionType.PROFESSOR: "професор",
}


class RegulationType(str, enum.Enum):
    STANDARD = "standard"
    CUSTOM = "custom"


class ClubStatus(str, enum.Enum):
    DRAFT = "draft"                                  # ініціатор ще переглядає форму/наказ перед підтвердженням
    PENDING_VRSP_REVIEW = "pending_vrsp_review"   # верифікація ВРСП форми
    PENDING_SIGNATURE = "pending_signature"        # "Перебуває в узгодженні"
    REGISTERED = "registered"                       # "Зареєстрований"
    REJECTED = "rejected"                            # "Відмовлено"
    CLOSED = "closed"                                # "Закритий"


class RequestType(str, enum.Enum):
    RENAME = "rename"
    CHANGE_HEAD = "change_head"
    CLOSE = "close"


class HeadChangeMode(str, enum.Enum):
    MUTUAL = "mutual"   # зміна керівника за згодою сторін
    ADD = "add"          # додавання співкерівника
    REMOVE = "remove"    # вилучення співкерівника


class RequestStatus(str, enum.Enum):
    DRAFT = "draft"           # керівник ще переглядає згенерований наказ перед підтвердженням
    ASSIGNED = "assigned"   # "Призначено"
    REJECTED = "rejected"    # "Відмовлено"
    DONE = "done"             # "Виконано"


class ClubRequestHeadAction(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"


# ---------- BP-5: Звітування гуртка ----------

class Semester(str, enum.Enum):
    SPRING = "spring"   # весняний
    AUTUMN = "autumn"    # осінній


SEMESTER_LABELS: dict[Semester, str] = {
    Semester.SPRING: "весняний",
    Semester.AUTUMN: "осінній",
}


class StudentCourse(str, enum.Enum):
    BACHELOR_1 = "bachelor_1"
    BACHELOR_2 = "bachelor_2"
    BACHELOR_3 = "bachelor_3"
    BACHELOR_4 = "bachelor_4"
    MASTER_1 = "master_1"
    MASTER_2 = "master_2"
    POSTGRAD_1 = "postgrad_1"
    POSTGRAD_2 = "postgrad_2"
    POSTGRAD_3 = "postgrad_3"
    POSTGRAD_4 = "postgrad_4"


STUDENT_COURSE_LABELS: dict[StudentCourse, str] = {
    StudentCourse.BACHELOR_1: "1 курс бакалаврату",
    StudentCourse.BACHELOR_2: "2 курс бакалаврату",
    StudentCourse.BACHELOR_3: "3 курс бакалаврату",
    StudentCourse.BACHELOR_4: "4 курс бакалаврату",
    StudentCourse.MASTER_1: "1 курс магістратури",
    StudentCourse.MASTER_2: "2 курс магістратури",
    StudentCourse.POSTGRAD_1: "1 курс аспірантури",
    StudentCourse.POSTGRAD_2: "2 курс аспірантури",
    StudentCourse.POSTGRAD_3: "3 курс аспірантури",
    StudentCourse.POSTGRAD_4: "4 курс аспірантури",
}


class EducationLevel(str, enum.Enum):
    BACHELOR = "bachelor"
    MASTER = "master"
    POSTGRAD = "postgrad"


EDUCATION_LEVEL_LABELS: dict[EducationLevel, str] = {
    EducationLevel.BACHELOR: "бакалавр",
    EducationLevel.MASTER: "магістр",
    EducationLevel.POSTGRAD: "аспірант",
}


class EventType(str, enum.Enum):
    CONFERENCE = "conference"
    HACKATHON = "hackathon"
    COMPETITION = "competition"
    OLYMPIAD = "olympiad"
    OTHER = "other"


EVENT_TYPE_LABELS: dict[EventType, str] = {
    EventType.CONFERENCE: "конференція",
    EventType.HACKATHON: "хакатон",
    EventType.COMPETITION: "конкурс",
    EventType.OLYMPIAD: "олімпіада",
    EventType.OTHER: "інше",
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, native_enum=False))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Faculty(Base):
    __tablename__ = "faculties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))   # називний відмінок, з малої літери (вживання в тексті наказу)
    abbreviation: Mapped[str] = mapped_column(String(50), default="")
    kind: Mapped[FacultyKind] = mapped_column(SAEnum(FacultyKind, native_enum=False))
    genitive: Mapped[str] = mapped_column(String(255))
    dative: Mapped[str] = mapped_column(String(255))
    instrumental: Mapped[str] = mapped_column(String(255))
    dean_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    departments: Mapped[list["Department"]] = relationship(back_populates="faculty")

    @property
    def head_title(self) -> str:
        return "декан" if self.kind == FacultyKind.FACULTY else "директор"

    @property
    def display_name(self) -> str:
        """Назва факультету з великої літери -- для показу в UI (списки, форми)."""
        return self.name[:1].upper() + self.name[1:] if self.name else self.name


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"))
    name: Mapped[str] = mapped_column(String(255))   # напр. "кафедра філософії"
    genitive: Mapped[str] = mapped_column(String(255))

    faculty: Mapped["Faculty"] = relationship(back_populates="departments")


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(75))
    direction: Mapped[ClubDirection] = mapped_column(SAEnum(ClubDirection, native_enum=False))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"))
    status: Mapped[ClubStatus] = mapped_column(
        SAEnum(ClubStatus, native_enum=False), default=ClubStatus.PENDING_VRSP_REVIEW
    )

    regulation_type: Mapped[RegulationType] = mapped_column(
        SAEnum(RegulationType, native_enum=False), default=RegulationType.STANDARD
    )
    regulation_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    faculty: Mapped["Faculty"] = relationship()
    heads: Mapped[list["ClubHead"]] = relationship(back_populates="club", order_by="ClubHead.id")
    name_history: Mapped[list["ClubNameHistory"]] = relationship(
        back_populates="club", order_by="ClubNameHistory.changed_at"
    )
    requests: Mapped[list["ClubRequest"]] = relationship(back_populates="club", order_by="ClubRequest.created_at")

    @property
    def active_heads(self) -> list["ClubHead"]:
        return [h for h in self.heads if h.is_active]

    @property
    def direction_label(self) -> str:
        return DIRECTION_LABELS[self.direction]["nomn"]


class ClubHead(Base):
    __tablename__ = "club_heads"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))

    full_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255))

    position_type: Mapped[PositionType] = mapped_column(SAEnum(PositionType, native_enum=False))
    position_custom: Mapped[str | None] = mapped_column(String(500), nullable=True)

    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    club: Mapped["Club"] = relationship(back_populates="heads")
    department: Mapped["Department | None"] = relationship()
    user: Mapped["User | None"] = relationship()

    @property
    def position_label(self) -> str:
        if self.position_type == PositionType.OTHER:
            return self.position_custom or ""
        return POSITION_LABELS[self.position_type]


class ClubNameHistory(Base):
    __tablename__ = "club_name_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    old_name: Mapped[str] = mapped_column(String(75))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    club: Mapped["Club"] = relationship(back_populates="name_history")


class ClubRequest(Base):
    """Заявка на зміну назви / зміну керівника / закриття гуртка (BP-2, BP-3, BP-4)."""

    __tablename__ = "club_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    type: Mapped[RequestType] = mapped_column(SAEnum(RequestType, native_enum=False))
    status: Mapped[RequestStatus] = mapped_column(
        SAEnum(RequestStatus, native_enum=False), default=RequestStatus.ASSIGNED
    )

    # BP-2: нова назва гуртка
    new_name: Mapped[str | None] = mapped_column(String(75), nullable=True)

    # BP-3: режим зміни керівника
    head_change_mode: Mapped[HeadChangeMode | None] = mapped_column(
        SAEnum(HeadChangeMode, native_enum=False), nullable=True
    )

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    order_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    club: Mapped["Club"] = relationship(back_populates="requests")
    created_by: Mapped["User"] = relationship()
    head_entries: Mapped[list["ClubRequestHead"]] = relationship(
        back_populates="request", order_by="ClubRequestHead.id"
    )


class ClubRequestHead(Base):
    """Керівник(и), яких заявка (BP-3) додає або знімає з посади гуртка."""

    __tablename__ = "club_request_heads"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("club_requests.id"))
    action: Mapped[ClubRequestHeadAction] = mapped_column(SAEnum(ClubRequestHeadAction, native_enum=False))

    # для action == REMOVE: посилання на наявного керівника гуртка
    existing_head_id: Mapped[int | None] = mapped_column(ForeignKey("club_heads.id"), nullable=True)

    # для action == ADD: дані нового керівника
    full_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_type: Mapped[PositionType | None] = mapped_column(SAEnum(PositionType, native_enum=False), nullable=True)
    position_custom: Mapped[str | None] = mapped_column(String(500), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)

    request: Mapped["ClubRequest"] = relationship(back_populates="head_entries")
    existing_head: Mapped["ClubHead | None"] = relationship()
    department: Mapped["Department | None"] = relationship()

    @property
    def position_label(self) -> str:
        if self.position_type == PositionType.OTHER:
            return self.position_custom or ""
        return POSITION_LABELS[self.position_type] if self.position_type else ""


class DocumentSignatory(Base):
    """Налаштування осіб, відповідальних за підписання/погодження наказів (адмінпанель ВРСП)."""

    __tablename__ = "document_signatories"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[SignatoryRole] = mapped_column(SAEnum(SignatoryRole, native_enum=False), unique=True)
    position_title: Mapped[str] = mapped_column(String(255), default="")
    full_name: Mapped[str] = mapped_column(String(255), default="")


class ReportSession(Base):
    """Сесія збору звітів гуртків за семестр (BP-5) -- відкриває ВРСП."""

    __tablename__ = "report_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    semester: Mapped[Semester] = mapped_column(SAEnum(Semester, native_enum=False))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reports: Mapped[list["ClubReport"]] = relationship(back_populates="session", order_by="ClubReport.submitted_at")

    @property
    def is_active(self) -> bool:
        today = date.today()
        return self.start_date <= today <= self.end_date

    @property
    def is_upcoming(self) -> bool:
        return date.today() < self.start_date

    @property
    def semester_label(self) -> str:
        return SEMESTER_LABELS[self.semester]

    @property
    def title(self) -> str:
        return f"{self.semester_label.capitalize()} семестр {self.year}"


class ClubReport(Base):
    """Звіт гуртка в межах сесії звітування (BP-5)."""

    __tablename__ = "club_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("report_sessions.id"))
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))

    projects_activities: Mapped[str] = mapped_column(Text, default="")
    difficulties: Mapped[str] = mapped_column(Text, default="")
    encouragement: Mapped[str] = mapped_column(Text, default="")
    plans: Mapped[str] = mapped_column(Text, default="")

    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ReportSession"] = relationship(back_populates="reports")
    club: Mapped["Club"] = relationship()
    submitted_by: Mapped["User"] = relationship()
    participants: Mapped[list["ReportParticipant"]] = relationship(
        back_populates="report", order_by="ReportParticipant.id"
    )
    events: Mapped[list["ReportEvent"]] = relationship(back_populates="report", order_by="ReportEvent.id")
    achievements: Mapped[list["ReportAchievement"]] = relationship(
        back_populates="report", order_by="ReportAchievement.id"
    )


class ReportParticipant(Base):
    """Учасник гуртка з числа здобувачів, вказаний у звіті (BP-5, п.1)."""

    __tablename__ = "report_participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("club_reports.id"))
    full_name: Mapped[str] = mapped_column(String(255))
    course: Mapped[StudentCourse] = mapped_column(SAEnum(StudentCourse, native_enum=False))
    group_code: Mapped[str] = mapped_column(String(7))
    education_level: Mapped[EducationLevel] = mapped_column(SAEnum(EducationLevel, native_enum=False))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"))

    report: Mapped["ClubReport"] = relationship(back_populates="participants")
    faculty: Mapped["Faculty"] = relationship()

    @property
    def course_label(self) -> str:
        return STUDENT_COURSE_LABELS[self.course]

    @property
    def education_level_label(self) -> str:
        return EDUCATION_LEVEL_LABELS[self.education_level]


class ReportEvent(Base):
    """Захід (конференція/хакатон/конкурс/тощо), у якому брав участь гурток (BP-5, п.3)."""

    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("club_reports.id"))
    name: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType, native_enum=False))
    event_type_custom: Mapped[str | None] = mapped_column(String(100), nullable=True)
    achievements_description: Mapped[str] = mapped_column(Text)

    report: Mapped["ClubReport"] = relationship(back_populates="events")

    @property
    def type_label(self) -> str:
        if self.event_type == EventType.OTHER:
            return self.event_type_custom or EVENT_TYPE_LABELS[EventType.OTHER]
        return EVENT_TYPE_LABELS[self.event_type]


class ReportAchievement(Base):
    """Досягнення члена гуртка протягом семестру (BP-5, п.4)."""

    __tablename__ = "report_achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("club_reports.id"))
    participant_full_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    report: Mapped["ClubReport"] = relationship(back_populates="achievements")
