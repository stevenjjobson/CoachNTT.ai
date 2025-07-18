import * as vscode from 'vscode';
import * as ts from 'typescript';
import { CodeAnalysisService } from '../services/code-analysis-service';
import { Logger } from '../utils/logger';
import {
    CodeLensData,
    AnalysisResult,
    ComplexityMetrics,
    PatternMatch,
    IssueSeverity
} from '../types/code-analysis.types';

/**
 * CodeLens provider for displaying inline code insights
 */
export class ComplexityCodeLensProvider implements vscode.CodeLensProvider {
    private logger: Logger;
    private analysisService: CodeAnalysisService;
    private codeLenses: Map<string, CodeLensData[]>;
    private onDidChangeCodeLensesEmitter: vscode.EventEmitter<void>;
    
    public readonly onDidChangeCodeLenses: vscode.Event<void>;
    
    constructor() {
        this.logger = Logger.getInstance();
        this.analysisService = CodeAnalysisService.getInstance();
        this.codeLenses = new Map();
        this.onDidChangeCodeLensesEmitter = new vscode.EventEmitter<void>();
        this.onDidChangeCodeLenses = this.onDidChangeCodeLensesEmitter.event;
        
        // Listen for analysis updates
        this.analysisService.on('analysisCompleted', (result: AnalysisResult) => {
            this.updateCodeLenses(result);
        });
    }
    
    /**
     * Provide code lenses for a document
     */
    public async provideCodeLenses(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeLens[]> {
        // Skip non-supported files
        if (!this.isSupportedDocument(document)) {
            return [];
        }
        
        try {
            // Get or trigger analysis
            const result = await this.getAnalysisResult(document.uri);
            if (!result) {
                return [];
            }
            
            // Generate code lenses
            const lenses: vscode.CodeLens[] = [];
            
            // Parse AST to find functions and classes
            const sourceFile = ts.createSourceFile(
                document.fileName,
                document.getText(),
                ts.ScriptTarget.Latest,
                true
            );
            
            const visit = (node: ts.Node) => {
                if (token.isCancellationRequested) {
                    return;
                }
                
                // Add complexity lens for functions
                if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isArrowFunction(node)) {
                    const functionLenses = this.createFunctionLenses(node, document, result);
                    lenses.push(...functionLenses);
                }
                
                // Add lens for classes
                if (ts.isClassDeclaration(node)) {
                    const classLenses = this.createClassLenses(node, document, result);
                    lenses.push(...classLenses);
                }
                
                ts.forEachChild(node, visit);
            };
            
            visit(sourceFile);
            
            // Add pattern lenses
            for (const pattern of result.patterns) {
                const patternLens = this.createPatternLens(pattern, document);
                if (patternLens) {
                    lenses.push(patternLens);
                }
            }
            
            return lenses;
            
        } catch (error) {
            this.logger.error('Failed to provide code lenses', error);
            return [];
        }
    }
    
    /**
     * Resolve code lens command
     */
    public resolveCodeLens?(
        codeLens: vscode.CodeLens,
        token: vscode.CancellationToken
    ): vscode.CodeLens {
        // Commands are already set in provideCodeLenses
        return codeLens;
    }
    
    /**
     * Create lenses for functions
     */
    private createFunctionLenses(
        node: ts.FunctionDeclaration | ts.MethodDeclaration | ts.ArrowFunction,
        document: vscode.TextDocument,
        result: AnalysisResult
    ): vscode.CodeLens[] {
        const lenses: vscode.CodeLens[] = [];
        const range = this.nodeToRange(node, document);
        
        // Calculate local complexity
        const localComplexity = this.calculateLocalComplexity(node);
        
        // Complexity lens
        const complexityLens = new vscode.CodeLens(range, {
            title: `Complexity: ${localComplexity.cyclomatic}`,
            tooltip: this.getComplexityTooltip(localComplexity),
            command: 'coachntt.showComplexityDetails',
            arguments: [document.uri, range, localComplexity]
        });
        
        // Style based on threshold
        if (localComplexity.cyclomatic > 20) {
            complexityLens.command!.title = `⚠️ ${complexityLens.command!.title}`;
        } else if (localComplexity.cyclomatic > 10) {
            complexityLens.command!.title = `⚡ ${complexityLens.command!.title}`;
        }
        
        lenses.push(complexityLens);
        
        // Performance hint if applicable
        const perfIssues = this.findPerformanceIssues(node);
        if (perfIssues.length > 0) {
            const perfLens = new vscode.CodeLens(range, {
                title: `🔍 Performance: ${perfIssues[0]}`,
                command: 'coachntt.showPerformanceHints',
                arguments: [document.uri, range, perfIssues]
            });
            lenses.push(perfLens);
        }
        
        return lenses;
    }
    
    /**
     * Create lenses for classes
     */
    private createClassLenses(
        node: ts.ClassDeclaration,
        document: vscode.TextDocument,
        result: AnalysisResult
    ): vscode.CodeLens[] {
        const lenses: vscode.CodeLens[] = [];
        const range = this.nodeToRange(node, document);
        
        // Count methods and properties
        let methodCount = 0;
        let propertyCount = 0;
        let totalComplexity = 0;
        
        node.members.forEach(member => {
            if (ts.isMethodDeclaration(member)) {
                methodCount++;
                totalComplexity += this.calculateLocalComplexity(member).cyclomatic;
            } else if (ts.isPropertyDeclaration(member)) {
                propertyCount++;
            }
        });
        
        // Class metrics lens
        const metricsLens = new vscode.CodeLens(range, {
            title: `📊 Methods: ${methodCount}, Properties: ${propertyCount}, Total Complexity: ${totalComplexity}`,
            tooltip: 'Click to see class analysis details',
            command: 'coachntt.showClassAnalysis',
            arguments: [document.uri, range, { methodCount, propertyCount, totalComplexity }]
        });
        
        // Warning for god class
        if (methodCount > 20 || totalComplexity > 50) {
            metricsLens.command!.title = `⚠️ God Class Risk - ${metricsLens.command!.title}`;
        }
        
        lenses.push(metricsLens);
        
        return lenses;
    }
    
