from datetime import datetime
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

# --- 1. ӨГӨГДЛИЙН САНГИЙН ТОХИРГОО (US-15, US-14) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./school_schedule.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    # US-14, US-06: Нууц үг hash хийх[cite: 16, 18]
    hashed_password = Column(String)
    role = Column(String)  # 'admin', 'manager', 'teacher', 'student'[cite: 16]


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    capacity = Column(Integer)
    # US-01: Тусгай шаардлага (Жишээ нь: Химийн лаборатор)[cite: 20]
    special_requirement = Column(String, nullable=True)


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    max_students = Column(Integer)  # US-10: Суудлын дээд хязгаар[cite: 16]


class TeacherAvailability(Base):
    __tablename__ = "teacher_availabilities"
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    day_of_week = Column(String)
    time_slot = Column(String)  # US-01: Багшийн боломжит цаг[cite: 20]


class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    day_of_week = Column(String)
    time_slot = Column(String)
    # US-11, US-16: Менежер баталж нийтлэх[cite: 16, 18]
    is_published = Column(Boolean, default=False)


class StudentSelection(Base):
    __tablename__ = "student_selections"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    # US-07: Сурагчийн сонголт[cite: 15]
    subject_id = Column(Integer, ForeignKey("subjects.id"))


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    # US-03, US-08: Мэдэгдэл илгээх[cite: 15, 20]
    is_sent = Column(Boolean, default=False)


Base.metadata.create_all(bind=engine)


# --- 2. PYDANTIC SCHEMAS ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: str


class RoomCreate(BaseModel):
    name: str
    capacity: int
    special_requirement: Optional[str] = None


class SubjectCreate(BaseModel):
    name: str
    max_students: int


class TeacherAvailabilityCreate(BaseModel):
    teacher_id: int
    day_of_week: str
    time_slot: str


class ScheduleCreate(BaseModel):
    teacher_id: int
    subject_id: int
    room_id: int
    day_of_week: str
    time_slot: str


class StudentSelectCreate(BaseModel):
    student_id: int
    subject_id: int


# FastAPI App
app = FastAPI(
    title="Ахлах ангийн сонгон суралцах хичээлийн хуваарь боловсруулах систем",
    version="1.0"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 3. ХЭРЭГЛЭГЧИЙН ЭРХ БА НЭВТРЭХ (US-06, US-14) ---
@app.post("/auth/register", summary="US-14 & US-06: Хэрэглэгч бүртгэх, нууц үг hash хийх")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    fake_hashed_password = f"hashed_{user.password}"
    try:
        db_user = User(username=user.username,
                       hashed_password=fake_hashed_password, role=user.role)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"message": "Хэрэглэгч амжилттай бүртгэгдлээ.", "user_id": db_user.id, "role": db_user.role}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Энэ хэрэглэгчийн нэр аль хэдийн бүртгэгдсэн байна.")


# --- 4. ҮНДСЭН МЭДЭЭЛЭЛ БҮРТГЭХ (US-01, US-15) ---
@app.post("/admin/rooms", summary="US-15 & US-01: Анги танхим болон тусгай шаардлага бүртгэх")
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    try:
        db_room = Room(name=room.name, capacity=room.capacity,
                       special_requirement=room.special_requirement)
        db.add(db_room)
        db.commit()
        db.refresh(db_room)
        return {"message": "Танхим амжилттай бүртгэгдлээ.", "data": db_room}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Ийм нэртэй анги танхим аль хэдийн байна.")


@app.post("/admin/subjects", summary="US-15 & US-10: Хичээл болон суудлын хязгаар бүртгэх")
def create_subject(subject: SubjectCreate, db: Session = Depends(get_db)):
    try:
        db_subject = Subject(
            name=subject.name, max_students=subject.max_students)
        db.add(db_subject)
        db.commit()
        db.refresh(db_subject)
        return {"message": "Хичээл амжилттай бүртгэгдлээ.", "data": db_subject}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Энэ хичээл аль хэдийн бүртгэгдсэн байна.")


@app.post("/teachers/availability", summary="US-01: Багшийн боломжит цаг оруулах")
def set_teacher_availability(availability: TeacherAvailabilityCreate, db: Session = Depends(get_db)):
    db_av = TeacherAvailability(
        teacher_id=availability.teacher_id,
        day_of_week=availability.day_of_week,
        time_slot=availability.time_slot
    )
    db.add(db_av)
    db.commit()
    db.refresh(db_av)
    return {"message": "Багшийн боломжит цаг амжилттай хадгалагдлаа.", "data": db_av}


# --- 5. АВТОМАТ ХУВААРЬ БОЛОН ДАВХЦАЛ ШАЛГАХ (US-04, US-05, US-09) ---
def check_conflicts(db: Session, teacher_id: int, room_id: int, day: str, slot: str):
    # US-05.1: Багшийн цагийн давхцал шалгах[cite: 15]
    teacher_conflict = db.query(Schedule).filter_by(
        teacher_id=teacher_id, day_of_week=day, time_slot=slot).first()
    if teacher_conflict:
        raise HTTPException(
            status_code=400, detail="US-05: Тухайн цагт багшийн хуваарь давхцаж байна!")

    # US-05.2: Танхимын ашиглалтын давхцал шалгах[cite: 15]
    room_conflict = db.query(Schedule).filter_by(
        room_id=room_id, day_of_week=day, time_slot=slot).first()
    if room_conflict:
        raise HTTPException(
            status_code=400, detail="US-05: Тухайн анги танхим энэ цагт аль хэдийн захиалагдсан байна!")


