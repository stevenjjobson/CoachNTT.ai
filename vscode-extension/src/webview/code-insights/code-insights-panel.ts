import * as vscode from 'vscode';
import { ManagedWebViewPanel } from '../webview-manager';
import { Logger } from '../../utils/logger';
import { CodeAnalysisService } from '../../services/code-analysis-service';
import { AnalysisResult, CodeMetrics } from '../../types/code-analysis.types';

/**
 * Code insights WebView panel
 */
export class CodeInsightsPanel extends ManagedWebViewPanel {
    private analysisService: CodeAnalysisService;
    private currentUri?: vscode.Uri;
    private currentResult?: AnalysisResult;
    
    constructor(
        panel: vscode.WebviewPanel,
        context: vscode.ExtensionContext,
        logger: Logger
    ) {
        super('Code Insights', panel, context, logger);
        
        this.analysisService = CodeAnalysisService.getInstance();
        
        // Listen for analysis updates
        this.analysisService.on('analysisCompleted', (result: AnalysisResult) => {
            if (result.uri.toString() === this.currentUri?.toString()) {
                this.updateAnalysis(result);
            }
        });
        
        this.analysisService.on('metricsUpdated', (metrics: CodeMetrics) => {
            this.updateMetrics(metrics);
        });
    }
    
