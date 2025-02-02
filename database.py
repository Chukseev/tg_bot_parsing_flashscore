from sqlalchemy import create_engine, Column, String, Enum, Boolean, BigInteger, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
import environ


env = environ.Env()
environ.Env.read_env()

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column('id', BigInteger, primary_key=True)
    username = Column(String(255))
    firstname = Column(String(255))
    lastname = Column(String(255))
    role = Column(Enum('admin', 'user', name="user_roles"), default='user', nullable=False)
    has_access = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


db_config = {
    'user': env('user_db', ),
    'password': env('password_db', ),
    'host': env('host_db', ),
    'port': env('port_db', ),
    'database': env('database', ),
}

DATABASE_URL = (f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/"
                f"{db_config['database']}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == '__main__':
    init_db()