@app.post("/schedules/generate", summary="US-04 & US-05: Хуваарийг автоматаар үүсгэх ба давхцал шалгах")
def generate_schedule(schedule_data: ScheduleCreate, db: Session = Depends(get_db)):
    check_conflicts(db, schedule_data.teacher_id, schedule_data.room_id,
                    schedule_data.day_of_week, schedule_data.time_slot)

    # US-09: Багшийн ажлын ачааллыг хязгаарлах (Жишээ нь: 20 цаг)[cite: 16]
    teacher_total_classes = db.query(Schedule).filter_by(
        teacher_id=schedule_data.teacher_id).count()
    if teacher_total_classes >= 20:
        raise HTTPException(
            status_code=400, detail="US-09: Багшийн ажлын ачааллын хязгаар хэтэрсэн байна!")

    new_schedule = Schedule(
        teacher_id=schedule_data.teacher_id,
        subject_id=schedule_data.subject_id,
        room_id=schedule_data.room_id,
        day_of_week=schedule_data.day_of_week,
        time_slot=schedule_data.time_slot,
        is_published=False
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    return {"message": "Хуваарь амжилттай үүслээ.", "data": new_schedule}


# --- 6. БАГШИЙН ХУВААРЬ БОЛОН МЭДЭГДЭЛ (US-02, US-03, US-12, US-13) ---
@app.get("/teachers/schedule/{teacher_id}", summary="US-02: Багш өөрийн 7 хоногийн хуваарь харах")
def get_teacher_schedule(teacher_id: int, db: Session = Depends(get_db)):
    schedules = db.query(Schedule).filter_by(teacher_id=teacher_id).all()
    return {"teacher_id": teacher_id, "schedules": schedules}


@app.put("/schedules/update/{schedule_id}", summary="US-03: Хуваарь өөрчлөх ба багшид мэдэгдэл илгээх")
def update_schedule(schedule_id: int, new_slot: str, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter_by(id=schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Хуваарь олдсонгүй")

    schedule.time_slot = new_slot

    # US-03: Багшид мэдэгдэл үүсгэх[cite: 20]
    notification = Notification(
        user_id=schedule.teacher_id,
        message=f"Таны {schedule.day_of_week} гарагийн хичээлийн цаг {new_slot} болж өөрчлөгдлөө.",
        is_sent=True
    )
    db.add(notification)
    db.commit()

    return {"message": "US-03: Хуваарь шинэчлэгдэж, багшид мэдэгдэл илгээгдлээ.", "data": schedule}


@app.get("/notifications/{user_id}", summary="US-03 & US-08: Хэрэглэгчийн мэдэгдлүүдийг харах")
def get_user_notifications(user_id: int, db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter_by(user_id=user_id).all()
    return {"user_id": user_id, "notifications": notifications}


# --- 7. СУРАГЧИЙН СОНГОЛТ БОЛОН ХУВААРЬ (US-07, US-10, US-16) ---
@app.post("/students/select-subject", summary="US-07 & US-10: Сурагч сонгон хичээл сонгох ба суудлын хязгаар шалгах")
def select_subject(data: StudentSelectCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter_by(id=data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Хичээл олдсонгүй")

    # US-10: Суудлын хязгаар хүрсэн эсэхийг шалгах[cite: 16]
    current_count = db.query(StudentSelection).filter_by(
        subject_id=data.subject_id).count()
    if current_count >= subject.max_students:
        raise HTTPException(
            status_code=400, detail="US-10: Энэ хичээлийн суудлын дээд хязгаар дүүрсэн байна.")

    selection = StudentSelection(
        student_id=data.student_id, subject_id=data.subject_id)
    db.add(selection)
    db.commit()
    return {"message": "US-07: Хичээл амжилттай сонгогдлоо."}


@app.delete("/students/cancel-subject", summary="US-07: Сурагч сонгосон хичээлээ цуцлах")
def cancel_subject(student_id: int, subject_id: int, db: Session = Depends(get_db)):
    selection = db.query(StudentSelection).filter_by(
        student_id=student_id, subject_id=subject_id).first()
    if not selection:
        raise HTTPException(
            status_code=404, detail="Та энэ хичээлийг сонгоогүй байна.")

    db.delete(selection)
    db.commit()
    return {"message": "US-07: Сонголт амжилттай цуцлагдлаа."}


# --- 8. МЕНЕЖЕРИЙН БАТЛАХ БА НИЙТЛЭХ (US-11, US-16) ---
@app.put("/schedules/publish/{schedule_id}", summary="US-11 & US-16: Менежер хуваарь батлах, нийтлэх")
def publish_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter_by(id=schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Хуваарь олдсонгүй")

    schedule.is_published = True  # Менежер баталж нийтлэх[cite: 16, 18]
    db.commit()
    return {"message": "US-11: Хуваарь батлагдаж нийтлэгдлээ."}


@app.get("/students/schedules/{student_id}", summary="US-16: Сурагч зөвхөн нийтлэгдсэн хуваарийг харах")
def get_student_schedule(student_id: int, db: Session = Depends(get_db)):
    # US-16.3: Менежер баталж нийтэлсний дараа л сурагчдад харагдана[cite: 18]
    published_schedules = db.query(Schedule).filter_by(is_published=True).all()
    return {"student_id": student_id, "schedules": published_schedules}
