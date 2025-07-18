import * as vscode from 'vscode';

/**
 * Living Document types for evolving project documentation
 */

/**
 * Document lifecycle stages
 */
export enum DocumentStage {
    Draft = 'draft',
    Active = 'active',
    Compacting = 'compacting',
    Archived = 'archived'
}

/**
 * Compaction strategies for context optimization
 */
export enum CompactionStrategy {
    Aggressive = 'aggressive',    // Maximum space saving
    Balanced = 'balanced',        // Balance between size and detail
    Conservative = 'conservative' // Preserve maximum detail
}

/**
 * Types of references that need abstraction
 */
export enum ReferenceType {
    FilePath = 'file_path',
    URL = 'url',
    CodeBlock = 'code_block',
    Image = 'image',
    Link = 'link',
    Credential = 'credential'
}


/**
 * Document safety metadata
 */
export interface DocumentSafetyMetadata {
    abstractionCoverage: number;      // 0-1 percentage of content abstracted
    sensitiveContentRemoved: number;  // Count of removed items
    compactionSafe: boolean;          // Can be safely compacted
    lastValidation: Date;
    validationScore: number;          // 0-1 safety score
}

/**
 * Core Living Document model
 */
export interface LivingDocument {
    id: string;
    uri: vscode.Uri;
    title: string;
    content: string;
    abstractedContent: string;
    stage: DocumentStage;
    
    // Safety tracking
    safetyMetadata: DocumentSafetyMetadata;
    safetyScore: number;
    
    // Temporal tracking
    createdAt: Date;
    updatedAt: Date;
    lastAccessed: Date;
    accessCount: number;
    relevanceScore: number;
    
    // Compaction tracking
    originalSize: number;
    currentSize: number;
    compactionRatio: number;
    compactionHistory: CompactionEvent[];
    
    // Evolution tracking
    referenceEvolution: Map<string, ReferenceEvolution[]>;
    
    // Metadata
    metadata: DocumentMetadata;
    
    // Session tracking
    sessionIds: string[];
    contextUsage: number; // Current token usage
}

/**
 * Compaction event tracking
 */
export interface CompactionEvent {
    timestamp: Date;
    strategy: CompactionStrategy;
    sizeBefore: number;
    sizeAfter: number;
    sectionsCompacted: string[];
    trigger: 'manual' | 'automatic' | 'threshold';
}

/**
 * Document metadata
 */
export interface DocumentMetadata {
    author?: string;
    tags: string[];
    category: DocumentCategory;
    language: string;
    encoding: string;
    linkedDocuments: string[]; // IDs of related documents
    codeReferences: CodeReference[];
    timestampHistory?: TimestampEvolution; // Track all timestamp changes
}

/**
 * Timestamp evolution tracking
 */
export interface TimestampEvolution {
    created: Date;
    updates: Array<{
        timestamp: Date;
        session?: string;
        changeType: 'content' | 'metadata' | 'compaction' | 'manual';
        source: 'user' | 'system' | 'automation';
    }>;
}

/**
 * Document categories
 */
export enum DocumentCategory {
    Architecture = 'architecture',
    API = 'api',
    Tutorial = 'tutorial',
    Reference = 'reference',
    Planning = 'planning',
    Notes = 'notes',
    Other = 'other'
}

/**
 * Code reference linking
 */
export interface CodeReference {
    documentId: string;
    codeUri: vscode.Uri;
    range: vscode.Range;
    symbol?: string;
    lastSync: Date;
}

/**
 * Context window allocation
 */
export interface ContextWindow {
    maxTokens: number;
    currentUsage: number;
    documentAllocations: Map<string, DocumentAllocation>;
    lastOptimization: Date;
}

/**
 * Document allocation in context
 */
export interface DocumentAllocation {
    documentId: string;
    tokens: number;
    priority: number;
    compressible: boolean;
    lastAccessed: Date;
}

/**
 * Document search options
 */
export interface DocumentSearchOptions {
    query: string;
    categories?: DocumentCategory[];
    tags?: string[];
    minRelevance?: number;
    includeArchived?: boolean;
    sortBy?: 'relevance' | 'updated' | 'accessed' | 'size';
    limit?: number;
}

/**
 * Document relevance scoring
 */
export interface DocumentRelevance {
    documentId: string;
    score: number;
    factors: {
        currentFile: number;
        recentFiles: number;
        symbols: number;
        branch: number;
        metadata: number;
    };
    timestamp: Date;
}

/**
 * Validation issue for document integrity
 */
export interface ValidationIssue {
    severity: 'info' | 'warning' | 'error';
    category: 'structure' | 'safety' | 'reference' | 'abstraction' | 'compaction' | 'validation';
    message: string;
    suggestion: string;
    line: number | null;
    details?: any;
}

/**
 * Document update event
 */
export interface DocumentUpdateEvent {
    documentId: string;
    type: 'created' | 'updated' | 'compacted' | 'archived' | 'deleted';
    changes?: DocumentChanges;
    timestamp: Date;
}

/**
 * Document changes tracking
 */
export interface DocumentChanges {
    content?: boolean;
    metadata?: boolean;
    compaction?: CompactionEvent;
    references?: string[];
}

/**
 * Evolution entry for tracking reference changes
 */
export interface EvolutionEntry {
    timestamp: Date;
    fromReference: string;
    toReference: string;
    abstractedForm: string;
    changeType: 'rename' | 'move' | 'refactor' | 'update';
    documentPath: string;
    confidence: number;
}

/**
 * Reference evolution tracking
 */
export interface ReferenceEvolution {
    originalReference: string;
    currentReference: string;
    abstractedForm: string;
    firstSeen: Date;
    lastUpdated: Date;
    documentPaths: Set<string>;
    evolutionChain: EvolutionEntry[];
}

/**
 * Abstraction result for documents
 */
export interface DocumentAbstractionResult {
    abstractedContent: string;
    references: Map<string, string>; // original -> abstracted
    safetyScore: number;
    warnings: string[];
    statistics: AbstractionStatistics;
}

/**
 * Abstraction statistics
 */
export interface AbstractionStatistics {
    totalReferences: number;
    abstractedReferences: number;
    filePathsAbstracted: number;
    urlsAbstracted: number;
    credentialsRemoved: number;
    processingTimeMs: number;
}

/**
 * Document tree item for sidebar
 */
export interface DocumentTreeItem extends vscode.TreeItem {
    document: LivingDocument;
    contextValue: 'document' | 'category' | 'archived';
}

/**
 * Document provider events
 */
export interface DocumentProviderEvents {
    onDidChangeDocuments: vscode.Event<DocumentUpdateEvent[]>;
    onDidChangeContextUsage: vscode.Event<ContextWindow>;
    onWillCompactDocument: vscode.Event<string>;
    onDidCompactDocument: vscode.Event<CompactionEvent>;
}