/**
 * Audio Player WebView Panel
 * 
 * Rich UI panel for audio playback with:
 * - Full playback controls
 * - Queue visualization
 * - Volume/speed controls
 * - Progress tracking
 * - Real-time updates
 */

import * as vscode from 'vscode';
import { ManagedWebViewPanel } from '../webview-manager';
import { MessageProtocol } from '../message-protocol';
import { BaseTemplate } from '../templates/base-template';
import { AudioPlaybackService, PlaybackState } from '../../services/audio-playback-service';
import { AudioItem } from '../../models/audio-queue';
import { Logger } from '../../utils/logger';

/**
 * Audio player panel state
 */
interface AudioPlayerPanelState {
    queue: AudioItem[];
    currentItemId?: string;
    playbackState: PlaybackState;
    volume: number;
    speed: number;
    lastUpdated: number;
}

/**
 * Audio Player WebView Panel
 */
export class AudioPlayerPanel extends ManagedWebViewPanel {
    private protocol: MessageProtocol;
    private audioService: AudioPlaybackService;
    
    constructor(
        panel: vscode.WebviewPanel,
        context: vscode.ExtensionContext,
        logger: Logger,
        audioService: AudioPlaybackService
    ) {
        super(panel, context, logger);
        this.audioService = audioService;
        
        // Initialize message protocol
        this.protocol = new MessageProtocol(
            message => this.panel.webview.postMessage(message),
            content => this.abstractContent(content)
        );
        
        // Set up protocol handlers
        this.setupProtocolHandlers();
        
        // Set up audio service listeners
        this.setupAudioServiceListeners();
        
        // Initial render
        this.render();
        
        // Send initial state
        this.sendInitialState();
    }
    
