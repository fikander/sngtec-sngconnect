from sngconnect.services.feed import FeedService
from sngconnect.database import FeedUser

def register_jobs(registry, scheduler):
    scheduler.add_interval_job(
        FeedService.assert_last_update,
        hours=2,
        args=[registry]
    )
    scheduler.add_cron_job(
        FeedUser.update_payments,
        hour=0,
        args=[registry]
    )
