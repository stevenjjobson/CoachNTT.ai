import * as vscode from 'vscode';
import * as path from 'path';
import { LivingDocument, ValidationIssue } from '../types/living-document.types';

/**
 * Comprehensive error handling for Living Documents
 * Provides graceful degradation and user-friendly error recovery
 */
export class LivingDocumentErrorHandler {
    private static errorLog: ErrorLogEntry[] = [];
    private static readonly MAX_LOG_ENTRIES = 100;

    /**
     * Handle abstraction failures gracefully
     */
    static async handleAbstractionFailure(
        document: vscode.TextDocument,
        error: Error,
        context?: AbstractionContext
    ): Promise<void> {
        // Log the error with context
        this.logError({
            type: 'abstraction_failure',
            message: error.message,
            stack: error.stack,
            documentPath: document.fileName,
            context
        });

        // Determine severity and recovery options
        const severity = this.determineSeverity(error);
        const recoveryOptions = this.getRecoveryOptions(severity, document);

        // Show user-friendly error message with actions
        const action = await vscode.window.showErrorMessage(
            this.formatErrorMessage(error, document),
            ...recoveryOptions.map(opt => opt.label)
        );

        // Handle user's choice
        if (action) {
            const option = recoveryOptions.find(opt => opt.label === action);
            if (option) {
                await option.handler();
            }
        }
    }

    /**
     * Validate document integrity
     */
    static async validateDocumentIntegrity(
        document: LivingDocument
    ): Promise<ValidationResult> {
        const issues: ValidationIssue[] = [];

        try {
            // Check abstraction coverage
            const coverage = this.calculateAbstractionCoverage(document);
            if (coverage < 0.8) {
                issues.push({
                    severity: 'warning',
                    category: 'abstraction',
                    message: `Low abstraction coverage: ${(coverage * 100).toFixed(1)}%`,
                    suggestion: 'Review document for unabstracted sensitive data',
                    line: null
                });
            }

            // Check for stale references
            const staleRefs = await this.detectStaleReferences(document);
            if (staleRefs.length > 0) {
                issues.push({
                    severity: 'error',
                    category: 'reference',
                    message: `Found ${staleRefs.length} stale reference(s)`,
                    suggestion: 'Update or remove outdated references',
                    line: null,
                    details: staleRefs
                });
            }

            // Check document structure
            const structureIssues = this.validateDocumentStructure(document);
            issues.push(...structureIssues);

            // Check safety compliance
            const safetyIssues = this.validateSafety(document);
            issues.push(...safetyIssues);

            // Check compaction health
            const compactionIssues = this.validateCompaction(document);
            issues.push(...compactionIssues);

        } catch (error) {
            issues.push({
                severity: 'error',
                category: 'validation',
                message: 'Validation failed',
                suggestion: 'Document may be corrupted',
                line: null,
                details: error
            });
        }

        return {
            valid: !issues.some(i => i.severity === 'error'),
            issues,
            timestamp: new Date()
        };
    }

    /**
     * Handle file system errors
     */
    static async handleFileSystemError(
        uri: vscode.Uri,
        operation: 'read' | 'write' | 'delete',
        error: Error
    ): Promise<void> {
        this.logError({
            type: 'filesystem_error',
            message: `${operation} operation failed: ${error.message}`,
            documentPath: uri.fsPath,
            operation
        });

        const message = this.getFileSystemErrorMessage(operation, uri, error);
        
        const action = await vscode.window.showErrorMessage(
            message,
            'Retry',
            'Show Details',
            'Ignore'
        );

        switch (action) {
            case 'Retry':
                await this.retryFileOperation(uri, operation);
                break;
            case 'Show Details':
                await this.showErrorDetails(error, uri);
                break;
        }
    }

    /**
     * Handle compaction errors
     */
    static async handleCompactionError(
        document: LivingDocument,
        error: Error,
        strategy: string
    ): Promise<void> {
        this.logError({
            type: 'compaction_error',
            message: error.message,
            documentPath: document.uri.fsPath,
            context: { strategy }
        });

        const fallbackStrategies = this.getFallbackStrategies(strategy);
        
        const action = await vscode.window.showWarningMessage(
            `Compaction failed with ${strategy} strategy. ${error.message}`,
            ...fallbackStrategies.map(s => `Try ${s}`),
            'Skip Compaction',
            'Show Details'
        );

        if (action && action.startsWith('Try')) {
            const newStrategy = action.replace('Try ', '').toLowerCase();
            await vscode.commands.executeCommand('coachntt.compactDocument', {
                documentId: document.id,
                strategy: newStrategy
            });
        } else if (action === 'Show Details') {
            await this.showCompactionErrorDetails(document, error, strategy);
        }
    }

