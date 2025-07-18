/**
 * Audio Playback Service
 * 
 * Central service for managing audio playback with:
 * - Queue management
 * - Playback state tracking
 * - MCP synthesis integration
 * - Event emission for UI updates
 * - Cross-platform support
 */

import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { 
    AudioQueue, 
    AudioItem, 
    AudioStatus, 
    AudioPriority,
    AudioSourceType,
    AudioQueueState 
} from '../models/audio-queue';
import { AudioCache } from '../utils/audio-cache';
import { MCPClient } from './mcp-client';
import { Logger } from '../utils/logger';
import { ConfigurationService } from '../config/settings';

/**
 * Playback state
 */
export enum PlaybackState {
    STOPPED = 'stopped',
    PLAYING = 'playing',
    PAUSED = 'paused',
    LOADING = 'loading'
}

/**
 * Audio synthesis options
 */
export interface AudioSynthesisOptions {
    voice?: string;
    language?: string;
    speed?: number;
    pitch?: number;
    volume?: number;
}

/**
 * Playback events
 */
export interface AudioPlaybackEvents {
    'stateChanged': (state: PlaybackState) => void;
    'itemChanged': (item: AudioItem | undefined) => void;
    'queueChanged': (items: ReadonlyArray<AudioItem>) => void;
    'progressChanged': (progress: number, duration: number) => void;
    'volumeChanged': (volume: number) => void;
    'speedChanged': (speed: number) => void;
    'error': (error: Error) => void;
}

/**
 * Audio service configuration
 */
export interface AudioServiceConfig {
    volume: number;
    speed: number;
    autoPlay: boolean;
    cacheEnabled: boolean;
    synthesisTimeout: number;
}

/**
 * Audio Playback Service
 */
export class AudioPlaybackService extends EventEmitter {
    private static instance: AudioPlaybackService;
    
    private queue: AudioQueue;
    private cache: AudioCache;
    private mcpClient: MCPClient;
    private logger: Logger;
    private config: ConfigurationService;
    
    private state: PlaybackState = PlaybackState.STOPPED;
    private currentItem?: AudioItem;
    private volume: number = 100;
    private speed: number = 1.0;
    private autoPlay: boolean = true;
    private cacheEnabled: boolean = true;
    
    private statusBarItem?: vscode.StatusBarItem;
    private synthesisInProgress: Map<string, Promise<string>> = new Map();
    
