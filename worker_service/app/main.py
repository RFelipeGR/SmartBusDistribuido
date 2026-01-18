import os
import time
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "telemetry.events")

def connect_with_retry(max_attempts: int = 30, delay_seconds: int = 2):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)

    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            return pika.BlockingConnection(params)
        except Exception as e:
            last_err = e
            print(f"[worker] RabbitMQ not ready (attempt {attempt}/{max_attempts}). Retrying in {delay_seconds}s...")
            time.sleep(delay_seconds)

    raise last_err

def main():
    connection = connect_with_retry()
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        print(f"[worker] Event received: {body.decode('utf-8')}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)

    print(f"[worker] Consuming from queue: {RABBITMQ_QUEUE}")
    channel.start_consuming()

if __name__ == "__main__":
    main()
