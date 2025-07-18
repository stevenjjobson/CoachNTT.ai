import { EventEmitter } from 'eventemitter3';
import * as vscode from 'vscode';
import { 
    SystemMetrics, 
    PerformanceMetrics, 
    SafetyMetrics,
    MemoryScalingConfig,
    Alert,
    MetricCollection,
    ResourceThresholds,
    MemoryMetrics,
    CPUMetrics,
    DiskMetrics
} from '../types/monitoring.types';
import { MCPClient } from './mcp-client';
import { Logger } from '../utils/logger';
import { ConfigurationService } from '../config/settings';

/**
 * Monitoring Service Events
 */
export interface MonitoringEventMap {
    metricsUpdate: (metrics: SystemMetrics) => void;
    performanceUpdate: (metrics: PerformanceMetrics) => void;
    safetyUpdate: (metrics: SafetyMetrics) => void;
    alert: (alert: Alert) => void;
    sessionCountChange: (count: number) => void;
    thresholdChange: (resource: string, threshold: number) => void;
}

/**
 * Monitoring Service
 * 
 * Collects system metrics, manages thresholds, and provides
 * real-time monitoring data with dynamic memory scaling.
 */
export class MonitoringService extends EventEmitter<MonitoringEventMap> {
    private static instance: MonitoringService;
    private logger: Logger;
    private config: ConfigurationService;
    private mcpClient: MCPClient;
    
    // Metrics storage
    private metrics: MetricCollection;
    private memoryScaling: MemoryScalingConfig;
    private thresholds: ResourceThresholds;
    
    // Collection intervals
    private metricsInterval: NodeJS.Timer | null = null;
    private isCollecting: boolean = false;
    
    // Smoothing for dynamic thresholds
    private thresholdHistory: number[] = [];
    
    private constructor() {
        super();
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        this.mcpClient = MCPClient.getInstance();
        
        // Initialize metrics collection
        this.metrics = {
            system: [],
            performance: [],
            safety: [],
            maxDataPoints: 720 // 1 hour at 5-second intervals
        };
        
        // Initialize memory scaling config
        this.memoryScaling = {
            baseThresholdPercentage: 80,
            scalingFactorPerSession: 5,
            maxThresholdPercentage: 90,
            smoothingWindow: 5,
            currentSessions: 1
        };
        
        // Initialize thresholds
        this.thresholds = {
            cpu: { warning: 70, critical: 90 },
            memory: { warning: 70, critical: 80, dynamic: true },
            disk: { warning: 80, critical: 90 }
        };
        
        this.setupWebSocketSubscriptions();
    }
    
    /**
     * Get singleton instance
     */
    public static getInstance(): MonitoringService {
        if (!MonitoringService.instance) {
            MonitoringService.instance = new MonitoringService();
        }
        return MonitoringService.instance;
    }
    
    /**
     * Setup WebSocket subscriptions
     */
    private setupWebSocketSubscriptions(): void {
        // Subscribe to performance updates
        this.mcpClient.on('performance_updates', (data: any) => {
            const metrics: PerformanceMetrics = {
                responseTime: data.response_time || 0,
                throughput: data.throughput || 0,
                errorRate: data.error_rate || 0,
                activeConnections: data.active_connections || 0,
                timestamp: Date.now()
            };
            this.addPerformanceMetrics(metrics);
        });
        
        // Subscribe to safety scores
        this.mcpClient.on('safety_scores', (data: any) => {
            const metrics: SafetyMetrics = {
                score: data.score || 0,
                violations: data.violations || 0,
                validations: data.validations || 0,
                timestamp: Date.now()
            };
            this.addSafetyMetrics(metrics);
        });
        
        // Subscribe to session count updates
        this.mcpClient.on('session_count', (data: any) => {
            const count = data.count || 1;
            this.updateSessionCount(count);
        });
    }
    
    /**
     * Start metrics collection
     */
    public startCollection(): void {
        if (this.isCollecting) {
            return;
        }
        
        this.isCollecting = true;
        this.logger.info('Starting metrics collection');
        
        // Collect metrics every 5 seconds
        this.metricsInterval = setInterval(() => {
            this.collectSystemMetrics();
        }, 5000);
        
        // Initial collection
        this.collectSystemMetrics();
    }
    
    /**
     * Stop metrics collection
     */
    public stopCollection(): void {
        if (!this.isCollecting) {
            return;
        }
        
        this.isCollecting = false;
        this.logger.info('Stopping metrics collection');
        
        if (this.metricsInterval) {
            clearInterval(this.metricsInterval);
            this.metricsInterval = null;
        }
    }
    
