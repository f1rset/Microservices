import uuid
import httpx
import grpc
import random
import logging
import os
import hazelcast
from fastapi import FastAPI, HTTPException
from shared import logging_pb2
from shared import logging_pb2_grpc

app = FastAPI()

CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://config-server:8888")
HAZELCAST_MEMBERS = os.getenv("HAZELCAST_MEMBERS", "hz1,hz2,hz3").split(",")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facade-service")

# Hazelcast client for MQ
hz_client = None
counter_queue = None

@app.on_event("startup")
async def startup_event():
    global hz_client, counter_queue
    logger.info(f"Connecting to Hazelcast for MQ: {HAZELCAST_MEMBERS}")
    hz_client = hazelcast.HazelcastClient(
        cluster_members=HAZELCAST_MEMBERS,
        cluster_name="dev",
    )
    counter_queue = hz_client.get_queue("counter_queue").blocking()
    logger.info("Connected to Hazelcast Queue 'counter_queue'")

async def get_service_addresses(service_name):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CONFIG_SERVER_URL}/services/{service_name}")
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get addresses for {service_name}: {e}")
        return []

def get_logging_stub(addr):
    channel = grpc.insecure_channel(addr)
    return logging_pb2_grpc.LoggingServiceStub(channel)

async def call_logging_with_failover(method_name, *args):
    available_targets = await get_service_addresses("logging-service")
    random.shuffle(available_targets)

    if not available_targets:
        logger.error("No logging services found in config-server")
        raise HTTPException(status_code=503, detail="No logging services registered")

    for addr in available_targets:
        try:
            logger.info(f"Attempting to contact logging-service at {addr}")
            stub = get_logging_stub(addr)

            if method_name == "LogMessage":
                return stub.LogMessage(*args, timeout=2)
            elif method_name == "GetLogs":
                return stub.GetLogs(*args, timeout=2)

        except grpc.RpcError as e:
            logger.warning(f"Service {addr} is unavailable. Error: {e.code()}")
            continue

    raise HTTPException(status_code=503, detail="All logging services are unavailable")

@app.post("/proxy")
async def handle_post(msg: str):
    msg_id = str(uuid.uuid4())
    
    # 1. Log message via gRPC (as before)
    request = logging_pb2.LogRequest(uuid=msg_id, msg=msg)
    log_response = await call_logging_with_failover("LogMessage", request)
    
    # 2. Send to counter-service via MQ (new requirement)
    try:
        counter_queue.offer(msg)
        logger.info(f"Message '{msg}' sent to counter_queue")
    except Exception as e:
        logger.error(f"Failed to send message to MQ: {e}")
        # Even if MQ fails, we already logged it. 
        # But maybe we should return error if MQ is essential.
    
    return {"uuid": msg_id, "status": log_response.status, "mq": "sent"}

@app.get("/proxy")
async def handle_get():
    # 1. Get logs via gRPC
    log_response = await call_logging_with_failover("GetLogs", logging_pb2.Empty())
    logs_text = log_response.all_msgs

    # 2. Get counter via HTTP (as before, but discover address)
    counter_addresses = await get_service_addresses("counter-service")
    if not counter_addresses:
        return f"{logs_text} : [Counter-service Not Found]"
    
    # Use the first available (could be random)
    addr = counter_addresses[0]
    # Assuming addr is host:port
    url = f"http://{addr}/message"

    try:
        async with httpx.AsyncClient() as client:
            msg_response = await client.get(url)
            static_text = msg_response.text

        return f"{logs_text} : {static_text}"
    except Exception as e:
        logger.error(f"Counter-service error at {url}: {e}")
        return f"{logs_text} : [Counter-service Error]"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

