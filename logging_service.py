import grpc
from concurrent import futures
import logging_pb2
import logging_pb2_grpc


class LoggingServicer(logging_pb2_grpc.LoggingServiceServicer):
    def __init__(self):
        self.data_storage = {}

    def LogMessage(self, request, context):
        if request.uuid not in self.data_storage:
            self.data_storage[request.uuid] = request.msg
            print(f"gRPC Received: {request.uuid} -> {request.msg}")
        return logging_pb2.LogResponse(status="Stored")

    def GetLogs(self, request, context):
        all_msgs = ", ".join(self.data_storage.values())
        return logging_pb2.LogsResponse(all_msgs=all_msgs)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    logging_pb2_grpc.add_LoggingServiceServicer_to_server(LoggingServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
