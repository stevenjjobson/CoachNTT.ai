/**
 * Audio Queue Models and Data Structures
 * 
 * Defines the audio queue system for managing playback items with:
 * - Priority handling
 * - Metadata abstraction
 * - Queue persistence
 * - State management
 */

import { Logger } from '../utils/logger';

/**
 * Audio item priority levels
 */
export enum AudioPriority {
    LOW = 0,
    NORMAL = 1,
    HIGH = 2,
    URGENT = 3
}

/**
 * Audio item status
 */
export enum AudioStatus {
    PENDING = 'pending',
    DOWNLOADING = 'downloading',
    READY = 'ready',
    PLAYING = 'playing',
    PAUSED = 'paused',
    COMPLETED = 'completed',
    ERROR = 'error'
}

/**
 * Audio source type
 */
export enum AudioSourceType {
    SYNTHESIS = 'synthesis',     // AI-generated speech
    MEMORY = 'memory',          // Memory content TTS
    NOTIFICATION = 'notification', // System notifications
    RESPONSE = 'response'       // AI response audio
}

/**
 * Audio item metadata
 */
export interface AudioMetadata {
    title: string;
    description?: string;
    sourceType: AudioSourceType;
    sourceId?: string;          // Abstracted reference
    duration?: number;          // Duration in seconds
    voice?: string;             // Voice ID/name
    language?: string;          // Language code
    timestamp: number;          // Creation timestamp
    abstractedPath?: string;    // Abstracted file path
}

/**
 * Audio item interface
 */
export interface AudioItem {
    id: string;
    content: string;            // Text content for synthesis
    metadata: AudioMetadata;
    priority: AudioPriority;
    status: AudioStatus;
    audioUrl?: string;          // vscode-resource URL
    progress?: number;          // Playback progress (0-1)
    error?: string;             // Error message if failed
    addedAt: number;            // Queue addition timestamp
}

/**
 * Type alias for backward compatibility
 */
export type AudioQueueItem = AudioItem;

/**
 * Audio queue state for persistence
 */
export interface AudioQueueState {
    items: AudioItem[];
    currentItemId?: string;
    isPlaying: boolean;
    volume: number;
    speed: number;
    lastUpdated: number;
}

/**
 * Audio queue configuration
 */
export interface AudioQueueConfig {
    maxItems: number;
    autoCleanup: boolean;
    cleanupThreshold: number;   // Days to keep completed items
    persistQueue: boolean;
}

/**
 * Audio Queue Class
 * 
 * Manages a priority queue of audio items with persistence
 */
export class AudioQueue {
    private items: AudioItem[] = [];
    private itemMap: Map<string, AudioItem> = new Map();
    private currentItemId?: string;
    private logger: Logger;
    private config: AudioQueueConfig;
    
    constructor(config?: Partial<AudioQueueConfig>) {
        this.logger = Logger.getInstance();
        this.config = {
            maxItems: 100,
            autoCleanup: true,
            cleanupThreshold: 7,
            persistQueue: true,
            ...config
        };
    }
    
    /**
     * Add item to queue
     */
    public add(item: Omit<AudioItem, 'id' | 'addedAt'>): string {
        const id = this.generateId();
        const newItem: AudioItem = {
            ...item,
            id,
            addedAt: Date.now()
        };
        
        // Check queue limit
        if (this.items.length >= this.config.maxItems) {
            this.removeOldestCompleted();
        }
        
        // Add to queue based on priority
        const insertIndex = this.findInsertIndex(newItem.priority);
        this.items.splice(insertIndex, 0, newItem);
        this.itemMap.set(id, newItem);
        
        this.logger.debug(`Added audio item to queue: ${id}`);
        
        // Auto cleanup if enabled
        if (this.config.autoCleanup) {
            this.cleanupOldItems();
        }
        
        return id;
    }
    
    /**
     * Remove item from queue
     */
    public remove(id: string): boolean {
        const item = this.itemMap.get(id);
        if (!item) return false;
        
        const index = this.items.findIndex(i => i.id === id);
        if (index !== -1) {
            this.items.splice(index, 1);
        }
        
        this.itemMap.delete(id);
        
        if (this.currentItemId === id) {
            this.currentItemId = undefined;
        }
        
        this.logger.debug(`Removed audio item from queue: ${id}`);
        return true;
    }
    
    /**
     * Get item by ID
     */
    public get(id: string): AudioItem | undefined {
        return this.itemMap.get(id);
    }
    
    /**
     * Get all items
     */
    public getAll(): ReadonlyArray<AudioItem> {
        return [...this.items];
    }
    
    /**
     * Get next item to play
     */
    public getNext(): AudioItem | undefined {
        // Find first non-completed item
        return this.items.find(item => 
            item.status !== AudioStatus.COMPLETED && 
            item.status !== AudioStatus.ERROR
        );
    }
    
    /**
     * Get current playing item
     */
    public getCurrent(): AudioItem | undefined {
        return this.currentItemId ? this.itemMap.get(this.currentItemId) : undefined;
    }
    
    /**
     * Set current playing item
     */
    public setCurrent(id: string | undefined): void {
        this.currentItemId = id;
    }
    
    /**
     * Update item status
     */
    public updateStatus(id: string, status: AudioStatus, error?: string): boolean {
        const item = this.itemMap.get(id);
        if (!item) return false;
        
        item.status = status;
        if (error) {
            item.error = this.abstractError(error);
        }
        
        this.logger.debug(`Updated audio item status: ${id} -> ${status}`);
        return true;
    }
    
