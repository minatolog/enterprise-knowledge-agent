from functools import lru_cache

from celery import Celery

from app.enterprise.config import Settings


@lru_cache
def runtime():
    from app.enterprise.db import Database
    from app.enterprise.storage import ObjectStore
    from app.enterprise.index import Index
    from app.enterprise.runtime import Runtime
    settings = Settings()
    database, objects = Database(settings), ObjectStore(settings)
    return Runtime(settings, database, objects, Index(settings, database, objects))


def create_queue(settings):
    queue = Celery("enterprise", broker=settings.broker_url)
    queue.conf.update(task_always_eager=settings.eager, task_acks_late=True,
        task_serializer="json", accept_content=["json"], worker_prefetch_multiplier=1,
        task_soft_time_limit=1800, task_time_limit=1900,
        broker_connection_retry_on_startup=True)
    return queue


def worker_app():
    settings = Settings()
    queue = create_queue(settings)
    @queue.task(bind=True, name="enterprise.publish", max_retries=3)
    def publish(self, identity):
        try:
            return runtime().run_job(identity)
        except Exception as exc:
            raise self.retry(exc=RuntimeError(type(exc).__name__), countdown=min(60, 2 ** self.request.retries))
    @queue.task(name="enterprise.sync_connectors")
    def synchronize():
        import json
        from app.enterprise.auth import Principal
        from app.enterprise.connectors import fetch_pages
        if not settings.connectors_file:
            return {"configured": 0}
        configurations = json.loads(settings.connectors_file.read_text())
        for entry in configurations:
            principal = Principal("connector", entry["tenant_id"], tuple(entry["groups"]), ("admin",))
            pages = fetch_pages(settings, entry["url"])
            runtime().sync_pages(principal, entry["url"], pages, entry["groups"])
            runtime().run_job(runtime().db.new_job(principal.tenant))
        return {"configured": len(configurations)}
    if settings.connectors_file:
        queue.conf.beat_schedule = {"sync-configured-sources": {
            "task": "enterprise.sync_connectors", "schedule": settings.sync_interval_seconds}}
    return queue
