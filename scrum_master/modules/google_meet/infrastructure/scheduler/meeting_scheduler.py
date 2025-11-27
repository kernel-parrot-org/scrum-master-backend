"""Meeting Scheduler - triggers bot to join meetings at scheduled times."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from uuid import UUID

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class MeetingScheduler:
    """Scheduler for triggering bot to join meetings."""
    
    def __init__(self, bot_trigger_url: str = 'http://localhost:8000/api/v1/meet/connect'):
        self.scheduler = AsyncIOScheduler()
        self.bot_trigger_url = bot_trigger_url
        self._started = False
    
    def start(self):
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info('Meeting scheduler started')
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self._started:
            self.scheduler.shutdown()
            self._started = False
            logger.info('Meeting scheduler stopped')
    
    async def trigger_bot(self, meet_url: str, bot_name: str, user_token: Optional[str] = None):
        """Trigger the bot to join a meeting."""
        logger.info(f'🤖 Triggering bot for meeting: {meet_url}')
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {}
                if user_token:
                    headers['Authorization'] = f'Bearer {user_token}'
                
                response = await client.post(
                    self.bot_trigger_url,
                    json={
                        'meet_url': meet_url,
                        'bot_name': bot_name,
                    },
                    headers=headers,
                )
                response.raise_for_status()
                logger.info(f'✓ Bot triggered successfully for {meet_url}')
                return response.json()
        except Exception as e:
            logger.error(f'Failed to trigger bot: {e}')
            raise
    
    def schedule_once(
        self,
        job_id: str,
        meet_url: str,
        bot_name: str,
        run_time: datetime,
        user_token: Optional[str] = None,
    ) -> str:
        """Schedule a one-time meeting."""
        # Schedule 1 minute before meeting starts
        trigger_time = run_time - timedelta(minutes=1)
        
        self.scheduler.add_job(
            self._async_trigger_wrapper,
            trigger=DateTrigger(run_date=trigger_time),
            id=job_id,
            args=[meet_url, bot_name, user_token],
            replace_existing=True,
        )
        
        logger.info(f'Scheduled one-time meeting {job_id} for {trigger_time}')
        return job_id
    
    def schedule_daily(
        self,
        job_id: str,
        meet_url: str,
        bot_name: str,
        hour: int,
        minute: int,
        user_token: Optional[str] = None,
    ) -> str:
        """Schedule a daily recurring meeting."""
        # Trigger 1 minute before
        trigger_minute = minute - 1 if minute > 0 else 59
        trigger_hour = hour if minute > 0 else (hour - 1 if hour > 0 else 23)
        
        self.scheduler.add_job(
            self._async_trigger_wrapper,
            trigger=CronTrigger(hour=trigger_hour, minute=trigger_minute),
            id=job_id,
            args=[meet_url, bot_name, user_token],
            replace_existing=True,
        )
        
        logger.info(f'Scheduled daily meeting {job_id} at {trigger_hour}:{trigger_minute}')
        return job_id
    
    def schedule_weekly(
        self,
        job_id: str,
        meet_url: str,
        bot_name: str,
        days_of_week: str,  # "0,2,4" for Mon,Wed,Fri
        hour: int,
        minute: int,
        user_token: Optional[str] = None,
    ) -> str:
        """Schedule a weekly recurring meeting on specific days."""
        # Trigger 1 minute before
        trigger_minute = minute - 1 if minute > 0 else 59
        trigger_hour = hour if minute > 0 else (hour - 1 if hour > 0 else 23)
        
        self.scheduler.add_job(
            self._async_trigger_wrapper,
            trigger=CronTrigger(
                day_of_week=days_of_week,
                hour=trigger_hour,
                minute=trigger_minute,
            ),
            id=job_id,
            args=[meet_url, bot_name, user_token],
            replace_existing=True,
        )
        
        logger.info(f'Scheduled weekly meeting {job_id} on days {days_of_week} at {trigger_hour}:{trigger_minute}')
        return job_id
    
    def remove_schedule(self, job_id: str) -> bool:
        """Remove a scheduled meeting."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f'Removed schedule {job_id}')
            return True
        except Exception as e:
            logger.warning(f'Failed to remove schedule {job_id}: {e}')
            return False
    
    def get_next_run_time(self, job_id: str) -> Optional[datetime]:
        """Get the next run time for a scheduled job."""
        job = self.scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None
    
    def list_jobs(self) -> list[dict]:
        """List all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run_time': job.next_run_time,
                'args': job.args,
            })
        return jobs
    
    def _async_trigger_wrapper(self, meet_url: str, bot_name: str, user_token: Optional[str]):
        """Wrapper to run async trigger_bot in sync context."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.trigger_bot(meet_url, bot_name, user_token))
        finally:
            loop.close()

