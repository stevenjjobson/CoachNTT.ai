import * as vscode from 'vscode';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { Memory, MemoryIntent } from '../models/memory.model';
import { MCPClient } from './mcp-client';
import { Logger } from '../utils/logger';
import { DocumentAbstractor } from './document-abstractor';
import {
    LivingDocument,
    DocumentStage,
    DocumentCategory,
    DocumentMetadata,
    DocumentSafetyMetadata
} from '../types/living-document.types';

/**
 * Minimal service for handling .CoachNTT Living Documents
 */
export class LivingDocumentService {
    private static instance: LivingDocumentService;
    private logger: Logger;
    private abstractor: DocumentAbstractor;
    private documents: Map<string, LivingDocument>;
    
    private constructor(
        private mcpClient: MCPClient
    ) {
        this.logger = Logger.getInstance();
        this.abstractor = DocumentAbstractor.getInstance();
        this.documents = new Map();
    }
    
    public static getInstance(mcpClient: MCPClient): LivingDocumentService {
        if (!LivingDocumentService.instance) {
            LivingDocumentService.instance = new LivingDocumentService(mcpClient);
        }
        return LivingDocumentService.instance;
    }
    
    /**
     * Process a .CoachNTT file
     */
    public async processCoachNTTFile(uri: vscode.Uri, autoSave: boolean = true): Promise<LivingDocument> {
        try {
            // Read file content
            const content = await vscode.workspace.fs.readFile(uri);
            const text = new TextDecoder().decode(content);
            
            // Check if we already have this document
            let document = this.findDocumentByUri(uri);
            
            if (!document) {
                // Create new document
                document = await this.createDocument(uri, text);
            } else {
                // Update existing document
                document = await this.updateDocument(document, text);
                
                // Auto-save updated content with new timestamp
                if (autoSave && document.content !== text) {
                    await this.saveDocument(document);
                }
            }
            
            // Store as memory if connected
            if (this.mcpClient.isConnected()) {
                await this.storeAsMemory(document);
            }
            
            return document;
            
        } catch (error) {
            this.logger.error('Failed to process .CoachNTT file', error);
            throw error;
        }
    }
    
    /**
     * Save document content back to disk
     */
    private async saveDocument(document: LivingDocument): Promise<void> {
        try {
            const content = Buffer.from(document.content, 'utf-8');
            await vscode.workspace.fs.writeFile(document.uri, content);
            this.logger.info(`Updated timestamps in ${document.uri.fsPath}`);
        } catch (error) {
            this.logger.error('Failed to save document', error);
            throw error;
        }
    }
    
    /**
     * Create a new Living Document
     */
    private async createDocument(uri: vscode.Uri, content: string): Promise<LivingDocument> {
        // Abstract the content
        const abstractionResult = await this.abstractor.abstractDocument(content);
        
        // Extract timestamps from content
        const timestamps = this.extractTimestamps(content);
        const now = new Date();
        const createdAt = timestamps.created ? new Date(timestamps.created) : now;
        const updatedAt = timestamps.updated ? new Date(timestamps.updated) : now;
        
        // Create document
        const document: LivingDocument = {
            id: uuidv4(),
            uri,
            title: this.extractTitle(content) || path.basename(uri.fsPath, '.CoachNTT'),
            content,
            abstractedContent: abstractionResult.abstractedContent,
            stage: DocumentStage.Active,
            safetyMetadata: this.abstractor.createSafetyMetadata(abstractionResult),
            safetyScore: abstractionResult.safetyScore,
            createdAt,
            updatedAt,
            lastAccessed: new Date(),
            accessCount: 1,
            relevanceScore: 1.0,
            originalSize: this.estimateTokens(content),
            currentSize: this.estimateTokens(abstractionResult.abstractedContent),
            compactionRatio: 1.0,
            compactionHistory: [],
            referenceEvolution: new Map(),
            metadata: this.extractMetadata(content, uri),
            sessionIds: [],
            contextUsage: 0
        };
        
        // Store locally
        this.documents.set(document.id, document);
        
        return document;
    }
    
