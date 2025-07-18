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
    public async processCoachNTTFile(uri: vscode.Uri): Promise<LivingDocument> {
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
     * Create a new Living Document
     */
    private async createDocument(uri: vscode.Uri, content: string): Promise<LivingDocument> {
        // Abstract the content
        const abstractionResult = await this.abstractor.abstractDocument(content);
        
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
            createdAt: new Date(),
            updatedAt: new Date(),
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
        // Abstract the new content
        const abstractionResult = await this.abstractor.abstractDocument(
            newContent,
            document.referenceEvolution
        );
        
        // Update document
        document.content = newContent;
        document.abstractedContent = abstractionResult.abstractedContent;
        document.safetyMetadata = this.abstractor.createSafetyMetadata(abstractionResult);
        document.safetyScore = abstractionResult.safetyScore;
        document.updatedAt = new Date();
        document.lastAccessed = new Date();
        document.accessCount++;
        document.currentSize = this.estimateTokens(abstractionResult.abstractedContent);
        document.compactionRatio = document.currentSize / document.originalSize;
        
        return document;
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
        
        // Extract tags from YAML frontmatter
        const yamlMatch = content.match(/^---\s*\n([\s\S]*?)\n---/m);
        if (yamlMatch) {
            const yaml = yamlMatch[1];
            const tagsMatch = yaml.match(/tags:\s*\[([^\]]+)\]/);
            if (tagsMatch) {
                metadata.tags = tagsMatch[1].split(',').map(t => t.trim());
            }
        }
        
        return metadata;
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
}