    /**
     * Abstract content for safety
     */
    private abstractContent(content: string): string {
        content = content.replace(/([A-Za-z]:)?[\\/\\\\][\\w\\s-]+[\\/\\\\][\\w\\s-]+\.(ts|js|json|py|md|audio|mp3|wav)/g, '<project>/<module>/<file>');
        content = content.replace(/([A-Za-z]:)?[\\/\\\\][\\w\\s-]+[\\/\\\\]/g, '<directory>/');
        content = content.replace(/https?:\/\/[^\s]+/g, '<url>');
        content = content.replace(/ws:\/\/[^\s]+/g, '<websocket_url>');
        content = content.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '<ip_address>');
        content = content.replace(/[A-Za-z0-9]{32,}/g, '<token>');
        content = content.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, '<uuid>');
        return content;
    }
    
    /**
     * Set up message protocol handlers
     */
    private setupProtocolHandlers(): void {
        // Playback controls
        this.protocol.onRequest('play', async (params: { itemId?: string }) => {
            if (params.itemId) {
                await this.audioService.play(params.itemId);
            } else {
                await this.audioService.play();
            }
        });
        
        this.protocol.onRequest('pause', async () => {
            this.audioService.pause();
        });
        
        this.protocol.onRequest('stop', async () => {
            this.audioService.stop();
        });
        
        this.protocol.onRequest('next', async () => {
            await this.audioService.next();
        });
        
        this.protocol.onRequest('previous', async () => {
            await this.audioService.previous();
        });
        
        // Seek control
        this.protocol.onRequest('seek', async (params: { position: number }) => {
            this.audioService.seek(params.position);
        });
        
        // Volume control
        this.protocol.onRequest('setVolume', async (params: { volume: number }) => {
            this.audioService.setVolume(params.volume);
        });
        
        // Speed control
        this.protocol.onRequest('setSpeed', async (params: { speed: number }) => {
            this.audioService.setSpeed(params.speed);
        });
        
        // Queue management
        this.protocol.onRequest('removeFromQueue', async (params: { itemId: string }) => {
            this.audioService.removeFromQueue(params.itemId);
        });
        
        this.protocol.onRequest('clearQueue', async () => {
            this.audioService.clearQueue();
        });
        
        this.protocol.onRequest('clearCompleted', async () => {
            const count = this.audioService.clearCompleted();
            return { count };
        });
        
        this.protocol.onRequest('reorderQueue', async (params: { itemId: string; newIndex: number }) => {
            const success = this.audioService.reorderQueue(params.itemId, params.newIndex);
            return { success };
        });
        
        // Get current state
        this.protocol.onRequest('getState', async () => {
            return {
                queue: this.audioService.getQueue(),
                currentItem: this.audioService.getCurrentItem(),
                playbackState: this.audioService.getState(),
                volume: this.audioService.getVolume(),
                speed: this.audioService.getSpeed(),
                stats: {
                    queue: this.audioService.getQueueStats(),
                    cache: this.audioService.getCacheStats()
                }
            };
        });
        
        // Audio element events from WebView
        this.protocol.onRequest('audioProgress', async (params: { itemId: string; currentTime: number; duration: number }) => {
            const progress = params.duration > 0 ? params.currentTime / params.duration : 0;
            this.audioService.emit('webview:progress', {
                itemId: params.itemId,
                progress,
                duration: params.duration
            });
        });
        
        this.protocol.onRequest('audioEnded', async (params: { itemId: string }) => {
            this.audioService.emit('webview:ended', { itemId: params.itemId });
        });
        
        this.protocol.onRequest('audioError', async (params: { itemId: string; error: string }) => {
            this.audioService.emit('webview:error', {
                itemId: params.itemId,
                error: this.abstractContent(params.error)
            });
        });
    }
    
    /**
     * Set up audio service listeners
     */
    private setupAudioServiceListeners(): void {
        // State changes
        this.disposables.push(
            this.audioService.on('stateChanged', (state: PlaybackState) => {
                this.protocol.sendEvent('stateChanged', { state });
            })
        );
        
        // Item changes
        this.disposables.push(
            this.audioService.on('itemChanged', (item: AudioItem | undefined) => {
                this.protocol.sendEvent('itemChanged', { item: item ? this.sanitizeItem(item) : undefined });
            })
        );
        
        // Queue changes
        this.disposables.push(
            this.audioService.on('queueChanged', (items: ReadonlyArray<AudioItem>) => {
                this.protocol.sendEvent('queueChanged', { 
                    items: items.map(item => this.sanitizeItem(item))
                });
            })
        );
        
        // Progress changes
        this.disposables.push(
            this.audioService.on('progressChanged', (progress: number, duration: number) => {
                this.protocol.sendEvent('progressChanged', { progress, duration });
            })
        );
        
        // Volume changes
        this.disposables.push(
            this.audioService.on('volumeChanged', (volume: number) => {
                this.protocol.sendEvent('volumeChanged', { volume });
            })
        );
        
        // Speed changes
        this.disposables.push(
            this.audioService.on('speedChanged', (speed: number) => {
                this.protocol.sendEvent('speedChanged', { speed });
            })
        );
        
        // WebView commands from service
        this.disposables.push(
            this.audioService.on('webview:command', (command: any) => {
                this.protocol.sendCommand(command.command, command.data);
            })
        );
    }
    
    /**
     * Send initial state to WebView
     */
    private sendInitialState(): void {
        const state = {
            queue: this.audioService.getQueue().map(item => this.sanitizeItem(item)),
            currentItem: this.audioService.getCurrentItem(),
            playbackState: this.audioService.getState(),
            volume: this.audioService.getVolume(),
            speed: this.audioService.getSpeed()
        };
        
        this.protocol.sendEvent('initialState', state);
    }
    
    /**
     * Sanitize audio item for display
     */
    private sanitizeItem(item: AudioItem): AudioItem {
        return {
            ...item,
            content: this.abstractContent(item.content.substring(0, 200)),
            audioUrl: item.audioUrl ? this.abstractContent(item.audioUrl) : undefined,
            error: item.error ? this.abstractContent(item.error) : undefined,
            metadata: {
                ...item.metadata,
                title: this.abstractContent(item.metadata.title),
                description: item.metadata.description ? this.abstractContent(item.metadata.description) : undefined,
                abstractedPath: item.metadata.abstractedPath || '<audio_file>'
            }
        };
    }
    
    /**
     * Render the WebView content
     */
    private render(): void {
        const styleUri = this.getResourceUri('media/audio-player.css');
        const scriptUri = this.getResourceUri('media/audio-player.js');
        const webviewUri = this.getResourceUri('media/webview.css');
        
        const html = BaseTemplate.generateHTML({
            title: 'Audio Player',
            nonce: this.nonce,
            styleUris: [webviewUri, styleUri],
            scriptUris: [scriptUri],
            inlineStyles: this.getInlineStyles(),
            bodyContent: this.getBodyContent()
        });
        
        this.updateContent(html);
    }
    
    /**
     * Get inline styles
     */
    private getInlineStyles(): string {
        return `
            .audio-player {
                display: flex;
                flex-direction: column;
                height: 100vh;
                overflow: hidden;
            }
            
            .player-header {
                padding: 20px;
                background-color: var(--vscode-editor-background);
                border-bottom: 1px solid var(--vscode-panel-border);
            }
            
            .player-controls {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 20px;
                margin: 20px 0;
            }
            
            .control-button {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .control-button:hover {
                background-color: var(--vscode-button-hoverBackground);
            }
            
            .control-button.primary {
                width: 50px;
                height: 50px;
                background-color: var(--vscode-button-background);
                color: var(--vscode-button-foreground);
            }
            
            .progress-container {
                margin: 20px 0;
            }
            
            .progress-bar {
                width: 100%;
                height: 4px;
                background-color: var(--vscode-progressBar-background);
                border-radius: 2px;
                cursor: pointer;
                position: relative;
            }
            
            .progress-fill {
                height: 100%;
                background-color: var(--vscode-progressBar-foreground);
                border-radius: 2px;
                transition: width 0.1s;
            }
            
            .time-display {
                display: flex;
                justify-content: space-between;
                margin-top: 5px;
                font-size: 0.9em;
                color: var(--vscode-descriptionForeground);
            }
            
            .volume-speed-controls {
                display: flex;
                gap: 30px;
                justify-content: center;
                margin: 20px 0;
            }
            
            .slider-control {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .slider {
                width: 100px;
                -webkit-appearance: none;
                appearance: none;
                height: 4px;
                background: var(--vscode-input-background);
                outline: none;
                cursor: pointer;
            }
            
            .slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 12px;
                height: 12px;
                background: var(--vscode-button-background);
                cursor: pointer;
                border-radius: 50%;
            }
            
            .queue-container {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
            }
            
            .queue-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            
            .queue-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            
            .queue-item {
                padding: 10px;
                margin-bottom: 5px;
                background-color: var(--vscode-list-hoverBackground);
                border-radius: 5px;
                display: flex;
                align-items: center;
                gap: 10px;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .queue-item:hover {
                background-color: var(--vscode-list-activeSelectionBackground);
            }
            
            .queue-item.current {
                background-color: var(--vscode-list-activeSelectionBackground);
                color: var(--vscode-list-activeSelectionForeground);
            }
            
            .queue-item-status {
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .queue-item-content {
                flex: 1;
                overflow: hidden;
            }
            
            .queue-item-title {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .queue-item-meta {
                font-size: 0.85em;
                color: var(--vscode-descriptionForeground);
            }
            
            .queue-item-actions {
                opacity: 0;
                transition: opacity 0.2s;
            }
            
            .queue-item:hover .queue-item-actions {
                opacity: 1;
            }
            
            .empty-queue {
                text-align: center;
                padding: 40px;
                color: var(--vscode-descriptionForeground);
            }
        `;
    }
    
    /**
     * Get body content
     */
    private getBodyContent(): string {
        return `
            <div class="audio-player">
                <div class="player-header">
                    <h2>Audio Player</h2>
                    
                    <div class="current-track">
                        <div id="current-title">No track selected</div>
                        <div id="current-meta" class="queue-item-meta"></div>
                    </div>
                    
                    <div class="player-controls">
                        <button class="control-button" onclick="handleAction('previous')" title="Previous">
                            <span class="codicon codicon-debug-step-back"></span>
                        </button>
                        
                        <button id="play-pause-btn" class="control-button primary" onclick="handleAction('togglePlayback')" title="Play/Pause">
                            <span class="codicon codicon-play"></span>
                        </button>
                        
                        <button class="control-button" onclick="handleAction('next')" title="Next">
                            <span class="codicon codicon-debug-step-over"></span>
                        </button>
                        
                        <button class="control-button" onclick="handleAction('stop')" title="Stop">
                            <span class="codicon codicon-debug-stop"></span>
                        </button>
                    </div>
                    
                    <div class="progress-container">
                        <div class="progress-bar" onclick="handleSeek(event)">
                            <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
                        </div>
                        <div class="time-display">
                            <span id="current-time">0:00</span>
                            <span id="total-time">0:00</span>
                        </div>
                    </div>
                    
                    <div class="volume-speed-controls">
                        <div class="slider-control">
                            <span class="codicon codicon-unmute"></span>
                            <input type="range" id="volume-slider" class="slider" 
                                   min="0" max="100" value="100" 
                                   oninput="handleVolumeChange(this.value)">
                            <span id="volume-value">100%</span>
                        </div>
                        
                        <div class="slider-control">
                            <span class="codicon codicon-dashboard"></span>
                            <input type="range" id="speed-slider" class="slider" 
                                   min="50" max="200" value="100" step="10"
                                   oninput="handleSpeedChange(this.value)">
                            <span id="speed-value">1.0x</span>
                        </div>
                    </div>
                </div>
                
                <div class="queue-container">
                    <div class="queue-header">
                        <h3>Queue (<span id="queue-count">0</span>)</h3>
                        <div>
                            <button onclick="handleAction('clearCompleted')" title="Clear completed">
                                <span class="codicon codicon-clear-all"></span> Clear Completed
                            </button>
                            <button onclick="handleAction('clearQueue')" title="Clear all">
                                <span class="codicon codicon-trash"></span> Clear All
                            </button>
                        </div>
                    </div>
                    
                    <ul id="queue-list" class="queue-list">
                        <li class="empty-queue">
                            <span class="codicon codicon-music"></span>
                            <p>No items in queue</p>
                            <p>Add audio from memories or AI responses</p>
                        </li>
                    </ul>
                </div>
                
                <!-- Hidden audio element -->
                <audio id="audio-element" style="display: none;"></audio>
            </div>
        `;
    }
    
    /**
     * Handle incoming messages
     */
    protected handleMessage(message: any): void {
        this.protocol.handleMessage(message);
    }
    
    /**
     * Get panel state for persistence
     */
    protected getPanelState(): AudioPlayerPanelState {
        return {
            queue: this.audioService.getQueue() as AudioItem[],
            currentItemId: this.audioService.getCurrentItem()?.id,
            playbackState: this.audioService.getState(),
            volume: this.audioService.getVolume(),
            speed: this.audioService.getSpeed(),
            lastUpdated: Date.now()
        };
    }
    
    /**
     * Restore panel state
     */
    public restoreState(state: AudioPlayerPanelState): void {
        // State is managed by AudioPlaybackService
        this.sendInitialState();
    }
    
    /**
     * Dispose resources
     */
    public dispose(): void {
        this.disposables.forEach(d => d.dispose());
        this.protocol.dispose();
        super.dispose();
    }
}