    /**
     * Update an existing document
     */
    private async updateDocument(document: LivingDocument, newContent: string): Promise<LivingDocument> {
        // Update content with new timestamp in frontmatter
        const updatedContent = this.updateContentTimestamps(newContent, document.createdAt);
        
        // Abstract the new content
        const abstractionResult = await this.abstractor.abstractDocument(
            updatedContent,
            document.referenceEvolution
        );
        
        // Update document
        document.content = updatedContent;
        document.abstractedContent = abstractionResult.abstractedContent;
        document.safetyMetadata = this.abstractor.createSafetyMetadata(abstractionResult);
        document.safetyScore = abstractionResult.safetyScore;
        document.updatedAt = new Date();
        document.lastAccessed = new Date();
        document.accessCount++;
        document.currentSize = this.estimateTokens(abstractionResult.abstractedContent);
        document.compactionRatio = document.currentSize / document.originalSize;
        
        // Track timestamp evolution
        if (!document.metadata.timestampHistory) {
            document.metadata.timestampHistory = {
                created: document.createdAt,
                updates: []
            };
        }
        
        document.metadata.timestampHistory.updates.push({
            timestamp: document.updatedAt,
            session: this.getCurrentSession(),
            changeType: 'content',
            source: 'user'
        });
        
        return document;
    }
    
    /**
     * Update timestamps in content frontmatter
     */
    private updateContentTimestamps(content: string, originalCreated: Date): string {
        const yamlMatch = content.match(/^---\s*\n([\s\S]*?)\n---/m);
        if (!yamlMatch) {
            // No frontmatter, add one
            const header = this.createMinimalHeader(originalCreated);
            return header + '\n\n' + content;
        }
        
        const yaml = yamlMatch[1];
        const now = new Date().toISOString();
        
        // Update or add timestamps
        let updatedYaml = yaml;
        
        // Preserve created timestamp if it exists, otherwise use original
        if (!yaml.match(/created:/)) {
            updatedYaml += `\ncreated: ${originalCreated.toISOString()}`;
        }
        
        // Update the updated timestamp
        if (yaml.match(/updated:/)) {
            updatedYaml = updatedYaml.replace(/updated:\s*.+$/m, `updated: ${now}`);
        } else {
            updatedYaml += `\nupdated: ${now}`;
        }
        
        return content.replace(yamlMatch[0], `---\n${updatedYaml}\n---`);
    }
    
    /**
     * Create minimal frontmatter header
     */
    private createMinimalHeader(created: Date): string {
        const now = new Date().toISOString();
        return `---
created: ${created.toISOString()}
updated: ${now}
---`;
    }
    
    /**
     * Store document as memory
     */
    private async storeAsMemory(document: LivingDocument): Promise<void> {
        try {
            const memory: Partial<Memory> = {
                content: document.abstractedContent,
                intent: MemoryIntent.LIVING_DOCUMENT,
                importance: document.relevanceScore,
                tags: document.metadata.tags,
                metadata: {
                    document_id: document.id,
                    document_path: document.uri.fsPath,
                    safety_score: document.safetyScore,
                    category: document.metadata.category,
                    abstraction_score: document.safetyMetadata.abstractionCoverage
                }
            };
            
            // Call MCP tool to create memory
            await this.mcpClient.callTool('memory_create', {
                content: memory.content,
                intent: memory.intent,
                importance: memory.importance,
                tags: memory.tags,
                metadata: memory.metadata
            });
            
        } catch (error) {
            this.logger.error('Failed to store document as memory', error);
        }
    }
    
    /**
     * Convert any file to .CoachNTT
     */
    public async convertToCoachNTT(sourceUri: vscode.Uri): Promise<vscode.Uri> {
        try {
            // Read source file
            const content = await vscode.workspace.fs.readFile(sourceUri);
            const text = new TextDecoder().decode(content);
            
            // Create new .CoachNTT file path
            const dir = path.dirname(sourceUri.fsPath);
            const basename = path.basename(sourceUri.fsPath, path.extname(sourceUri.fsPath));
            const newPath = path.join(dir, `${basename}.CoachNTT`);
            const newUri = vscode.Uri.file(newPath);
            
            // Add metadata header
            const header = this.createDocumentHeader(basename, sourceUri);
            const fullContent = header + '\n\n' + text;
            
            // Write new file
            await vscode.workspace.fs.writeFile(newUri, Buffer.from(fullContent, 'utf-8'));
            
            // Process the new file
            await this.processCoachNTTFile(newUri);
            
            return newUri;
            
        } catch (error) {
            this.logger.error('Failed to convert to .CoachNTT', error);
            throw error;
        }
    }
    
