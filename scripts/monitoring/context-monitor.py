#!/usr/bin/env python3
"""
Context window and performance monitoring script for CoachNTT.ai.

Monitors system performance, memory usage, safety scores, and development metrics
with real-time tracking and historical analysis.

Usage:
    python3 context-monitor.py [options]

Options:
    --mode MODE            Monitoring mode: realtime, batch, analyze
    --duration SECONDS     Duration for monitoring (default: 60)
    --interval SECONDS     Update interval (default: 5)
    --output FILE         Output file for results
    --threshold-memory MB  Memory usage alert threshold
    --threshold-safety SCORE Safety score alert threshold  
    --help                Show this help message

Example:
    python3 context-monitor.py --mode realtime --duration 300
    python3 context-monitor.py --mode analyze --output metrics.json
"""

import asyncio
import sys
import argparse
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from decimal import Decimal

# Add framework path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psutil
except ImportError:
    print("ERROR: psutil is required. Install with: pip install psutil")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("ERROR: rich is required. Install with: pip install rich")
    sys.exit(1)

from framework import ScriptLogger, LogLevel


@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""
    
    timestamp: datetime
    
    # CPU metrics
    cpu_percent: float
    cpu_count: int
    load_average: Optional[float] = None
    
    # Memory metrics  
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float
    
    # Disk metrics
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    
    # Process metrics
    process_count: int
    python_processes: int
    
    # Network metrics (if available)
    network_connections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class DevelopmentMetrics:
    """Development-specific metrics."""
    
    timestamp: datetime
    
    # Code metrics
    python_files_count: int
    total_lines_of_code: int
    test_files_count: int
    
    # Git metrics
    git_branch: str
    uncommitted_changes: int
    commits_today: int
    
    # Safety metrics
    avg_safety_score: float
    safety_violations: int
    abstraction_compliance: float
    
    # Performance metrics
    avg_memory_usage_mb: float
    avg_cpu_usage: float
    context_window_usage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class AlertConfig:
    """Configuration for monitoring alerts."""
    
    memory_threshold_percent: float = 85.0
    cpu_threshold_percent: float = 90.0
    disk_threshold_percent: float = 90.0
    safety_score_threshold: float = 0.8
    process_count_threshold: int = 200
    
    enabled: bool = True


@dataclass
class MonitoringSession:
    """Complete monitoring session data."""
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    system_metrics: List[SystemMetrics] = field(default_factory=list)
    development_metrics: List[DevelopmentMetrics] = field(default_factory=list)
    
    alerts_triggered: List[Dict[str, Any]] = field(default_factory=list)
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'system_metrics': [m.to_dict() for m in self.system_metrics],
            'development_metrics': [m.to_dict() for m in self.development_metrics],
            'alerts_triggered': self.alerts_triggered,
            'summary_stats': self.summary_stats
        }


