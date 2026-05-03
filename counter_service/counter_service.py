import time
import os
import threading
import hazelcast
import logging
from fastapi import FastAPI
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from shared.consul_utils import ConsulClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("counter-service")

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/counter_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SERVICE_NAME = "counter-service"
consul_client = ConsulClient()

class MessageCounter(Base):
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, index=True)
    count = Column(Integer, default=0)

def init_db():
    while True:
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception:
            time.sleep(1)

def start_mq_consumer():
    hz_members_str = consul_client.get_kv("config/hazelcast/members", "hz1,hz2,hz3")
    hz_cluster_members = hz_members_str.split(",")
    queue_name = consul_client.get_kv("config/mq/queue_name", "counter_queue")

    logger.info(f"Connecting to Hazelcast for MQ: {hz_cluster_members}")
    client = hazelcast.HazelcastClient(
        cluster_members=hz_cluster_members,
        cluster_name="dev",
    )
    queue = client.get_queue(queue_name).blocking()
    logger.info(f"Connected to Hazelcast Queue '{queue_name}'")

    def consume():
        while True:
            try:
                msg = queue.take()
                logger.info(f"Received message from MQ: {msg}")
                
                db = SessionLocal()
                try:
                    counter = db.query(MessageCounter).first()
                    if not counter:
                        counter = MessageCounter(count=0)
                        db.add(counter)
                    counter.count += 1
                    db.commit()
                    logger.info(f"Updated counter to: {counter.count}")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error in MQ consumer: {e}")
                time.sleep(1)

    thread = threading.Thread(target=consume, daemon=True)
    thread.start()

@app.get("/message")
async def get_and_increment_count():
    db = SessionLocal()
    try:
        counter = db.query(MessageCounter).first()
        if not counter:
            counter = MessageCounter(count=0)
            db.add(counter)
        return f"Total messages processed and saved in DB: {counter.count}"
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    init_db()
    consul_client.register_service(SERVICE_NAME, 8002)
    start_mq_consumer()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
