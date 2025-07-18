import * as vscode from 'vscode';
import {
    LivingDocument,
    ReferenceType,
    ReferenceEvolution,
    DocumentAbstractionResult,
    AbstractionStatistics,
    DocumentSafetyMetadata
} from '../types/living-document.types';
import { Logger } from '../utils/logger';

/**
 * Service for abstracting sensitive content in Living Documents
 */
export class DocumentAbstractor {
    private static instance: DocumentAbstractor;
    private logger: Logger;
    
    // Abstraction patterns
    private patterns: Map<ReferenceType, RegExp[]>;
    private projectRoot: string;
    
    // Temporal patterns that should NOT be abstracted
    private temporalPatterns: RegExp[] = [
        /\d{4}-\d{2}-\d{2}/,  // ISO dates: 2025-07-18
        /\d{2}:\d{2}/,        // Times: 17:34
        /\b(January|February|March|April|May|June|July|August|September|October|November|December)\b/i,
        /\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/i,
        /\b(today|yesterday|tomorrow|now)\b/i
    ];
    
    private constructor() {
        this.logger = Logger.getInstance();
        this.patterns = this.initializePatterns();
        this.projectRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
    }
    
    public static getInstance(): DocumentAbstractor {
        if (!DocumentAbstractor.instance) {
            DocumentAbstractor.instance = new DocumentAbstractor();
        }
        return DocumentAbstractor.instance;
    }
    
    /**
     * Abstract sensitive content in a document
     */
    public async abstractDocument(
        content: string,
        existingEvolution?: Map<string, ReferenceEvolution[]>
    ): Promise<DocumentAbstractionResult> {
        const startTime = Date.now();
        const references = new Map<string, string>();
        const warnings: string[] = [];
        let abstractedContent = content;
        
        // Statistics tracking
        const stats: AbstractionStatistics = {
            totalReferences: 0,
            abstractedReferences: 0,
            filePathsAbstracted: 0,
            urlsAbstracted: 0,
            credentialsRemoved: 0,
            processingTimeMs: 0
        };
        
        try {
            // Process each reference type
            for (const [type, patterns] of this.patterns) {
                for (const pattern of patterns) {
                    abstractedContent = abstractedContent.replace(
                        pattern,
                        (match, ...args) => {
                            stats.totalReferences++;
                            
                            const abstracted = this.abstractReference(type, match, args);
                            if (abstracted !== match) {
                                stats.abstractedReferences++;
                                references.set(match, abstracted);
                                
                                // Update statistics by type
                                switch (type) {
                                    case ReferenceType.FilePath:
                                        stats.filePathsAbstracted++;
                                        break;
                                    case ReferenceType.URL:
                                        stats.urlsAbstracted++;
                                        break;
                                    case ReferenceType.Credential:
                                        stats.credentialsRemoved++;
                                        break;
                                }
                                
                                // Track evolution
                                if (existingEvolution) {
                                    this.trackEvolution(existingEvolution, match, abstracted);
                                }
                            }
                            
                            return abstracted;
                        }
                    );
                }
            }
            
            // Calculate safety score
            const safetyScore = this.calculateSafetyScore(content, abstractedContent, stats);
            
            // Add warnings for potential issues
            if (stats.credentialsRemoved > 0) {
                warnings.push(`Removed ${stats.credentialsRemoved} potential credentials`);
            }
            
            if (safetyScore < 0.8) {
                warnings.push('Document may contain unabstracted sensitive content');
            }
            
            stats.processingTimeMs = Date.now() - startTime;
            
            return {
                abstractedContent,
                references,
                safetyScore,
                warnings,
                statistics: stats
            };
            
        } catch (error) {
            this.logger.error('Document abstraction failed', error);
            throw error;
        }
    }
    
