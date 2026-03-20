import time
import os
from fastapi import FastAPI
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/counter_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MessageCounter(Base):
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, index=True)
    count = Column(Integer, default=0)


while True:
    try:
        Base.metadata.create_all(bind=engine)
        break
    except Exception:
        time.sleep(1)


@app.get("/message")
async def get_and_increment_count():
    db = SessionLocal()
    try:
        counter = db.query(MessageCounter).first()
        if not counter:
            counter = MessageCounter(count=0)
            db.add(counter)
        counter.count += 1
        db.commit()
        return f"Total messages processed and saved in DB: {counter.count}"
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
