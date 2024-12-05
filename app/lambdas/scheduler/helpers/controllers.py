from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
import queue
import threading
import time
from typing import Generator

from .queries import (
    query_by_gsi,
    update,
)
from .schemas import (
    Invitation,
    InvitationStatus,
)


def send_to_queue(
    data_queue: queue.Queue,
    items_generator: Generator[Invitation, None, None],
):
    for items in items_generator:
        data_queue.put(items)

    # signal no more items
    data_queue.put(None)


def update_expired_status(table, item: Invitation):
    return update(
        table=table,
        email=item["email"],
        code=item["code"],
        payload={"invite_status": InvitationStatus.EXPIRED},
    )


def process_queue(
    table,
    data_queue: queue.Queue,
    executor: ThreadPoolExecutor,
):
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    while True:
        items = data_queue.get()
        if items is None:
            data_queue.task_done()
            break

        to_update_items = [
            x
            for x in items
            if x["expiry_date"] < now_utc
            and x["invite_status"] != InvitationStatus.CONFIRMED
        ]

        t0 = time.time()
        executor.map(partial(update_expired_status, table), to_update_items)
        print(f"Batch update of {len(to_update_items)} items took {time.time()-t0}s")

        data_queue.task_done()


def process_expired_unconfirmed_invitations(
    table,
    gsi_name: str,
):
    data_queue = queue.Queue()
    items_generator = query_by_gsi(
        table=table,
        gsi_name=gsi_name,
        invite_status=InvitationStatus.UNCONFIRMED,
    )

    try:
        executor = ThreadPoolExecutor(max_workers=10)

        producer = threading.Thread(
            target=send_to_queue,
            args=(data_queue, items_generator),
        )
        consumer = threading.Thread(
            target=process_queue,
            args=(table, data_queue, executor),
        )

        producer.start()
        consumer.start()

        producer.join()
        data_queue.join()  # block until all items processed
        consumer.join()

    finally:
        executor.shutdown()