    /**
     * Collect system metrics
     */
    private async collectSystemMetrics(): Promise<void> {
        try {
            const metrics: SystemMetrics = {
                cpu: this.collectCPUMetrics(),
                memory: await this.collectMemoryMetrics(),
                disk: this.collectDiskMetrics(),
                timestamp: Date.now()
            };
            
            this.addSystemMetrics(metrics);
            this.checkThresholds(metrics);
            
        } catch (error) {
            this.logger.error('Failed to collect system metrics', error);
        }
    }
    
    /**
     * Collect CPU metrics
     */
    private collectCPUMetrics(): CPUMetrics {
        // In a real implementation, this would use system APIs
        // For now, return mock data with some variation
        const base = 30;
        const variation = Math.sin(Date.now() / 10000) * 20;
        
        return {
            usage: Math.max(0, Math.min(100, base + variation + Math.random() * 10)),
            loadAverage: [1.2, 1.5, 1.8],
            cores: 4
        };
    }
    
    /**
     * Collect memory metrics with dynamic threshold
     */
    private async collectMemoryMetrics(): Promise<MemoryMetrics> {
        // In a real implementation, this would use process.memoryUsage()
        // For now, return mock data with realistic patterns
        const total = 8 * 1024 * 1024 * 1024; // 8GB
        const base = total * 0.4; // 40% base usage
        const sessionUsage = this.memoryScaling.currentSessions * 200 * 1024 * 1024; // 200MB per session
        const variation = Math.sin(Date.now() / 15000) * 500 * 1024 * 1024; // ±500MB variation
        
        const used = Math.max(0, Math.min(total, base + sessionUsage + variation));
        const free = total - used;
        const percentage = (used / total) * 100;
        
        // Calculate dynamic threshold
        const threshold = this.calculateDynamicMemoryThreshold();
        const scaledThreshold = (threshold / 100) * total;
        
        return {
            used,
            total,
            free,
            percentage,
            threshold,
            scaledThreshold
        };
    }
    
    /**
     * Collect disk metrics
     */
    private collectDiskMetrics(): DiskMetrics {
        // Mock implementation
        const total = 100 * 1024 * 1024 * 1024; // 100GB
        const used = total * 0.65; // 65% used
        
        return {
            used,
            total,
            free: total - used,
            percentage: (used / total) * 100
        };
    }
    
    /**
     * Calculate dynamic memory threshold based on session count
     */
    private calculateDynamicMemoryThreshold(): number {
        const { baseThresholdPercentage, scalingFactorPerSession, maxThresholdPercentage, currentSessions } = this.memoryScaling;
        
        // Calculate raw threshold
        const rawThreshold = baseThresholdPercentage + (currentSessions - 1) * scalingFactorPerSession;
        
        // Cap at maximum
        const cappedThreshold = Math.min(rawThreshold, maxThresholdPercentage);
        
        // Apply smoothing
        this.thresholdHistory.push(cappedThreshold);
        if (this.thresholdHistory.length > this.memoryScaling.smoothingWindow) {
            this.thresholdHistory.shift();
        }
        
        const smoothedThreshold = this.thresholdHistory.reduce((a, b) => a + b, 0) / this.thresholdHistory.length;
        
        // Emit threshold change if significant
        const currentThreshold = this.thresholds.memory.critical;
        if (Math.abs(smoothedThreshold - currentThreshold) > 1) {
            this.thresholds.memory.critical = smoothedThreshold;
            this.emit('thresholdChange', 'memory', smoothedThreshold);
        }
        
        return smoothedThreshold;
    }
    
    /**
     * Update session count
     */
    public updateSessionCount(count: number): void {
        if (count !== this.memoryScaling.currentSessions) {
            this.memoryScaling.currentSessions = count;
            this.emit('sessionCountChange', count);
            this.logger.info('Session count updated', { count });
            
            // Recalculate threshold immediately
            this.calculateDynamicMemoryThreshold();
        }
    }
    
    /**
     * Add system metrics
     */
    private addSystemMetrics(metrics: SystemMetrics): void {
        this.metrics.system.push(metrics);
        
        // Maintain rolling window
        if (this.metrics.system.length > this.metrics.maxDataPoints) {
            this.metrics.system.shift();
        }
        
        this.emit('metricsUpdate', metrics);
    }
    
