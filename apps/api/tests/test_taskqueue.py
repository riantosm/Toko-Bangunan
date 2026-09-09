from unittest.mock import AsyncMock

import pytest

from app.core.taskqueue import (
    CloudTasksQueue,
    LocalTaskQueue,
    get_task_queue,
)


def test_get_task_queue_returns_local() -> None:
    assert isinstance(get_task_queue(), LocalTaskQueue)


async def test_local_task_queue_pushes_to_arq(monkeypatch) -> None:
    pool = AsyncMock()
    monkeypatch.setattr(
        "app.workers.queue.get_queue", AsyncMock(return_value=pool)
    )

    await LocalTaskQueue().enqueue("process_intake_job", 7, "Budi", "2 sak semen")

    pool.enqueue_job.assert_awaited_once_with(
        "process_intake_job", 7, "Budi", "2 sak semen"
    )


async def test_cloud_tasks_queue_is_a_sketch() -> None:
    q = CloudTasksQueue(
        project="p",
        location="asia-southeast2",
        queue="intake",
        worker_url="https://worker.run.app/",
        oidc_service_account="sa@p.iam.gserviceaccount.com",
    )
    assert q.worker_url == "https://worker.run.app"
    with pytest.raises(NotImplementedError):
        await q.enqueue("process_intake_job", 1)
