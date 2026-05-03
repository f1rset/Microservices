import os
import consul
import socket
import logging
import time

logger = logging.getLogger("consul-utils")

class ConsulClient:
    def __init__(self, host=None, port=8500):
        self.host = host or os.getenv("CONSUL_HOST", "localhost")
        self.port = port
        self.c = consul.Consul(host=self.host, port=self.port)

    def register_service(self, name, port, tags=None, check=None):
        hostname = socket.gethostname()
        # In Docker, hostname is usually the container ID, but for discovery we need the IP or a resolvable name.
        # Inside Docker network, the hostname is resolvable.
        service_id = f"{name}-{hostname}-{port}"
        
        # Basic TTL check if none provided
        if not check:
            check = consul.Check.tcp(hostname, port, interval="10s", timeout="5s")

        while True:
            try:
                self.c.agent.service.register(
                    name=name,
                    service_id=service_id,
                    address=hostname,
                    port=port,
                    tags=tags,
                    check=check
                )
                logger.info(f"Registered service {name} with ID {service_id}")
                break
            except Exception as e:
                logger.warning(f"Failed to register service {name}: {e}. Retrying...")
                time.sleep(2)

    def get_service_addresses(self, name):
        try:
            _, services = self.c.health.service(name, passing=True)
            addresses = []
            for s in services:
                addr = s['Service']['Address']
                port = s['Service']['Port']
                addresses.append(f"{addr}:{port}")
            return addresses
        except Exception as e:
            logger.error(f"Failed to get services for {name}: {e}")
            return []

    def get_kv(self, key, default=None):
        try:
            _, data = self.c.kv.get(key)
            if data and data['Value']:
                return data['Value'].decode('utf-8')
            return default
        except Exception as e:
            logger.error(f"Failed to get KV for {key}: {e}")
            return default
