from grpc_tools import protoc


def generate_stubs():
    print("Generating gRPC stubs from logging.proto...")
    result = protoc.main(
        (
            "",
            "-I.",
            "--python_out=.",
            "--grpc_python_out=.",
            "logging.proto",
        )
    )
    if result == 0:
        print("Success: logging_pb2.py and logging_pb2_grpc.py generated.")
    else:
        print("Error: gRPC stub generation failed.")


if __name__ == "__main__":
    generate_stubs()
