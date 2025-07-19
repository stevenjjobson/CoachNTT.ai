import * as vscode from 'vscode';
import * as path from 'path';
import { ManagedWebViewPanel } from '../webview-manager';
import { MessageProtocol, WebViewMessage } from '../message-protocol';
import { MonitoringService } from '../../services/monitoring-service';
import { 
    SystemMetrics, 
    PerformanceMetrics, 
    SafetyMetrics,
    Alert,
    ChartConfig,
    ChartDataset,
    TimeRange,
    ExportOptions
} from '../../types/monitoring.types';

/**
 * Monitoring Dashboard Panel
 * 
 * WebView panel for real-time system monitoring with Chart.js visualizations
 * and dynamic memory threshold support.
 */
export class MonitoringDashboard extends ManagedWebViewPanel {
    private monitoringService: MonitoringService;
    private updateInterval: NodeJS.Timer | null = null;
    private charts: Map<string, ChartConfig>;
    private timeRange: TimeRange;
    private alerts: Alert[] = [];
    
    constructor(
        panel: vscode.WebviewPanel,
        context: vscode.ExtensionContext,
        logger: Logger
    ) {
        super(panel, context, logger);
        
        this.monitoringService = MonitoringService.getInstance();
        this.charts = new Map();
        
        // Default time range: last hour
        this.timeRange = {
            start: Date.now() - 3600000,
            end: Date.now(),
            duration: 3600000
        };
        
        this.initialize();
    }
    
    /**
     * Initialize dashboard
     */
    private initialize(): void {
        // Setup monitoring service listeners
        this.setupMonitoringListeners();
        
        // Initialize charts configuration
        this.initializeCharts();
        
        // Start metrics collection
        this.monitoringService.startCollection();
        
        // Start update interval
        this.startUpdates();
        
        // Send initial data
        this.sendInitialData();
    }
    
    /**
     * Setup monitoring service listeners
     */
    private setupMonitoringListeners(): void {
        // System metrics updates
        this.monitoringService.on('metricsUpdate', (metrics: SystemMetrics) => {
            this.sendMessage({
                type: 'metricsUpdate',
                data: metrics
            });
        });
        
        // Performance updates
        this.monitoringService.on('performanceUpdate', (metrics: PerformanceMetrics) => {
            this.sendMessage({
                type: 'performanceUpdate',
                data: metrics
            });
        });
        
        // Safety updates
        this.monitoringService.on('safetyUpdate', (metrics: SafetyMetrics) => {
            this.sendMessage({
                type: 'safetyUpdate',
                data: metrics
            });
        });
        
        // Alerts
        this.monitoringService.on('alert', (alert: Alert) => {
            this.alerts.push(alert);
            // Keep last 50 alerts
            if (this.alerts.length > 50) {
                this.alerts.shift();
            }
            
            this.sendMessage({
                type: 'alert',
                data: alert
            });
        });
        
        // Session count changes
        this.monitoringService.on('sessionCountChange', (count: number) => {
            this.sendMessage({
                type: 'sessionCountUpdate',
                data: { count }
            });
        });
        
        // Threshold changes
        this.monitoringService.on('thresholdChange', (resource: string, threshold: number) => {
            this.sendMessage({
                type: 'thresholdUpdate',
                data: { resource, threshold }
            });
        });
    }
    
    /**
     * Initialize chart configurations
     */
    private initializeCharts(): void {
        // CPU usage chart
        this.charts.set('cpu', {
            type: 'line',
            title: 'CPU Usage',
            datasets: [{
                label: 'CPU %',
                data: [],
                color: '#4CAF50'
            }]
        });
        
        // Memory usage chart with dynamic threshold
        this.charts.set('memory', {
            type: 'line',
            title: 'Memory Usage',
            datasets: [
                {
                    label: 'Memory %',
                    data: [],
                    color: '#2196F3'
                },
                {
                    label: 'Dynamic Threshold',
                    data: [],
                    color: '#FF9800',
                    borderColor: '#FF9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    fill: '+1'
                }
            ]
        });
        
        // Disk usage gauge
        this.charts.set('disk', {
            type: 'gauge',
            title: 'Disk Usage',
            datasets: [{
                label: 'Disk %',
                data: [],
                color: '#9C27B0'
            }]
        });
        
        // Safety score trend
        this.charts.set('safety', {
            type: 'line',
            title: 'Safety Score',
            datasets: [{
                label: 'Score',
                data: [],
                color: '#4CAF50',
                tension: 0.4
            }]
        });
        
        // Performance metrics
        this.charts.set('performance', {
            type: 'line',
            title: 'Performance Metrics',
            datasets: [
                {
                    label: 'Response Time (ms)',
                    data: [],
                    color: '#FF5722'
                },
                {
                    label: 'Throughput (rps)',
                    data: [],
                    color: '#00BCD4'
                }
            ]
        });
    }
    
