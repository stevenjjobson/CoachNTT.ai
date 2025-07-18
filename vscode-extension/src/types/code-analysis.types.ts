import * as vscode from 'vscode';

/**
 * Code analysis result for a file or code block
 */
export interface AnalysisResult {
    uri: vscode.Uri;
    timestamp: Date;
    version: number;
    metrics: ComplexityMetrics;
    patterns: PatternMatch[];
    suggestions: CodeSuggestion[];
    issues: CodeIssue[];
    summary: AnalysisSummary;
}

/**
 * Complexity metrics for code analysis
 */
export interface ComplexityMetrics {
    cyclomatic: number;          // McCabe complexity
    cognitive: number;           // Cognitive complexity
    halstead: HalsteadMetrics;   // Halstead metrics
    linesOfCode: number;
    linesOfComments: number;
    nestingDepth: number;
    maintainabilityIndex: number; // 0-100 score
}

/**
 * Halstead complexity metrics
 */
export interface HalsteadMetrics {
    vocabulary: number;
    length: number;
    volume: number;
    difficulty: number;
    effort: number;
    time: number;
    bugs: number;
}

/**
 * Detected pattern in code
 */
export interface PatternMatch {
    type: PatternType;
    name: string;
    location: vscode.Range;
    confidence: number;         // 0-1 confidence score
    description: string;
    impact: 'positive' | 'negative' | 'neutral';
    suggestion?: string;
}

/**
 * Pattern types for detection
 */
export enum PatternType {
    // Design Patterns
    Singleton = 'singleton',
    Factory = 'factory',
    Observer = 'observer',
    Strategy = 'strategy',
    Decorator = 'decorator',
    
    // Anti-patterns
    GodClass = 'god-class',
    SpaghettiCode = 'spaghetti-code',
    CopyPasteCode = 'copy-paste-code',
    DeadCode = 'dead-code',
    LongMethod = 'long-method',
    
    // Performance Issues
    NestedLoops = 'nested-loops',
    SynchronousIO = 'synchronous-io',
    MemoryLeak = 'memory-leak',
    CircularDependency = 'circular-dependency',
    
    // Security Issues
    HardcodedSecret = 'hardcoded-secret',
    SQLInjection = 'sql-injection',
    InsecureRandom = 'insecure-random'
}

/**
 * Code improvement suggestion
 */
export interface CodeSuggestion {
    id: string;
    type: SuggestionType;
    severity: 'info' | 'warning' | 'error';
    location: vscode.Range;
    message: string;
    replacement?: string;
    explanation?: string;
    documentationUrl?: string;
    autoFixable: boolean;
}

/**
 * Suggestion types
 */
export enum SuggestionType {
    Refactoring = 'refactoring',
    Performance = 'performance',
    Security = 'security',
    BestPractice = 'best-practice',
    Modernization = 'modernization',
    Accessibility = 'accessibility'
}

/**
 * Code issue found during analysis
 */
export interface CodeIssue {
    rule: string;
    severity: IssueSeverity;
    location: vscode.Range;
    message: string;
    fixable: boolean;
}

/**
 * Issue severity levels
 */
export enum IssueSeverity {
    Error = 'error',
    Warning = 'warning',
    Info = 'info',
    Hint = 'hint'
}

/**
 * Analysis summary
 */
export interface AnalysisSummary {
    score: number;              // 0-100 overall score
    grade: 'A' | 'B' | 'C' | 'D' | 'F';
    strengths: string[];
    weaknesses: string[];
    trends: TrendData[];
}

/**
 * Trend data for metrics
 */
export interface TrendData {
    metric: string;
    current: number;
    previous: number;
    change: number;
    trend: 'improving' | 'declining' | 'stable';
}

/**
 * Analysis settings
 */
export interface AnalysisSettings {
    enabledPatterns: PatternType[];
    complexityThresholds: ComplexityThresholds;
    excludePatterns: string[];
    includePatterns: string[];
    maxFileSize: number;
    enableAutoFix: boolean;
    enableCodeLens: boolean;
    analysisDepth: 'shallow' | 'normal' | 'deep';
}

/**
 * Complexity thresholds for warnings
 */
export interface ComplexityThresholds {
    cyclomatic: { warning: number; error: number };
    cognitive: { warning: number; error: number };
    nestingDepth: { warning: number; error: number };
    functionLength: { warning: number; error: number };
}

/**
 * Pattern detector interface
 */
export interface PatternDetector {
    type: PatternType;
    name: string;
    detect(ast: any, context: AnalysisContext): PatternMatch[];
}

/**
 * Analysis context
 */
export interface AnalysisContext {
    uri: vscode.Uri;
    document: vscode.TextDocument;
    ast: any;
    settings: AnalysisSettings;
    cache: Map<string, any>;
}

/**
 * Code lens data
 */
export interface CodeLensData {
    type: 'complexity' | 'pattern' | 'suggestion';
    range: vscode.Range;
    title: string;
    tooltip?: string;
    command?: vscode.Command;
    severity?: IssueSeverity;
}

/**
 * Analysis task for background processing
 */
export interface AnalysisTask {
    id: string;
    uri: vscode.Uri;
    priority: 'high' | 'normal' | 'low';
    status: 'pending' | 'running' | 'completed' | 'failed';
    startTime?: Date;
    endTime?: Date;
    result?: AnalysisResult;
    error?: Error;
}

/**
 * Code metrics for monitoring integration
 */
export interface CodeMetrics {
    timestamp: Date;
    fileCount: number;
    totalComplexity: number;
    averageComplexity: number;
    issueCount: { [key in IssueSeverity]: number };
    patternCount: { [key: string]: number };
    codeQualityScore: number;
}