import uuid
import httpx
import grpc
import random
import logging
import os
import hazelcast
import time
from fastapi import FastAPI, HTTPException
from shared import logging_pb2
from shared import logging_pb2_grpc
from shared.consul_utils import ConsulClient

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facade-service")

SERVICE_NAME = "facade-service"
consul_client = ConsulClient()

# Hazelcast client for MQ
hz_client = None
counter_queue = None

@app.on_event("startup")
async def startup_event():
    global hz_client, counter_queue
    
    # 1. Register with Consul
    consul_client.register_service(SERVICE_NAME, 8000)
    
    # 2. Get Hazelcast config from Consul KV
    hz_members_str = consul_client.get_kv("config/hazelcast/members", "hz1,hz2,hz3")
    hz_cluster_members = hz_members_str.split(",")
    queue_name = consul_client.get_kv("config/mq/queue_name", "counter_queue")

    logger.info(f"Connecting to Hazelcast for MQ: {hz_cluster_members}")
    # Small delay to ensure hz nodes are up if starting all at once
    hz_client = hazelcast.HazelcastClient(
        cluster_members=hz_cluster_members,
        cluster_name="dev",
    )
    counter_queue = hz_client.get_queue(queue_name).blocking()
    logger.info(f"Connected to Hazelcast Queue '{queue_name}'")

def get_logging_stub(addr):
    channel = grpc.insecure_channel(addr)
    return logging_pb2_grpc.LoggingServiceStub(channel)

async def call_logging_with_failover(method_name, *args):
    # Discover via Consul
    available_targets = consul_client.get_service_addresses("logging-service")
    random.shuffle(available_targets)

    if not available_targets:
        logger.error("No logging services found in Consul")
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
    
    # 1. Log message via gRPC
    start_logging = time.time()
    request = logging_pb2.LogRequest(uuid=msg_id, msg=msg)
    log_response = await call_logging_with_failover("LogMessage", request)
    logging_duration = time.time() - start_logging
    
    # 2. Send to counter-service via MQ
    start_mq = time.time()
    try:
        counter_queue.offer(msg)
        logger.info(f"Message '{msg}' sent to counter_queue")
    except Exception as e:
        logger.error(f"Failed to send message to MQ: {e}")
    mq_duration = time.time() - start_mq
    
    return {
        "uuid": msg_id, 
        "status": log_response.status, 
        "mq": "sent",
        "durations": {
            "logging_service": f"{logging_duration:.4f}s",
            "mq_operation": f"{mq_duration:.4f}s"
        }
    }

@app.get("/proxy")
async def handle_get():
    start_total = time.time()
    
    # 1. Get logs via gRPC
    start_logging = time.time()
    log_response = await call_logging_with_failover("GetLogs", logging_pb2.Empty())
    logs_text = log_response.all_msgs
    logging_duration = time.time() - start_logging

    # 2. Discover counter-service via Consul
    start_counter = time.time()
    counter_addresses = consul_client.get_service_addresses("counter-service")
    if not counter_addresses:
        counter_text = "[Counter-service Not Found]"
        counter_duration = time.time() - start_counter
    else:
        addr = counter_addresses[0]
        url = f"http://{addr}/message"
        try:
            async with httpx.AsyncClient() as client:
                msg_response = await client.get(url)
                counter_text = msg_response.text
        except Exception as e:
            logger.error(f"Counter-service error at {url}: {e}")
            counter_text = "[Counter-service Error]"
        counter_duration = time.time() - start_counter

    total_duration = time.time() - start_total
    
    return {
        "result": f"{logs_text} : {counter_text}",
        "durations": {
            "logging_service_contribution": f"{logging_duration:.4f}s",
            "counter_service_contribution": f"{counter_duration:.4f}s",
            "total_time": f"{total_duration:.4f}s"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
