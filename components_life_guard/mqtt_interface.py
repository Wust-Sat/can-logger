import json
import asyncio
from typing import Optional
import paho.mqtt.client as mqtt
from pydantic import BaseModel
from components_life_guard.life_center import LifeGuard

class MQTTConfig(BaseModel):
    broker_host: str = "localhost"
    broker_port: int = 1883
    topic_prefix: str = "lifeguard"
    username: Optional[str] = None
    password: Optional[str] = None

class LifeGuardMQTT(LifeGuard):
    def __init__(self, mqtt_config: MQTTConfig):
        super().__init__()
        self.mqtt_config = mqtt_config
        self.mqtt_client = mqtt.Client()
        self._setup_mqtt()

    def _setup_mqtt(self):
        """Konfiguruje połączenie z Mosquitto."""
        if self.mqtt_config.username and self.mqtt_config.password:
            self.mqtt_client.username_pw_set(
                self.mqtt_config.username,
                self.mqtt_config.password
            )

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.connect(
            self.mqtt_config.broker_host,
            self.mqtt_config.broker_port
        )

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT (code: {rc})")
        print(f"Subscribed to: {self.mqtt_config.topic_prefix}/status/get")
        client.subscribe(f"{self.mqtt_config.topic_prefix}/status/get")
        client.subscribe(f"{self.mqtt_config.topic_prefix}/device/+/set")

    def _on_mqtt_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic == f"{self.mqtt_config.topic_prefix}/status/get":
            self._publish_status()

        elif topic.startswith(f"{self.mqtt_config.topic_prefix}/device/"):
            node_id = int(topic.split("/")[-2])
            self.send_state_change(node_id, payload)

    def _publish_status(self):
        """Wysyła status urządzeń na temat `lifeguard/status`."""
        status_data = {
            dev.node_id: {
                "name": dev.name,
                "status": dev.status.name
            } for dev in self.devices
        }
        print(f"Publishing to {self.mqtt_config.topic_prefix}/status: {status_data}")
        self.mqtt_client.publish(
            f"{self.mqtt_config.topic_prefix}/status",
            json.dumps(status_data)
        )

    async def start(self):
        self.mqtt_client.loop_start()
        await super().start()

    async def stop(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        await super().stop()