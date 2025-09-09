from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

###### PostgreSQL database 
DATABASE_URL = "postgresql://admin:admin@localhost:5432/polyminder"
dev_engine = create_engine(DATABASE_URL)


# ########### currently the stable database 
# DEV_DATABASE_URL = "postgresql://admin:admin@localhost:5433/polyminder_dev"
# dev_engine = create_engine(DEV_DATABASE_URL)

##### SQLite database URL
# DATABASE_URL = "sqlite:///./data.db"
# engine = create_engine(
#     DATABASE_URL, connect_args={"check_same_thread": False}
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# SessionLocal = sessionmaker(bind=engine)
dev_SessionLocal = sessionmaker(bind=dev_engine)

Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def get_dev_db():
    db = dev_SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Base.metadata.create_all(engine)
# Base.metadata.create_all(dev_engine)
# pg_dump -U admin -h localhost -p 5432 polyminder > /home/antrieu/dump.sql