    /**
     * Update item progress
     */
    public updateProgress(id: string, progress: number): boolean {
        const item = this.itemMap.get(id);
        if (!item) return false;
        
        item.progress = Math.max(0, Math.min(1, progress));
        return true;
    }
    
    /**
     * Update audio URL
     */
    public updateAudioUrl(id: string, url: string): boolean {
        const item = this.itemMap.get(id);
        if (!item) return false;
        
        item.audioUrl = url;
        item.status = AudioStatus.READY;
        return true;
    }
    
    /**
     * Clear completed items
     */
    public clearCompleted(): number {
        const completed = this.items.filter(item => 
            item.status === AudioStatus.COMPLETED || 
            item.status === AudioStatus.ERROR
        );
        
        completed.forEach(item => this.remove(item.id));
        
        this.logger.info(`Cleared ${completed.length} completed items`);
        return completed.length;
    }
    
    /**
     * Clear all items
     */
    public clear(): void {
        this.items = [];
        this.itemMap.clear();
        this.currentItemId = undefined;
        this.logger.info('Cleared audio queue');
    }
    
    /**
     * Reorder item in queue
     */
    public reorder(id: string, newIndex: number): boolean {
        const currentIndex = this.items.findIndex(item => item.id === id);
        if (currentIndex === -1 || newIndex < 0 || newIndex >= this.items.length) {
            return false;
        }
        
        const [item] = this.items.splice(currentIndex, 1);
        this.items.splice(newIndex, 0, item);
        
        this.logger.debug(`Reordered item ${id}: ${currentIndex} -> ${newIndex}`);
        return true;
    }
    
    /**
     * Get queue state for persistence
     */
    public getState(): AudioQueueState {
        return {
            items: this.items.map(item => this.sanitizeItem(item)),
            currentItemId: this.currentItemId,
            isPlaying: false, // Will be set by service
            volume: 100,      // Will be set by service
            speed: 1.0,       // Will be set by service
            lastUpdated: Date.now()
        };
    }
    
    /**
     * Restore queue from state
     */
    public restoreState(state: AudioQueueState): void {
        this.clear();
        
        state.items.forEach(item => {
            this.items.push(item);
            this.itemMap.set(item.id, item);
        });
        
        this.currentItemId = state.currentItemId;
        
        this.logger.info(`Restored queue with ${this.items.length} items`);
        
        // Clean up old items after restore
        if (this.config.autoCleanup) {
            this.cleanupOldItems();
        }
    }
    
    /**
     * Get queue statistics
     */
    public getStats(): Record<string, number> {
        const stats: Record<string, number> = {
            total: this.items.length,
            pending: 0,
            ready: 0,
            completed: 0,
            error: 0
        };
        
        this.items.forEach(item => {
            switch (item.status) {
                case AudioStatus.PENDING:
                case AudioStatus.DOWNLOADING:
                    stats.pending++;
                    break;
                case AudioStatus.READY:
                case AudioStatus.PLAYING:
                case AudioStatus.PAUSED:
                    stats.ready++;
                    break;
                case AudioStatus.COMPLETED:
                    stats.completed++;
                    break;
                case AudioStatus.ERROR:
                    stats.error++;
                    break;
            }
        });
        
        return stats;
    }
    
    /**
     * Generate unique ID
     */
    private generateId(): string {
        return `audio_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }
    
    /**
     * Find insert index based on priority
     */
    private findInsertIndex(priority: AudioPriority): number {
        // Find the first item with lower priority
        for (let i = 0; i < this.items.length; i++) {
            if (this.items[i].priority < priority) {
                return i;
            }
        }
        return this.items.length;
    }
    
    /**
     * Remove oldest completed item
     */
    private removeOldestCompleted(): void {
        const completed = this.items.filter(item => 
            item.status === AudioStatus.COMPLETED || 
            item.status === AudioStatus.ERROR
        );
        
        if (completed.length > 0) {
            // Sort by addedAt and remove oldest
            completed.sort((a, b) => a.addedAt - b.addedAt);
            this.remove(completed[0].id);
        } else {
            // No completed items, remove oldest pending
            const oldest = [...this.items].sort((a, b) => a.addedAt - b.addedAt)[0];
            if (oldest) {
                this.remove(oldest.id);
            }
        }
    }
    
    /**
     * Clean up old items
     */
    private cleanupOldItems(): void {
        const threshold = Date.now() - (this.config.cleanupThreshold * 24 * 60 * 60 * 1000);
        
        const oldItems = this.items.filter(item => 
            (item.status === AudioStatus.COMPLETED || item.status === AudioStatus.ERROR) &&
            item.addedAt < threshold
        );
        
        oldItems.forEach(item => this.remove(item.id));
        
        if (oldItems.length > 0) {
            this.logger.debug(`Cleaned up ${oldItems.length} old items`);
        }
    }
    
    /**
     * Abstract error message
     */
    private abstractError(error: string): string {
        // Abstract file paths
        error = error.replace(/([A-Za-z]:)?[\\/\\][^\s]+/g, '<path>');
        // Abstract URLs
        error = error.replace(/https?:\/\/[^\s]+/g, '<url>');
        // Abstract IPs
        error = error.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '<ip>');
        return error;
    }
    
    /**
     * Sanitize item for persistence
     */
    private sanitizeItem(item: AudioItem): AudioItem {
        return {
            ...item,
            content: item.content.substring(0, 1000), // Limit content size
            error: item.error ? this.abstractError(item.error) : undefined
        };
    }
}