    /**
     * Show error recovery assistant
     */
    static async showRecoveryAssistant(
        document: LivingDocument,
        issues: ValidationIssue[]
    ): Promise<void> {
        const panel = vscode.window.createWebviewPanel(
            'recoveryAssistant',
            'Document Recovery Assistant',
            vscode.ViewColumn.Beside,
            { enableScripts: true }
        );

        panel.webview.html = this.getRecoveryAssistantHtml(document, issues);

        panel.webview.onDidReceiveMessage(async message => {
            switch (message.command) {
                case 'fixIssue':
                    await this.attemptAutoFix(document, message.issue);
                    break;
                case 'ignoreIssue':
                    await this.ignoreIssue(document, message.issue);
                    break;
            }
        });
    }

    // Private helper methods

    private static calculateAbstractionCoverage(document: LivingDocument): number {
        const sensitivePatterns = [
            /\/[\w.-]+\/[\w.-]+/g, // File paths
            /https?:\/\/[^\s]+/g,   // URLs
            /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, // Emails
            /[A-Za-z0-9+/]{20,}={0,2}/g // Potential tokens/keys
        ];

        let totalSensitive = 0;
        let abstractedCount = 0;

        sensitivePatterns.forEach(pattern => {
            const matches = document.content.match(pattern) || [];
            totalSensitive += matches.length;
            
            matches.forEach(match => {
                if (!document.abstractedContent.includes(match)) {
                    abstractedCount++;
                }
            });
        });

        return totalSensitive > 0 ? abstractedCount / totalSensitive : 1;
    }

    private static async detectStaleReferences(
        document: LivingDocument
    ): Promise<StaleReference[]> {
        const staleRefs: StaleReference[] = [];
        
        // Extract file references from abstracted content
        const fileRefs = this.extractFileReferences(document.abstractedContent);
        
        for (const ref of fileRefs) {
            try {
                // Check if referenced file exists
                const uri = vscode.Uri.file(this.resolveReference(ref));
                await vscode.workspace.fs.stat(uri);
            } catch {
                staleRefs.push({
                    reference: ref,
                    type: 'file',
                    lastSeen: document.updatedAt
                });
            }
        }

        return staleRefs;
    }

    private static validateDocumentStructure(
        document: LivingDocument
    ): ValidationIssue[] {
        const issues: ValidationIssue[] = [];

        // Check frontmatter
        if (!document.content.startsWith('---')) {
            issues.push({
                severity: 'warning',
                category: 'structure',
                message: 'Missing frontmatter',
                suggestion: 'Add YAML frontmatter with title and metadata',
                line: 1
            });
        }

        // Check for required sections
        const requiredSections = ['## Overview', '## Key'];
        requiredSections.forEach(section => {
            if (!document.content.includes(section)) {
                issues.push({
                    severity: 'info',
                    category: 'structure',
                    message: `Missing recommended section: ${section}`,
                    suggestion: `Consider adding ${section} section`,
                    line: null
                });
            }
        });

        return issues;
    }

    private static validateSafety(document: LivingDocument): ValidationIssue[] {
        const issues: ValidationIssue[] = [];

        // Check safety score
        if (document.safetyMetadata.safetyScore < 0.6) {
            issues.push({
                severity: 'error',
                category: 'safety',
                message: 'Low safety score',
                suggestion: 'Document contains too much sensitive information',
                line: null
            });
        }

        // Check for common security patterns
        const securityPatterns = [
            { pattern: /password\s*[:=]\s*["'][^"']+["']/gi, name: 'hardcoded password' },
            { pattern: /api[_-]?key\s*[:=]\s*["'][^"']+["']/gi, name: 'API key' },
            { pattern: /private[_-]?key/gi, name: 'private key reference' }
        ];

        securityPatterns.forEach(({ pattern, name }) => {
            const matches = document.abstractedContent.match(pattern);
            if (matches) {
                issues.push({
                    severity: 'error',
                    category: 'safety',
                    message: `Potential ${name} found`,
                    suggestion: 'Remove or properly abstract sensitive data',
                    line: null,
                    details: matches
                });
            }
        });

        return issues;
    }

    private static validateCompaction(
        document: LivingDocument
    ): ValidationIssue[] {
        const issues: ValidationIssue[] = [];

        // Check compaction ratio
        if (document.compactionMetadata.ratio > 0.8) {
            issues.push({
                severity: 'info',
                category: 'compaction',
                message: 'High compaction ratio',
                suggestion: 'Document may benefit from more aggressive compaction',
                line: null
            });
        }

        // Check compaction history
        const recentCompactions = document.compactionMetadata.history
            .filter(c => new Date(c.timestamp).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000);
        
        if (recentCompactions.length > 5) {
            issues.push({
                severity: 'warning',
                category: 'compaction',
                message: 'Frequent compactions detected',
                suggestion: 'Consider using a more stable compaction strategy',
                line: null
            });
        }

        return issues;
    }

