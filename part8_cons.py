import hazelcast
import time

def start_consumer(name):
    client = hazelcast.HazelcastClient(cluster_name="dev")
    queue = client.get_queue("bounded-queue").blocking()

    print(f"Consumer {name} ready...")

    while True:
        item = queue.take()
        print(f"Consumer {name} got: {item}")
        time.sleep(0.5)

if __name__ == "__main__":
    import sys
    consumer_name = sys.argv[1] if len(sys.argv) > 1 else "A"
    start_consumer(consumer_name)