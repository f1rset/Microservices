import grpc
import logging
import os
import hazelcast
from concurrent import futures
import logging_pb2
import logging_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("logging-service")


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
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