class ContextMonitor:
    """
    Advanced performance and context monitoring system.
    
    Provides real-time monitoring of system resources, development metrics,
    and safety compliance with alerting and historical analysis.
    """
    
    def __init__(
        self,
        project_root: Optional[Path] = None,
        logger: Optional[ScriptLogger] = None,
        alert_config: Optional[AlertConfig] = None
    ):
        """
        Initialize context monitor.
        
        Args:
            project_root: Project root directory
            logger: Logger instance
            alert_config: Alert configuration
        """
        self.project_root = project_root or self._detect_project_root()
        self.logger = logger or ScriptLogger(
            script_name="context-monitor",
            log_level=LogLevel.INFO,
            abstract_content=True
        )
        self.alert_config = alert_config or AlertConfig()
        
        # Initialize rich console
        self.console = Console()
        
        # Current session
        self.current_session: Optional[MonitoringSession] = None
        
        # Metrics history
        self.metrics_history_file = self.project_root / "logs" / "monitoring" / "metrics_history.json"
        self.metrics_history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Git repository for development metrics
        self._git_repo = None
        try:
            import git
            self._git_repo = git.Repo(self.project_root)
        except Exception:
            self.logger.warning("Git repository not available for development metrics")
        
        self.logger.info("ContextMonitor initialized", project_root=str(self.project_root))
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current_dir = Path(__file__).parent
        
        for _ in range(5):
            if (current_dir / ".git").exists() or (current_dir / "pyproject.toml").exists():
                return current_dir
            current_dir = current_dir.parent
        
        return Path.cwd()
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Load average (Unix-like systems only)
        load_avg = None
        try:
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None
        except Exception:
            pass
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024**3)
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage(str(self.project_root))
        disk_total_gb = disk.total / (1024**3)
        disk_used_gb = disk.used / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        
        # Process metrics
        process_count = len(psutil.pids())
        python_processes = len([p for p in psutil.process_iter(['name']) 
                              if p.info['name'] and 'python' in p.info['name'].lower()])
        
        # Network connections
        network_connections = 0
        try:
            network_connections = len(psutil.net_connections())
        except Exception:
            pass
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            load_average=load_avg,
            memory_total_gb=memory_total_gb,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            memory_percent=memory.percent,
            disk_total_gb=disk_total_gb,
            disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb,
            disk_percent=disk.percent,
            process_count=process_count,
            python_processes=python_processes,
            network_connections=network_connections
        )
    
    async def collect_development_metrics(self) -> DevelopmentMetrics:
        """Collect development-specific metrics."""
        # Code metrics
        python_files = list(self.project_root.glob("**/*.py"))
        python_files_count = len([f for f in python_files if not any(p in str(f) for p in ['.git', '__pycache__', '.pytest_cache'])])
        
        # Count lines of code
        total_lines = 0
        for py_file in python_files:
            if not any(p in str(py_file) for p in ['.git', '__pycache__', '.pytest_cache']):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        total_lines += len(f.readlines())
                except Exception:
                    pass
        
        # Test files
        test_files_count = len(list(self.project_root.glob("**/test_*.py"))) + \
                          len(list(self.project_root.glob("**/*_test.py")))
        
        # Git metrics
        git_branch = "<branch>"
        uncommitted_changes = 0
        commits_today = 0
        
        if self._git_repo:
            try:
                git_branch = self._git_repo.active_branch.name
                uncommitted_changes = len(self._git_repo.index.diff(None)) + len(self._git_repo.index.diff("HEAD"))
                
                # Count commits today
                today = datetime.now().date()
                for commit in self._git_repo.iter_commits(since=f"{today} 00:00:00"):
                    commits_today += 1
                    if commits_today >= 50:  # Limit for performance
                        break
                        
            except Exception as e:
                self.logger.debug(f"Git metrics collection failed: {e}")
        
        # Safety metrics (simplified - would integrate with actual safety validator)
        avg_safety_score = 0.95  # Placeholder
        safety_violations = 0
        abstraction_compliance = 1.0
        
        # Performance metrics from recent system data
        avg_memory_usage = 0.0
        avg_cpu_usage = 0.0
        
        if self.current_session and self.current_session.system_metrics:
            recent_metrics = self.current_session.system_metrics[-10:]  # Last 10 readings
            avg_memory_usage = sum(m.memory_used_gb * 1024 for m in recent_metrics) / len(recent_metrics)
            avg_cpu_usage = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        
        return DevelopmentMetrics(
            timestamp=datetime.now(),
            python_files_count=python_files_count,
            total_lines_of_code=total_lines,
            test_files_count=test_files_count,
            git_branch=git_branch,
            uncommitted_changes=uncommitted_changes,
            commits_today=commits_today,
            avg_safety_score=avg_safety_score,
            safety_violations=safety_violations,
            abstraction_compliance=abstraction_compliance,
            avg_memory_usage_mb=avg_memory_usage,
            avg_cpu_usage=avg_cpu_usage
        )
    
    def check_alerts(self, system_metrics: SystemMetrics, dev_metrics: DevelopmentMetrics) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        if not self.alert_config.enabled:
            return alerts
        
        # Memory usage alert
        if system_metrics.memory_percent > self.alert_config.memory_threshold_percent:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f'Memory usage high: {system_metrics.memory_percent:.1f}%',
                'timestamp': datetime.now().isoformat(),
                'value': system_metrics.memory_percent,
                'threshold': self.alert_config.memory_threshold_percent
            })
        
        # CPU usage alert
        if system_metrics.cpu_percent > self.alert_config.cpu_threshold_percent:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f'CPU usage high: {system_metrics.cpu_percent:.1f}%',
                'timestamp': datetime.now().isoformat(),
                'value': system_metrics.cpu_percent,
                'threshold': self.alert_config.cpu_threshold_percent
            })
        
        # Disk usage alert
        if system_metrics.disk_percent > self.alert_config.disk_threshold_percent:
            alerts.append({
                'type': 'disk_high',
                'severity': 'critical',
                'message': f'Disk usage high: {system_metrics.disk_percent:.1f}%',
                'timestamp': datetime.now().isoformat(),
                'value': system_metrics.disk_percent,
                'threshold': self.alert_config.disk_threshold_percent
            })
        
        # Safety score alert
        if dev_metrics.avg_safety_score < self.alert_config.safety_score_threshold:
            alerts.append({
                'type': 'safety_low',
                'severity': 'critical',
                'message': f'Safety score low: {dev_metrics.avg_safety_score:.3f}',
                'timestamp': datetime.now().isoformat(),
                'value': dev_metrics.avg_safety_score,
                'threshold': self.alert_config.safety_score_threshold
            })
        
        # Process count alert
        if system_metrics.process_count > self.alert_config.process_count_threshold:
            alerts.append({
                'type': 'process_count_high',
                'severity': 'info',
                'message': f'Process count high: {system_metrics.process_count}',
                'timestamp': datetime.now().isoformat(),
                'value': system_metrics.process_count,
                'threshold': self.alert_config.process_count_threshold
            })
        
        return alerts
    
    def create_realtime_display(self, system_metrics: SystemMetrics, dev_metrics: DevelopmentMetrics) -> Layout:
        """Create rich display layout for real-time monitoring."""
        layout = Layout()
        
        # Split into sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=5)
        )
        
        layout["main"].split_row(
            Layout(name="system"),
            Layout(name="development")
        )
        
        # Header
        header_text = Text("CoachNTT.ai Context Monitor", style="bold blue")
        header_text.append(f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        layout["header"].update(Panel(header_text, border_style="blue"))
        
        # System metrics table
        system_table = Table(title="System Metrics", border_style="green")
        system_table.add_column("Metric", style="cyan")
        system_table.add_column("Value", style="magenta")
        system_table.add_column("Status", style="green")
        
        # CPU
        cpu_status = "🔴" if system_metrics.cpu_percent > 80 else "🟡" if system_metrics.cpu_percent > 60 else "🟢"
        system_table.add_row("CPU", f"{system_metrics.cpu_percent:.1f}%", cpu_status)
        
        # Memory
        memory_status = "🔴" if system_metrics.memory_percent > 85 else "🟡" if system_metrics.memory_percent > 70 else "🟢"
        system_table.add_row("Memory", f"{system_metrics.memory_used_gb:.1f}GB / {system_metrics.memory_total_gb:.1f}GB ({system_metrics.memory_percent:.1f}%)", memory_status)
        
        # Disk
        disk_status = "🔴" if system_metrics.disk_percent > 90 else "🟡" if system_metrics.disk_percent > 80 else "🟢"
        system_table.add_row("Disk", f"{system_metrics.disk_used_gb:.1f}GB / {system_metrics.disk_total_gb:.1f}GB ({system_metrics.disk_percent:.1f}%)", disk_status)
        
        # Processes
        system_table.add_row("Processes", str(system_metrics.process_count), "🟢")
        system_table.add_row("Python Processes", str(system_metrics.python_processes), "🟢")
        
        layout["system"].update(Panel(system_table, border_style="green"))
        
        # Development metrics table
        dev_table = Table(title="Development Metrics", border_style="yellow")
        dev_table.add_column("Metric", style="cyan")
        dev_table.add_column("Value", style="magenta")
        dev_table.add_column("Status", style="green")
        
        dev_table.add_row("Python Files", str(dev_metrics.python_files_count), "🟢")
        dev_table.add_row("Lines of Code", f"{dev_metrics.total_lines_of_code:,}", "🟢")
        dev_table.add_row("Test Files", str(dev_metrics.test_files_count), "🟢")
        dev_table.add_row("Git Branch", dev_metrics.git_branch, "🟢")
        dev_table.add_row("Uncommitted", str(dev_metrics.uncommitted_changes), "🟡" if dev_metrics.uncommitted_changes > 0 else "🟢")
        
        safety_status = "🔴" if dev_metrics.avg_safety_score < 0.8 else "🟡" if dev_metrics.avg_safety_score < 0.9 else "🟢"
        dev_table.add_row("Safety Score", f"{dev_metrics.avg_safety_score:.3f}", safety_status)
        
        layout["development"].update(Panel(dev_table, border_style="yellow"))
        
        # Footer with alerts
        if self.current_session and self.current_session.alerts_triggered:
            recent_alerts = self.current_session.alerts_triggered[-3:]  # Last 3 alerts
            alerts_text = "Recent Alerts: " + " | ".join([alert['message'] for alert in recent_alerts])
        else:
            alerts_text = "No active alerts"
        
        footer_text = Text(alerts_text, style="dim")
        layout["footer"].update(Panel(footer_text, title="Alerts", border_style="red"))
        
        return layout
    
    async def start_monitoring_session(
        self,
        duration_seconds: float,
        interval_seconds: float = 5.0,
        mode: str = "realtime"
    ) -> MonitoringSession:
        """Start a monitoring session."""
        session_id = f"monitor_{int(time.time())}"
        session = MonitoringSession(
            session_id=session_id,
            start_time=datetime.now()
        )
        
        self.current_session = session
        self.logger.info(f"Starting monitoring session: {session_id}")
        
        if mode == "realtime":
            await self._run_realtime_monitoring(session, duration_seconds, interval_seconds)
        elif mode == "batch":
            await self._run_batch_monitoring(session, duration_seconds, interval_seconds)
        
        # Finalize session
        session.end_time = datetime.now()
        session.duration_seconds = (session.end_time - session.start_time).total_seconds()
        session.summary_stats = self._calculate_session_summary(session)
        
        # Save session data
        await self._save_session_data(session)
        
        self.logger.info(f"Monitoring session completed: {session_id}")
        return session
    
    async def _run_realtime_monitoring(
        self,
        session: MonitoringSession,
        duration_seconds: float,
        interval_seconds: float
    ):
        """Run real-time monitoring with live display."""
        start_time = time.time()
        
        with Live(console=self.console, refresh_per_second=1) as live:
            while (time.time() - start_time) < duration_seconds:
                # Collect metrics
                system_metrics = await self.collect_system_metrics()
                dev_metrics = await self.collect_development_metrics()
                
                # Check alerts
                alerts = self.check_alerts(system_metrics, dev_metrics)
                
                # Store data
                session.system_metrics.append(system_metrics)
                session.development_metrics.append(dev_metrics)
                session.alerts_triggered.extend(alerts)
                
                # Update display
                layout = self.create_realtime_display(system_metrics, dev_metrics)
                live.update(layout)
                
                # Log alerts
                for alert in alerts:
                    self.logger.warning(f"Alert: {alert['message']}")
                
                await asyncio.sleep(interval_seconds)
    
    async def _run_batch_monitoring(
        self,
        session: MonitoringSession,
        duration_seconds: float,
        interval_seconds: float
    ):
        """Run batch monitoring without display."""
        start_time = time.time()
        
        while (time.time() - start_time) < duration_seconds:
            system_metrics = await self.collect_system_metrics()
            dev_metrics = await self.collect_development_metrics()
            alerts = self.check_alerts(system_metrics, dev_metrics)
            
            session.system_metrics.append(system_metrics)
            session.development_metrics.append(dev_metrics)
            session.alerts_triggered.extend(alerts)
            
            # Log key metrics
            self.logger.info(
                "Monitoring update",
                cpu_percent=system_metrics.cpu_percent,
                memory_percent=system_metrics.memory_percent,
                safety_score=dev_metrics.avg_safety_score,
                alerts_count=len(alerts)
            )
            
            await asyncio.sleep(interval_seconds)
    
    def _calculate_session_summary(self, session: MonitoringSession) -> Dict[str, Any]:
        """Calculate summary statistics for monitoring session."""
        if not session.system_metrics:
            return {}
        
        system_metrics = session.system_metrics
        dev_metrics = session.development_metrics
        
        return {
            'metrics_collected': len(system_metrics),
            'avg_cpu_percent': sum(m.cpu_percent for m in system_metrics) / len(system_metrics),
            'max_cpu_percent': max(m.cpu_percent for m in system_metrics),
            'avg_memory_percent': sum(m.memory_percent for m in system_metrics) / len(system_metrics),
            'max_memory_percent': max(m.memory_percent for m in system_metrics),
            'avg_disk_percent': sum(m.disk_percent for m in system_metrics) / len(system_metrics),
            'total_alerts': len(session.alerts_triggered),
            'alert_types': list(set(alert['type'] for alert in session.alerts_triggered)),
            'final_safety_score': dev_metrics[-1].avg_safety_score if dev_metrics else 1.0,
            'lines_of_code': dev_metrics[-1].total_lines_of_code if dev_metrics else 0
        }
    
    async def _save_session_data(self, session: MonitoringSession):
        """Save session data to file."""
        try:
            # Load existing history
            history = []
            if self.metrics_history_file.exists():
                with open(self.metrics_history_file, 'r') as f:
                    history = json.load(f)
            
            # Add current session
            history.append(session.to_dict())
            
            # Keep only last 100 sessions
            history = history[-100:]
            
            # Save updated history
            with open(self.metrics_history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            self.logger.info(f"Session data saved to {self.metrics_history_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    async def analyze_historical_data(self, days: int = 7) -> Dict[str, Any]:
        """Analyze historical monitoring data."""
        if not self.metrics_history_file.exists():
            return {"error": "No historical data available"}
        
        try:
            with open(self.metrics_history_file, 'r') as f:
                history = json.load(f)
            
            # Filter to last N days
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_sessions = [
                session for session in history
                if datetime.fromisoformat(session['start_time']) >= cutoff_date
            ]
            
            if not recent_sessions:
                return {"error": f"No data available for last {days} days"}
            
            # Aggregate metrics
            total_monitoring_time = sum(session['duration_seconds'] for session in recent_sessions)
            total_alerts = sum(len(session['alerts_triggered']) for session in recent_sessions)
            
            # CPU/Memory trends
            all_cpu_readings = []
            all_memory_readings = []
            
            for session in recent_sessions:
                for metric in session['system_metrics']:
                    all_cpu_readings.append(metric['cpu_percent'])
                    all_memory_readings.append(metric['memory_percent'])
            
            analysis = {
                'period_days': days,
                'sessions_analyzed': len(recent_sessions),
                'total_monitoring_time_hours': total_monitoring_time / 3600,
                'total_alerts': total_alerts,
                'avg_cpu_percent': sum(all_cpu_readings) / len(all_cpu_readings) if all_cpu_readings else 0,
                'max_cpu_percent': max(all_cpu_readings) if all_cpu_readings else 0,
                'avg_memory_percent': sum(all_memory_readings) / len(all_memory_readings) if all_memory_readings else 0,
                'max_memory_percent': max(all_memory_readings) if all_memory_readings else 0,
                'alert_frequency_per_hour': total_alerts / (total_monitoring_time / 3600) if total_monitoring_time > 0 else 0
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze historical data: {e}")
            return {"error": str(e)}


async def main():
    """Main context monitor function."""
    parser = argparse.ArgumentParser(
        description="Context window and performance monitoring for CoachNTT.ai",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--mode",
        choices=["realtime", "batch", "analyze"],
        default="realtime",
        help="Monitoring mode"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Monitoring duration in seconds"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Update interval in seconds"
    )
    parser.add_argument(
        "--output",
        help="Output file for results"
    )
    parser.add_argument(
        "--threshold-memory",
        type=float,
        default=85.0,
        help="Memory usage alert threshold (percent)"
    )
    parser.add_argument(
        "--threshold-safety",
        type=float,
        default=0.8,
        help="Safety score alert threshold"
    )
    
    args = parser.parse_args()
    
    # Configure alerts
    alert_config = AlertConfig(
        memory_threshold_percent=args.threshold_memory,
        safety_score_threshold=args.threshold_safety
    )
    
    # Initialize monitor
    monitor = ContextMonitor(alert_config=alert_config)
    
    try:
        if args.mode == "analyze":
            # Analyze historical data
            analysis = await monitor.analyze_historical_data(days=7)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2)
                print(f"Analysis saved to {args.output}")
            else:
                print(json.dumps(analysis, indent=2))
        
        else:
            # Run monitoring session
            session = await monitor.start_monitoring_session(
                duration_seconds=args.duration,
                interval_seconds=args.interval,
                mode=args.mode
            )
            
            # Output results
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(session.to_dict(), f, indent=2)
                print(f"Session data saved to {args.output}")
            
            # Print summary
            print(f"\nMonitoring Session Summary:")
            print(f"Duration: {session.duration_seconds:.1f} seconds")
            print(f"Metrics collected: {len(session.system_metrics)}")
            print(f"Alerts triggered: {len(session.alerts_triggered)}")
            if session.summary_stats:
                print(f"Average CPU: {session.summary_stats.get('avg_cpu_percent', 0):.1f}%")
                print(f"Average Memory: {session.summary_stats.get('avg_memory_percent', 0):.1f}%")
                print(f"Safety Score: {session.summary_stats.get('final_safety_score', 1.0):.3f}")
    
    except KeyboardInterrupt:
        print("\nMonitoring cancelled by user.")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)