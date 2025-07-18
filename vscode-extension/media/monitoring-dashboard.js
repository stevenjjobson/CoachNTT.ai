// Monitoring Dashboard Client-Side Logic

(function() {
    const vscode = acquireVsCodeApi();
    
    // Chart instances
    const charts = {};
    
    // Current state
    let state = {
        metrics: {
            system: [],
            performance: [],
            safety: []
        },
        memoryScaling: {},
        thresholds: {},
        alerts: [],
        timeRange: {}
    };
    
    // Chart colors
    const colors = {
        green: '#4CAF50',
        blue: '#2196F3',
        orange: '#FF9800',
        purple: '#9C27B0',
        red: '#F44336',
        cyan: '#00BCD4',
        yellow: '#FFEB3B',
        grey: '#9E9E9E'
    };
    
    // Initialize on load
    window.addEventListener('load', () => {
        initializeCharts();
        setupEventListeners();
        
        // Notify extension we're ready
        vscode.postMessage({ type: 'ready' });
    });
    
    // Initialize all charts
    function initializeCharts() {
        // CPU Gauge
        const cpuCtx = document.getElementById('cpu-gauge').getContext('2d');
        charts.cpuGauge = new Chart(cpuCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [colors.green, 'rgba(255, 255, 255, 0.1)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                circumference: 180,
                rotation: 270,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
        
        // Memory Gauge with dynamic threshold
        const memoryCtx = document.getElementById('memory-gauge').getContext('2d');
        charts.memoryGauge = new Chart(memoryCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [colors.blue, 'rgba(255, 255, 255, 0.1)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                circumference: 180,
                rotation: 270,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
        
        // Disk Gauge
        const diskCtx = document.getElementById('disk-gauge').getContext('2d');
        charts.diskGauge = new Chart(diskCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [colors.purple, 'rgba(255, 255, 255, 0.1)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                circumference: 180,
                rotation: 270,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
        
        // Memory Line Chart with threshold
        const memoryChartCtx = document.getElementById('memory-chart').getContext('2d');
        charts.memoryChart = new Chart(memoryChartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Memory Usage %',
                        data: [],
                        borderColor: colors.blue,
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Dynamic Threshold',
                        data: [],
                        borderColor: colors.orange,
                        borderDash: [5, 5],
                        backgroundColor: 'transparent',
                        fill: false,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 10
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
        
        // CPU Line Chart
        const cpuChartCtx = document.getElementById('cpu-chart').getContext('2d');
        charts.cpuChart = new Chart(cpuChartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage %',
                    data: [],
                    borderColor: colors.green,
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        
        // Safety Score Chart
        const safetyChartCtx = document.getElementById('safety-chart').getContext('2d');
        charts.safetyChart = new Chart(safetyChartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Safety Score',
                    data: [],
                    borderColor: colors.green,
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2);
                            }
                        }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        
        // Performance Chart
        const perfChartCtx = document.getElementById('performance-chart').getContext('2d');
        charts.performanceChart = new Chart(perfChartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Response Time (ms)',
                        data: [],
                        borderColor: colors.red,
                        backgroundColor: 'rgba(244, 67, 54, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Throughput (rps)',
                        data: [],
                        borderColor: colors.cyan,
                        backgroundColor: 'rgba(0, 188, 212, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Throughput (rps)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }
    
    // Setup event listeners
    function setupEventListeners() {
        // Control buttons
        document.getElementById('refresh-btn').addEventListener('click', () => {
            vscode.postMessage({ type: 'refreshMetrics' });
        });
        
        document.getElementById('export-btn').addEventListener('click', showExportDialog);
        
        document.getElementById('settings-btn').addEventListener('click', showSettingsModal);
        
        // Settings modal
        document.getElementById('save-settings').addEventListener('click', saveSettings);
        document.getElementById('cancel-settings').addEventListener('click', hideSettingsModal);
        
        // Close modal on background click
        document.getElementById('settings-modal').addEventListener('click', (e) => {
            if (e.target.id === 'settings-modal') {
                hideSettingsModal();
            }
        });
    }
    
    // Handle messages from extension
    window.addEventListener('message', event => {
        const message = event.data;
        
        switch (message.type) {
            case 'initialize':
                handleInitialize(message.data);
                break;
            case 'metricsUpdate':
                handleMetricsUpdate(message.data);
                break;
            case 'performanceUpdate':
                handlePerformanceUpdate(message.data);
                break;
            case 'safetyUpdate':
                handleSafetyUpdate(message.data);
                break;
            case 'alert':
                handleAlert(message.data);
                break;
            case 'sessionCountUpdate':
                handleSessionCountUpdate(message.data);
                break;
            case 'thresholdUpdate':
                handleThresholdUpdate(message.data);
                break;
            case 'chartsUpdate':
                handleChartsUpdate(message.data);
                break;
            case 'alertsCleared':
                clearAlerts();
                break;
        }
    });
    
    // Handle initialization
    function handleInitialize(data) {
        state = { ...state, ...data };
        
        // Update session count
        document.getElementById('session-count').textContent = state.memoryScaling.currentSessions;
        
        // Update settings form
        document.getElementById('base-threshold').value = state.memoryScaling.baseThresholdPercentage;
        document.getElementById('scaling-factor').value = state.memoryScaling.scalingFactorPerSession;
        document.getElementById('max-threshold').value = state.memoryScaling.maxThresholdPercentage;
        
        // Display any existing alerts
        state.alerts.forEach(alert => displayAlert(alert));
    }
    
    // Handle metrics update
    function handleMetricsUpdate(metrics) {
        // Update gauges
        updateGauge(charts.cpuGauge, metrics.cpu.usage, getGaugeColor(metrics.cpu.usage, 70, 90));
        updateGauge(charts.memoryGauge, metrics.memory.percentage, getMemoryGaugeColor(metrics.memory.percentage, metrics.memory.threshold));
        updateGauge(charts.diskGauge, metrics.disk.percentage, getGaugeColor(metrics.disk.percentage, 80, 90));
        
        // Update values
        document.getElementById('cpu-value').textContent = `${metrics.cpu.usage.toFixed(1)}%`;
        document.getElementById('memory-value').textContent = `${metrics.memory.percentage.toFixed(1)}%`;
        document.getElementById('disk-value').textContent = `${metrics.disk.percentage.toFixed(1)}%`;
        document.getElementById('memory-threshold-value').textContent = `${metrics.memory.threshold.toFixed(1)}%`;
    }
    
    // Handle performance update
    function handlePerformanceUpdate(metrics) {
        document.getElementById('response-time').textContent = `${metrics.responseTime}ms`;
        document.getElementById('throughput').textContent = `${metrics.throughput} rps`;
        document.getElementById('error-rate').textContent = `${metrics.errorRate}%`;
        document.getElementById('connections').textContent = metrics.activeConnections;
    }
    
    // Handle safety update
    function handleSafetyUpdate(metrics) {
        const scoreElement = document.querySelector('.score-value');
        const fillElement = document.getElementById('safety-fill');
        
        scoreElement.textContent = metrics.score.toFixed(2);
        fillElement.style.width = `${metrics.score * 100}%`;
        
        // Update color based on score
        if (metrics.score >= 0.8) {
            scoreElement.style.color = colors.green;
            fillElement.style.backgroundColor = colors.green;
        } else if (metrics.score >= 0.6) {
            scoreElement.style.color = colors.orange;
            fillElement.style.backgroundColor = colors.orange;
        } else {
            scoreElement.style.color = colors.red;
            fillElement.style.backgroundColor = colors.red;
        }
    }
    
    // Handle alerts
    function handleAlert(alert) {
        displayAlert(alert);
    }
    
    // Display alert
    function displayAlert(alert) {
        const container = document.getElementById('alerts-container');
        const alertEl = document.createElement('div');
        alertEl.className = `alert alert-${alert.type}`;
        alertEl.innerHTML = `
            <span class="codicon codicon-${alert.type === 'critical' ? 'error' : 'warning'}"></span>
            <span>${alert.message} (${alert.value.toFixed(1)}% > ${alert.threshold}%)</span>
            <span class="alert-dismiss codicon codicon-close" onclick="this.parentElement.remove()"></span>
        `;
        
        container.appendChild(alertEl);
        
        // Auto-remove after 10 seconds
        setTimeout(() => alertEl.remove(), 10000);
    }
    
    // Clear alerts
    function clearAlerts() {
        document.getElementById('alerts-container').innerHTML = '';
    }
    
    // Handle session count update
    function handleSessionCountUpdate(data) {
        document.getElementById('session-count').textContent = data.count;
        document.getElementById('session-count').classList.add('updating');
        setTimeout(() => {
            document.getElementById('session-count').classList.remove('updating');
        }, 1000);
    }
    
    // Handle threshold update
    function handleThresholdUpdate(data) {
        if (data.resource === 'memory') {
            document.getElementById('memory-threshold-value').textContent = `${data.threshold.toFixed(1)}%`;
        }
    }
    
    // Handle charts update
    function handleChartsUpdate(data) {
        const { metrics, timeRange } = data;
        const maxPoints = 60; // Show last 60 data points
        
        // Update memory chart
        if (metrics.system.length > 0) {
            const memoryData = metrics.system.slice(-maxPoints);
            const labels = memoryData.map(m => formatTime(m.timestamp));
            const usage = memoryData.map(m => m.memory.percentage);
            const threshold = memoryData.map(m => m.memory.threshold);
            
            charts.memoryChart.data.labels = labels;
            charts.memoryChart.data.datasets[0].data = usage;
            charts.memoryChart.data.datasets[1].data = threshold;
            charts.memoryChart.update('none');
            
            // Update CPU chart
            const cpuData = memoryData.map(m => m.cpu.usage);
            charts.cpuChart.data.labels = labels;
            charts.cpuChart.data.datasets[0].data = cpuData;
            charts.cpuChart.update('none');
        }
        
        // Update safety chart
        if (metrics.safety.length > 0) {
            const safetyData = metrics.safety.slice(-maxPoints);
            const labels = safetyData.map(m => formatTime(m.timestamp));
            const scores = safetyData.map(m => m.score);
            
            charts.safetyChart.data.labels = labels;
            charts.safetyChart.data.datasets[0].data = scores;
            charts.safetyChart.update('none');
        }
        
        // Update performance chart
        if (metrics.performance.length > 0) {
            const perfData = metrics.performance.slice(-maxPoints);
            const labels = perfData.map(m => formatTime(m.timestamp));
            const responseTimes = perfData.map(m => m.responseTime);
            const throughput = perfData.map(m => m.throughput);
            
            charts.performanceChart.data.labels = labels;
            charts.performanceChart.data.datasets[0].data = responseTimes;
            charts.performanceChart.data.datasets[1].data = throughput;
            charts.performanceChart.update('none');
        }
    }
    
    // Update gauge chart
    function updateGauge(chart, value, color) {
        chart.data.datasets[0].data = [value, 100 - value];
        chart.data.datasets[0].backgroundColor[0] = color;
        chart.update('none');
    }
    
    // Get gauge color based on thresholds
    function getGaugeColor(value, warning, critical) {
        if (value >= critical) return colors.red;
        if (value >= warning) return colors.orange;
        return colors.green;
    }
    
    // Get memory gauge color based on dynamic threshold
    function getMemoryGaugeColor(value, threshold) {
        if (value >= threshold) return colors.red;
        if (value >= threshold - 10) return colors.orange;
        return colors.blue;
    }
    
    // Format timestamp for chart labels
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    
    // Show settings modal
    function showSettingsModal() {
        document.getElementById('settings-modal').classList.add('show');
    }
    
    // Hide settings modal
    function hideSettingsModal() {
        document.getElementById('settings-modal').classList.remove('show');
    }
    
    // Save settings
    function saveSettings() {
        const config = {
            baseThresholdPercentage: parseInt(document.getElementById('base-threshold').value),
            scalingFactorPerSession: parseInt(document.getElementById('scaling-factor').value),
            maxThresholdPercentage: parseInt(document.getElementById('max-threshold').value)
        };
        
        vscode.postMessage({
            type: 'updateMemoryScaling',
            data: config
        });
        
        hideSettingsModal();
    }
    
    // Show export dialog
    function showExportDialog() {
        const format = prompt('Export format (json, csv, png):', 'json');
        if (format) {
            vscode.postMessage({
                type: 'export',
                data: {
                    format: format.toLowerCase(),
                    timeRange: state.timeRange,
                    metrics: ['system', 'performance', 'safety'],
                    includeAlerts: true,
                    sanitize: true
                }
            });
        }
    }
})();