    /**
     * Create lens for pattern match
     */
    private createPatternLens(
        pattern: PatternMatch,
        document: vscode.TextDocument
    ): vscode.CodeLens | null {
        const icon = pattern.impact === 'positive' ? '✅' : 
                     pattern.impact === 'negative' ? '⚠️' : 'ℹ️';
        
        return new vscode.CodeLens(pattern.location, {
            title: `${icon} ${pattern.name}`,
            tooltip: pattern.description,
            command: 'coachntt.showPatternDetails',
            arguments: [document.uri, pattern]
        });
    }
    
    /**
     * Calculate local complexity for a node
     */
    private calculateLocalComplexity(node: ts.Node): Partial<ComplexityMetrics> {
        let cyclomatic = 1;
        let cognitive = 0;
        let nestingDepth = 0;
        let maxNesting = 0;
        
        const visit = (n: ts.Node, depth: number) => {
            // Cyclomatic complexity
            if (this.isDecisionPoint(n)) {
                cyclomatic++;
            }
            
            // Cognitive complexity
            if (this.isDecisionPoint(n)) {
                cognitive += 1 + depth;
            }
            
            // Track nesting
            if (this.increasesNesting(n)) {
                depth++;
                maxNesting = Math.max(maxNesting, depth);
            }
            
            ts.forEachChild(n, child => visit(child, depth));
        };
        
        ts.forEachChild(node, child => visit(child, 0));
        
        return {
            cyclomatic,
            cognitive,
            nestingDepth: maxNesting
        };
    }
    
    /**
     * Find performance issues in a node
     */
    private findPerformanceIssues(node: ts.Node): string[] {
        const issues: string[] = [];
        
        const visit = (n: ts.Node) => {
            // Nested loops
            if (this.isLoop(n)) {
                let hasNestedLoop = false;
                ts.forEachChild(n, child => {
                    if (this.containsLoop(child)) {
                        hasNestedLoop = true;
                    }
                });
                if (hasNestedLoop) {
                    issues.push('Nested loops detected');
                }
            }
            
            // Synchronous file operations
            if (ts.isCallExpression(n) && n.expression.getText().includes('Sync')) {
                issues.push('Synchronous operation detected');
            }
            
            ts.forEachChild(n, visit);
        };
        
        visit(node);
        
        return issues;
    }
    
    /**
     * Helper methods
     */
    private isDecisionPoint(node: ts.Node): boolean {
        return ts.isIfStatement(node) ||
               ts.isConditionalExpression(node) ||
               ts.isCaseClause(node) ||
               this.isLoop(node);
    }
    
    private isLoop(node: ts.Node): boolean {
        return ts.isForStatement(node) ||
               ts.isForInStatement(node) ||
               ts.isForOfStatement(node) ||
               ts.isWhileStatement(node) ||
               ts.isDoStatement(node);
    }
    
    private containsLoop(node: ts.Node): boolean {
        let hasLoop = false;
        const visit = (n: ts.Node) => {
            if (this.isLoop(n)) {
                hasLoop = true;
                return;
            }
            ts.forEachChild(n, visit);
        };
        visit(node);
        return hasLoop;
    }
    
    private increasesNesting(node: ts.Node): boolean {
        return ts.isBlock(node) || 
               ts.isIfStatement(node) || 
               this.isLoop(node) ||
               ts.isTryStatement(node);
    }
    
    private nodeToRange(node: ts.Node, document: vscode.TextDocument): vscode.Range {
        const start = document.positionAt(node.getStart());
        const end = document.positionAt(node.getEnd());
        
        // For functions/classes, put lens on the line with the declaration
        if (ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node) || ts.isMethodDeclaration(node)) {
            return new vscode.Range(start.line, 0, start.line, 0);
        }
        
        return new vscode.Range(start, end);
    }
    
    private getComplexityTooltip(metrics: Partial<ComplexityMetrics>): string {
        return `Cyclomatic: ${metrics.cyclomatic || 0}
Cognitive: ${metrics.cognitive || 0}
Nesting: ${metrics.nestingDepth || 0}

Click for detailed analysis`;
    }
    
    private isSupportedDocument(document: vscode.TextDocument): boolean {
        const supportedLanguages = ['typescript', 'javascript', 'typescriptreact', 'javascriptreact'];
        return supportedLanguages.includes(document.languageId);
    }
    
    private async getAnalysisResult(uri: vscode.Uri): Promise<AnalysisResult | null> {
        try {
            return await this.analysisService.analyzeFile(uri);
        } catch (error) {
            this.logger.error('Failed to get analysis result', error);
            return null;
        }
    }
    
    /**
     * Update code lenses when analysis completes
     */
    private updateCodeLenses(result: AnalysisResult): void {
        const key = result.uri.toString();
        const lensData: CodeLensData[] = [];
        
        // Store lens data for this file
        this.codeLenses.set(key, lensData);
        
        // Trigger refresh
        this.onDidChangeCodeLensesEmitter.fire();
    }
    
    /**
     * Dispose provider
     */
    public dispose(): void {
        this.codeLenses.clear();
        this.onDidChangeCodeLensesEmitter.dispose();
    }
}