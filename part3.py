import hazelcast

client = hazelcast.HazelcastClient()
dist_map = client.get_map("distributed-map").blocking()

for i in range(1000):
    dist_map.put(i, f"Value-{i}")

print(f"Map size: {dist_map.size()}")
client.shutdown()
