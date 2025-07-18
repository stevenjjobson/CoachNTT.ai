import * as vscode from 'vscode';
import * as ts from 'typescript';
import { EventEmitter } from 'events';
import {
    AnalysisResult,
    AnalysisSettings,
    AnalysisTask,
    CodeIssue,
    CodeMetrics,
    CodeSuggestion,
    ComplexityMetrics,
    ComplexityThresholds,
    HalsteadMetrics,
    IssueSeverity,
    PatternDetector,
    PatternMatch,
    PatternType,
    SuggestionType,
    AnalysisContext
} from '../types/code-analysis.types';
import { Logger } from '../utils/logger';
import { MonitoringService } from './monitoring-service';

/**
 * Code analysis service for advanced pattern detection and metrics
 */
export class CodeAnalysisService extends EventEmitter {
    private static instance: CodeAnalysisService;
    private logger: Logger;
    private monitoring: MonitoringService;
    
    // Analysis state
    private analysisCache: Map<string, AnalysisResult>;
    private activeAnalyses: Map<string, AnalysisTask>;
    private patternDetectors: Map<PatternType, PatternDetector>;
    private settings: AnalysisSettings;
    
    // Performance tracking
    private analysisQueue: AnalysisTask[];
    private isProcessing: boolean;
    private lastAnalysisTime: number;
    
    private constructor() {
        super();
        this.logger = Logger.getInstance();
        this.monitoring = MonitoringService.getInstance();
        
        this.analysisCache = new Map();
        this.activeAnalyses = new Map();
        this.patternDetectors = new Map();
        this.analysisQueue = [];
        this.isProcessing = false;
        this.lastAnalysisTime = 0;
        
        this.settings = this.getDefaultSettings();
        this.initializePatternDetectors();
    }
    
    public static getInstance(): CodeAnalysisService {
        if (!CodeAnalysisService.instance) {
            CodeAnalysisService.instance = new CodeAnalysisService();
        }
        return CodeAnalysisService.instance;
    }
    
    /**
     * Analyze a file
     */
    public async analyzeFile(uri: vscode.Uri): Promise<AnalysisResult> {
        const cacheKey = uri.toString();
        
        // Check cache
        const cached = this.analysisCache.get(cacheKey);
        if (cached && this.isCacheValid(cached, uri)) {
            return cached;
        }
        
        // Create analysis task
        const task: AnalysisTask = {
            id: `analysis-${Date.now()}`,
            uri,
            priority: 'normal',
            status: 'pending',
            startTime: new Date()
        };
        
        this.activeAnalyses.set(task.id, task);
        this.emit('analysisStarted', task);
        
        try {
            // Read document
            const document = await vscode.workspace.openTextDocument(uri);
            
            // Check file size limit
            if (document.getText().length > this.settings.maxFileSize) {
                throw new Error('File too large for analysis');
            }
            
            // Parse AST
            const ast = this.parseTypeScript(document.getText(), uri.fsPath);
            
            // Create analysis context
            const context: AnalysisContext = {
                uri,
                document,
                ast,
                settings: this.settings,
                cache: new Map()
            };
            
            // Calculate metrics
            const metrics = this.calculateComplexityMetrics(ast, context);
            
            // Detect patterns
            const patterns = this.detectPatterns(ast, context);
            
            // Generate suggestions
            const suggestions = this.generateSuggestions(metrics, patterns, context);
            
            // Find issues
            const issues = this.findIssues(ast, context);
            
            // Create result
            const result: AnalysisResult = {
                uri,
                timestamp: new Date(),
                version: document.version,
                metrics,
                patterns,
                suggestions,
                issues,
                summary: this.generateSummary(metrics, patterns, issues)
            };
            
            // Update cache
            this.analysisCache.set(cacheKey, result);
            
            // Update task
            task.status = 'completed';
            task.endTime = new Date();
            task.result = result;
            
            // Emit events
            this.emit('analysisCompleted', result);
            this.updateCodeMetrics();
            
            return result;
            
        } catch (error) {
            task.status = 'failed';
            task.endTime = new Date();
            task.error = error as Error;
            
            this.logger.error('Code analysis failed', error);
            this.emit('analysisFailed', { task, error });
            
            throw error;
        } finally {
            this.activeAnalyses.delete(task.id);
            this.lastAnalysisTime = Date.now();
        }
    }
    
