import uuid
import httpx
import grpc
from fastapi import FastAPI, HTTPException
from tenacity import retry, stop_after_attempt, wait_fixed
import logging_pb2
import logging_pb2_grpc

app = FastAPI()
LOGGING_GRPC_ADDR = "localhost:50051"
MESSAGES_SERVICE_URL = "http://localhost:8002/message"
channel = grpc.insecure_channel(LOGGING_GRPC_ADDR)
logging_stub = logging_pb2_grpc.LoggingServiceStub(channel)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def call_logging_grpc(msg_id: str, msg: str):
    request = logging_pb2.LogRequest(uuid=msg_id, msg=msg)
    return logging_stub.LogMessage(request)


@app.post("/proxy")
async def handle_post(msg: str):
    msg_id = str(uuid.uuid4())
    try:
        response = call_logging_grpc(msg_id, msg)
        return {"uuid": msg_id, "status": response.status}
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Logging service unavailable: {str(e)}"
        )


@app.get("/proxy")
async def handle_get():
    try:
        log_response = logging_stub.GetLogs(logging_pb2.Empty())
        logs_text = log_response.all_msgs

        async with httpx.AsyncClient() as client:
            msg_response = await client.get(MESSAGES_SERVICE_URL)
            static_text = msg_response.text

        return f"{logs_text} : {static_text}"

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal service error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

