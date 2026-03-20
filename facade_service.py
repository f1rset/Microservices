import uuid
import httpx
import grpc
import random
import logging
from fastapi import FastAPI, HTTPException
import logging_pb2
import logging_pb2_grpc

app = FastAPI()

LOGGING_SERVICES = ["logging-1:50051", "logging-2:50051", "logging-3:50051"]
MESSAGES_SERVICE_URL = "http://counter-service:8002/message"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facade-service")


def get_logging_stub(addr):
    channel = grpc.insecure_channel(addr)
    return logging_pb2_grpc.LoggingServiceStub(channel)


def call_logging_with_failover(method_name, *args):
    available_targets = list(LOGGING_SERVICES)
    random.shuffle(available_targets)

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
    request = logging_pb2.LogRequest(uuid=msg_id, msg=msg)

    response = call_logging_with_failover("LogMessage", request)
    return {"uuid": msg_id, "status": response.status}


@app.get("/proxy")
async def handle_get():
    log_response = call_logging_with_failover("GetLogs", logging_pb2.Empty())
    logs_text = log_response.all_msgs

    try:
        async with httpx.AsyncClient() as client:
            msg_response = await client.get(MESSAGES_SERVICE_URL)
            static_text = msg_response.text

        return f"{logs_text} : {static_text}"
    except Exception as e:
        logger.error(f"Counter-service error: {e}")
        return f"{logs_text} : [Counter-service Error]"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

