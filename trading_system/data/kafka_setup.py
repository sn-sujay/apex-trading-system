"""
APEX Trading Intelligence System - Kafka Setup and Management
"""

import logging
from typing import List, Dict, Any, Optional
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic

logger = logging.getLogger("apex.kafka")


class KafkaManager:
    """Kafka topic management and producer/consumer factory"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka manager

        Args:
            bootstrap_servers: Kafka broker addresses
        """
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})
        logger.info(f"Kafka manager initialized: {bootstrap_servers}")

    def create_topics(self) -> Dict[str, bool]:
        """
        Create all required Kafka topics

        Returns:
            Dict of topic_name -> created (bool)
        """
        topics = [
            NewTopic("market.ticks", num_partitions=12, replication_factor=1),
            NewTopic("agent.signals", num_partitions=6, replication_factor=1),
            NewTopic("decisions.output", num_partitions=3, replication_factor=1),
            NewTopic("risk.alerts", num_partitions=3, replication_factor=1),
            NewTopic("execution.orders", num_partitions=3, replication_factor=1),
            NewTopic("performance.metrics", num_partitions=2, replication_factor=1),
        ]

        results = {}

        try:
            # Create topics
            fs = self.admin_client.create_topics(topics, request_timeout=10.0)

            for topic, f in fs.items():
                try:
                    f.result()  # Wait for operation to complete
                    results[topic] = True
                    logger.info(f"Topic created: {topic}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        results[topic] = True
                        logger.info(f"Topic already exists: {topic}")
                    else:
                        results[topic] = False
                        logger.error(f"Failed to create topic {topic}: {e}")

        except Exception as e:
            logger.error(f"Error creating topics: {e}")

        return results

    def get_producer(self) -> Producer:
        """
        Get Kafka producer with JSON serialization

        Returns:
            Configured Kafka Producer
        """
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": "apex-producer",
            "acks": "all",
            "compression.type": "snappy",
            "linger.ms": 10,
            "batch.size": 16384,
        }

        producer = Producer(config)
        logger.info("Kafka producer created")
        return producer

    def get_consumer(
        self,
        topics: List[str],
        group_id: str,
        auto_offset_reset: str = "latest"
    ) -> Consumer:
        """
        Get Kafka consumer

        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID
            auto_offset_reset: Offset reset policy (earliest/latest)

        Returns:
            Configured Kafka Consumer
        """
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": True,
            "session.timeout.ms": 10000,
        }

        consumer = Consumer(config)
        consumer.subscribe(topics)
        logger.info(f"Kafka consumer created: group={group_id}, topics={topics}")
        return consumer

    def topic_health_check(self) -> Dict[str, Any]:
        """
        Check health of all topics

        Returns:
            Health status dict
        """
        try:
            metadata = self.admin_client.list_topics(timeout=5)
            topics = metadata.topics

            health = {
                "status": "healthy",
                "topics": {},
                "broker_count": len(metadata.brokers),
            }

            for topic_name, topic_meta in topics.items():
                if topic_name.startswith("apex.") or topic_name.split(".")[0] in [
                    "market", "agent", "decisions", "risk", "execution", "performance"
                ]:
                    health["topics"][topic_name] = {
                        "partitions": len(topic_meta.partitions),
                        "error": topic_meta.error,
                    }

            return health

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}

    def delete_topic(self, topic: str) -> bool:
        """
        Delete a topic (use with caution)

        Args:
            topic: Topic name

        Returns:
            True if successful

        """
        try:
            fs = self.admin_client.delete_topics([topic], request_timeout=10.0)
            fs[topic].result()
            logger.info(f"Topic deleted: {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete topic {topic}: {e}")
            return False

    def get_topic_offset(self, topic: str, partition: int = 0) -> Optional[int]:
        """
        Get current offset for a topic partition

        Args:
            topic: Topic name
            partition: Partition number

        Returns:
            Current offset or None
        """
        try:
            consumer = self.get_consumer([topic], "offset-checker")

            from confluent_kafka import TopicPartition
            tp = TopicPartition(topic, partition)

            # Get high watermark
            low, high = consumer.get_watermark_offsets(tp, timeout=5)
            consumer.close()

            return high

        except Exception as e:
            logger.error(f"Error getting offset for {topic}: {e}")
            return None
