from sngconnect.services.feed import FeedService

def register_jobs(registry, scheduler):
    scheduler.add_interval_job(
        FeedService.assert_last_update,
        hours=2,
        args=[registry]
    )
