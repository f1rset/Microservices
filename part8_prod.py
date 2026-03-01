import hazelcast
import time

def start_producer():
    client = hazelcast.HazelcastClient(cluster_name="dev")
    queue = client.get_queue("bounded-queue").blocking()

    for i in range(1, 101):
        print(f"Try put: {i}")
        queue.put(i)
        print(f"Put: {i} (queue size: {queue.size()})")

    client.shutdown()

if __name__ == "__main__":
    start_producer()