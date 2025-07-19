import * as vscode from 'vscode';
import * as ts from 'typescript';
import { SemanticQuery, SearchConstraint } from './semantic-analyzer';
import { Logger } from '../../utils/logger';
import { CodeAnalysisService } from '../code-analysis-service';

export interface SearchResult {
    uri: vscode.Uri;
    node: ts.Node;
    name: string;
    type: NodeType;
    range: vscode.Range;
    score: number;
    snippet: string;
    context: SearchContext;
}

export interface SearchContext {
    fileName: string;
    className?: string;
    functionName?: string;
    lineNumber: number;
    parentType?: NodeType;
    depth: number;
}

export type NodeType = 'function' | 'class' | 'interface' | 'method' | 'property' | 
                      'variable' | 'type' | 'enum' | 'import' | 'export';

export interface SearchOptions {
    maxResults: number;
    minScore: number;
    includeSnippets: boolean;
    snippetLines: number;
}

export class CodeSearchEngine {
    private logger: Logger;
    private codeAnalysis: CodeAnalysisService;
    private searchCache: Map<string, SearchResult[]>;
    private astCache: Map<string, ts.SourceFile>;
    
    constructor() {
        this.logger = Logger.getInstance();
        this.codeAnalysis = CodeAnalysisService.getInstance();
        this.searchCache = new Map();
        this.astCache = new Map();
    }
    
    public async search(
        query: SemanticQuery,
        options: SearchOptions = this.getDefaultOptions()
    ): Promise<SearchResult[]> {
        this.logger.info(`Starting code search with ${query.constraints.length} constraints`);
        
        // Get all TypeScript/JavaScript files
        const files = await this.findSearchableFiles();
        
        const allResults: SearchResult[] = [];
        
        // Search each file
        for (const file of files) {
            try {
                const fileResults = await this.searchFile(file, query, options);
                allResults.push(...fileResults);
            } catch (error) {
                this.logger.error(`Search failed for ${file.fsPath}`, error);
            }
        }
        
        // Sort by score and limit results
        const sortedResults = allResults
            .sort((a, b) => b.score - a.score)
            .filter(r => r.score >= options.minScore)
            .slice(0, options.maxResults);
        
        this.logger.info(`Found ${sortedResults.length} results`);
        return sortedResults;
    }
    
    private async searchFile(
        uri: vscode.Uri,
        query: SemanticQuery,
        options: SearchOptions
    ): Promise<SearchResult[]> {
        // Get or parse AST
        const ast = await this.getAST(uri);
        if (!ast) {
            return [];
        }
        
        const results: SearchResult[] = [];
        const document = await vscode.workspace.openTextDocument(uri);
        
        // Visit all nodes in the AST
        const visit = (node: ts.Node, context: SearchContext) => {
            // Skip if max depth exceeded
            if (context.depth > query.searchScope.maxDepth) {
                return;
            }
            
            // Check if node matches search criteria
            const score = this.scoreNode(node, query, context);
            if (score > 0) {
                const result = this.createSearchResult(node, uri, document, score, context, options);
                if (result) {
                    results.push(result);
                }
            }
            
            // Visit children with updated context
            const childContext = this.updateContext(node, context);
            ts.forEachChild(node, child => visit(child, childContext));
        };
        
        // Start visiting from root
        const rootContext: SearchContext = {
            fileName: uri.fsPath,
            lineNumber: 0,
            depth: 0
        };
        
        visit(ast, rootContext);
        
        return results;
    }
    
    private scoreNode(node: ts.Node, query: SemanticQuery, context: SearchContext): number {
        let score = 0;
        
        // Get node info
        const nodeInfo = this.getNodeInfo(node);
        if (!nodeInfo) {
            return 0;
        }
        
        // Apply constraints
        for (const constraint of query.constraints) {
            const constraintScore = this.applyConstraint(node, nodeInfo, constraint, context);
            
            switch (constraint.type) {
                case 'must':
                    if (constraintScore === 0) {
                        return 0; // Must constraints are mandatory
                    }
                    score += constraintScore * constraint.weight;
                    break;
                case 'should':
                    score += constraintScore * constraint.weight;
                    break;
                case 'mustNot':
                    if (constraintScore > 0) {
                        return 0; // MustNot constraints are exclusionary
                    }
                    break;
            }
        }
        
        // Apply context requirements
        for (const requirement of query.contextRequirements) {
            if (!this.meetsContextRequirement(node, requirement, context)) {
                score *= 0.5; // Reduce score for unmet context requirements
            }
        }
        
        // Boost for certain conditions
        if (nodeInfo.isExported && query.searchScope.includeExports) {
            score *= 1.2;
        }
        
        if (nodeInfo.hasJSDoc) {
            score *= 1.1;
        }
        
        return score;
    }
    