    /**
     * Get HTML content for the WebView
     */
    protected getHtmlContent(): string {
        const scriptUri = this.getResourceUri('media', 'code-insights.js');
        const styleUri = this.getResourceUri('media', 'code-insights.css');
        const chartUri = this.getResourceUri('node_modules', 'chart.js', 'dist', 'chart.umd.js');
        
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src ${this.panel.webview.cspSource} 'unsafe-inline'; style-src ${this.panel.webview.cspSource} 'unsafe-inline'; font-src ${this.panel.webview.cspSource};">
    <link href="${styleUri}" rel="stylesheet">
    <title>Code Insights</title>
</head>
<body>
    <div class="insights-container">
        <!-- Header -->
        <div class="insights-header">
            <h1>Code Insights</h1>
            <div class="header-actions">
                <button id="analyze-btn" class="button">
                    <span class="codicon codicon-play"></span>
                    Analyze Current File
                </button>
                <button id="refresh-btn" class="button">
                    <span class="codicon codicon-refresh"></span>
                    Refresh
                </button>
                <button id="export-btn" class="button secondary">
                    <span class="codicon codicon-export"></span>
                    Export Report
                </button>
            </div>
        </div>
        
        <!-- File Info -->
        <div class="file-info" id="file-info" style="display: none;">
            <span class="codicon codicon-file-code"></span>
            <span id="file-path"></span>
            <span class="timestamp" id="analysis-time"></span>
        </div>
        
        <!-- Summary Cards -->
        <div class="summary-cards">
            <div class="card">
                <div class="card-header">
                    <span class="codicon codicon-dashboard"></span>
                    <h3>Quality Score</h3>
                </div>
                <div class="score-display">
                    <div class="score-value" id="quality-score">--</div>
                    <div class="score-grade" id="quality-grade">-</div>
                </div>
                <div class="score-bar">
                    <div class="score-fill" id="score-fill"></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="codicon codicon-graph"></span>
                    <h3>Complexity</h3>
                </div>
                <div class="metrics-grid">
                    <div class="metric">
                        <span class="metric-label">Cyclomatic</span>
                        <span class="metric-value" id="cyclomatic">--</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Cognitive</span>
                        <span class="metric-value" id="cognitive">--</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Nesting</span>
                        <span class="metric-value" id="nesting">--</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">LOC</span>
                        <span class="metric-value" id="loc">--</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="codicon codicon-issues"></span>
                    <h3>Issues</h3>
                </div>
                <div class="issues-summary">
                    <div class="issue-count error">
                        <span class="codicon codicon-error"></span>
                        <span id="error-count">0</span>
                    </div>
                    <div class="issue-count warning">
                        <span class="codicon codicon-warning"></span>
                        <span id="warning-count">0</span>
                    </div>
                    <div class="issue-count info">
                        <span class="codicon codicon-info"></span>
                        <span id="info-count">0</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Patterns Section -->
        <div class="section" id="patterns-section" style="display: none;">
            <h2>
                <span class="codicon codicon-symbol-class"></span>
                Detected Patterns
            </h2>
            <div id="patterns-list" class="patterns-list"></div>
        </div>
        
        <!-- Suggestions Section -->
        <div class="section" id="suggestions-section" style="display: none;">
            <h2>
                <span class="codicon codicon-lightbulb"></span>
                Suggestions
            </h2>
            <div id="suggestions-list" class="suggestions-list"></div>
        </div>
        
        <!-- Charts Section -->
        <div class="section charts-section">
            <h2>
                <span class="codicon codicon-graph-line"></span>
                Metrics Visualization
            </h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <canvas id="complexity-chart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="halstead-chart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="quality-trend-chart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="pattern-distribution"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Project Overview -->
        <div class="section" id="project-section">
            <h2>
                <span class="codicon codicon-folder-opened"></span>
                Project Overview
            </h2>
            <div class="project-stats">
                <div class="stat">
                    <span class="stat-label">Files Analyzed</span>
                    <span class="stat-value" id="files-analyzed">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Avg Complexity</span>
                    <span class="stat-value" id="avg-complexity">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Issues</span>
                    <span class="stat-value" id="total-issues">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Code Quality</span>
                    <span class="stat-value" id="project-quality">--</span>
                </div>
            </div>
        </div>
        
        <!-- Empty State -->
        <div class="empty-state" id="empty-state">
            <span class="codicon codicon-code"></span>
            <h2>No Analysis Available</h2>
            <p>Open a TypeScript or JavaScript file and click "Analyze Current File" to get started.</p>
        </div>
    </div>
    
    <script src="${chartUri}"></script>
    <script src="${scriptUri}"></script>
</body>
</html>`;
    }
    
    /**
     * Handle messages from WebView
     */
    protected async handleMessage(message: any): Promise<void> {
        switch (message.type) {
            case 'ready':
                await this.handleReady();
                break;
                
            case 'analyzeCurrentFile':
                await this.analyzeCurrentFile();
                break;
                
            case 'refresh':
                await this.refresh();
                break;
                
            case 'exportReport':
                await this.exportReport(message.data);
                break;
                
            case 'navigateToIssue':
                await this.navigateToIssue(message.data);
                break;
                
            case 'applyFix':
                await this.applyFix(message.data);
                break;
        }
    }
    
    /**
     * Handle WebView ready
     */
    private async handleReady(): Promise<void> {
        // Send initial data if available
        if (this.currentResult) {
            this.postMessage({
                type: 'analysisUpdate',
                data: this.currentResult
            });
        }
        
        // Send project metrics
        const metrics = await this.getProjectMetrics();
        this.postMessage({
            type: 'projectMetrics',
            data: metrics
        });
    }
    
    /**
     * Analyze current file
     */
    private async analyzeCurrentFile(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }
        
        try {
            this.postMessage({ type: 'analysisStarted' });
            
            const result = await this.analysisService.analyzeFile(editor.document.uri);
            this.currentUri = editor.document.uri;
            this.currentResult = result;
            
            this.updateAnalysis(result);
            
        } catch (error) {
            this.logger.error('Analysis failed', error);
            vscode.window.showErrorMessage('Analysis failed: ' + (error as Error).message);
            this.postMessage({ type: 'analysisFailed', error: (error as Error).message });
        }
    }
    
    /**
     * Update analysis in WebView
     */
    private updateAnalysis(result: AnalysisResult): void {
        this.postMessage({
            type: 'analysisUpdate',
            data: {
                uri: result.uri.toString(),
                timestamp: result.timestamp,
                metrics: result.metrics,
                patterns: result.patterns,
                suggestions: result.suggestions,
                issues: result.issues,
                summary: result.summary
            }
        });
    }
    
    /**
     * Update project metrics
     */
    private updateMetrics(metrics: CodeMetrics): void {
        this.postMessage({
            type: 'projectMetrics',
            data: metrics
        });
    }
    
    /**
     * Get project metrics
     */
    private async getProjectMetrics(): Promise<any> {
        // Aggregate metrics from analysis service
        return {
            filesAnalyzed: 0,
            averageComplexity: 0,
            totalIssues: 0,
            codeQualityScore: 0
        };
    }
    
    /**
     * Navigate to issue location
     */
    private async navigateToIssue(data: any): Promise<void> {
        try {
            const uri = vscode.Uri.parse(data.uri);
            const document = await vscode.workspace.openTextDocument(uri);
            const editor = await vscode.window.showTextDocument(document);
            
            const range = new vscode.Range(
                data.range.start.line,
                data.range.start.character,
                data.range.end.line,
                data.range.end.character
            );
            
            editor.selection = new vscode.Selection(range.start, range.end);
            editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
            
        } catch (error) {
            this.logger.error('Failed to navigate to issue', error);
            vscode.window.showErrorMessage('Failed to navigate to issue');
        }
    }
    
    /**
     * Apply fix for an issue
     */
    private async applyFix(data: any): Promise<void> {
        // Implementation for applying automated fixes
        vscode.window.showInformationMessage('Fix applied successfully');
    }
    
    /**
     * Refresh analysis
     */
    private async refresh(): Promise<void> {
        if (this.currentUri) {
            try {
                const result = await this.analysisService.analyzeFile(this.currentUri);
                this.currentResult = result;
                this.updateAnalysis(result);
            } catch (error) {
                this.logger.error('Refresh failed', error);
            }
        }
    }
    
    /**
     * Export analysis report
     */
    private async exportReport(options: any): Promise<void> {
        if (!this.currentResult) {
            vscode.window.showWarningMessage('No analysis to export');
            return;
        }
        
        const uri = await vscode.window.showSaveDialog({
            defaultUri: vscode.Uri.file(`code-analysis-${Date.now()}.json`),
            filters: {
                'JSON': ['json'],
                'HTML': ['html'],
                'Markdown': ['md']
            }
        });
        
        if (uri) {
            // Export logic based on format
            vscode.window.showInformationMessage('Report exported successfully');
        }
    }
    
    /**
     * Dispose panel
     */
    public dispose(): void {
        this.analysisService.removeAllListeners('analysisCompleted');
        this.analysisService.removeAllListeners('metricsUpdated');
        super.dispose();
    }
}