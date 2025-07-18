/**
 * Monitoring Types
 * 
 * Type definitions for the real-time monitoring dashboard
 * with dynamic memory scaling support.
 */

/**
 * System resource metrics
 */
export interface SystemMetrics {
    cpu: CPUMetrics;
    memory: MemoryMetrics;
    disk: DiskMetrics;
    timestamp: number;
}

/**
 * CPU metrics
 */
export interface CPUMetrics {
    usage: number;          // Percentage 0-100
    loadAverage: number[];  // 1, 5, 15 minute averages
    cores: number;          // Number of CPU cores
}

/**
 * Memory metrics with dynamic scaling
 */
export interface MemoryMetrics {
    used: number;           // Bytes used
    total: number;          // Total bytes available
    free: number;           // Bytes free
    percentage: number;     // Usage percentage 0-100
    threshold: number;      // Dynamic threshold percentage
    scaledThreshold: number; // Actual threshold value in bytes
}

/**
 * Disk metrics
 */
export interface DiskMetrics {
    used: number;           // Bytes used
    total: number;          // Total bytes available
    free: number;           // Bytes free
    percentage: number;     // Usage percentage 0-100
}

/**
 * Memory scaling configuration
 */
export interface MemoryScalingConfig {
    baseThresholdPercentage: number;    // Default: 80%
    scalingFactorPerSession: number;    // Default: 5%
    maxThresholdPercentage: number;      // Default: 90%
    smoothingWindow: number;             // Default: 5 samples
    currentSessions: number;             // Active session count
}

/**
 * Performance metrics
 */
export interface PerformanceMetrics {
    responseTime: number;    // Average response time in ms
    throughput: number;      // Requests per second
    errorRate: number;       // Error percentage
    activeConnections: number;
    timestamp: number;
}

/**
 * Safety metrics
 */
export interface SafetyMetrics {
    score: number;          // 0.0 - 1.0
    violations: number;     // Count of safety violations
    validations: number;    // Total validations performed
    timestamp: number;
}

/**
 * Chart configuration
 */
export interface ChartConfig {
    type: 'line' | 'bar' | 'gauge' | 'area' | 'sparkline';
    title: string;
    datasets: ChartDataset[];
    options?: any; // Chart.js specific options
}

/**
 * Chart dataset
 */
export interface ChartDataset {
    label: string;
    data: ChartDataPoint[];
    color?: string;
    backgroundColor?: string;
    borderColor?: string;
    tension?: number;
    fill?: boolean | string;
}

/**
 * Chart data point
 */
export interface ChartDataPoint {
    x: number | string;
    y: number;
    threshold?: number; // For dynamic threshold lines
}

/**
 * Resource thresholds
 */
export interface ResourceThresholds {
    cpu: ThresholdConfig;
    memory: ThresholdConfig;
    disk: ThresholdConfig;
}

/**
 * Threshold configuration
 */
export interface ThresholdConfig {
    warning: number;        // Warning threshold percentage
    critical: number;       // Critical threshold percentage
    dynamic?: boolean;      // Whether threshold is dynamic
}

/**
 * Monitoring state
 */
export interface MonitoringState {
    metrics: MetricCollection;
    charts: Map<string, ChartConfig>;
    alerts: Alert[];
    isStreaming: boolean;
    timeRange: TimeRange;
    sessionCount: number;
    memoryScaling: MemoryScalingConfig;
}

/**
 * Metric collection
 */
export interface MetricCollection {
    system: SystemMetrics[];
    performance: PerformanceMetrics[];
    safety: SafetyMetrics[];
    maxDataPoints: number;  // Rolling window size
}

/**
 * Alert
 */
export interface Alert {
    id: string;
    type: 'warning' | 'critical' | 'info';
    resource: 'cpu' | 'memory' | 'disk' | 'performance' | 'safety';
    message: string;
    value: number;
    threshold: number;
    timestamp: number;
}

/**
 * Time range for data display
 */
export interface TimeRange {
    start: number;
    end: number;
    duration: number; // in milliseconds
}

/**
 * Export options
 */
export interface ExportOptions {
    format: 'json' | 'csv' | 'png';
    timeRange: TimeRange;
    metrics: string[];      // Which metrics to export
    includeAlerts: boolean;
    sanitize: boolean;      // Remove sensitive data
}