    /**
     * Add performance metrics
     */
    private addPerformanceMetrics(metrics: PerformanceMetrics): void {
        this.metrics.performance.push(metrics);
        
        // Maintain rolling window
        if (this.metrics.performance.length > this.metrics.maxDataPoints) {
            this.metrics.performance.shift();
        }
        
        this.emit('performanceUpdate', metrics);
    }
    
    /**
     * Add safety metrics
     */
    private addSafetyMetrics(metrics: SafetyMetrics): void {
        this.metrics.safety.push(metrics);
        
        // Maintain rolling window
        if (this.metrics.safety.length > this.metrics.maxDataPoints) {
            this.metrics.safety.shift();
        }
        
        this.emit('safetyUpdate', metrics);
    }
    
    /**
     * Check thresholds and generate alerts
     */
    private checkThresholds(metrics: SystemMetrics): void {
        // Check CPU threshold
        if (metrics.cpu.usage > this.thresholds.cpu.critical) {
            this.generateAlert('critical', 'cpu', 'CPU usage critical', metrics.cpu.usage, this.thresholds.cpu.critical);
        } else if (metrics.cpu.usage > this.thresholds.cpu.warning) {
            this.generateAlert('warning', 'cpu', 'CPU usage high', metrics.cpu.usage, this.thresholds.cpu.warning);
        }
        
        // Check memory threshold (using dynamic threshold)
        const memoryThreshold = this.thresholds.memory.critical;
        if (metrics.memory.percentage > memoryThreshold) {
            this.generateAlert('critical', 'memory', 
                `Memory usage exceeds dynamic threshold (${this.memoryScaling.currentSessions} sessions)`, 
                metrics.memory.percentage, memoryThreshold);
        } else if (metrics.memory.percentage > this.thresholds.memory.warning) {
            this.generateAlert('warning', 'memory', 'Memory usage approaching threshold', 
                metrics.memory.percentage, this.thresholds.memory.warning);
        }
        
        // Check disk threshold
        if (metrics.disk.percentage > this.thresholds.disk.critical) {
            this.generateAlert('critical', 'disk', 'Disk space critical', metrics.disk.percentage, this.thresholds.disk.critical);
        } else if (metrics.disk.percentage > this.thresholds.disk.warning) {
            this.generateAlert('warning', 'disk', 'Disk space low', metrics.disk.percentage, this.thresholds.disk.warning);
        }
    }
    
    /**
     * Generate alert
     */
    private generateAlert(type: 'warning' | 'critical' | 'info', 
                         resource: 'cpu' | 'memory' | 'disk' | 'performance' | 'safety',
                         message: string, value: number, threshold: number): void {
        const alert: Alert = {
            id: `${resource}-${Date.now()}`,
            type,
            resource,
            message,
            value,
            threshold,
            timestamp: Date.now()
        };
        
        this.emit('alert', alert);
        this.logger.warn('Alert generated', alert);
    }
    
    /**
     * Get current metrics
     */
    public getCurrentMetrics(): MetricCollection {
        return this.metrics;
    }
    
    /**
     * Get memory scaling config
     */
    public getMemoryScalingConfig(): MemoryScalingConfig {
        return this.memoryScaling;
    }
    
    /**
     * Update memory scaling config
     */
    public updateMemoryScalingConfig(config: Partial<MemoryScalingConfig>): void {
        this.memoryScaling = { ...this.memoryScaling, ...config };
        this.logger.info('Memory scaling config updated', this.memoryScaling);
    }
    
    /**
     * Get resource thresholds
     */
    public getThresholds(): ResourceThresholds {
        return this.thresholds;
    }
    
    /**
     * Export metrics
     */
    public exportMetrics(format: 'json' | 'csv', sanitize: boolean = true): string {
        const data = {
            system: this.metrics.system,
            performance: this.metrics.performance,
            safety: this.metrics.safety,
            memoryScaling: this.memoryScaling,
            thresholds: this.thresholds
        };
        
        if (sanitize) {
            // Abstract any sensitive information
            // In this case, our mock data is already abstracted
        }
        
        if (format === 'json') {
            return JSON.stringify(data, null, 2);
        } else {
            // CSV export would be implemented here
            return 'CSV export not yet implemented';
        }
    }
    
    /**
     * Dispose
     */
    public dispose(): void {
        this.stopCollection();
        this.removeAllListeners();
        this.logger.debug('Monitoring service disposed');
    }
}