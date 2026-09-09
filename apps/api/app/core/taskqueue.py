"""Task-dispatch abstraction.

The app enqueues background work through `TaskQueue` so the transport can be
swapped without touching business code:

* `LocalTaskQueue` — pushes onto the ARQ Redis queue; the `arq` worker picks it
  up by function name. Used for local dev and this demo.
* `CloudTasksQueue` — production sketch: creates a Google Cloud Task that POSTs
  to an HTTP worker (Cloud Run). Not wired here (no GCP creds); the real body is
  kept as a comment so the swap is explicit — see Fase 13.

This is the answer to prescreening Q3 ("test Cloud Tasks locally without
deploying"): tests and local runs go through `LocalTaskQueue`; the same call
sites work against `CloudTasksQueue` in production.
"""

from abc import ABC, abstractmethod
from typing import Any


class TaskQueue(ABC):
    @abstractmethod
    async def enqueue(self, task: str, *args: Any) -> None:
        """Schedule `task` (a registered worker function name) with `args`."""


class LocalTaskQueue(TaskQueue):
    async def enqueue(self, task: str, *args: Any) -> None:
        from app.workers.queue import get_queue

        queue = await get_queue()
        await queue.enqueue_job(task, *args)


class CloudTasksQueue(TaskQueue):
    def __init__(
        self,
        *,
        project: str,
        location: str,
        queue: str,
        worker_url: str,
        oidc_service_account: str,
    ) -> None:
        self.project = project
        self.location = location
        self.queue = queue
        self.worker_url = worker_url.rstrip("/")
        self.oidc_service_account = oidc_service_account

    async def enqueue(self, task: str, *args: Any) -> None:
        # import json
        # from google.cloud import tasks_v2
        #
        # client = tasks_v2.CloudTasksAsyncClient()
        # parent = client.queue_path(self.project, self.location, self.queue)
        # await client.create_task(
        #     parent=parent,
        #     task={
        #         "http_request": {
        #             "http_method": tasks_v2.HttpMethod.POST,
        #             "url": f"{self.worker_url}/tasks/{task}",
        #             "headers": {"Content-Type": "application/json"},
        #             "body": json.dumps(args).encode(),
        #             "oidc_token": {
        #                 "service_account_email": self.oidc_service_account
        #             },
        #         },
        #         # retry / dead-letter live in the queue config, not here
        #     },
        # )
        raise NotImplementedError(
            "CloudTasksQueue: wire GCP credentials + an HTTP worker router in Fase 13"
        )


def get_task_queue() -> TaskQueue:
    # In production this would branch on config to return CloudTasksQueue(...)
    # with GCP settings; the demo only ever uses the local (ARQ) queue.
    return LocalTaskQueue()
