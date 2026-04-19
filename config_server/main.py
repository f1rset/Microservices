from fastapi import FastAPI, Request
import uvicorn
import logging

app = FastAPI()
services = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("config-server")

@app.post("/register")
async def register(request: Request):
    data = await request.json()
    service_name = data.get("service_name")
    address = data.get("address")
    
    if service_name not in services:
        services[service_name] = set()
    
    services[service_name].add(address)
    logger.info(f"Registered {service_name} at {address}")
    return {"status": "registered"}

@app.get("/services/{service_name}")
async def get_service(service_name: str):
    logger.info(f"Getting addresses for {service_name}")
    return list(services.get(service_name, []))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