    /**
     * Start periodic updates
     */
    private startUpdates(): void {
        // Update charts every second for smooth animations
        this.updateInterval = setInterval(() => {
            this.updateCharts();
        }, 1000);
    }
    
    /**
     * Update charts with latest data
     */
    private updateCharts(): void {
        const metrics = this.monitoringService.getCurrentMetrics();
        const memoryScaling = this.monitoringService.getMemoryScalingConfig();
        
        // Update chart configurations
        this.sendMessage({
            type: 'chartsUpdate',
            data: {
                charts: Array.from(this.charts.entries()).map(([id, config]) => ({
                    id,
                    config
                })),
                metrics,
                memoryScaling,
                timeRange: this.timeRange
            }
        });
    }
    
    /**
     * Send initial data to WebView
     */
    private sendInitialData(): void {
        const metrics = this.monitoringService.getCurrentMetrics();
        const memoryScaling = this.monitoringService.getMemoryScalingConfig();
        const thresholds = this.monitoringService.getThresholds();
        
        this.sendMessage({
            type: 'initialize',
            data: {
                metrics,
                memoryScaling,
                thresholds,
                charts: Array.from(this.charts.entries()).map(([id, config]) => ({
                    id,
                    config
                })),
                alerts: this.alerts,
                timeRange: this.timeRange
            }
        });
    }
    
    /**
     * Handle messages from WebView
     */
    protected async handleMessage(message: WebViewMessage): Promise<void> {
        switch (message.type) {
            case 'ready':
                this.sendInitialData();
                break;
                
            case 'updateTimeRange':
                this.timeRange = message.data;
                this.updateCharts();
                break;
                
            case 'export':
                await this.handleExport(message.data as ExportOptions);
                break;
                
            case 'updateMemoryScaling':
                this.monitoringService.updateMemoryScalingConfig(message.data);
                break;
                
            case 'clearAlerts':
                this.alerts = [];
                this.sendMessage({
                    type: 'alertsCleared',
                    data: null
                });
                break;
                
            case 'refreshMetrics':
                this.updateCharts();
                break;
                
            default:
                this.logger.warn('Unknown message type from monitoring dashboard', { type: message.type });
        }
    }
    
    /**
     * Handle export request
     */
    private async handleExport(options: ExportOptions): Promise<void> {
        try {
            if (options.format === 'json' || options.format === 'csv') {
                const data = this.monitoringService.exportMetrics(options.format, options.sanitize);
                
                // Save to file
                const uri = await vscode.window.showSaveDialog({
                    defaultUri: vscode.Uri.file(`monitoring-export-${Date.now()}.${options.format}`),
                    filters: {
                        [options.format.toUpperCase()]: [options.format]
                    }
                });
                
                if (uri) {
                    await vscode.workspace.fs.writeFile(uri, Buffer.from(data, 'utf8'));
                    vscode.window.showInformationMessage('Monitoring data exported successfully');
                }
            } else if (options.format === 'png') {
                // PNG export would be handled by the WebView
                this.sendMessage({
                    type: 'exportChart',
                    data: options
                });
            }
        } catch (error) {
            this.logger.error('Export failed', error);
            vscode.window.showErrorMessage('Failed to export monitoring data');
        }
    }
    
