import click
from click_tools import FileUrlIterStringParamType

from aws_utils.queue_manager import QueueManager


@click.command()
@click.option("--fifo", is_flag=True, default=False, help="Use FIFO queue.")
@click.option("--avoid-duplicates / --allow-duplicates", "avoid_duplicates", is_flag=True, default=True, help="Allow duplicates.")
@click.argument("queue_name", type=str)
@click.argument("message_file", type=FileUrlIterStringParamType("r"), default="-")
def cli(fifo, avoid_duplicates, queue_name, message_file):
    """Simple CLI for sending messages to an AWS SQS queue."""
    queue_manager = QueueManager(queue_name, fifo=fifo, deduplicate=avoid_duplicates)

    bulk = []
    for msg in message_file:
        msg = msg.strip()
        click.echo(msg)

        bulk.append(msg)

        if len(bulk) == 10:
            queue_manager + bulk
            bulk = []

    if bulk:
        queue_manager + bulk

if __name__ == "__main__":
    cli()
