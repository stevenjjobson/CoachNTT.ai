"""
Safety metrics collection and monitoring for the Cognitive Coding Partner.
Tracks abstraction quality, validation performance, and safety compliance.
"""
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from src.core.safety.models import (
    ValidationResult,
    AbstractionResult,
    SafetyMetrics,
    ValidationSeverity
)


logger = logging.getLogger(__name__)


@dataclass
class MetricEvent:
    """A single metric event."""
    timestamp: datetime
    event_type: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for abstraction operations."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_processing_time_ms: float = 0.0
    p95_processing_time_ms: float = 0.0
    p99_processing_time_ms: float = 0.0
    processing_times: List[float] = field(default_factory=list)
    
    def add_timing(self, processing_time_ms: float, success: bool = True):
        """Add a processing time measurement."""
        self.total_operations += 1
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        
        self.processing_times.append(processing_time_ms)
        
        # Keep only last 1000 measurements
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]
        
        # Recalculate averages
        if self.processing_times:
            self.average_processing_time_ms = statistics.mean(self.processing_times)
            sorted_times = sorted(self.processing_times)
            n = len(sorted_times)
            self.p95_processing_time_ms = sorted_times[int(n * 0.95)] if n > 0 else 0.0
            self.p99_processing_time_ms = sorted_times[int(n * 0.99)] if n > 0 else 0.0


@dataclass
class QualityMetrics:
    """Quality metrics for abstractions."""
    safety_scores: List[float] = field(default_factory=list)
    coverage_scores: List[float] = field(default_factory=list)
    abstraction_counts: List[int] = field(default_factory=list)
    reference_counts: List[int] = field(default_factory=list)
    
    @property
    def average_safety_score(self) -> float:
        return statistics.mean(self.safety_scores) if self.safety_scores else 0.0
    
    @property
    def average_coverage_score(self) -> float:
        return statistics.mean(self.coverage_scores) if self.coverage_scores else 0.0
    
    @property
    def median_safety_score(self) -> float:
        return statistics.median(self.safety_scores) if self.safety_scores else 0.0
    
    @property
    def safety_score_variance(self) -> float:
        return statistics.variance(self.safety_scores) if len(self.safety_scores) > 1 else 0.0


