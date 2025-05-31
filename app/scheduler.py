"""
Pipeline scheduling system for automated execution
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import re

from app.models import Pipeline, ScheduleType, ScheduleConfig, PipelineStatus
from app.database import db
from app.pipeline_engine import engine
from app.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

print("Test updated")


@dataclass
class ScheduledJob:
    """Represents a scheduled pipeline job"""
    pipeline_id: str
    pipeline_name: str
    schedule: ScheduleConfig
    next_run: datetime
    last_run: Optional[datetime] = None
    enabled: bool = True


class PipelineScheduler:
    """Handles scheduling and automatic execution of pipelines"""

    def __init__(self):
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler"""
        if self.running:
            return

        self.running = True
        await self._load_scheduled_pipelines()
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Pipeline scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Pipeline scheduler stopped")

    async def _load_scheduled_pipelines(self):
        """Load all scheduled pipelines from database"""
        pipelines = await db.list_pipelines(status=PipelineStatus.ACTIVE)

        for pipeline in pipelines:
            if pipeline.schedule:
                await self.add_pipeline_schedule(pipeline)

    async def add_pipeline_schedule(self, pipeline: Pipeline):
        """Add a pipeline to the schedule"""
        if not pipeline.schedule:
            return

        next_run = self._calculate_next_run(pipeline.schedule)
        if next_run:
            job = ScheduledJob(pipeline_id=pipeline.id,
                               pipeline_name=pipeline.name,
                               schedule=pipeline.schedule,
                               next_run=next_run)
            self.jobs[pipeline.id] = job
            logger.info(f"Scheduled pipeline {pipeline.name} for {next_run}")

    async def remove_pipeline_schedule(self, pipeline_id: str):
        """Remove a pipeline from the schedule"""
        if pipeline_id in self.jobs:
            job = self.jobs.pop(pipeline_id)
            logger.info(f"Removed schedule for pipeline {job.pipeline_name}")

    async def update_pipeline_schedule(self, pipeline: Pipeline):
        """Update an existing pipeline schedule"""
        await self.remove_pipeline_schedule(pipeline.id)
        await self.add_pipeline_schedule(pipeline)

    def _calculate_next_run(self,
                            schedule: ScheduleConfig) -> Optional[datetime]:
        """Calculate the next run time for a schedule"""
        now = datetime.utcnow()

        if schedule.start_time and schedule.start_time > now:
            start_time = schedule.start_time
        else:
            start_time = now

        if schedule.end_time and start_time > schedule.end_time:
            return None

        if schedule.type == ScheduleType.ONCE:
            return schedule.start_time if schedule.start_time else now

        elif schedule.type == ScheduleType.HOURLY:
            interval = schedule.interval or 1
            next_run = start_time.replace(minute=0, second=0, microsecond=0)
            while next_run <= now:
                next_run += timedelta(hours=interval)
            return next_run

        elif schedule.type == ScheduleType.DAILY:
            interval = schedule.interval or 1
            next_run = start_time.replace(hour=0,
                                          minute=0,
                                          second=0,
                                          microsecond=0)
            while next_run <= now:
                next_run += timedelta(days=interval)
            return next_run

        elif schedule.type == ScheduleType.WEEKLY:
            interval = schedule.interval or 1
            # Start from beginning of week (Monday)
            days_since_monday = start_time.weekday()
            next_run = start_time - timedelta(days=days_since_monday)
            next_run = next_run.replace(hour=0,
                                        minute=0,
                                        second=0,
                                        microsecond=0)
            while next_run <= now:
                next_run += timedelta(weeks=interval)
            return next_run

        elif schedule.type == ScheduleType.MONTHLY:
            interval = schedule.interval or 1
            next_run = start_time.replace(day=1,
                                          hour=0,
                                          minute=0,
                                          second=0,
                                          microsecond=0)
            while next_run <= now:
                # Add months
                month = next_run.month
                year = next_run.year
                month += interval
                while month > 12:
                    month -= 12
                    year += 1
                next_run = next_run.replace(year=year, month=month)
            return next_run

        elif schedule.type == ScheduleType.CRON:
            # Basic cron parsing (simplified)
            return self._parse_cron_expression(schedule.cron_expression, now)

        return None

    def _parse_cron_expression(self, cron_expr: str,
                               from_time: datetime) -> Optional[datetime]:
        """Parse a cron expression and calculate next run (simplified implementation)"""
        try:
            # Expected format: "minute hour day month weekday"
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                logger.warning(f"Invalid cron expression: {cron_expr}")
                return None

            minute, hour, day, month, weekday = parts

            # For simplicity, only handle basic cases
            # This is a very basic implementation - a real scheduler would use a proper cron library

            next_run = from_time.replace(second=0, microsecond=0)

            # If all parts are "*", run every minute
            if all(p == "*" for p in parts):
                return next_run + timedelta(minutes=1)

            # Handle specific minute and hour
            if minute.isdigit() and hour.isdigit():
                target_minute = int(minute)
                target_hour = int(hour)

                next_run = next_run.replace(minute=target_minute,
                                            hour=target_hour)
                if next_run <= from_time:
                    next_run += timedelta(days=1)

                return next_run

            # For more complex cron expressions, return None
            # In a production system, you would use a proper cron library like croniter
            logger.warning(
                f"Complex cron expression not supported: {cron_expr}")
            return None

        except Exception as e:
            logger.error(f"Error parsing cron expression {cron_expr}: {e}")
            return None

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_and_execute_jobs()
                await asyncio.sleep(settings.scheduler_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _check_and_execute_jobs(self):
        """Check for jobs that need to be executed"""
        now = datetime.utcnow()

        for job in list(self.jobs.values()):
            if not job.enabled:
                continue

            # Check if job should run
            if job.next_run <= now:
                # Check if pipeline still exists and is active
                pipeline = await db.get_pipeline(job.pipeline_id)
                if not pipeline or pipeline.status != PipelineStatus.ACTIVE:
                    await self.remove_pipeline_schedule(job.pipeline_id)
                    continue

                # Check end time
                if job.schedule.end_time and now > job.schedule.end_time:
                    await self.remove_pipeline_schedule(job.pipeline_id)
                    continue

                # Execute pipeline
                try:
                    logger.info(
                        f"Executing scheduled pipeline: {job.pipeline_name}")
                    execution = await engine.execute_pipeline(
                        pipeline, parameters={"triggered_by": "scheduler"})

                    job.last_run = now

                    # Calculate next run for recurring schedules
                    if job.schedule.type != ScheduleType.ONCE:
                        job.next_run = self._calculate_next_run(job.schedule)
                        if not job.next_run:
                            await self.remove_pipeline_schedule(job.pipeline_id
                                                                )
                    else:
                        # Remove one-time schedules after execution
                        await self.remove_pipeline_schedule(job.pipeline_id)

                except Exception as e:
                    logger.error(
                        f"Error executing scheduled pipeline {job.pipeline_name}: {e}"
                    )
                    # Still update next run to prevent continuous failures
                    if job.schedule.type != ScheduleType.ONCE:
                        job.next_run = self._calculate_next_run(job.schedule)

    async def get_scheduled_jobs(self) -> List[Dict]:
        """Get list of all scheduled jobs"""
        jobs = []
        for job in self.jobs.values():
            jobs.append({
                "pipeline_id":
                job.pipeline_id,
                "pipeline_name":
                job.pipeline_name,
                "schedule_type":
                job.schedule.type,
                "next_run":
                job.next_run.isoformat() if job.next_run else None,
                "last_run":
                job.last_run.isoformat() if job.last_run else None,
                "enabled":
                job.enabled
            })
        return jobs

    async def enable_job(self, pipeline_id: str):
        """Enable a scheduled job"""
        if pipeline_id in self.jobs:
            self.jobs[pipeline_id].enabled = True
            logger.info(f"Enabled scheduled job for pipeline {pipeline_id}")

    async def disable_job(self, pipeline_id: str):
        """Disable a scheduled job"""
        if pipeline_id in self.jobs:
            self.jobs[pipeline_id].enabled = False
            logger.info(f"Disabled scheduled job for pipeline {pipeline_id}")
