import hazelcast
import time
import sys


def get_client_map(map_name):
    # Ensure cluster_name matches your Docker config
    client = hazelcast.HazelcastClient(cluster_name="dev")
    return client, client.get_map(map_name).blocking()


def increment_no_lock(m, iterations):
    for _ in range(iterations):
        val = m.get("key")
        val += 1
        m.put("key", val)  # Race condition expected


def increment_pessimistic(m, iterations):
    for _ in range(iterations):
        m.lock("key")  # Blocks other clients
        try:
            val = m.get("key")
            m.put("key", val + 1)
        finally:
            m.unlock("key")


def increment_optimistic(m, iterations):
    for _ in range(iterations):
        while True:
            old_val = m.get("key")
            new_val = old_val + 1
            if m.replace_if_same("key", old_val, new_val):  # Atomic conditional update
                break


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "no_lock"
    iters = 10000

    client, m = get_client_map("counting_map")

    print(f"Starting {mode} for {iters} iterations...")
    start_time = time.perf_counter()  # High resolution timer [cite: 88, 89]

    if mode == "no_lock":
        increment_no_lock(m, iters)
    elif mode == "pessimistic":
        increment_pessimistic(m, iters)
    elif mode == "optimistic":
        increment_optimistic(m, iters)

    end_time = time.perf_counter()
    duration = end_time - start_time

    print(f"Finished {mode}")
    print(f"Time taken: {duration:.4f} seconds")
    print(f"Final Value in Map: {m.get('key')}")

    client.shutdown()
