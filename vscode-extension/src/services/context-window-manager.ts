import * as vscode from 'vscode';
import {
    LivingDocument,
    CompactionStrategy,
    CompactionEvent,
    ContextWindow,
    DocumentAllocation
} from '../types/living-document.types';
import { Logger } from '../utils/logger';
import { EventEmitter } from 'events';

/**
 * Manages context window allocation for Living Documents
 */
export class ContextWindowManager extends EventEmitter {
    private static instance: ContextWindowManager;
    private logger: Logger;
    
    // Context window configuration
    private maxTokens: number;
    private documentPercentage: number;
    private window: ContextWindow;
    
    // Token estimation (rough approximation)
    private readonly CHARS_PER_TOKEN = 4;
    
    private constructor() {
        super();
        this.logger = Logger.getInstance();
        
        // Get configuration
        const config = vscode.workspace.getConfiguration('coachntt.livingDocuments');
        this.maxTokens = config.get('maxContextTokens', 100000);
        this.documentPercentage = config.get('documentContextPercentage', 0.3);
        
        // Initialize context window
        const documentBudget = Math.floor(this.maxTokens * this.documentPercentage);
        this.window = {
            maxTokens: documentBudget,
            currentUsage: 0,
            documentAllocations: new Map(),
            lastOptimization: new Date()
        };
    }
    
    public static getInstance(): ContextWindowManager {
        if (!ContextWindowManager.instance) {
            ContextWindowManager.instance = new ContextWindowManager();
        }
        return ContextWindowManager.instance;
    }
    
    /**
     * Add a document to the context window
     */
    public async addDocument(
        document: LivingDocument,
        priority: number = 1.0
    ): Promise<boolean> {
        const tokens = this.estimateTokens(document.abstractedContent);
        
        // Check if we need to make space
        if (this.window.currentUsage + tokens > this.window.maxTokens * 0.8) {
            await this.optimizeContextWindow(tokens);
        }
        
        // Try to add document
        if (this.window.currentUsage + tokens <= this.window.maxTokens) {
            this.window.documentAllocations.set(document.id, {
                documentId: document.id,
                tokens,
                priority,
                compressible: true,
                lastAccessed: new Date()
            });
            
            this.window.currentUsage += tokens;
            
            // Update document tracking
            document.lastAccessed = new Date();
            document.accessCount++;
            document.contextUsage = tokens;
            
            this.emit('documentAdded', {
                documentId: document.id,
                tokens,
                totalUsage: this.window.currentUsage
            });
            
            return true;
        }
        
        this.logger.warn(`Cannot add document ${document.id} - insufficient context space`);
        return false;
    }
    
    /**
     * Remove a document from context
     */
    public removeDocument(documentId: string): boolean {
        const allocation = this.window.documentAllocations.get(documentId);
        if (!allocation) {
            return false;
        }
        
        this.window.currentUsage -= allocation.tokens;
        this.window.documentAllocations.delete(documentId);
        
        this.emit('documentRemoved', {
            documentId,
            tokensFreed: allocation.tokens,
            totalUsage: this.window.currentUsage
        });
        
        return true;
    }
    
    /**
     * Optimize context window by compacting documents
     */
    private async optimizeContextWindow(requiredSpace: number): Promise<void> {
        this.emit('optimizationStarted', { requiredSpace });
        
        // Sort documents by priority and access patterns
        const sortedAllocations = Array.from(this.window.documentAllocations.values())
            .filter(a => a.compressible)
            .sort((a, b) => {
                // Lower score = better candidate for compaction
                const scoreA = this.calculateCompactionScore(a);
                const scoreB = this.calculateCompactionScore(b);
                return scoreA - scoreB;
            });
        
        let spaceFreed = 0;
        const compactedDocuments: string[] = [];
        
        for (const allocation of sortedAllocations) {
            if (spaceFreed >= requiredSpace) {
                break;
            }
            
            // Simulate compaction (in real implementation, would call document service)
            const compactionRatio = 0.6; // Assume 40% reduction
            const newSize = Math.floor(allocation.tokens * compactionRatio);
            const freed = allocation.tokens - newSize;
            
            // Update allocation
            allocation.tokens = newSize;
            spaceFreed += freed;
            compactedDocuments.push(allocation.documentId);
            
            this.emit('documentCompacted', {
                documentId: allocation.documentId,
                oldSize: allocation.tokens + freed,
                newSize: allocation.tokens,
                strategy: CompactionStrategy.Balanced
            });
        }
        
        this.window.currentUsage -= spaceFreed;
        this.window.lastOptimization = new Date();
        
        this.emit('optimizationCompleted', {
            spaceFreed,
            documentsCompacted: compactedDocuments.length,
            totalUsage: this.window.currentUsage
        });
    }
    
    /**
     * Calculate compaction score (lower = better candidate)
     */
    private calculateCompactionScore(allocation: DocumentAllocation): number {
        const now = Date.now();
        const lastAccessedMs = allocation.lastAccessed.getTime();
        const ageHours = (now - lastAccessedMs) / (1000 * 60 * 60);
        
        // Factors:
        // - Priority (higher = keep)
        // - Age (older = compact)
        // - Size (larger = more benefit from compaction)
        
        const priorityWeight = allocation.priority * 10;
        const ageWeight = Math.min(ageHours / 24, 1) * 5;
        const sizeWeight = (allocation.tokens / this.window.maxTokens) * 3;
        
        return priorityWeight - ageWeight - sizeWeight;
    }
    
