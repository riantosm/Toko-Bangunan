import asyncio

from app.workers.queue import get_queue


async def main() -> None:
    q = await get_queue()
    job = await q.enqueue_job("ping", "andrian")
    assert job is not None
    print("enqueued job_id:", job.job_id)
    print("result:", await job.result(timeout=20))


if __name__ == "__main__":
    asyncio.run(main())
