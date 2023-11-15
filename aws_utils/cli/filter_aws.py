from multiprocessing import Pool
from typing import Tuple

import click
from click_tools import FileIterStringParamType

from aws_utils import is_aws as main_is_aws


def is_aws(target: str) -> Tuple[str, str]:
    return (target, main_is_aws(target))


def iter_input(domain_list, concurrency):
    """Run parallel requests"""
    with Pool(processes=concurrency) as mp_pool:
        results = mp_pool.imap_unordered(is_aws, (target.strip() for target in domain_list))
        for target, is_aws_flag in results:
            if not is_aws_flag:
                continue

            yield target


@click.command()
@click.option("-c", "--concurrency", help="set the concurrency level", type=int, default=40, show_default=True)
@click.argument("target-list", type=FileIterStringParamType("r"), default="-")
def cli(concurrency, target_list):
    """Given a list of domains/ips outputs those belonging to AWS."""
    for host in iter_input(target_list, concurrency):
        click.secho(host, fg="green")


if __name__ == "__main__":
    cli()
