from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from database import User


def create_user(db: Session, id: int, username: str, firstname: str, lastname: str):
    db_user = User(id=id, username=username, firstname=firstname, lastname=lastname)
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()


def get_user_role(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first().role


def get_all_users(db: Session):
    return db.query(User).filter(User.role != 'admin').order_by(User.created_at).all()


def get_status(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first().has_access


def update_user_status(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if user.has_access:
            user.has_access = False
        else:
            user.has_access = True
        db.commit()
        db.refresh(user)
    return user


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def is_admin(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    return user and user.role == "admin"