    /**
     * Create document header with metadata
     */
    private createDocumentHeader(title: string, sourceUri: vscode.Uri): string {
        const now = new Date().toISOString();
        const category = this.inferCategory(sourceUri);
        
        return `---
title: ${title}
created: ${now}
updated: ${now}
category: ${category}
tags: []
source: ${sourceUri.fsPath}
---`;
    }
    
    /**
     * Extract title from content
     */
    private extractTitle(content: string): string | null {
        // Check for markdown title
        const titleMatch = content.match(/^#\s+(.+)$/m);
        if (titleMatch) return titleMatch[1];
        
        // Check for YAML frontmatter
        const yamlMatch = content.match(/^---\s*\ntitle:\s*(.+)\n/m);
        if (yamlMatch) return yamlMatch[1];
        
        return null;
    }
    
    /**
     * Extract metadata from content
     */
    private extractMetadata(content: string, uri: vscode.Uri): DocumentMetadata {
        const metadata: DocumentMetadata = {
            tags: [],
            category: this.inferCategory(uri),
            language: 'markdown',
            encoding: 'utf-8',
            linkedDocuments: [],
            codeReferences: []
        };
        
        // Extract metadata from YAML frontmatter
        const yamlMatch = content.match(/^---\s*\n([\s\S]*?)\n---/m);
        if (yamlMatch) {
            const yaml = yamlMatch[1];
            
            // Extract tags
            const tagsMatch = yaml.match(/tags:\s*\[([^\]]+)\]/);
            if (tagsMatch) {
                metadata.tags = tagsMatch[1].split(',').map(t => t.trim());
            }
            
            // Extract category if specified
            const categoryMatch = yaml.match(/category:\s*(.+)$/m);
            if (categoryMatch) {
                const cat = categoryMatch[1].trim() as DocumentCategory;
                if (Object.values(DocumentCategory).includes(cat)) {
                    metadata.category = cat;
                }
            }
        }
        
        return metadata;
    }
    
    /**
     * Extract timestamps from content
     */
    private extractTimestamps(content: string): { created?: string; updated?: string } {
        const timestamps: { created?: string; updated?: string } = {};
        
        const yamlMatch = content.match(/^---\s*\n([\s\S]*?)\n---/m);
        if (yamlMatch) {
            const yaml = yamlMatch[1];
            
            const createdMatch = yaml.match(/created:\s*(.+)$/m);
            if (createdMatch) {
                timestamps.created = createdMatch[1].trim();
            }
            
            const updatedMatch = yaml.match(/updated:\s*(.+)$/m);
            if (updatedMatch) {
                timestamps.updated = updatedMatch[1].trim();
            }
        }
        
        return timestamps;
    }
    
    /**
     * Infer document category from path
     */
    private inferCategory(uri: vscode.Uri): DocumentCategory {
        const path = uri.fsPath.toLowerCase();
        
        if (path.includes('api')) return DocumentCategory.API;
        if (path.includes('architecture')) return DocumentCategory.Architecture;
        if (path.includes('tutorial')) return DocumentCategory.Tutorial;
        if (path.includes('reference')) return DocumentCategory.Reference;
        if (path.includes('plan')) return DocumentCategory.Planning;
        if (path.includes('note')) return DocumentCategory.Notes;
        
        return DocumentCategory.Other;
    }
    
    /**
     * Estimate token count
     */
    private estimateTokens(content: string): number {
        return Math.ceil(content.length / 4);
    }
    
    /**
     * Find document by URI
     */
    private findDocumentByUri(uri: vscode.Uri): LivingDocument | undefined {
        for (const doc of this.documents.values()) {
            if (doc.uri.toString() === uri.toString()) {
                return doc;
            }
        }
        return undefined;
    }
    
    /**
     * Get all documents
     */
    public getAllDocuments(): LivingDocument[] {
        return Array.from(this.documents.values());
    }
    
    /**
     * Get document by ID
     */
    public getDocument(id: string): LivingDocument | undefined {
        return this.documents.get(id);
    }
    
    /**
     * Get current session from workspace configuration or environment
     */
    private getCurrentSession(): string | undefined {
        // Try to get from configuration
        const config = vscode.workspace.getConfiguration('coachntt');
        const session = config.get<string>('currentSession');
        if (session) return session;
        
        // Try to extract from recent git commits or workspace
        // This is a placeholder - could be enhanced to read from git or project files
        return undefined;
    }
}