    /**
     * Parse TypeScript/JavaScript code
     */
    private parseTypeScript(content: string, fileName: string): ts.SourceFile {
        return ts.createSourceFile(
            fileName,
            content,
            ts.ScriptTarget.Latest,
            true,
            fileName.endsWith('.tsx') || fileName.endsWith('.jsx')
                ? ts.ScriptKind.TSX
                : ts.ScriptKind.TS
        );
    }
    
    /**
     * Calculate complexity metrics
     */
    private calculateComplexityMetrics(ast: ts.SourceFile, context: AnalysisContext): ComplexityMetrics {
        let cyclomatic = 1; // Base complexity
        let cognitive = 0;
        let maxNesting = 0;
        let currentNesting = 0;
        let operatorCount = 0;
        let operandCount = 0;
        const operators = new Set<string>();
        const operands = new Set<string>();
        
        const visit = (node: ts.Node) => {
            // Cyclomatic complexity
            if (this.isDecisionPoint(node)) {
                cyclomatic++;
            }
            
            // Cognitive complexity
            cognitive += this.getCognitiveWeight(node, currentNesting);
            
            // Nesting depth
            if (this.increasesNesting(node)) {
                currentNesting++;
                maxNesting = Math.max(maxNesting, currentNesting);
            }
            
            // Halstead metrics
            if (this.isOperator(node)) {
                operatorCount++;
                operators.add(node.kind.toString());
            } else if (this.isOperand(node)) {
                operandCount++;
                operands.add(node.getText());
            }
            
            ts.forEachChild(node, visit);
            
            if (this.increasesNesting(node)) {
                currentNesting--;
            }
        };
        
        visit(ast);
        
        // Calculate Halstead metrics
        const vocabulary = operators.size + operands.size;
        const length = operatorCount + operandCount;
        const volume = length * Math.log2(vocabulary);
        const difficulty = (operators.size / 2) * (operandCount / operands.size);
        const effort = difficulty * volume;
        const time = effort / 18; // seconds
        const bugs = volume / 3000;
        
        const halstead: HalsteadMetrics = {
            vocabulary,
            length,
            volume,
            difficulty,
            effort,
            time,
            bugs
        };
        
        // Count lines
        const lines = context.document.getText().split('\n');
        const linesOfCode = lines.filter(line => line.trim().length > 0).length;
        const linesOfComments = lines.filter(line => 
            line.trim().startsWith('//') || line.trim().startsWith('/*')
        ).length;
        
        // Maintainability index
        const maintainabilityIndex = Math.max(
            0,
            Math.min(
                100,
                171 - 5.2 * Math.log(halstead.volume) - 0.23 * cyclomatic - 16.2 * Math.log(linesOfCode)
            )
        );
        
        return {
            cyclomatic,
            cognitive,
            halstead,
            linesOfCode,
            linesOfComments,
            nestingDepth: maxNesting,
            maintainabilityIndex
        };
    }
    
    /**
     * Detect patterns in code
     */
    private detectPatterns(ast: ts.SourceFile, context: AnalysisContext): PatternMatch[] {
        const patterns: PatternMatch[] = [];
        
        for (const [type, detector] of this.patternDetectors) {
            if (this.settings.enabledPatterns.includes(type)) {
                try {
                    const matches = detector.detect(ast, context);
                    patterns.push(...matches);
                } catch (error) {
                    this.logger.error(`Pattern detection failed for ${type}`, error);
                }
            }
        }
        
        return patterns;
    }
    
