"""
System monitoring and metrics collection service
"""

import asyncio
import psutil
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from app.database import db
from app.pipeline_engine import engine
from app.models import ExecutionStatus, PipelineStatus
from app.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    active_executions: int
    total_pipelines: int
    successful_executions_24h: int
    failed_executions_24h: int


@dataclass
class PipelineMetrics:
    """Pipeline-specific metrics"""
    pipeline_id: str
    pipeline_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration: float
    last_execution_time: datetime
    success_rate: float


class MonitoringService:
    """Service for collecting and analyzing system metrics"""
    
    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1440  # 24 hours of minute-by-minute metrics
        self.collection_interval = 60  # Collect metrics every minute
        self.running = False
        self._collection_task = None
    
    async def start(self):
        """Start metrics collection"""
        if self.running:
            return
        
        self.running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop metrics collection"""
        self.running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring service stopped")
    
    async def _collection_loop(self):
        """Main metrics collection loop"""
        while self.running:
            try:
                metrics = await self.collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Maintain history size
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size:]
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Application metrics
            running_executions = await engine.get_running_executions()
            active_executions_count = len(running_executions)
            
            # Database statistics
            db_stats = await db.get_statistics()
            total_pipelines = db_stats.get("pipelines", {}).get("total", 0)
            
            # Recent execution statistics
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_executions = await db.list_executions(limit=10000)  # Get all for analysis
            recent_executions = [e for e in recent_executions if e.created_at >= recent_cutoff]
            
            successful_24h = len([e for e in recent_executions if e.status == ExecutionStatus.COMPLETED])
            failed_24h = len([e for e in recent_executions if e.status == ExecutionStatus.FAILED])
            
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_total_gb=memory.total / (1024**3),
                disk_percent=disk.percent,
                disk_used_gb=disk.used / (1024**3),
                disk_total_gb=disk.total / (1024**3),
                active_executions=active_executions_count,
                total_pipelines=total_pipelines,
                successful_executions_24h=successful_24h,
                failed_executions_24h=failed_24h
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            # Return default metrics in case of error
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_total_gb=0.0,
                disk_percent=0.0,
                disk_used_gb=0.0,
                disk_total_gb=0.0,
                active_executions=0,
                total_pipelines=0,
                successful_executions_24h=0,
                failed_executions_24h=0
            )
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        metrics = await self.collect_system_metrics()
        return asdict(metrics)
    
    async def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics for the specified number of hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_metrics = [
            asdict(m) for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        return filtered_metrics
    
    async def get_pipeline_metrics(self, pipeline_id: str = None) -> List[PipelineMetrics]:
        """Get metrics for pipelines"""
        pipeline_metrics = []
        
        if pipeline_id:
            pipelines = [await db.get_pipeline(pipeline_id)]
            pipelines = [p for p in pipelines if p is not None]
        else:
            pipelines = await db.list_pipelines(limit=1000)
        
        for pipeline in pipelines:
            executions = await db.list_executions(pipeline_id=pipeline.id, limit=1000)
            
            total_executions = len(executions)
            successful = len([e for e in executions if e.status == ExecutionStatus.COMPLETED])
            failed = len([e for e in executions if e.status == ExecutionStatus.FAILED])
            
            # Calculate average duration for completed executions
            completed_executions = [e for e in executions if e.status == ExecutionStatus.COMPLETED and e.duration]
            avg_duration = sum(e.duration for e in completed_executions) / len(completed_executions) if completed_executions else 0
            
            # Success rate
            success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
            
            # Last execution time
            last_execution = max(executions, key=lambda x: x.created_at) if executions else None
            last_execution_time = last_execution.created_at if last_execution else pipeline.created_at
            
            metrics = PipelineMetrics(
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                total_executions=total_executions,
                successful_executions=successful,
                failed_executions=failed,
                average_duration=round(avg_duration, 2),
                last_execution_time=last_execution_time,
                success_rate=round(success_rate, 2)
            )
            
            pipeline_metrics.append(metrics)
        
        return pipeline_metrics
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            current_metrics = await self.collect_system_metrics()
            
            # Determine health status based on thresholds
            health_checks = {
                "cpu_healthy": current_metrics.cpu_percent < 80,
                "memory_healthy": current_metrics.memory_percent < 85,
                "disk_healthy": current_metrics.disk_percent < 90,
                "executions_healthy": current_metrics.active_executions <= settings.max_concurrent_executions
            }
            
            overall_healthy = all(health_checks.values())
            
            # Get recent error rate
            total_recent = current_metrics.successful_executions_24h + current_metrics.failed_executions_24h
            error_rate = (current_metrics.failed_executions_24h / total_recent * 100) if total_recent > 0 else 0
            
            return {
                "overall_status": "healthy" if overall_healthy else "warning",
                "timestamp": current_metrics.timestamp.isoformat(),
                "health_checks": health_checks,
                "metrics": asdict(current_metrics),
                "error_rate_24h": round(error_rate, 2),
                "alerts": await self._generate_alerts(current_metrics, health_checks)
            }
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                "overall_status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "health_checks": {},
                "metrics": {},
                "error_rate_24h": 0,
                "alerts": ["System health check failed"]
            }
    
    async def _generate_alerts(self, metrics: SystemMetrics, health_checks: Dict[str, bool]) -> List[str]:
        """Generate alert messages based on current metrics"""
        alerts = []
        
        if not health_checks["cpu_healthy"]:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        if not health_checks["memory_healthy"]:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        if not health_checks["disk_healthy"]:
            alerts.append(f"High disk usage: {metrics.disk_percent:.1f}%")
        
        if not health_checks["executions_healthy"]:
            alerts.append(f"Too many concurrent executions: {metrics.active_executions}")
        
        # Check for high error rate
        total_executions = metrics.successful_executions_24h + metrics.failed_executions_24h
        if total_executions > 0:
            error_rate = metrics.failed_executions_24h / total_executions * 100
            if error_rate > 20:  # Alert if error rate is above 20%
                alerts.append(f"High error rate in last 24h: {error_rate:.1f}%")
        
        return alerts
    
    async def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends over time"""
        history = await self.get_metrics_history(hours)
        
        if not history:
            return {
                "cpu_trend": "stable",
                "memory_trend": "stable",
                "execution_trend": "stable",
                "average_cpu": 0,
                "average_memory": 0,
                "peak_executions": 0
            }
        
        # Calculate trends
        cpu_values = [m["cpu_percent"] for m in history]
        memory_values = [m["memory_percent"] for m in history]
        execution_values = [m["active_executions"] for m in history]
        
        # Simple trend calculation (compare first half vs second half)
        mid_point = len(history) // 2
        if mid_point > 0:
            cpu_trend = "increasing" if sum(cpu_values[mid_point:]) > sum(cpu_values[:mid_point]) else "decreasing"
            memory_trend = "increasing" if sum(memory_values[mid_point:]) > sum(memory_values[:mid_point]) else "decreasing"
            exec_trend = "increasing" if sum(execution_values[mid_point:]) > sum(execution_values[:mid_point]) else "decreasing"
        else:
            cpu_trend = memory_trend = exec_trend = "stable"
        
        return {
            "cpu_trend": cpu_trend,
            "memory_trend": memory_trend,
            "execution_trend": exec_trend,
            "average_cpu": round(sum(cpu_values) / len(cpu_values), 2),
            "average_memory": round(sum(memory_values) / len(memory_values), 2),
            "peak_executions": max(execution_values),
            "data_points": len(history)
        }


# Global monitoring service instance
monitoring_service = MonitoringService()