    private applyConstraint(
        node: ts.Node,
        nodeInfo: NodeInfo,
        constraint: SearchConstraint,
        context: SearchContext
    ): number {
        switch (constraint.field) {
            case 'name':
                return this.matchName(nodeInfo.name, constraint.value) ? 1 : 0;
                
            case 'type':
                return nodeInfo.type === constraint.value ? 1 : 0;
                
            case 'content':
                return this.matchContent(node, constraint.value) ? 1 : 0;
                
            case 'comment':
                return this.matchComment(nodeInfo.jsDoc, constraint.value) ? 1 : 0;
                
            default:
                return 0;
        }
    }
    
    private matchName(name: string, pattern: string | RegExp): boolean {
        if (typeof pattern === 'string') {
            return name.toLowerCase().includes(pattern.toLowerCase());
        }
        return pattern.test(name);
    }
    
    private matchContent(node: ts.Node, pattern: string | RegExp): boolean {
        const content = node.getText();
        if (typeof pattern === 'string') {
            return content.toLowerCase().includes(pattern.toLowerCase());
        }
        return pattern.test(content);
    }
    
    private matchComment(jsDoc: string | undefined, pattern: string | RegExp): boolean {
        if (!jsDoc) {
            return false;
        }
        if (typeof pattern === 'string') {
            return jsDoc.toLowerCase().includes(pattern.toLowerCase());
        }
        return pattern.test(jsDoc);
    }
    
    private meetsContextRequirement(
        node: ts.Node,
        requirement: any,
        context: SearchContext
    ): boolean {
        switch (requirement.type) {
            case 'hasParent':
                return this.hasParentOfType(node, requirement.nodeType);
                
            case 'inScope':
                return context.className === requirement.pattern || 
                       context.functionName === requirement.pattern;
                       
            default:
                return true;
        }
    }
    
    private hasParentOfType(node: ts.Node, type: string): boolean {
        let parent = node.parent;
        while (parent) {
            if (this.getNodeType(parent) === type) {
                return true;
            }
            parent = parent.parent;
        }
        return false;
    }
    
    private createSearchResult(
        node: ts.Node,
        uri: vscode.Uri,
        document: vscode.TextDocument,
        score: number,
        context: SearchContext,
        options: SearchOptions
    ): SearchResult | null {
        const nodeInfo = this.getNodeInfo(node);
        if (!nodeInfo) {
            return null;
        }
        
        const range = this.nodeToRange(node, document);
        
        return {
            uri,
            node,
            name: nodeInfo.name,
            type: nodeInfo.type,
            range,
            score,
            snippet: options.includeSnippets ? 
                this.extractSnippet(document, range, options.snippetLines) : '',
            context
        };
    }
    
    private extractSnippet(
        document: vscode.TextDocument,
        range: vscode.Range,
        lines: number
    ): string {
        const startLine = Math.max(0, range.start.line - Math.floor(lines / 2));
        const endLine = Math.min(document.lineCount - 1, range.end.line + Math.floor(lines / 2));
        
        const snippet: string[] = [];
        for (let i = startLine; i <= endLine; i++) {
            const line = document.lineAt(i);
            const prefix = i === range.start.line ? '▶ ' : '  ';
            snippet.push(`${prefix}${line.text}`);
        }
        
        return snippet.join('\n');
    }
    