    /**
     * Get HTML content
     */
    protected getHtmlContent(): string {
        const scriptUri = this.getUri('media', 'monitoring-dashboard.js');
        const styleUri = this.getUri('media', 'monitoring-dashboard.css');
        const chartJsUri = this.getUri('node_modules', 'chart.js', 'dist', 'chart.umd.js');
        
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${this.panel.webview.cspSource} 'unsafe-inline'; script-src ${this.panel.webview.cspSource}; img-src ${this.panel.webview.cspSource} data:;">
    <link href="${styleUri}" rel="stylesheet">
    <title>Monitoring Dashboard</title>
</head>
<body>
    <div class="dashboard-container">
        <!-- Header -->
        <header class="dashboard-header">
            <h1>System Monitoring Dashboard</h1>
            <div class="header-controls">
                <div class="session-indicator">
                    <span class="session-label">Active Sessions:</span>
                    <span id="session-count" class="session-count">1</span>
                </div>
                <button id="refresh-btn" class="control-btn" title="Refresh">
                    <span class="codicon codicon-refresh"></span>
                </button>
                <button id="export-btn" class="control-btn" title="Export">
                    <span class="codicon codicon-export"></span>
                </button>
                <button id="settings-btn" class="control-btn" title="Settings">
                    <span class="codicon codicon-settings-gear"></span>
                </button>
            </div>
        </header>
        
        <!-- Alerts Section -->
        <div id="alerts-container" class="alerts-container"></div>
        
        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <!-- Resource Gauges -->
            <div class="metric-card">
                <h3>CPU Usage</h3>
                <canvas id="cpu-gauge"></canvas>
                <div class="metric-value" id="cpu-value">0%</div>
            </div>
            
            <div class="metric-card">
                <h3>Memory Usage</h3>
                <canvas id="memory-gauge"></canvas>
                <div class="metric-value" id="memory-value">0%</div>
                <div class="threshold-indicator" id="memory-threshold">
                    Threshold: <span id="memory-threshold-value">80%</span>
                </div>
            </div>
            
            <div class="metric-card">
                <h3>Disk Usage</h3>
                <canvas id="disk-gauge"></canvas>
                <div class="metric-value" id="disk-value">0%</div>
            </div>
            
            <!-- Performance Metrics Cards -->
            <div class="metric-card metric-card-wide">
                <h3>Performance Metrics</h3>
                <div class="metric-stats">
                    <div class="stat-item">
                        <span class="stat-label">Response Time</span>
                        <span class="stat-value" id="response-time">0ms</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Throughput</span>
                        <span class="stat-value" id="throughput">0 rps</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Error Rate</span>
                        <span class="stat-value" id="error-rate">0%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Connections</span>
                        <span class="stat-value" id="connections">0</span>
                    </div>
                </div>
            </div>
            
            <!-- Safety Score -->
            <div class="metric-card">
                <h3>Safety Score</h3>
                <div class="safety-score" id="safety-score">
                    <span class="score-value">0.00</span>
                    <div class="score-bar">
                        <div class="score-fill" id="safety-fill"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Charts Section -->
        <div class="charts-section">
            <!-- Memory Usage Chart with Dynamic Threshold -->
            <div class="chart-container chart-large">
                <h3>Memory Usage Over Time</h3>
                <canvas id="memory-chart"></canvas>
            </div>
            
            <!-- CPU Usage Chart -->
            <div class="chart-container">
                <h3>CPU Usage Trend</h3>
                <canvas id="cpu-chart"></canvas>
            </div>
            
            <!-- Safety Score Chart -->
            <div class="chart-container">
                <h3>Safety Score Trend</h3>
                <canvas id="safety-chart"></canvas>
            </div>
            
            <!-- Performance Chart -->
            <div class="chart-container chart-large">
                <h3>Performance Metrics</h3>
                <canvas id="performance-chart"></canvas>
            </div>
        </div>
        
        <!-- Settings Modal -->
        <div id="settings-modal" class="modal">
            <div class="modal-content">
                <h2>Memory Scaling Settings</h2>
                <div class="settings-form">
                    <div class="form-group">
                        <label for="base-threshold">Base Threshold (%)</label>
                        <input type="number" id="base-threshold" min="50" max="95" step="5">
                    </div>
                    <div class="form-group">
                        <label for="scaling-factor">Scaling Factor (% per session)</label>
                        <input type="number" id="scaling-factor" min="1" max="10" step="1">
                    </div>
                    <div class="form-group">
                        <label for="max-threshold">Max Threshold (%)</label>
                        <input type="number" id="max-threshold" min="60" max="95" step="5">
                    </div>
                    <div class="form-actions">
                        <button id="save-settings" class="btn btn-primary">Save</button>
                        <button id="cancel-settings" class="btn btn-secondary">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="${chartJsUri}"></script>
    <script src="${scriptUri}"></script>
</body>
</html>`;
    }
    
    /**
     * Get panel state for persistence
     */
    protected getPanelState(): any {
        return {
            timeRange: this.timeRange,
            charts: Array.from(this.charts.entries()),
            alerts: this.alerts
        };
    }
    
    /**
     * Restore panel state
     */
    public restoreState(state: any): void {
        if (state.timeRange) {
            this.timeRange = state.timeRange;
        }
        if (state.charts) {
            this.charts = new Map(state.charts);
        }
        if (state.alerts) {
            this.alerts = state.alerts;
        }
    }
    
    /**
     * Dispose
     */
    public dispose(): void {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        this.monitoringService.stopCollection();
        super.dispose();
    }
}