class SafetyMetricsCollector:
    """
    Collects and aggregates safety metrics for the abstraction framework.
    Provides real-time monitoring and historical analysis capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the safety metrics collector.
        
        Args:
            config: Configuration for metrics collection
        """
        self.config = config or {}
        self.retention_hours = self.config.get('retention_hours', 24)
        self.max_events = self.config.get('max_events', 10000)
        
        # Metrics storage
        self.events: deque = deque(maxlen=self.max_events)
        self.performance_metrics = PerformanceMetrics()
        self.quality_metrics = QualityMetrics()
        self.error_distribution: Dict[str, int] = defaultdict(int)
        self.warning_distribution: Dict[str, int] = defaultdict(int)
        
        # Time-based aggregations
        self.hourly_stats: Dict[str, Dict[str, Any]] = {}
        self.daily_stats: Dict[str, Dict[str, Any]] = {}
        
        # Alerts and thresholds
        self.safety_threshold = self.config.get('safety_threshold', 0.8)
        self.performance_threshold_ms = self.config.get('performance_threshold_ms', 5000)
        self.error_rate_threshold = self.config.get('error_rate_threshold', 0.05)
        
        logger.info("Initialized SafetyMetricsCollector")
    
    def record_abstraction_result(self, result: AbstractionResult, context: Optional[Dict[str, Any]] = None):
        """
        Record metrics from an abstraction result.
        
        Args:
            result: The abstraction result to record
            context: Additional context for the metrics
        """
        context = context or {}
        timestamp = datetime.now()
        
        # Record performance metrics
        self.performance_metrics.add_timing(
            result.processing_time_ms,
            success=result.is_safe
        )
        
        # Record quality metrics
        if result.validation.safety_score is not None:
            self.quality_metrics.safety_scores.append(result.validation.safety_score)
        
        self.quality_metrics.coverage_scores.append(result.coverage_score)
        self.quality_metrics.abstraction_counts.append(len(result.abstractions))
        self.quality_metrics.reference_counts.append(len(result.references))
        
        # Record errors and warnings
        for error in result.validation.errors:
            self.error_distribution[error.code] += 1
        
        for warning in result.validation.warnings:
            self.warning_distribution[warning.code] += 1
        
        # Create metric events
        events = [
            MetricEvent(
                timestamp=timestamp,
                event_type="abstraction_completed",
                value=1.0,
                metadata={
                    "success": result.is_safe,
                    "processing_time_ms": result.processing_time_ms,
                    "safety_score": result.validation.safety_score,
                    "coverage_score": result.coverage_score,
                    "reference_count": len(result.references),
                    "abstraction_count": len(result.abstractions),
                    **context
                }
            ),
            MetricEvent(
                timestamp=timestamp,
                event_type="safety_score",
                value=result.validation.safety_score or 0.0,
                metadata={"context": context}
            ),
            MetricEvent(
                timestamp=timestamp,
                event_type="processing_time",
                value=result.processing_time_ms,
                metadata={"success": result.is_safe, "context": context}
            ),
        ]
        
        # Add events to collection
        for event in events:
            self.events.append(event)
        
        # Update time-based aggregations
        self._update_time_aggregations(timestamp, result)
        
        # Check for alerts
        self._check_alerts(result)
        
        logger.debug(f"Recorded metrics for abstraction with safety score: {result.validation.safety_score:.3f}")
    
    def record_validation_result(self, result: ValidationResult, context: Optional[Dict[str, Any]] = None):
        """
        Record metrics from a validation result.
        
        Args:
            result: The validation result to record
            context: Additional context
        """
        context = context or {}
        timestamp = datetime.now()
        
        # Record errors and warnings
        for error in result.errors:
            self.error_distribution[error.code] += 1
        
        for warning in result.warnings:
            self.warning_distribution[warning.code] += 1
        
        # Create metric event
        event = MetricEvent(
            timestamp=timestamp,
            event_type="validation_completed",
            value=1.0 if result.valid else 0.0,
            metadata={
                "valid": result.valid,
                "safety_score": result.safety_score,
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "has_critical": result.has_critical_errors,
                **context
            }
        )
        
        self.events.append(event)
        
        if result.safety_score is not None:
            self.quality_metrics.safety_scores.append(result.safety_score)
        
        logger.debug(f"Recorded validation metrics - Valid: {result.valid}, Score: {result.safety_score}")
    
    def record_custom_metric(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a custom metric.
        
        Args:
            name: Name of the metric
            value: Metric value
            metadata: Additional metadata
        """
        event = MetricEvent(
            timestamp=datetime.now(),
            event_type=f"custom_{name}",
            value=value,
            metadata=metadata or {}
        )
        
        self.events.append(event)
        logger.debug(f"Recorded custom metric '{name}': {value}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        now = datetime.now()
        
        # Calculate success rates
        total_ops = self.performance_metrics.total_operations
        success_rate = (
            self.performance_metrics.successful_operations / total_ops
            if total_ops > 0 else 0.0
        )
        
        # Get recent events (last hour)
        cutoff = now - timedelta(hours=1)
        recent_events = [e for e in self.events if e.timestamp > cutoff]
        
        return {
            "timestamp": now.isoformat(),
            "performance": {
                "total_operations": total_ops,
                "success_rate": success_rate,
                "average_processing_time_ms": self.performance_metrics.average_processing_time_ms,
                "p95_processing_time_ms": self.performance_metrics.p95_processing_time_ms,
                "p99_processing_time_ms": self.performance_metrics.p99_processing_time_ms,
            },
            "quality": {
                "average_safety_score": self.quality_metrics.average_safety_score,
                "median_safety_score": self.quality_metrics.median_safety_score,
                "average_coverage_score": self.quality_metrics.average_coverage_score,
                "safety_score_variance": self.quality_metrics.safety_score_variance,
            },
            "errors": dict(self.error_distribution),
            "warnings": dict(self.warning_distribution),
            "recent_activity": {
                "events_last_hour": len(recent_events),
                "events_total": len(self.events)
            }
        }
    
    def get_time_series(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get time series data for a specific metric.
        
        Args:
            metric_name: Name of the metric
            hours: Number of hours to include
            
        Returns:
            List of time series points
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        relevant_events = [
            e for e in self.events
            if e.timestamp > cutoff and e.event_type == metric_name
        ]
        
        return [
            {
                "timestamp": event.timestamp.isoformat(),
                "value": event.value,
                "metadata": event.metadata
            }
            for event in relevant_events
        ]
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status."""
        alerts = []
        
        # Safety score alerts
        if self.quality_metrics.average_safety_score < self.safety_threshold:
            alerts.append({
                "type": "safety_score_low",
                "severity": "warning",
                "message": f"Average safety score {self.quality_metrics.average_safety_score:.3f} below threshold {self.safety_threshold}",
                "current_value": self.quality_metrics.average_safety_score,
                "threshold": self.safety_threshold
            })
        
        # Performance alerts
        if self.performance_metrics.p95_processing_time_ms > self.performance_threshold_ms:
            alerts.append({
                "type": "processing_time_high",
                "severity": "warning",
                "message": f"P95 processing time {self.performance_metrics.p95_processing_time_ms:.1f}ms above threshold",
                "current_value": self.performance_metrics.p95_processing_time_ms,
                "threshold": self.performance_threshold_ms
            })
        
        # Error rate alerts
        total_ops = self.performance_metrics.total_operations
        if total_ops > 0:
            error_rate = self.performance_metrics.failed_operations / total_ops
            if error_rate > self.error_rate_threshold:
                alerts.append({
                    "type": "error_rate_high",
                    "severity": "critical",
                    "message": f"Error rate {error_rate:.1%} above threshold {self.error_rate_threshold:.1%}",
                    "current_value": error_rate,
                    "threshold": self.error_rate_threshold
                })
        
        return {
            "alert_count": len(alerts),
            "alerts": alerts,
            "last_checked": datetime.now().isoformat()
        }
    
    def _update_time_aggregations(self, timestamp: datetime, result: AbstractionResult):
        """Update hourly and daily aggregations."""
        hour_key = timestamp.strftime("%Y-%m-%d-%H")
        day_key = timestamp.strftime("%Y-%m-%d")
        
        # Initialize if needed
        if hour_key not in self.hourly_stats:
            self.hourly_stats[hour_key] = {
                "operations": 0,
                "successful": 0,
                "failed": 0,
                "safety_scores": [],
                "processing_times": []
            }
        
        if day_key not in self.daily_stats:
            self.daily_stats[day_key] = {
                "operations": 0,
                "successful": 0,
                "failed": 0,
                "safety_scores": [],
                "processing_times": []
            }
        
        # Update hourly
        hourly = self.hourly_stats[hour_key]
        hourly["operations"] += 1
        if result.is_safe:
            hourly["successful"] += 1
        else:
            hourly["failed"] += 1
        
        if result.validation.safety_score is not None:
            hourly["safety_scores"].append(result.validation.safety_score)
        hourly["processing_times"].append(result.processing_time_ms)
        
        # Update daily
        daily = self.daily_stats[day_key]
        daily["operations"] += 1
        if result.is_safe:
            daily["successful"] += 1
        else:
            daily["failed"] += 1
        
        if result.validation.safety_score is not None:
            daily["safety_scores"].append(result.validation.safety_score)
        daily["processing_times"].append(result.processing_time_ms)
        
        # Clean old data
        self._cleanup_old_aggregations()
    
    def _cleanup_old_aggregations(self):
        """Remove old aggregation data beyond retention period."""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        
        # Clean hourly stats
        keys_to_remove = [
            key for key in self.hourly_stats.keys()
            if datetime.strptime(key, "%Y-%m-%d-%H") < cutoff
        ]
        for key in keys_to_remove:
            del self.hourly_stats[key]
        
        # Clean daily stats (keep longer)
        daily_cutoff = datetime.now() - timedelta(days=30)
        keys_to_remove = [
            key for key in self.daily_stats.keys()
            if datetime.strptime(key, "%Y-%m-%d") < daily_cutoff
        ]
        for key in keys_to_remove:
            del self.daily_stats[key]
    
    def _check_alerts(self, result: AbstractionResult):
        """Check if any alert conditions are met."""
        # Critical safety score
        if result.validation.safety_score and result.validation.safety_score < 0.5:
            logger.warning(f"Critical safety score detected: {result.validation.safety_score:.3f}")
        
        # High processing time
        if result.processing_time_ms > self.performance_threshold_ms * 2:
            logger.warning(f"High processing time detected: {result.processing_time_ms:.1f}ms")
        
        # Failed abstraction
        if not result.is_safe:
            logger.error("Abstraction failed safety validation")
    
    def reset_metrics(self):
        """Reset all collected metrics."""
        self.events.clear()
        self.performance_metrics = PerformanceMetrics()
        self.quality_metrics = QualityMetrics()
        self.error_distribution.clear()
        self.warning_distribution.clear()
        self.hourly_stats.clear()
        self.daily_stats.clear()
        logger.info("Reset all safety metrics")
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for persistence or analysis."""
        return {
            "export_timestamp": datetime.now().isoformat(),
            "current_metrics": self.get_current_metrics(),
            "hourly_aggregations": self.hourly_stats,
            "daily_aggregations": self.daily_stats,
            "alert_status": self.get_alert_status(),
            "config": self.config
        }