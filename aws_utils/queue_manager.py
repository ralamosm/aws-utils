import json
from datetime import datetime

import boto3


def date_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()


class QueueManager:
    """
    Class for managing queues with AWS SQS
    """

    def __init__(self, queue_name, fifo=False, region="us-west-2", visibility_timeout=60, deduplicate=False, retention=60 * 60 * 24 * 14):
        self.queue_name = queue_name.strip()
        self.fifo = fifo
        self.region = region
        self.visibility_timeout = visibility_timeout
        self.deduplicate = deduplicate
        self.retention = str(retention)
        self._url = None

        if self.fifo and not self.queue_name.endswith(".fifo"):
            self.queue_name = f"{self.queue_name}.fifo"
        elif self.queue_name.endswith(".fifo"):
            self.fifo = True

    def serialize(self, message):
        if isinstance(message, (dict, list)):
            message = json.dumps(message, default=date_serializer)
        return message

    def unserialize(self, message):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            pass
        return message

    @property
    def sqs(self):
        if not hasattr(self, "_sqs"):
            self._sqs = boto3.client("sqs", region_name=self.region)
        return self._sqs

    @property
    def url(self):
        if self._url is None:
            queue_attributes = {"MessageRetentionPeriod": self.retention}

            if self.fifo:
                queue_attributes["FifoQueue"] = "true"
                if self.deduplicate:
                    queue_attributes["ContentBasedDeduplication"] = "true"

            response = self.sqs.create_queue(QueueName=self.queue_name, Attributes=queue_attributes)
            self._url = response["QueueUrl"]
        return self._url

    def append(self, message, message_group_id="default"):
        kwargs = {"QueueUrl": self.url, "MessageBody": self.serialize(message)}
        if self.fifo:
            kwargs["MessageGroupId"] = message_group_id
        self.sqs.send_message(**kwargs)

    def send_messages_batch(self, messages, message_group_id="default"):
        for i in range(0, len(messages), 10):
            chunk = messages[i : i + 10]  # noqa E203
            entries = [{"Id": str(i), "MessageBody": self.unserialize(str(msg))} for i, msg in enumerate(chunk)]
            if self.fifo:
                for entry in entries:
                    entry["MessageGroupId"] = message_group_id
            self.sqs.send_message_batch(QueueUrl=self.url, Entries=entries)

    def get_messages(self, num_messages=10):
        response = self.sqs.receive_message(QueueUrl=self.url, MaxNumberOfMessages=num_messages, VisibilityTimeout=self.visibility_timeout)
        return response.get("Messages", [])

    def delete_messages_range(self, start, stop, step):
        messages = self.get_messages(num_messages=stop)
        for i in range(start, stop, step):
            if i < len(messages):
                self.sqs.delete_message(QueueUrl=self.url, ReceiptHandle=messages[i]["ReceiptHandle"])

    def delete_single_message(self, index):
        messages = self.get_messages(num_messages=index + 1)
        if index < len(messages):
            self.sqs.delete_message(QueueUrl=self.url, ReceiptHandle=messages[index]["ReceiptHandle"])
        else:
            raise IndexError("Index out of range.")

    def shift(self, num_items=1):
        """Remove and return the first num_items messages from the queue."""
        messages = self.get_messages(num_messages=num_items)
        if messages:
            if num_items > 1:
                entries = [{"Id": str(i), "ReceiptHandle": msg["ReceiptHandle"]} for i, msg in enumerate(messages)]
                self.sqs.delete_message_batch(QueueUrl=self.url, Entries=entries)
                return [self.unserialize(msg["Body"]) for msg in messages]
            else:
                message = messages[0]
                self.sqs.delete_message(QueueUrl=self.url, ReceiptHandle=message["ReceiptHandle"])
                return self.unserialize(message["Body"])
        else:
            return None

    def __getitem__(self, index):
        messages = self.get_messages(num_messages=index + 1)
        if index < len(messages):
            return self.unserialize(messages[index]["Body"])
        else:
            raise IndexError("Index out of range.")

    def __delitem__(self, item):
        if isinstance(item, slice):
            self.delete_messages_range(item.start, item.stop, item.step)
        elif isinstance(item, int):
            self.delete_single_message(item)
        else:
            raise TypeError("Invalid argument type.")

    def __iter__(self):
        while True:
            messages = self.get_messages(num_messages=10)
            if not messages:
                break
            for message in messages:
                yield self.unserialize(message["Body"])

    def __add__(self, other):
        if not isinstance(other, list):
            raise TypeError('Can only concatenate list (not "{}") to QueueManager'.format(type(other).__name__))

        self.send_messages_batch(other)
        return self