    /**
     * Generate code suggestions
     */
    private generateSuggestions(
        metrics: ComplexityMetrics,
        patterns: PatternMatch[],
        context: AnalysisContext
    ): CodeSuggestion[] {
        const suggestions: CodeSuggestion[] = [];
        
        // Complexity suggestions
        if (metrics.cyclomatic > this.settings.complexityThresholds.cyclomatic.warning) {
            suggestions.push({
                id: 'high-cyclomatic',
                type: SuggestionType.Refactoring,
                severity: metrics.cyclomatic > this.settings.complexityThresholds.cyclomatic.error ? 'error' : 'warning',
                location: new vscode.Range(0, 0, 0, 0),
                message: `High cyclomatic complexity (${metrics.cyclomatic}). Consider breaking this into smaller functions.`,
                autoFixable: false
            });
        }
        
        // Pattern-based suggestions
        for (const pattern of patterns) {
            if (pattern.suggestion && pattern.impact === 'negative') {
                suggestions.push({
                    id: `pattern-${pattern.type}`,
                    type: SuggestionType.BestPractice,
                    severity: 'warning',
                    location: pattern.location,
                    message: pattern.suggestion,
                    autoFixable: false
                });
            }
        }
        
        return suggestions;
    }
    
    /**
     * Find code issues
     */
    private findIssues(ast: ts.SourceFile, context: AnalysisContext): CodeIssue[] {
        const issues: CodeIssue[] = [];
        
        const visit = (node: ts.Node) => {
            // Check for common issues
            if (ts.isIfStatement(node) && !node.elseStatement && this.isEmptyBlock(node.thenStatement)) {
                issues.push({
                    rule: 'empty-if',
                    severity: IssueSeverity.Warning,
                    location: this.nodeToRange(node, context.document),
                    message: 'Empty if statement',
                    fixable: true
                });
            }
            
            ts.forEachChild(node, visit);
        };
        
        visit(ast);
        
        return issues;
    }
    
    /**
     * Generate analysis summary
     */
    private generateSummary(
        metrics: ComplexityMetrics,
        patterns: PatternMatch[],
        issues: CodeIssue[]
    ): any {
        const score = Math.round(metrics.maintainabilityIndex);
        const grade = score >= 80 ? 'A' : score >= 60 ? 'B' : score >= 40 ? 'C' : score >= 20 ? 'D' : 'F';
        
        const strengths: string[] = [];
        const weaknesses: string[] = [];
        
        if (metrics.cyclomatic < 10) strengths.push('Low complexity');
        if (patterns.some(p => p.impact === 'positive')) strengths.push('Good design patterns used');
        
        if (metrics.cyclomatic > 20) weaknesses.push('High complexity');
        if (issues.length > 10) weaknesses.push('Multiple code issues');
        
        return {
            score,
            grade,
            strengths,
            weaknesses,
            trends: []
        };
    }
    
