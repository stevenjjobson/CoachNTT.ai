// Code Insights Panel Client Logic

(function() {
    const vscode = acquireVsCodeApi();
    
    // Chart instances
    const charts = {};
    
    // Current state
    let currentAnalysis = null;
    let projectMetrics = null;
    
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
        vscode.postMessage({ type: 'ready' });
    });
    
    // Initialize all charts
    function initializeCharts() {
        // Complexity distribution chart
        const complexityCtx = document.getElementById('complexity-chart').getContext('2d');
        charts.complexity = new Chart(complexityCtx, {
            type: 'bar',
            data: {
                labels: ['Cyclomatic', 'Cognitive', 'Nesting', 'Lines'],
                datasets: [{
                    label: 'Complexity Metrics',
                    data: [0, 0, 0, 0],
                    backgroundColor: [colors.blue, colors.purple, colors.orange, colors.cyan]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Complexity Distribution'
                    }
                }
            }
        });
        
        // Halstead metrics radar chart
        const halsteadCtx = document.getElementById('halstead-chart').getContext('2d');
        charts.halstead = new Chart(halsteadCtx, {
            type: 'radar',
            data: {
                labels: ['Vocabulary', 'Length', 'Volume', 'Difficulty', 'Effort'],
                datasets: [{
                    label: 'Halstead Metrics',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(33, 150, 243, 0.2)',
                    borderColor: colors.blue,
                    pointBackgroundColor: colors.blue
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Halstead Complexity'
                    }
                }
            }
        });
        
        // Quality trend line chart
        const trendCtx = document.getElementById('quality-trend-chart').getContext('2d');
        charts.qualityTrend = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Quality Score',
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
                        max: 100
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Quality Score Trend'
                    }
                }
            }
        });
        
        // Pattern distribution pie chart
        const patternCtx = document.getElementById('pattern-distribution').getContext('2d');
        charts.patternDist = new Chart(patternCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        colors.green,
                        colors.red,
                        colors.blue,
                        colors.orange,
                        colors.purple
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Pattern Distribution'
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    // Setup event listeners
    function setupEventListeners() {
        document.getElementById('analyze-btn').addEventListener('click', () => {
            vscode.postMessage({ type: 'analyzeCurrentFile' });
        });
        
        document.getElementById('refresh-btn').addEventListener('click', () => {
            vscode.postMessage({ type: 'refresh' });
        });
        
        document.getElementById('export-btn').addEventListener('click', () => {
            vscode.postMessage({ 
                type: 'exportReport',
                data: { format: 'json' }
            });
        });
    }
    
    // Handle messages from extension
    window.addEventListener('message', event => {
        const message = event.data;
        
        switch (message.type) {
            case 'analysisStarted':
                showAnalyzing();
                break;
                
            case 'analysisUpdate':
                handleAnalysisUpdate(message.data);
                break;
                
            case 'analysisFailed':
                showError(message.error);
                break;
                
            case 'projectMetrics':
                handleProjectMetrics(message.data);
                break;
        }
    });
    
    // Handle analysis update
    function handleAnalysisUpdate(data) {
        currentAnalysis = data;
        
        // Hide empty state
        document.getElementById('empty-state').style.display = 'none';
        
        // Update file info
        const fileInfo = document.getElementById('file-info');
        fileInfo.style.display = 'flex';
        document.getElementById('file-path').textContent = data.uri.split('/').pop();
        document.getElementById('analysis-time').textContent = new Date(data.timestamp).toLocaleTimeString();
        
        // Update summary cards
        updateSummaryCards(data);
        
        // Update patterns
        updatePatterns(data.patterns);
        
        // Update suggestions
        updateSuggestions(data.suggestions);
        
        // Update charts
        updateCharts(data);
    }
    
    // Update summary cards
    function updateSummaryCards(data) {
        // Quality score
        const score = data.summary.score;
        const grade = data.summary.grade;
        
        document.getElementById('quality-score').textContent = score;
        document.getElementById('quality-grade').textContent = grade;
        document.getElementById('score-fill').style.width = `${score}%`;
        
        // Apply grade color
        const scoreValue = document.getElementById('quality-score');
        if (score >= 80) scoreValue.style.color = colors.green;
        else if (score >= 60) scoreValue.style.color = colors.blue;
        else if (score >= 40) scoreValue.style.color = colors.orange;
        else scoreValue.style.color = colors.red;
        
        // Complexity metrics
        document.getElementById('cyclomatic').textContent = data.metrics.cyclomatic;
        document.getElementById('cognitive').textContent = data.metrics.cognitive;
        document.getElementById('nesting').textContent = data.metrics.nestingDepth;
        document.getElementById('loc').textContent = data.metrics.linesOfCode;
        
        // Issues count
        const issueCounts = { error: 0, warning: 0, info: 0 };
        data.issues.forEach(issue => {
            if (issue.severity in issueCounts) {
                issueCounts[issue.severity]++;
            }
        });
        
        document.getElementById('error-count').textContent = issueCounts.error;
        document.getElementById('warning-count').textContent = issueCounts.warning;
        document.getElementById('info-count').textContent = issueCounts.info;
    }
    
    // Update patterns list
    function updatePatterns(patterns) {
        const container = document.getElementById('patterns-list');
        const section = document.getElementById('patterns-section');
        
        if (patterns.length === 0) {
            section.style.display = 'none';
            return;
        }
        
        section.style.display = 'block';
        container.innerHTML = '';
        
        patterns.forEach(pattern => {
            const item = document.createElement('div');
            item.className = `pattern-item ${pattern.impact}`;
            
            const icon = pattern.impact === 'positive' ? '✅' :
                        pattern.impact === 'negative' ? '⚠️' : 'ℹ️';
            
            item.innerHTML = `
                <span class="pattern-icon">${icon}</span>
                <div class="pattern-content">
                    <div class="pattern-name">${pattern.name}</div>
                    <div class="pattern-description">${pattern.description}</div>
                </div>
                <span class="pattern-confidence">${Math.round(pattern.confidence * 100)}%</span>
            `;
            
            item.addEventListener('click', () => {
                vscode.postMessage({
                    type: 'navigateToIssue',
                    data: {
                        uri: currentAnalysis.uri,
                        range: pattern.location
                    }
                });
            });
            
            container.appendChild(item);
        });
    }
    
    // Update suggestions list
    function updateSuggestions(suggestions) {
        const container = document.getElementById('suggestions-list');
        const section = document.getElementById('suggestions-section');
        
        if (suggestions.length === 0) {
            section.style.display = 'none';
            return;
        }
        
        section.style.display = 'block';
        container.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            
            const severityIcon = {
                error: 'error',
                warning: 'warning',
                info: 'info'
            }[suggestion.severity];
            
            item.innerHTML = `
                <div class="suggestion-header">
                    <span class="codicon codicon-${severityIcon}"></span>
                    <span class="suggestion-type">${suggestion.type}</span>
                </div>
                <div class="suggestion-message">${suggestion.message}</div>
                ${suggestion.explanation ? `<div class="suggestion-explanation">${suggestion.explanation}</div>` : ''}
                <div class="suggestion-actions">
                    ${suggestion.autoFixable ? '<button class="button" data-fix="true">Apply Fix</button>' : ''}
                    <button class="button secondary" data-navigate="true">Go to Code</button>
                </div>
            `;
            
            // Add event listeners
            const fixBtn = item.querySelector('[data-fix]');
            if (fixBtn) {
                fixBtn.addEventListener('click', () => {
                    vscode.postMessage({
                        type: 'applyFix',
                        data: { suggestionId: suggestion.id }
                    });
                });
            }
            
            const navBtn = item.querySelector('[data-navigate]');
            navBtn.addEventListener('click', () => {
                vscode.postMessage({
                    type: 'navigateToIssue',
                    data: {
                        uri: currentAnalysis.uri,
                        range: suggestion.location
                    }
                });
            });
            
            container.appendChild(item);
        });
    }
    
    // Update charts
    function updateCharts(data) {
        // Update complexity chart
        charts.complexity.data.datasets[0].data = [
            data.metrics.cyclomatic,
            data.metrics.cognitive,
            data.metrics.nestingDepth,
            data.metrics.linesOfCode / 10 // Scale down for display
        ];
        charts.complexity.update();
        
        // Update Halstead chart
        const h = data.metrics.halstead;
        charts.halstead.data.datasets[0].data = [
            h.vocabulary,
            h.length / 10, // Scale down
            h.volume / 100, // Scale down
            h.difficulty,
            h.effort / 1000 // Scale down
        ];
        charts.halstead.update();
        
        // Update pattern distribution
        const patternCounts = {};
        data.patterns.forEach(p => {
            patternCounts[p.type] = (patternCounts[p.type] || 0) + 1;
        });
        
        charts.patternDist.data.labels = Object.keys(patternCounts);
        charts.patternDist.data.datasets[0].data = Object.values(patternCounts);
        charts.patternDist.update();
        
        // Update quality trend (append to existing data)
        const timestamp = new Date(data.timestamp).toLocaleTimeString();
        charts.qualityTrend.data.labels.push(timestamp);
        charts.qualityTrend.data.datasets[0].data.push(data.summary.score);
        
        // Keep only last 10 points
        if (charts.qualityTrend.data.labels.length > 10) {
            charts.qualityTrend.data.labels.shift();
            charts.qualityTrend.data.datasets[0].data.shift();
        }
        
        charts.qualityTrend.update();
    }
    
    // Handle project metrics
    function handleProjectMetrics(metrics) {
        projectMetrics = metrics;
        
        document.getElementById('files-analyzed').textContent = metrics.fileCount || 0;
        document.getElementById('avg-complexity').textContent = 
            metrics.averageComplexity ? metrics.averageComplexity.toFixed(1) : '--';
        document.getElementById('total-issues').textContent = 
            Object.values(metrics.issueCount || {}).reduce((a, b) => a + b, 0);
        document.getElementById('project-quality').textContent = 
            metrics.codeQualityScore ? Math.round(metrics.codeQualityScore) : '--';
    }
    
    // Show analyzing state
    function showAnalyzing() {
        // Could add a loading spinner
    }
    
    // Show error state
    function showError(error) {
        // Could show error message
    }
})();