    /**
     * Compact a document with specified strategy
     */
    public async compactDocument(
        document: LivingDocument,
        strategy: CompactionStrategy
    ): Promise<CompactionEvent> {
        const originalSize = this.estimateTokens(document.abstractedContent);
        
        // Apply compaction based on strategy
        const compactedContent = await this.applyCompactionStrategy(
            document.abstractedContent,
            strategy
        );
        
        const newSize = this.estimateTokens(compactedContent);
        
        // Create compaction event
        const event: CompactionEvent = {
            timestamp: new Date(),
            strategy,
            sizeBefore: originalSize,
            sizeAfter: newSize,
            sectionsCompacted: this.identifyCompactedSections(
                document.abstractedContent,
                compactedContent
            ),
            trigger: 'manual'
        };
        
        // Update document
        document.abstractedContent = compactedContent;
        document.currentSize = newSize;
        document.compactionRatio = newSize / document.originalSize;
        document.compactionHistory.push(event);
        
        // Update allocation if in context
        const allocation = this.window.documentAllocations.get(document.id);
        if (allocation) {
            const tokenDiff = allocation.tokens - newSize;
            allocation.tokens = newSize;
            this.window.currentUsage -= tokenDiff;
        }
        
        this.emit('documentCompacted', event);
        
        return event;
    }
    
    /**
     * Apply compaction strategy to content
     */
    private async applyCompactionStrategy(
        content: string,
        strategy: CompactionStrategy
    ): Promise<string> {
        let compacted = content;
        
        switch (strategy) {
            case CompactionStrategy.Aggressive:
                // Remove code blocks, examples, and verbose sections
                compacted = compacted
                    // Remove code blocks
                    .replace(/```[\s\S]*?```/g, '```\n<code removed>\n```')
                    // Remove blockquotes
                    .replace(/^>\s+.+$/gm, '> <quote removed>')
                    // Compress lists
                    .replace(/^(\s*[-*+]\s+).+$/gm, '$1<item>')
                    // Remove extra newlines
                    .replace(/\n{3,}/g, '\n\n');
                break;
                
            case CompactionStrategy.Balanced:
                // Keep structure but reduce detail
                compacted = compacted
                    // Shorten code blocks
                    .replace(/```([\s\S]{200,}?)```/g, (match, code) => {
                        const lines = code.split('\n');
                        if (lines.length > 10) {
                            return `\`\`\`\n${lines.slice(0, 5).join('\n')}\n... (${lines.length - 10} lines)\n${lines.slice(-5).join('\n')}\n\`\`\``;
                        }
                        return match;
                    })
                    // Compress long paragraphs
                    .replace(/^(.{200,})$/gm, (match) => {
                        return match.substring(0, 150) + '... <truncated>';
                    })
                    // Remove excessive examples
                    .replace(/(?:example|Example):\s*\n([\s\S]+?)(?=\n\n|\n#|$)/gi, 'Example: <removed>\n');
                break;
                
            case CompactionStrategy.Conservative:
                // Minimal compaction - just remove redundancy
                compacted = compacted
                    // Remove duplicate newlines
                    .replace(/\n{3,}/g, '\n\n')
                    // Remove trailing spaces
                    .replace(/ +$/gm, '')
                    // Compress repeated patterns
                    .replace(/(.+\n)\1{2,}/g, '$1<repeated>\n');
                break;
        }
        
        return compacted;
    }
    
    /**
     * Identify which sections were compacted
     */
    private identifyCompactedSections(original: string, compacted: string): string[] {
        const sections: string[] = [];
        
        // Simple heuristic - check for major differences
        if (original.includes('```') && compacted.includes('<code removed>')) {
            sections.push('code blocks');
        }
        
        if (original.includes('>') && compacted.includes('<quote removed>')) {
            sections.push('blockquotes');
        }
        
        if (compacted.includes('<truncated>')) {
            sections.push('long paragraphs');
        }
        
        if (compacted.includes('<removed>')) {
            sections.push('examples');
        }
        
        return sections;
    }
    
    /**
     * Estimate token count for content
     */
    private estimateTokens(content: string): number {
        // Simple estimation: ~4 characters per token
        return Math.ceil(content.length / this.CHARS_PER_TOKEN);
    }
    
    /**
     * Get current context window state
     */
    public getContextState(): ContextWindow {
        return {
            ...this.window,
            documentAllocations: new Map(this.window.documentAllocations)
        };
    }
    
    /**
     * Get usage percentage
     */
    public getUsagePercentage(): number {
        return (this.window.currentUsage / this.window.maxTokens) * 100;
    }
    
    /**
     * Check if document can fit
     */
    public canFitDocument(content: string): boolean {
        const tokens = this.estimateTokens(content);
        return this.window.currentUsage + tokens <= this.window.maxTokens;
    }
    
    /**
     * Get recommendations for optimization
     */
    public getOptimizationRecommendations(): string[] {
        const recommendations: string[] = [];
        const usage = this.getUsagePercentage();
        
        if (usage > 90) {
            recommendations.push('Context window critical - immediate compaction recommended');
        } else if (usage > 80) {
            recommendations.push('Context window high - consider compacting old documents');
        }
        
        // Check for stale documents
        const staleThreshold = Date.now() - 24 * 60 * 60 * 1000; // 24 hours
        const staleDocuments = Array.from(this.window.documentAllocations.values())
            .filter(a => a.lastAccessed.getTime() < staleThreshold);
        
        if (staleDocuments.length > 0) {
            recommendations.push(`${staleDocuments.length} documents haven't been accessed in 24 hours`);
        }
        
        return recommendations;
    }
}