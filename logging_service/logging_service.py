import grpc
import logging
import os
import hazelcast
import httpx
import time
import socket
from concurrent import futures
from shared import logging_pb2
from shared import logging_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("logging-service")

CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://config-server:8888")
SERVICE_NAME = "logging-service"

def register_with_config_server(grpc_port):
    # In Docker, we can use the hostname
    hostname = socket.gethostname()
    address = f"{hostname}:{grpc_port}"
    
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
    logger.error("Could not register with config-server after multiple attempts")

class LoggingServicer(logging_pb2_grpc.LoggingServiceServicer):
    def __init__(self):
        hz_cluster_members = os.getenv("HAZELCAST_MEMBERS", "127.0.0.1:5701").split(",")

        logger.info(f"Connecting to Hazelcast cluster: {hz_cluster_members}")

        self.client = hazelcast.HazelcastClient(
            cluster_members=hz_cluster_members,
            cluster_name="dev",
        )
        self.distributed_map = self.client.get_map("logging_map").blocking()
        logger.info("Connected to Hazelcast Distributed Map 'logging_map'")

    def LogMessage(self, request, context):
        self.distributed_map.put(request.uuid, request.msg)

        logger.info(f" [gRPC] Received and stored: {request.uuid} -> {request.msg}")

        return logging_pb2.LogResponse(status="Stored in Hazelcast")

    def GetLogs(self, request, context):
        all_values = self.distributed_map.values()
        all_msgs = ", ".join([str(val) for val in all_values])

        logger.info(f" [gRPC] Returning all logs. Count: {len(all_values)}")
        return logging_pb2.LogsResponse(all_msgs=all_msgs)


def serve():
    port = os.getenv("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    logging_pb2_grpc.add_LoggingServiceServicer_to_server(LoggingServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info(f"Logging Service started on port {port}")
    server.start()
    
    # Register after starting server
    register_with_config_server(port)
    
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
