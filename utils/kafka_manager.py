import json
import time
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from config import load_config


class KafkaManager:
    """
    Kafka Manager class that handles both producing and consuming messages
    """

    def __init__(self):
        """
        Initialize KafkaManager
        """
        # Load configuration
        config = load_config()
        self.BOOTSTRAP_SERVERS = config.kafka.bootstrap_servers
        self.TOPIC = config.kafka.topic
        self.producer = None
        self.consumer = None

    def create_producer(self):
        """
        Create a Kafka producer instance
        """
        self.producer = KafkaProducer(
            bootstrap_servers=self.BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=5,
            request_timeout_ms=30000
        )
        return self.producer

    def send_message(self, message, key=None):
        """
        Send a message to Kafka topic
        """
        if not self.producer:
            self.create_producer()

        try:
            future = self.producer.send(self.TOPIC, key=key, value=message)
            # Wait for the send operation to complete
            record_metadata = future.get(timeout=30)
            print(f"Message sent successfully:")
            print(f"  Topic: {record_metadata.topic}")
            print(f"  Partition: {record_metadata.partition}")
            print(f"  Offset: {record_metadata.offset}")
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def send_messages(self, messages):
        """
        Send multiple messages to Kafka topic
        """
        if not self.producer:
            self.create_producer()

        try:
            for i, msg in enumerate(messages):
                key = f"key-{i}"  # Optional key for message
                self.send_message(msg, key)
                time.sleep(0.1)  # Small delay between messages

            print("All messages sent!")
            return True
        except Exception as e:
            print(f"Error sending messages: {e}")
            return False

    def close_producer(self):
        """
        Close the Kafka producer
        """
        if self.producer:
            self.producer.close()
            self.producer = None

    def create_consumer(self, group_id='python-kafka-consumer-group'):
        """
        Create a Kafka consumer instance
        """
        self.consumer = KafkaConsumer(
            self.TOPIC,
            bootstrap_servers=self.BOOTSTRAP_SERVERS,
            group_id=group_id,
            auto_offset_reset='latest',  # Start from latest messages
            enable_auto_commit=True,  # Automatically commit offsets
            auto_commit_interval_ms=1000,  # Commit offsets every second
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=30000  # Stop iterating if no message found for 30 seconds
        )
        return self.consumer

    def consume_messages(self, max_messages=None):
        """
        Consume messages from Kafka topic
        """
        if not self.consumer:
            self.create_consumer()

        print(f"Starting consumer for topic: {self.TOPIC}")
        print("Waiting for messages... (Press Ctrl+C to stop)")
        
        message_count = 0
        try:
            for message in self.consumer:
                print(f"\nReceived message:")
                print(f"  Topic: {message.topic}")
                print(f"  Partition: {message.partition}")
                print(f"  Offset: {message.offset}")
                print(f"  Key: {message.key}")
                print(f"  Value: {message.value}")
                print(f"  Timestamp: {message.timestamp}")
                
                message_count += 1
                if max_messages and message_count >= max_messages:
                    break
                    
        except KeyboardInterrupt:
            print("\nConsumer interrupted by user")
        except Exception as e:
            print(f"Error consuming messages: {e}")
        finally:
            self.close_consumer()
            print("Consumer closed")

    def close_consumer(self):
        """
        Close the Kafka consumer
        """
        if self.consumer:
            self.consumer.close()
            self.consumer = None

    def __enter__(self):
        """
        Context manager entry
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit
        """
        self.close_producer()
        self.close_consumer()


def main():
    """
    Main function demonstrating both producer and consumer functionality
    """
    print("Kafka Manager Demo")
    print("1. Send sample messages")
    print("2. Consume messages")
    print("3. Exit")
    
    choice = input("Enter your choice (1/2/3): ").strip()
    
    kafka_manager = KafkaManager()
    
    if choice == '1':
        # Example messages to send
        messages = [
            {"id": 1, "name": "Product A", "price": 29.99},
            {"id": 2, "name": "Product B", "price": 39.99},
            {"id": 3, "name": "Product C", "price": 19.99}
        ]
        
        with kafka_manager:
            kafka_manager.send_messages(messages)
            
    elif choice == '2':
        max_msgs = input("Enter max messages to consume (or press Enter for unlimited): ").strip()
        max_msgs = int(max_msgs) if max_msgs else None
        
        with kafka_manager:
            kafka_manager.consume_messages(max_msgs)
            
    elif choice == '3':
        print("Exiting...")
        return
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()