    private static determineSeverity(error: Error): ErrorSeverity {
        if (error.message.includes('EACCES') || error.message.includes('EPERM')) {
            return 'critical';
        }
        if (error.message.includes('ENOENT')) {
            return 'warning';
        }
        if (error.message.includes('timeout')) {
            return 'warning';
        }
        return 'error';
    }

    private static getRecoveryOptions(
        severity: ErrorSeverity,
        document: vscode.TextDocument
    ): RecoveryOption[] {
        const options: RecoveryOption[] = [];

        options.push({
            label: 'Save Without Abstraction',
            handler: async () => {
                await document.save();
                vscode.window.showWarningMessage(
                    'Document saved without abstraction. Review for sensitive data.'
                );
            }
        });

        if (severity !== 'critical') {
            options.push({
                label: 'Retry Abstraction',
                handler: async () => {
                    await vscode.commands.executeCommand('coachntt.abstractDocument', document.uri);
                }
            });
        }

        options.push({
            label: 'View Details',
            handler: async () => {
                await this.showErrorDetails(new Error('Abstraction failed'), document.uri);
            }
        });

        options.push({
            label: 'Cancel',
            handler: async () => {
                // No-op
            }
        });

        return options;
    }

    private static formatErrorMessage(
        error: Error,
        document: vscode.TextDocument
    ): string {
        const fileName = path.basename(document.fileName);
        
        if (error.message.includes('timeout')) {
            return `Abstraction timed out for ${fileName}. The document may be too large.`;
        }
        
        if (error.message.includes('memory')) {
            return `Insufficient memory to process ${fileName}. Try closing other applications.`;
        }
        
        return `Failed to abstract ${fileName}: ${error.message}`;
    }

    private static getFileSystemErrorMessage(
        operation: string,
        uri: vscode.Uri,
        error: Error
    ): string {
        const fileName = path.basename(uri.fsPath);
        
        if (error.message.includes('EACCES')) {
            return `Permission denied: Cannot ${operation} ${fileName}`;
        }
        
        if (error.message.includes('ENOENT')) {
            return `File not found: ${fileName}`;
        }
        
        if (error.message.includes('ENOSPC')) {
            return `No space left on device: Cannot ${operation} ${fileName}`;
        }
        
        return `Failed to ${operation} ${fileName}: ${error.message}`;
    }

