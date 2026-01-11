from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///warehouse.db", echo=False)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
