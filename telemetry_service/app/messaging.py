import json
import pika
from datetime import datetime, timezone

class RabbitPublisher:
    def __init__(self, host: str, user: str, password: str, queue: str):
        self.host = host
        self.user = user
        self.password = password
        self.queue = queue

    def publish_event(self, event_type: str, payload: dict):
        credentials = pika.PlainCredentials(self.user, self.password)
        params = pika.ConnectionParameters(host=self.host, credentials=credentials)

        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=self.queue, durable=True)

        message = {
            "event_type": event_type,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        channel.basic_publish(
            exchange="",
            routing_key=self.queue,
            body=json.dumps(message).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