    private static async retryFileOperation(
        uri: vscode.Uri,
        operation: string
    ): Promise<void> {
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `Retrying ${operation}...`,
            cancellable: false
        }, async () => {
            await vscode.commands.executeCommand(`coachntt.${operation}Document`, uri);
        });
    }

    private static extractFileReferences(content: string): string[] {
        const refs: string[] = [];
        const patterns = [
            /<project>\/([^>\s]+)/g,
            /<(\w+)>\/([^>\s]+)/g
        ];

        patterns.forEach(pattern => {
            let match;
            while ((match = pattern.exec(content)) !== null) {
                refs.push(match[0]);
            }
        });

        return [...new Set(refs)];
    }

    private static resolveReference(ref: string): string {
        // Simple reference resolution
        return ref.replace(/<project>/, vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '');
    }

    private static getFallbackStrategies(failedStrategy: string): string[] {
        const strategies = ['aggressive', 'balanced', 'conservative'];
        return strategies.filter(s => s !== failedStrategy.toLowerCase());
    }

    private static async showErrorDetails(error: Error, uri?: vscode.Uri): Promise<void> {
        const details = [
            `Error: ${error.message}`,
            `Type: ${error.name}`,
            uri ? `File: ${uri.fsPath}` : '',
            `Time: ${new Date().toISOString()}`,
            '',
            'Stack Trace:',
            error.stack || 'No stack trace available'
        ].filter(line => line).join('\n');

        const doc = await vscode.workspace.openTextDocument({
            content: details,
            language: 'text'
        });
        
        await vscode.window.showTextDocument(doc, { preview: false });
    }

    private static async showCompactionErrorDetails(
        document: LivingDocument,
        error: Error,
        strategy: string
    ): Promise<void> {
        const details = [
            `# Compaction Error Report`,
            ``,
            `## Document Information`,
            `- Title: ${document.title}`,
            `- ID: ${document.id}`,
            `- Current Size: ${document.currentSize} bytes`,
            `- Original Size: ${document.originalSize} bytes`,
            ``,
            `## Error Details`,
            `- Strategy: ${strategy}`,
            `- Error: ${error.message}`,
            `- Time: ${new Date().toISOString()}`,
            ``,
            `## Compaction History`,
            ...document.compactionMetadata.history.slice(-5).map(h => 
                `- ${new Date(h.timestamp).toLocaleString()}: ${h.strategy} (${h.sizeBefore} → ${h.sizeAfter} bytes)`
            ),
            ``,
            `## Stack Trace`,
            `\`\`\``,
            error.stack || 'No stack trace available',
            `\`\`\``
        ].join('\n');

        const doc = await vscode.workspace.openTextDocument({
            content: details,
            language: 'markdown'
        });
        
        await vscode.window.showTextDocument(doc, { preview: false });
    }

    private static logError(entry: ErrorLogEntry): void {
        this.errorLog.unshift({
            ...entry,
            timestamp: new Date()
        });

        // Keep log size manageable
        if (this.errorLog.length > this.MAX_LOG_ENTRIES) {
            this.errorLog = this.errorLog.slice(0, this.MAX_LOG_ENTRIES);
        }

        // Also log to console for debugging
        console.error(`[Living Documents] ${entry.type}:`, entry.message, entry);
    }

    private static getRecoveryAssistantHtml(
        document: LivingDocument,
        issues: ValidationIssue[]
    ): string {
        // Generate HTML for recovery assistant webview
        return `<!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: var(--vscode-font-family); }
                .issue { margin: 10px 0; padding: 10px; border-radius: 5px; }
                .error { background: #f44336; color: white; }
                .warning { background: #ff9800; color: white; }
                .info { background: #2196f3; color: white; }
                button { margin: 5px; padding: 5px 10px; }
            </style>
        </head>
        <body>
            <h2>Document Recovery Assistant</h2>
            <p>Found ${issues.length} issue(s) in ${document.title}</p>
            ${issues.map((issue, i) => `
                <div class="issue ${issue.severity}">
                    <strong>${issue.category}:</strong> ${issue.message}<br>
                    <em>${issue.suggestion}</em><br>
                    <button onclick="fixIssue(${i})">Auto-fix</button>
                    <button onclick="ignoreIssue(${i})">Ignore</button>
                </div>
            `).join('')}
            <script>
                const vscode = acquireVsCodeApi();
                function fixIssue(index) {
                    vscode.postMessage({ command: 'fixIssue', issue: ${JSON.stringify(issues)}[index] });
                }
                function ignoreIssue(index) {
                    vscode.postMessage({ command: 'ignoreIssue', issue: ${JSON.stringify(issues)}[index] });
                }
            </script>
        </body>
        </html>`;
    }

    private static async attemptAutoFix(
        document: LivingDocument,
        issue: ValidationIssue
    ): Promise<void> {
        // Implement auto-fix logic based on issue type
        switch (issue.category) {
            case 'structure':
                await this.fixStructureIssue(document, issue);
                break;
            case 'safety':
                await this.fixSafetyIssue(document, issue);
                break;
            case 'reference':
                await this.fixReferenceIssue(document, issue);
                break;
        }
    }

    private static async fixStructureIssue(
        document: LivingDocument,
        issue: ValidationIssue
    ): Promise<void> {
        // Auto-fix structure issues
        if (issue.message.includes('Missing frontmatter')) {
            const frontmatter = `---
title: ${document.title}
created: ${new Date().toISOString()}
category: general
tags: []
---

`;
            // Would update document content here
        }
    }

    private static async fixSafetyIssue(
        document: LivingDocument,
        issue: ValidationIssue
    ): Promise<void> {
        // Auto-fix safety issues by re-abstracting
        await vscode.commands.executeCommand('coachntt.reabstractDocument', document.id);
    }

    private static async fixReferenceIssue(
        document: LivingDocument,
        issue: ValidationIssue
    ): Promise<void> {
        // Auto-fix reference issues
        if (issue.details && Array.isArray(issue.details)) {
            // Would update stale references here
        }
    }

    private static async ignoreIssue(
        document: LivingDocument,
        issue: ValidationIssue
    ): Promise<void> {
        // Mark issue as ignored in document metadata
        console.log(`Ignoring issue: ${issue.message} in ${document.title}`);
    }
}

// Type definitions

interface ErrorLogEntry {
    type: string;
    message: string;
    stack?: string;
    documentPath?: string;
    timestamp?: Date;
    context?: any;
    operation?: string;
}

interface AbstractionContext {
    strategy?: string;
    patterns?: string[];
    options?: any;
}

interface ValidationResult {
    valid: boolean;
    issues: ValidationIssue[];
    timestamp: Date;
}

interface StaleReference {
    reference: string;
    type: 'file' | 'url' | 'symbol';
    lastSeen: Date;
}

interface RecoveryOption {
    label: string;
    handler: () => Promise<void>;
}

type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical';