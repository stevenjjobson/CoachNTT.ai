/**
 * Audio Cache Utilities
 * 
 * Implements LRU caching for synthesized audio with:
 * - Size-based eviction (50MB limit)
 * - Performance monitoring
 * - Abstracted paths
 * - Cache invalidation
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { Logger } from './logger';

/**
 * Cache entry metadata
 */
export interface CacheEntry {
    id: string;
    key: string;
    size: number;           // Size in bytes
    hits: number;           // Access count
    lastAccessed: number;   // Last access timestamp
    created: number;        // Creation timestamp
    abstractedPath: string; // Abstracted file path for display
}

/**
 * Cache statistics
 */
export interface CacheStats {
    entries: number;
    totalSize: number;
    hitRate: number;
    evictions: number;
    avgAccessTime: number;
}

/**
 * Audio cache configuration
 */
export interface AudioCacheConfig {
    maxSize: number;        // Max cache size in bytes
    maxEntries: number;     // Max number of entries
    ttl?: number;          // Time to live in milliseconds
    cleanupInterval: number; // Cleanup interval in milliseconds
}

/**
 * LRU Audio Cache Implementation
 */
export class AudioCache {
    private entries: Map<string, CacheEntry> = new Map();
    private accessOrder: string[] = [];
    private currentSize: number = 0;
    private hits: number = 0;
    private misses: number = 0;
    private evictions: number = 0;
    private cacheDir: string;
    private cleanupTimer?: NodeJS.Timer;
    private logger: Logger;
    private config: AudioCacheConfig;
    
    constructor(
        private context: vscode.ExtensionContext,
        config?: Partial<AudioCacheConfig>
    ) {
        this.logger = Logger.getInstance();
        this.config = {
            maxSize: 50 * 1024 * 1024,  // 50MB default
            maxEntries: 200,
            ttl: 7 * 24 * 60 * 60 * 1000, // 7 days default
            cleanupInterval: 60 * 60 * 1000, // 1 hour default
            ...config
        };
        
        // Initialize cache directory
        this.cacheDir = path.join(context.globalStorageUri.fsPath, 'audio-cache');
        this.ensureCacheDirectory();
        
        // Load existing cache metadata
        this.loadCacheMetadata();
        
        // Start cleanup timer
        this.startCleanupTimer();
    }
    
    /**
     * Get cached audio file
     */
    public async get(key: string): Promise<vscode.Uri | undefined> {
        const entry = this.entries.get(key);
        
        if (!entry) {
            this.misses++;
            return undefined;
        }
        
        const filePath = this.getFilePath(entry.id);
        
        // Check if file exists
        if (!fs.existsSync(filePath)) {
            this.logger.warn(`Cache file missing: ${entry.abstractedPath}`);
            this.remove(key);
            this.misses++;
            return undefined;
        }
        
        // Update access info
        entry.hits++;
        entry.lastAccessed = Date.now();
        this.hits++;
        
        // Update LRU order
        this.updateAccessOrder(key);
        
        // Return vscode URI
        return vscode.Uri.file(filePath);
    }
    
    /**
     * Add audio file to cache
     */
    public async put(key: string, audioData: Buffer): Promise<vscode.Uri> {
        // Check if key already exists
        if (this.entries.has(key)) {
            this.logger.debug(`Cache hit for existing key: ${key}`);
            return (await this.get(key))!;
        }
        
        const size = audioData.length;
        
        // Check size limits
        if (size > this.config.maxSize) {
            throw new Error('Audio file too large for cache');
        }
        
        // Evict entries if needed
        while (this.currentSize + size > this.config.maxSize || 
               this.entries.size >= this.config.maxEntries) {
            this.evictLRU();
        }
        
        // Generate file ID and path
        const id = this.generateId(key);
        const filePath = this.getFilePath(id);
        
        // Write file
        await fs.promises.writeFile(filePath, audioData);
        
        // Create entry
        const entry: CacheEntry = {
            id,
            key,
            size,
            hits: 0,
            lastAccessed: Date.now(),
            created: Date.now(),
            abstractedPath: `<cache>/audio/${id.substring(0, 8)}...`
        };
        
        // Add to cache
        this.entries.set(key, entry);
        this.accessOrder.push(key);
        this.currentSize += size;
        
        this.logger.debug(`Cached audio: ${entry.abstractedPath} (${this.formatSize(size)})`);
        
        // Save metadata
        this.saveCacheMetadata();
        
        return vscode.Uri.file(filePath);
    }
    
    /**
     * Remove entry from cache
     */
    public remove(key: string): boolean {
        const entry = this.entries.get(key);
        if (!entry) return false;
        
        // Delete file
        const filePath = this.getFilePath(entry.id);
        try {
            if (fs.existsSync(filePath)) {
                fs.unlinkSync(filePath);
            }
        } catch (error) {
            this.logger.error('Failed to delete cache file', error);
        }
        
        // Remove from cache
        this.entries.delete(key);
        this.accessOrder = this.accessOrder.filter(k => k !== key);
        this.currentSize -= entry.size;
        
        this.logger.debug(`Removed from cache: ${entry.abstractedPath}`);
        
        // Save metadata
        this.saveCacheMetadata();
        
        return true;
    }
    
    /**
     * Clear entire cache
     */
    public async clear(): Promise<void> {
        this.logger.info('Clearing audio cache');
        
        // Delete all files
        for (const entry of this.entries.values()) {
            const filePath = this.getFilePath(entry.id);
            try {
                if (fs.existsSync(filePath)) {
                    await fs.promises.unlink(filePath);
                }
            } catch (error) {
                this.logger.error('Failed to delete cache file', error);
            }
        }
        
        // Reset state
        this.entries.clear();
        this.accessOrder = [];
        this.currentSize = 0;
        this.hits = 0;
        this.misses = 0;
        this.evictions = 0;
        
        // Save metadata
        this.saveCacheMetadata();
    }
    
    /**
     * Get cache statistics
     */
    public getStats(): CacheStats {
        const totalRequests = this.hits + this.misses;
        const hitRate = totalRequests > 0 ? this.hits / totalRequests : 0;
        
        // Calculate average access time (simplified)
        let avgAccessTime = 0;
        if (this.entries.size > 0) {
            const now = Date.now();
            const totalAge = Array.from(this.entries.values())
                .reduce((sum, entry) => sum + (now - entry.lastAccessed), 0);
            avgAccessTime = totalAge / this.entries.size;
        }
        
        return {
            entries: this.entries.size,
            totalSize: this.currentSize,
            hitRate: Math.round(hitRate * 100) / 100,
            evictions: this.evictions,
            avgAccessTime: Math.round(avgAccessTime / 1000) // Convert to seconds
        };
    }
    
    /**
     * Warm cache with frequently used items
     */
    public async warmCache(items: Array<{ key: string; data: Buffer }>): Promise<void> {
        this.logger.info(`Warming cache with ${items.length} items`);
        
        for (const item of items) {
            try {
                await this.put(item.key, item.data);
            } catch (error) {
                this.logger.error(`Failed to warm cache for key: ${item.key}`, error);
            }
        }
    }
    
    /**
     * Generate cache key from content
     */
    public static generateKey(content: string, voice?: string, language?: string): string {
        const data = `${content}|${voice || 'default'}|${language || 'en'}`;
        return crypto.createHash('sha256').update(data).digest('hex');
    }
    
    /**
     * Dispose cache
     */
    public dispose(): void {
        if (this.cleanupTimer) {
            clearInterval(this.cleanupTimer);
        }
        this.saveCacheMetadata();
    }
    
    /**
     * Ensure cache directory exists
     */
    private ensureCacheDirectory(): void {
        if (!fs.existsSync(this.cacheDir)) {
            fs.mkdirSync(this.cacheDir, { recursive: true });
            this.logger.info(`Created cache directory: <cache>/audio/`);
        }
    }
    
    /**
     * Get file path for cache entry
     */
    private getFilePath(id: string): string {
        return path.join(this.cacheDir, `${id}.audio`);
    }
    
    /**
     * Generate unique ID for cache entry
     */
    private generateId(key: string): string {
        const timestamp = Date.now().toString(36);
        const hash = key.substring(0, 8);
        return `${timestamp}_${hash}`;
    }
    
    /**
     * Update LRU access order
     */
    private updateAccessOrder(key: string): void {
        const index = this.accessOrder.indexOf(key);
        if (index > -1) {
            this.accessOrder.splice(index, 1);
        }
        this.accessOrder.push(key);
    }
    
    /**
     * Evict least recently used entry
     */
    private evictLRU(): void {
        if (this.accessOrder.length === 0) return;
        
        const key = this.accessOrder.shift()!;
        const entry = this.entries.get(key);
        
        if (entry) {
            this.logger.debug(`Evicting LRU entry: ${entry.abstractedPath}`);
            this.remove(key);
            this.evictions++;
        }
    }
    
    /**
     * Start cleanup timer
     */
    private startCleanupTimer(): void {
        this.cleanupTimer = setInterval(() => {
            this.cleanup();
        }, this.config.cleanupInterval);
    }
    
    /**
     * Clean up expired entries
     */
    private cleanup(): void {
        if (!this.config.ttl) return;
        
        const now = Date.now();
        const expired: string[] = [];
        
        for (const [key, entry] of this.entries) {
            if (now - entry.created > this.config.ttl) {
                expired.push(key);
            }
        }
        
        if (expired.length > 0) {
            this.logger.info(`Cleaning up ${expired.length} expired cache entries`);
            expired.forEach(key => this.remove(key));
        }
    }
    
    /**
     * Load cache metadata from disk
     */
    private loadCacheMetadata(): void {
        const metadataPath = path.join(this.cacheDir, 'metadata.json');
        
        try {
            if (fs.existsSync(metadataPath)) {
                const data = fs.readFileSync(metadataPath, 'utf8');
                const metadata = JSON.parse(data);
                
                // Restore entries
                this.entries = new Map(metadata.entries);
                this.accessOrder = metadata.accessOrder || [];
                this.currentSize = metadata.currentSize || 0;
                this.evictions = metadata.evictions || 0;
                
                // Validate entries still exist
                this.validateCache();
                
                this.logger.info(`Loaded cache metadata: ${this.entries.size} entries`);
            }
        } catch (error) {
            this.logger.error('Failed to load cache metadata', error);
        }
    }
    
    /**
     * Save cache metadata to disk
     */
    private saveCacheMetadata(): void {
        const metadataPath = path.join(this.cacheDir, 'metadata.json');
        
        const metadata = {
            entries: Array.from(this.entries.entries()),
            accessOrder: this.accessOrder,
            currentSize: this.currentSize,
            evictions: this.evictions,
            lastSaved: Date.now()
        };
        
        try {
            fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
        } catch (error) {
            this.logger.error('Failed to save cache metadata', error);
        }
    }
    
    /**
     * Validate cache entries
     */
    private validateCache(): void {
        const invalid: string[] = [];
        
        for (const [key, entry] of this.entries) {
            const filePath = this.getFilePath(entry.id);
            if (!fs.existsSync(filePath)) {
                invalid.push(key);
            }
        }
        
        if (invalid.length > 0) {
            this.logger.warn(`Found ${invalid.length} invalid cache entries`);
            invalid.forEach(key => {
                this.entries.delete(key);
                this.accessOrder = this.accessOrder.filter(k => k !== key);
            });
            
            // Recalculate size
            this.recalculateSize();
        }
    }
    
    /**
     * Recalculate total cache size
     */
    private recalculateSize(): void {
        this.currentSize = 0;
        
        for (const entry of this.entries.values()) {
            const filePath = this.getFilePath(entry.id);
            try {
                if (fs.existsSync(filePath)) {
                    const stats = fs.statSync(filePath);
                    entry.size = stats.size;
                    this.currentSize += stats.size;
                }
            } catch (error) {
                this.logger.error('Failed to stat cache file', error);
            }
        }
    }
    
    /**
     * Format size for display
     */
    private formatSize(bytes: number): string {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }
}