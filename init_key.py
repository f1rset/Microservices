import hazelcast


def initialize():
    client = hazelcast.HazelcastClient(cluster_name="dev")
    m = client.get_map("counting_map").blocking()
    m.put("key", 0)
    print(f"Initialized 'key' with value: {m.get('key')}")
    client.shutdown()


if __name__ == "__main__":
    initialize()