    /**
     * Initialize abstraction patterns
     */
    private initializePatterns(): Map<ReferenceType, RegExp[]> {
        const patterns = new Map<ReferenceType, RegExp[]>();
        
        // File path patterns
        patterns.set(ReferenceType.FilePath, [
            // Absolute paths (Windows and Unix)
            /([A-Za-z]:)?[\/\\](?:Users|home|var|opt|etc|mnt)[\/\\][^\s\n"'`]+/g,
            // Relative paths with multiple segments
            /\.{1,2}[\/\\](?:[^\/\\\s\n"'`]+[\/\\]){2,}[^\/\\\s\n"'`]+/g,
            // File references in code blocks
            /(?:from|import|require)\s+["']([^"']+)["']/g,
        ]);
        
        // URL patterns
        patterns.set(ReferenceType.URL, [
            // HTTP(S) URLs
            /https?:\/\/[^\s\n<>"'`]+/g,
            // Git URLs
            /git@[^:]+:[^\/\s]+\/[^\.]+\.git/g,
            // SSH URLs
            /ssh:\/\/[^@]+@[^\/]+\/[^\s]+/g,
        ]);
        
        // Markdown-specific patterns
        patterns.set(ReferenceType.Link, [
            // Markdown links [text](url)
            /\[([^\]]+)\]\(([^)]+)\)/g,
            // Reference-style links [text][ref]
            /\[([^\]]+)\]\[([^\]]+)\]/g,
        ]);
        
        patterns.set(ReferenceType.Image, [
            // Markdown images ![alt](src)
            /!\[([^\]]*)\]\(([^)]+)\)/g,
        ]);
        
        patterns.set(ReferenceType.CodeBlock, [
            // Code blocks with file references
            /```(\w+)\s*(?:#|\/\/|--)\s*([^\n]+\.\w+)/g,
        ]);
        
        // Credential patterns
        patterns.set(ReferenceType.Credential, [
            // API keys and tokens
            /(?:api[_-]?key|token|secret|password)\s*[:=]\s*["']?([A-Za-z0-9+\/=_-]{20,})["']?/gi,
            // AWS keys
            /AKIA[0-9A-Z]{16}/g,
            // JWT tokens
            /eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,
        ]);
        
        return patterns;
    }
    
    /**
     * Abstract a specific reference based on its type
     */
    private abstractReference(type: ReferenceType, original: string, captures: any[]): string {
        // Check if this is temporal data - if so, don't abstract it
        for (const pattern of this.temporalPatterns) {
            if (pattern.test(original)) {
                return original; // Return unchanged
            }
        }
        
        switch (type) {
            case ReferenceType.FilePath:
                return this.abstractFilePath(original);
                
            case ReferenceType.URL:
                return this.abstractURL(original);
                
            case ReferenceType.Link:
                // For markdown links, preserve text but abstract URL
                if (captures.length >= 2) {
                    const text = captures[0];
                    const url = captures[1];
                    const abstractedUrl = this.abstractURL(url);
                    return original.replace(url, abstractedUrl);
                }
                return original;
                
            case ReferenceType.Image:
                // For images, abstract the source path
                if (captures.length >= 2) {
                    const alt = captures[0] || 'image';
                    const src = captures[1];
                    const abstractedSrc = this.abstractFilePath(src);
                    return `![${alt}](${abstractedSrc})`;
                }
                return '![image](<asset>)';
                
            case ReferenceType.CodeBlock:
                // For code blocks, abstract file reference
                if (captures.length >= 2) {
                    const lang = captures[0];
                    const file = captures[1];
                    const abstractedFile = this.abstractFilePath(file);
                    return `\`\`\`${lang} # ${abstractedFile}`;
                }
                return original;
                
            case ReferenceType.Credential:
                return '<credential>';
                
            default:
                return original;
        }
    }
    
    /**
     * Abstract file paths
     */
    private abstractFilePath(path: string): string {
        // Remove absolute path prefixes
        let abstracted = path;
        
        // Windows paths
        abstracted = abstracted.replace(/[A-Za-z]:[\\\/]/, '');
        
        // Common system paths
        abstracted = abstracted.replace(
            /^(?:\/)?(?:Users?|home|var|opt|etc|mnt|tmp)[\\\/][^\\\/]+[\\\/]/,
            '<system>/'
        );
        
        // Project-relative paths
        if (this.projectRoot && abstracted.includes(this.projectRoot)) {
            abstracted = abstracted.replace(this.projectRoot, '<project>');
        }
        
        // Node modules
        abstracted = abstracted.replace(/node_modules[\\\/]/, '<modules>/');
        
        // Common directories
        abstracted = abstracted.replace(/(?:src|lib|dist|build|out)[\\\/]/, '<source>/');
        
        return abstracted;
    }
    
    /**
     * Abstract URLs
     */
    private abstractURL(url: string): string {
        try {
            const parsed = new URL(url);
            
            // Preserve protocol and abstracted host
            const protocol = parsed.protocol;
            let host = parsed.hostname;
            
            // Abstract common domains
            if (host.includes('github.com')) {
                host = '<github>';
            } else if (host.includes('localhost') || host === '127.0.0.1') {
                host = '<local>';
            } else if (host.match(/\d+\.\d+\.\d+\.\d+/)) {
                host = '<ip>';
            } else {
                // Abstract to domain type
                const tld = host.split('.').pop();
                host = `<domain.${tld}>`;
            }
            
            // Abstract path
            let path = parsed.pathname;
            if (path.length > 1) {
                const segments = path.split('/').filter(s => s);
                if (segments.length > 0) {
                    path = '/<path>';
                }
            }
            
            return `${protocol}//${host}${path}`;
            
        } catch {
            // Not a valid URL, return generic abstraction
            return '<url>';
        }
    }
    
    /**
     * Track reference evolution
     */
    private trackEvolution(
        evolution: Map<string, ReferenceEvolution[]>,
        original: string,
        abstracted: string
    ): void {
        const history = evolution.get(original) || [];
        history.push({
            timestamp: new Date(),
            original,
            abstracted,
            confidence: 0.95 // High confidence for rule-based abstraction
        });
        evolution.set(original, history);
    }
    
    /**
     * Calculate safety score for abstracted content
     */
    private calculateSafetyScore(
        original: string,
        abstracted: string,
        stats: AbstractionStatistics
    ): number {
        // Base score on abstraction coverage
        const abstractionRatio = stats.totalReferences > 0
            ? stats.abstractedReferences / stats.totalReferences
            : 1.0;
        
        // Check for remaining sensitive patterns
        const remainingPaths = (abstracted.match(/[\/\\]Users[\/\\]|[\/\\]home[\/\\]/g) || []).length;
        const remainingUrls = (abstracted.match(/https?:\/\/[^<]/g) || []).length;
        const remainingCredentials = (abstracted.match(/api[_-]?key|token|secret|password/gi) || []).length;
        
        // Calculate penalties
        const pathPenalty = Math.min(remainingPaths * 0.1, 0.3);
        const urlPenalty = Math.min(remainingUrls * 0.05, 0.2);
        const credentialPenalty = remainingCredentials * 0.2;
        
        // Final score
        const score = Math.max(0, Math.min(1, abstractionRatio - pathPenalty - urlPenalty - credentialPenalty));
        
        return score;
    }
    
    /**
     * Create safety metadata for a document
     */
    public createSafetyMetadata(result: DocumentAbstractionResult): DocumentSafetyMetadata {
        return {
            abstractionCoverage: result.statistics.totalReferences > 0
                ? result.statistics.abstractedReferences / result.statistics.totalReferences
                : 1.0,
            sensitiveContentRemoved: result.statistics.credentialsRemoved,
            compactionSafe: result.safetyScore >= 0.8,
            lastValidation: new Date(),
            validationScore: result.safetyScore
        };
    }
}