    /**
     * Initialize pattern detectors
     */
    private initializePatternDetectors(): void {
        // Singleton pattern detector
        this.patternDetectors.set(PatternType.Singleton, {
            type: PatternType.Singleton,
            name: 'Singleton Pattern',
            detect: (ast, context) => {
                const matches: PatternMatch[] = [];
                // Implementation simplified for brevity
                return matches;
            }
        });
        
        // Long method detector
        this.patternDetectors.set(PatternType.LongMethod, {
            type: PatternType.LongMethod,
            name: 'Long Method',
            detect: (ast, context) => {
                const matches: PatternMatch[] = [];
                const visit = (node: ts.Node) => {
                    if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node)) {
                        const start = node.getStart();
                        const end = node.getEnd();
                        const lines = context.document.getText().substring(start, end).split('\n').length;
                        
                        if (lines > this.settings.complexityThresholds.functionLength.warning) {
                            matches.push({
                                type: PatternType.LongMethod,
                                name: 'Long Method',
                                location: this.nodeToRange(node, context.document),
                                confidence: 1.0,
                                description: `Method has ${lines} lines`,
                                impact: 'negative',
                                suggestion: 'Consider breaking this method into smaller functions'
                            });
                        }
                    }
                    ts.forEachChild(node, visit);
                };
                visit(ast);
                return matches;
            }
        });
    }
    
    /**
     * Helper methods
     */
    private isDecisionPoint(node: ts.Node): boolean {
        return ts.isIfStatement(node) ||
               ts.isConditionalExpression(node) ||
               ts.isCaseClause(node) ||
               ts.isForStatement(node) ||
               ts.isWhileStatement(node) ||
               ts.isDoStatement(node);
    }
    
    private getCognitiveWeight(node: ts.Node, nestingLevel: number): number {
        if (this.isDecisionPoint(node)) {
            return 1 + nestingLevel;
        }
        return 0;
    }
    
    private increasesNesting(node: ts.Node): boolean {
        return ts.isBlock(node) || ts.isIfStatement(node) || ts.isIterationStatement(node, true);
    }
    
    private isOperator(node: ts.Node): boolean {
        return node.kind >= ts.SyntaxKind.FirstAssignment && node.kind <= ts.SyntaxKind.LastBinaryOperator;
    }
    
    private isOperand(node: ts.Node): boolean {
        return ts.isIdentifier(node) || ts.isLiteralExpression(node);
    }
    
    private isEmptyBlock(node: ts.Node): boolean {
        return ts.isBlock(node) && node.statements.length === 0;
    }
    
    private nodeToRange(node: ts.Node, document: vscode.TextDocument): vscode.Range {
        const start = document.positionAt(node.getStart());
        const end = document.positionAt(node.getEnd());
        return new vscode.Range(start, end);
    }
    
    private isCacheValid(cached: AnalysisResult, uri: vscode.Uri): boolean {
        // Cache is valid for 5 minutes
        const cacheAge = Date.now() - cached.timestamp.getTime();
        return cacheAge < 5 * 60 * 1000;
    }
    
    private updateCodeMetrics(): void {
        const metrics: CodeMetrics = {
            timestamp: new Date(),
            fileCount: this.analysisCache.size,
            totalComplexity: 0,
            averageComplexity: 0,
            issueCount: {
                error: 0,
                warning: 0,
                info: 0,
                hint: 0
            },
            patternCount: {},
            codeQualityScore: 0
        };
        
        let totalScore = 0;
        
        for (const result of this.analysisCache.values()) {
            metrics.totalComplexity += result.metrics.cyclomatic;
            totalScore += result.summary.score;
            
            for (const issue of result.issues) {
                metrics.issueCount[issue.severity]++;
            }
            
            for (const pattern of result.patterns) {
                metrics.patternCount[pattern.type] = (metrics.patternCount[pattern.type] || 0) + 1;
            }
        }
        
        if (this.analysisCache.size > 0) {
            metrics.averageComplexity = metrics.totalComplexity / this.analysisCache.size;
            metrics.codeQualityScore = totalScore / this.analysisCache.size;
        }
        
        this.emit('metricsUpdated', metrics);
    }
    
    private getDefaultSettings(): AnalysisSettings {
        return {
            enabledPatterns: [
                PatternType.LongMethod,
                PatternType.GodClass,
                PatternType.NestedLoops,
                PatternType.DeadCode,
                PatternType.HardcodedSecret
            ],
            complexityThresholds: {
                cyclomatic: { warning: 10, error: 20 },
                cognitive: { warning: 15, error: 30 },
                nestingDepth: { warning: 4, error: 6 },
                functionLength: { warning: 50, error: 100 }
            },
            excludePatterns: ['**/node_modules/**', '**/dist/**'],
            includePatterns: ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx'],
            maxFileSize: 1024 * 1024, // 1MB
            enableAutoFix: false,
            enableCodeLens: true,
            analysisDepth: 'normal'
        };
    }
    
    /**
     * Dispose service
     */
    public dispose(): void {
        this.analysisCache.clear();
        this.activeAnalyses.clear();
        this.patternDetectors.clear();
        this.removeAllListeners();
    }
}