    private constructor(private context: vscode.ExtensionContext) {
        super();
        
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        this.mcpClient = MCPClient.getInstance();
        
        // Initialize queue
        this.queue = new AudioQueue({
            maxItems: 100,
            autoCleanup: true,
            cleanupThreshold: 7,
            persistQueue: true
        });
        
        // Initialize cache
        this.cache = new AudioCache(context, {
            maxSize: 50 * 1024 * 1024, // 50MB
            maxEntries: 200,
            ttl: 7 * 24 * 60 * 60 * 1000 // 7 days
        });
        
        // Load saved state
        this.loadState();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    /**
     * Get singleton instance
     */
    public static getInstance(context: vscode.ExtensionContext): AudioPlaybackService {
        if (!AudioPlaybackService.instance) {
            AudioPlaybackService.instance = new AudioPlaybackService(context);
        }
        return AudioPlaybackService.instance;
    }
    
    /**
     * Add audio to queue
     */
    public async addToQueue(
        content: string,
        sourceType: AudioSourceType,
        options?: {
            priority?: AudioPriority;
            metadata?: Record<string, any>;
            synthesisOptions?: AudioSynthesisOptions;
        }
    ): Promise<string> {
        const item: Omit<AudioItem, 'id' | 'addedAt'> = {
            content,
            metadata: {
                title: this.generateTitle(content, sourceType),
                sourceType,
                timestamp: Date.now(),
                ...options?.metadata
            },
            priority: options?.priority || AudioPriority.NORMAL,
            status: AudioStatus.PENDING
        };
        
        const id = this.queue.add(item);
        this.logger.info(`Added audio to queue: ${id}`);
        
        // Emit queue changed event
        this.emit('queueChanged', this.queue.getAll());
        
        // Start synthesis
        this.synthesizeAudio(id, options?.synthesisOptions);
        
        // Auto-play if enabled and not playing
        if (this.autoPlay && this.state === PlaybackState.STOPPED) {
            this.play();
        }
        
        return id;
    }
    
    /**
     * Play audio
     */
    public async play(itemId?: string): Promise<void> {
        try {
            // If specific item requested
            if (itemId) {
                const item = this.queue.get(itemId);
                if (!item) {
                    throw new Error('Audio item not found');
                }
                this.currentItem = item;
            }
            
            // Get current or next item
            if (!this.currentItem) {
                this.currentItem = this.queue.getNext();
                if (!this.currentItem) {
                    this.logger.info('No items in queue to play');
                    return;
                }
            }
            
            // Check if audio is ready
            if (this.currentItem.status !== AudioStatus.READY) {
                this.logger.info('Waiting for audio to be ready...');
                this.setState(PlaybackState.LOADING);
                return;
            }
            
            // Update queue current item
            this.queue.setCurrent(this.currentItem.id);
            
            // Update status
            this.queue.updateStatus(this.currentItem.id, AudioStatus.PLAYING);
            this.setState(PlaybackState.PLAYING);
            
            // Emit events
            this.emit('itemChanged', this.currentItem);
            
            // Send play command to WebView
            this.sendPlayCommand(this.currentItem);
            
        } catch (error) {
            this.logger.error('Failed to play audio', error);
            this.emit('error', error as Error);
        }
    }
    
    /**
     * Pause playback
     */
    public pause(): void {
        if (this.state !== PlaybackState.PLAYING) return;
        
        this.setState(PlaybackState.PAUSED);
        
        if (this.currentItem) {
            this.queue.updateStatus(this.currentItem.id, AudioStatus.PAUSED);
        }
        
        // Send pause command to WebView
        this.sendPauseCommand();
    }
    
    /**
     * Stop playback
     */
    public stop(): void {
        if (this.state === PlaybackState.STOPPED) return;
        
        this.setState(PlaybackState.STOPPED);
        
        if (this.currentItem) {
            this.queue.updateStatus(this.currentItem.id, AudioStatus.READY);
            this.queue.updateProgress(this.currentItem.id, 0);
        }
        
        this.currentItem = undefined;
        this.queue.setCurrent(undefined);
        
        // Send stop command to WebView
        this.sendStopCommand();
        
        this.emit('itemChanged', undefined);
    }
    
    /**
     * Skip to next item
     */
    public async next(): Promise<void> {
        if (this.currentItem) {
            // Mark current as completed
            this.queue.updateStatus(this.currentItem.id, AudioStatus.COMPLETED);
        }
        
        this.currentItem = undefined;
        await this.play();
    }
    
    /**
     * Skip to previous item (if available)
     */
    public async previous(): Promise<void> {
        // Simple implementation - just restart current
        if (this.currentItem) {
            this.queue.updateProgress(this.currentItem.id, 0);
            await this.play(this.currentItem.id);
        }
    }
    
    /**
     * Seek to position
     */
    public seek(position: number): void {
        if (!this.currentItem) return;
        
        // Update progress
        this.queue.updateProgress(this.currentItem.id, position);
        
        // Send seek command to WebView
        this.sendSeekCommand(position);
    }
    
    /**
     * Set volume
     */
    public setVolume(volume: number): void {
        this.volume = Math.max(0, Math.min(100, volume));
        this.emit('volumeChanged', this.volume);
        
        // Send volume command to WebView
        this.sendVolumeCommand(this.volume);
        
        // Save state
        this.saveState();
    }
    
    /**
     * Set playback speed
     */
    public setSpeed(speed: number): void {
        this.speed = Math.max(0.5, Math.min(2.0, speed));
        this.emit('speedChanged', this.speed);
        
        // Send speed command to WebView
        this.sendSpeedCommand(this.speed);
        
        // Save state
        this.saveState();
    }
    
    /**
     * Get current queue
     */
    public getQueue(): ReadonlyArray<AudioItem> {
        return this.queue.getAll();
    }
    
    /**
     * Get current item
     */
    public getCurrentItem(): AudioItem | undefined {
        return this.currentItem;
    }
    
    /**
     * Get playback state
     */
    public getState(): PlaybackState {
        return this.state;
    }
    
    /**
     * Get volume
     */
    public getVolume(): number {
        return this.volume;
    }
    
    /**
     * Get speed
     */
    public getSpeed(): number {
        return this.speed;
    }
    
    /**
     * Remove item from queue
     */
    public removeFromQueue(itemId: string): boolean {
        const wasCurrentItem = this.currentItem?.id === itemId;
        const removed = this.queue.remove(itemId);
        
        if (removed) {
            this.emit('queueChanged', this.queue.getAll());
            
            if (wasCurrentItem) {
                this.stop();
                // Auto-play next if available
                if (this.autoPlay) {
                    this.play();
                }
            }
        }
        
        return removed;
    }
    
    /**
     * Clear queue
     */
    public clearQueue(): void {
        this.stop();
        this.queue.clear();
        this.emit('queueChanged', []);
    }
    
    /**
     * Clear completed items
     */
    public clearCompleted(): number {
        const cleared = this.queue.clearCompleted();
        if (cleared > 0) {
            this.emit('queueChanged', this.queue.getAll());
        }
        return cleared;
    }
    
    /**
     * Reorder queue item
     */
    public reorderQueue(itemId: string, newIndex: number): boolean {
        const reordered = this.queue.reorder(itemId, newIndex);
        if (reordered) {
            this.emit('queueChanged', this.queue.getAll());
        }
        return reordered;
    }
    
    /**
     * Get queue statistics
     */
    public getQueueStats(): Record<string, number> {
        return this.queue.getStats();
    }
    
    /**
     * Get cache statistics
     */
    public getCacheStats(): any {
        return this.cache.getStats();
    }
    
    /**
     * Create status bar item
     */
    public createStatusBarItem(): vscode.StatusBarItem {
        if (!this.statusBarItem) {
            this.statusBarItem = vscode.window.createStatusBarItem(
                vscode.StatusBarAlignment.Right,
                90
            );
            this.updateStatusBarItem();
            this.statusBarItem.show();
        }
        return this.statusBarItem;
    }
    
    /**
     * Update status bar item
     */
    private updateStatusBarItem(): void {
        if (!this.statusBarItem) return;
        
        const icon = this.state === PlaybackState.PLAYING ? '$(debug-pause)' : '$(play)';
        const queueCount = this.queue.getAll().length;
        
        if (this.currentItem) {
            const title = this.truncateText(this.currentItem.metadata.title, 30);
            this.statusBarItem.text = `${icon} ${title}`;
            this.statusBarItem.tooltip = `${this.currentItem.metadata.title}\nQueue: ${queueCount} items\nClick to ${this.state === PlaybackState.PLAYING ? 'pause' : 'play'}`;
        } else {
            this.statusBarItem.text = `${icon} CoachNTT Audio`;
            this.statusBarItem.tooltip = `Queue: ${queueCount} items\nClick to open player`;
        }
        
        this.statusBarItem.command = 'coachntt.togglePlayback';
    }
    
    /**
     * Synthesize audio for item
     */
    private async synthesizeAudio(itemId: string, options?: AudioSynthesisOptions): Promise<void> {
        const item = this.queue.get(itemId);
        if (!item) return;
        
        try {
            // Check if already synthesizing
            const existingPromise = this.synthesisInProgress.get(itemId);
            if (existingPromise) {
                await existingPromise;
                return;
            }
            
            // Check cache first
            if (this.cacheEnabled) {
                const cacheKey = AudioCache.generateKey(
                    item.content,
                    options?.voice,
                    options?.language
                );
                
                const cachedUri = await this.cache.get(cacheKey);
                if (cachedUri) {
                    this.logger.debug(`Cache hit for audio: ${itemId}`);
                    this.queue.updateAudioUrl(itemId, cachedUri.toString());
                    this.onAudioReady(itemId);
                    return;
                }
            }
            
            // Update status
            this.queue.updateStatus(itemId, AudioStatus.DOWNLOADING);
            
            // Create synthesis promise
            const synthesisPromise = this.performSynthesis(item, options);
            this.synthesisInProgress.set(itemId, synthesisPromise);
            
            // Wait for synthesis
            const audioUrl = await synthesisPromise;
            
            // Update item
            this.queue.updateAudioUrl(itemId, audioUrl);
            this.onAudioReady(itemId);
            
        } catch (error) {
            this.logger.error(`Failed to synthesize audio for ${itemId}`, error);
            this.queue.updateStatus(itemId, AudioStatus.ERROR, (error as Error).message);
            this.emit('error', error as Error);
        } finally {
            this.synthesisInProgress.delete(itemId);
        }
    }
    
    /**
     * Perform audio synthesis via MCP
     */
    private async performSynthesis(item: AudioItem, options?: AudioSynthesisOptions): Promise<string> {
        // Call MCP audio synthesis tool
        const response = await this.mcpClient.callTool('audio_synthesize', {
            text: item.content,
            voice: options?.voice || 'default',
            language: options?.language || 'en',
            speed: options?.speed || this.speed,
            pitch: options?.pitch || 1.0,
            volume: options?.volume || this.volume / 100
        });
        
        if (!response.success || !response.audio_data) {
            throw new Error('Audio synthesis failed');
        }
        
        // Decode base64 audio data
        const audioBuffer = Buffer.from(response.audio_data, 'base64');
        
        // Cache the audio if enabled
        if (this.cacheEnabled) {
            const cacheKey = AudioCache.generateKey(
                item.content,
                options?.voice,
                options?.language
            );
            
            const cachedUri = await this.cache.put(cacheKey, audioBuffer);
            return cachedUri.toString();
        }
        
        // Create temporary file if caching disabled
        const tempFile = await this.createTempFile(audioBuffer);
        return vscode.Uri.file(tempFile).toString();
    }
    
    /**
     * Handle audio ready
     */
    private onAudioReady(itemId: string): void {
        const item = this.queue.get(itemId);
        if (!item) return;
        
        // Check if this is the current item waiting to play
        if (this.currentItem?.id === itemId && this.state === PlaybackState.LOADING) {
            this.play(itemId);
        }
        
        // Check if auto-play should start
        if (!this.currentItem && this.autoPlay && this.state === PlaybackState.STOPPED) {
            this.play();
        }
    }
    
    /**
     * Set playback state
     */
    private setState(state: PlaybackState): void {
        if (this.state === state) return;
        
        this.state = state;
        this.emit('stateChanged', state);
        this.updateStatusBarItem();
        
        // Save state
        this.saveState();
    }
    
    /**
     * Set up event listeners
     */
    private setupEventListeners(): void {
        // Handle progress updates from WebView
        this.on('webview:progress', (data: { itemId: string; progress: number; duration: number }) => {
            if (data.itemId === this.currentItem?.id) {
                this.queue.updateProgress(data.itemId, data.progress);
                this.emit('progressChanged', data.progress, data.duration);
            }
        });
        
        // Handle playback ended
        this.on('webview:ended', (data: { itemId: string }) => {
            if (data.itemId === this.currentItem?.id) {
                this.queue.updateStatus(data.itemId, AudioStatus.COMPLETED);
                this.next();
            }
        });
        
        // Handle playback error
        this.on('webview:error', (data: { itemId: string; error: string }) => {
            this.queue.updateStatus(data.itemId, AudioStatus.ERROR, data.error);
            this.emit('error', new Error(data.error));
            
            if (data.itemId === this.currentItem?.id) {
                this.next();
            }
        });
    }
    
    /**
     * Send play command to WebView
     */
    private sendPlayCommand(item: AudioItem): void {
        // This will be implemented when WebView is created
        this.emit('webview:command', {
            command: 'play',
            data: {
                itemId: item.id,
                url: item.audioUrl,
                volume: this.volume,
                speed: this.speed
            }
        });
    }
    
    /**
     * Send pause command to WebView
     */
    private sendPauseCommand(): void {
        this.emit('webview:command', { command: 'pause' });
    }
    
    /**
     * Send stop command to WebView
     */
    private sendStopCommand(): void {
        this.emit('webview:command', { command: 'stop' });
    }
    
    /**
     * Send seek command to WebView
     */
    private sendSeekCommand(position: number): void {
        this.emit('webview:command', { command: 'seek', data: { position } });
    }
    
    /**
     * Send volume command to WebView
     */
    private sendVolumeCommand(volume: number): void {
        this.emit('webview:command', { command: 'setVolume', data: { volume } });
    }
    
    /**
     * Send speed command to WebView
     */
    private sendSpeedCommand(speed: number): void {
        this.emit('webview:command', { command: 'setSpeed', data: { speed } });
    }
    
    /**
     * Generate title from content
     */
    private generateTitle(content: string, sourceType: AudioSourceType): string {
        const maxLength = 50;
        let prefix = '';
        
        switch (sourceType) {
            case AudioSourceType.SYNTHESIS:
                prefix = 'AI: ';
                break;
            case AudioSourceType.MEMORY:
                prefix = 'Memory: ';
                break;
            case AudioSourceType.NOTIFICATION:
                prefix = 'Notification: ';
                break;
            case AudioSourceType.RESPONSE:
                prefix = 'Response: ';
                break;
        }
        
        const text = content.trim().replace(/\n/g, ' ');
        const truncated = text.length > maxLength 
            ? text.substring(0, maxLength - 3) + '...'
            : text;
            
        return prefix + truncated;
    }
    
    /**
     * Truncate text
     */
    private truncateText(text: string, maxLength: number): string {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
    
    /**
     * Create temporary file
     */
    private async createTempFile(data: Buffer): Promise<string> {
        const tempDir = this.context.globalStorageUri.fsPath;
        const tempFile = `${tempDir}/temp_${Date.now()}.audio`;
        
        await vscode.workspace.fs.writeFile(
            vscode.Uri.file(tempFile),
            data
        );
        
        // Clean up after 1 hour
        setTimeout(() => {
            vscode.workspace.fs.delete(vscode.Uri.file(tempFile)).then(
                () => {},
                () => {} // Ignore errors
            );
        }, 60 * 60 * 1000);
        
        return tempFile;
    }
    
    /**
     * Load saved state
     */
    private loadState(): void {
        try {
            const savedState = this.context.workspaceState.get<AudioQueueState>('coachntt.audioQueue');
            if (savedState) {
                this.queue.restoreState(savedState);
                this.volume = savedState.volume || 100;
                this.speed = savedState.speed || 1.0;
                this.logger.info('Loaded audio queue state');
            }
        } catch (error) {
            this.logger.error('Failed to load audio state', error);
        }
    }
    
    /**
     * Save state
     */
    private saveState(): void {
        try {
            const state = this.queue.getState();
            state.volume = this.volume;
            state.speed = this.speed;
            state.isPlaying = this.state === PlaybackState.PLAYING;
            
            this.context.workspaceState.update('coachntt.audioQueue', state);
        } catch (error) {
            this.logger.error('Failed to save audio state', error);
        }
    }
    
    /**
     * Dispose service
     */
    public dispose(): void {
        this.stop();
        this.saveState();
        this.cache.dispose();
        
        if (this.statusBarItem) {
            this.statusBarItem.dispose();
        }
        
        this.removeAllListeners();
    }
}