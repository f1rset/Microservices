import time
import os
import threading
import socket
import httpx
import hazelcast
import logging
from fastapi import FastAPI
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("counter-service")

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/counter_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://config-server:8888")
SERVICE_NAME = "counter-service"
HAZELCAST_MEMBERS = os.getenv("HAZELCAST_MEMBERS", "hz1,hz2,hz3").split(",")

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

def register_with_config_server(port):
    hostname = socket.gethostname()
    address = f"{hostname}:{port}"
    
    max_retries = 10
    for i in range(max_retries):
        try:
            with httpx.Client() as client:
                client.post(f"{CONFIG_SERVER_URL}/register", json={
                    "service_name": SERVICE_NAME,
                    "address": address
                })
            logger.info(f"Registered {SERVICE_NAME} at {address} with config-server")
            return
        except Exception as e:
            logger.warning(f"Failed to register with config-server (attempt {i+1}/{max_retries}): {e}")
            time.sleep(2)

def start_mq_consumer():
    logger.info(f"Connecting to Hazelcast for MQ: {HAZELCAST_MEMBERS}")
    client = hazelcast.HazelcastClient(
        cluster_members=HAZELCAST_MEMBERS,
        cluster_name="dev",
    )
    queue = client.get_queue("counter_queue").blocking()
    logger.info("Connected to Hazelcast Queue 'counter_queue'")

    def consume():
        while True:
            try:
                # Take message from queue (blocking)
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
        # Note: The task says facade uses GET for reading. 
        # Usually GET shouldn't increment, but previous implementation did.
        # I'll keep it as just reading if that's what's intended for "reading".
        # But to match previous behavior exactly if needed:
        # counter.count += 1
        # db.commit()
        return f"Total messages processed and saved in DB: {counter.count}"
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    init_db()
    register_with_config_server(8002)
    start_mq_consumer()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