    private updateContext(node: ts.Node, parentContext: SearchContext): SearchContext {
        const context = { ...parentContext };
        context.depth++;
        
        const nodeInfo = this.getNodeInfo(node);
        if (!nodeInfo) {
            return context;
        }
        
        switch (nodeInfo.type) {
            case 'class':
                context.className = nodeInfo.name;
                context.parentType = 'class';
                break;
            case 'function':
            case 'method':
                context.functionName = nodeInfo.name;
                context.parentType = nodeInfo.type;
                break;
        }
        
        const sourceFile = node.getSourceFile();
        const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
        context.lineNumber = line + 1;
        
        return context;
    }
    
    private getNodeInfo(node: ts.Node): NodeInfo | null {
        const type = this.getNodeType(node);
        if (!type) {
            return null;
        }
        
        const name = this.getNodeName(node);
        if (!name) {
            return null;
        }
        
        return {
            name,
            type,
            isExported: this.isExported(node),
            hasJSDoc: this.hasJSDoc(node),
            jsDoc: this.getJSDoc(node)
        };
    }
    
    private getNodeType(node: ts.Node): NodeType | null {
        if (ts.isFunctionDeclaration(node)) return 'function';
        if (ts.isClassDeclaration(node)) return 'class';
        if (ts.isInterfaceDeclaration(node)) return 'interface';
        if (ts.isMethodDeclaration(node)) return 'method';
        if (ts.isPropertyDeclaration(node)) return 'property';
        if (ts.isVariableDeclaration(node)) return 'variable';
        if (ts.isTypeAliasDeclaration(node)) return 'type';
        if (ts.isEnumDeclaration(node)) return 'enum';
        if (ts.isImportDeclaration(node)) return 'import';
        if (ts.isExportDeclaration(node)) return 'export';
        return null;
    }
    
    private getNodeName(node: ts.Node): string | null {
        if ('name' in node && node.name && ts.isIdentifier(node.name)) {
            return node.name.text;
        }
        
        if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name)) {
            return node.name.text;
        }
        
        return null;
    }
    
    private isExported(node: ts.Node): boolean {
        return !!(node.modifiers && node.modifiers.some(
            mod => mod.kind === ts.SyntaxKind.ExportKeyword
        ));
    }
    
    private hasJSDoc(node: ts.Node): boolean {
        return ts.getJSDocCommentsAndTags(node).length > 0;
    }
    
    private getJSDoc(node: ts.Node): string | undefined {
        const jsDocs = ts.getJSDocCommentsAndTags(node);
        if (jsDocs.length === 0) {
            return undefined;
        }
        
        return jsDocs.map(doc => doc.getText()).join('\n');
    }
    
    private nodeToRange(node: ts.Node, document: vscode.TextDocument): vscode.Range {
        const start = document.positionAt(node.getStart());
        const end = document.positionAt(node.getEnd());
        return new vscode.Range(start, end);
    }
    
    private async getAST(uri: vscode.Uri): Promise<ts.SourceFile | null> {
        // Check cache
        const cached = this.astCache.get(uri.toString());
        if (cached) {
            return cached;
        }
        
        try {
            const document = await vscode.workspace.openTextDocument(uri);
            const content = document.getText();
            
            const ast = ts.createSourceFile(
                uri.fsPath,
                content,
                ts.ScriptTarget.Latest,
                true,
                uri.fsPath.endsWith('.tsx') || uri.fsPath.endsWith('.jsx')
                    ? ts.ScriptKind.TSX
                    : ts.ScriptKind.TS
            );
            
            // Cache the AST
            this.astCache.set(uri.toString(), ast);
            
            return ast;
        } catch (error) {
            this.logger.error(`Failed to parse ${uri.fsPath}`, error);
            return null;
        }
    }
    
    private async findSearchableFiles(): Promise<vscode.Uri[]> {
        const pattern = '**/*.{ts,tsx,js,jsx}';
        const exclude = '**/node_modules/**';
        
        return await vscode.workspace.findFiles(pattern, exclude);
    }
    
    private getDefaultOptions(): SearchOptions {
        return {
            maxResults: 50,
            minScore: 0.3,
            includeSnippets: true,
            snippetLines: 5
        };
    }
    
    public clearCache(): void {
        this.searchCache.clear();
        this.astCache.clear();
    }
}

interface NodeInfo {
    name: string;
    type: NodeType;
    isExported: boolean;
    hasJSDoc: boolean;
    jsDoc?: string;
}