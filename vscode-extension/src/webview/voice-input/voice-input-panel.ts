import * as vscode from 'vscode';
import { ManagedWebViewPanel } from '../managed-webview-panel';
import { MessageProtocol, WebViewMessage } from '../message-protocol';
import { AudioCaptureService, RecordingState } from '../../services/audio-capture-service';
import { Logger } from '../../utils/logger';

/**
 * Voice Input Panel Messages
 */
interface VoiceInputMessage extends WebViewMessage {
    command: 'startRecording' | 'stopRecording' | 'togglePushToTalk' | 
             'updateSettings' | 'requestState' | 'playAudio' | 'clearTranscription';
    data?: any;
}

/**
 * Voice Input Settings
 */
interface VoiceInputSettings {
    vadEnabled: boolean;
    pushToTalkKey: string;
    vadSensitivity: number;
    showWaveform: boolean;
    autoPlayback: boolean;
}

/**
 * Voice Input WebView Panel
 * 
 * Provides UI for voice recording with real-time waveform visualization,
 * VAD indicators, and transcription display.
 */
export class VoiceInputPanel extends ManagedWebViewPanel {
    private logger: Logger;
    private audioCapture: AudioCaptureService;
    private protocol: MessageProtocol<VoiceInputMessage>;
    private settings: VoiceInputSettings;
    private updateTimer?: NodeJS.Timer;
    private lastAudioBlob?: Blob;

    constructor(extensionPath: string) {
        super('voice-input', 'Voice Input', extensionPath);
        
        this.logger = Logger.getInstance();
        this.audioCapture = AudioCaptureService.getInstance();
        this.protocol = new MessageProtocol(this.logger);
        
        // Default settings
        this.settings = {
            vadEnabled: true,
            pushToTalkKey: 'Ctrl+Shift+V',
            vadSensitivity: 1.5,
            showWaveform: true,
            autoPlayback: false
        };
        
        this.setupAudioListeners();
    }

    /**
     * Setup audio capture event listeners
     */
    private setupAudioListeners(): void {
        // State changes
        this.audioCapture.on('stateChange', (state) => {
            this.sendMessage({
                command: 'stateUpdate',
                data: { state }
            });
            
            // Update panel title
            if (state === RecordingState.RECORDING) {
                this.updateTitle('Voice Input - Recording...');
            } else if (state === RecordingState.PROCESSING) {
                this.updateTitle('Voice Input - Processing...');
            } else {
                this.updateTitle('Voice Input');
            }
        });
        
        // Audio level updates
        this.audioCapture.on('levelUpdate', (level) => {
            this.sendMessage({
                command: 'levelUpdate',
                data: { level }
            });
        });
        
        // VAD state updates
        this.audioCapture.on('vadStateChange', (vadState) => {
            this.sendMessage({
                command: 'vadStateUpdate',
                data: vadState
            });
        });
        
        // Recording events
        this.audioCapture.on('recordingStart', () => {
            this.sendMessage({
                command: 'recordingStarted',
                data: {}
            });
        });
        
        this.audioCapture.on('recordingEnd', (audioBlob) => {
            this.lastAudioBlob = audioBlob;
            
            // Convert blob to base64 for WebView
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64 = reader.result as string;
                this.sendMessage({
                    command: 'recordingEnded',
                    data: { 
                        audioData: base64,
                        duration: audioBlob.size / (16000 * 2) // Approximate duration
                    }
                });
            };
            reader.readAsDataURL(audioBlob);
        });
        
        // Transcription results
        this.audioCapture.on('transcriptionResult', (text) => {
            this.sendMessage({
                command: 'transcriptionResult',
                data: { text }
            });
            
            // Show notification
            vscode.window.showInformationMessage(`Transcription: ${text.substring(0, 50)}...`);
        });
        
        // Errors
        this.audioCapture.on('error', (error) => {
            this.sendMessage({
                command: 'error',
                data: { 
                    message: error.message,
                    type: 'capture'
                }
            });
            
            vscode.window.showErrorMessage(`Voice input error: ${error.message}`);
        });
    }

    /**
     * Get HTML content for the WebView
     */
    protected getHtmlContent(): string {
        const nonce = this.getNonce();
        const baseUri = this.panel.webview.asWebviewUri(
            vscode.Uri.joinPath(this.extensionPath, 'media')
        );
        
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; 
        style-src ${this.panel.webview.cspSource} 'unsafe-inline'; 
        script-src 'nonce-${nonce}';
        img-src ${this.panel.webview.cspSource} data:;
        font-src ${this.panel.webview.cspSource};
        media-src ${this.panel.webview.cspSource} blob: data:;">
    <link href="${baseUri}/vscode.css" rel="stylesheet">
    <link href="${baseUri}/webview.css" rel="stylesheet">
    <link href="${baseUri}/voice-input.css" rel="stylesheet">
    <title>Voice Input</title>
</head>
<body>
    <div class="voice-input-container">
        <!-- Header -->
        <div class="header">
            <h2>Voice Input</h2>
            <div class="status-indicator" id="statusIndicator">
                <span class="status-dot"></span>
                <span class="status-text">Ready</span>
            </div>
        </div>
        
        <!-- Waveform Visualization -->
        <div class="waveform-container" id="waveformContainer">
            <canvas id="waveformCanvas"></canvas>
            <div class="audio-level-bar">
                <div class="audio-level-fill" id="audioLevelFill"></div>
            </div>
        </div>
        
        <!-- VAD Indicator -->
        <div class="vad-indicator" id="vadIndicator">
            <div class="vad-status">
                <span class="vad-label">Voice Activity:</span>
                <span class="vad-value" id="vadStatus">Inactive</span>
            </div>
            <div class="vad-metrics">
                <div class="metric">
                    <span class="metric-label">Energy:</span>
                    <span class="metric-value" id="energyValue">0.00</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Threshold:</span>
                    <span class="metric-value" id="thresholdValue">0.00</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Confidence:</span>
                    <span class="metric-value" id="confidenceValue">0%</span>
                </div>
            </div>
        </div>
        
        <!-- Recording Controls -->
        <div class="controls">
            <button class="control-button record-button" id="recordButton">
                <span class="icon">🎤</span>
                <span class="label">Start Recording</span>
            </button>
            
            <button class="control-button push-to-talk-button" id="pushToTalkButton">
                <span class="icon">🎙️</span>
                <span class="label">Push to Talk</span>
            </button>
            
            <div class="control-group">
                <label class="switch">
                    <input type="checkbox" id="vadToggle" checked>
                    <span class="slider"></span>
                </label>
                <span class="control-label">Voice Activity Detection</span>
            </div>
        </div>
        
        <!-- Transcription Display -->
        <div class="transcription-container" id="transcriptionContainer">
            <div class="transcription-header">
                <h3>Transcription</h3>
                <button class="clear-button" id="clearButton">Clear</button>
            </div>
            <div class="transcription-content" id="transcriptionContent">
                <p class="placeholder">Start recording to see transcription...</p>
            </div>
        </div>
        
        <!-- Audio Playback -->
        <div class="playback-container" id="playbackContainer" style="display: none;">
            <audio id="audioPlayer" controls></audio>
        </div>
        
        <!-- Settings -->
        <div class="settings-container">
            <details>
                <summary>Settings</summary>
                <div class="settings-content">
                    <div class="setting-item">
                        <label for="sensitivitySlider">VAD Sensitivity:</label>
                        <input type="range" id="sensitivitySlider" 
                               min="0.5" max="3" step="0.1" value="1.5">
                        <span id="sensitivityValue">1.5</span>
                    </div>
                    
                    <div class="setting-item">
                        <label class="checkbox-label">
                            <input type="checkbox" id="waveformToggle" checked>
                            Show Waveform
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label class="checkbox-label">
                            <input type="checkbox" id="autoPlaybackToggle">
                            Auto-playback recordings
                        </label>
                    </div>
                    
                    <div class="setting-item">
                        <label>Push-to-talk key:</label>
                        <code id="pushToTalkKey">Ctrl+Shift+V</code>
                    </div>
                </div>
            </details>
        </div>
    </div>
    
    <script nonce="${nonce}" src="${baseUri}/voice-input.js"></script>
</body>
</html>`;
    }

    /**
     * Setup message handlers
     */
    protected setupMessageHandlers(): void {
        this.protocol.onMessage(this.panel.webview, async (message) => {
            switch (message.command) {
                case 'startRecording':
                    await this.handleStartRecording();
                    break;
                    
                case 'stopRecording':
                    await this.handleStopRecording();
                    break;
                    
                case 'togglePushToTalk':
                    this.handleTogglePushToTalk(message.data?.active);
                    break;
                    
                case 'updateSettings':
                    this.handleUpdateSettings(message.data);
                    break;
                    
                case 'requestState':
                    this.sendCurrentState();
                    break;
                    
                case 'playAudio':
                    // Audio playback is handled in the WebView
                    break;
                    
                case 'clearTranscription':
                    // Clear is handled in the WebView
                    break;
                    
                default:
                    this.logger.warn('Unknown voice input command:', message.command);
            }
        });
    }

    /**
     * Handle start recording
     */
    private async handleStartRecording(): Promise<void> {
        try {
            // Initialize if needed
            const state = this.audioCapture.getState();
            if (state === RecordingState.IDLE) {
                await this.audioCapture.initialize();
            }
            
            // Start recording
            this.audioCapture.startRecording();
            
        } catch (error) {
            this.logger.error('Failed to start recording', error);
            this.sendMessage({
                command: 'error',
                data: {
                    message: 'Failed to start recording: ' + (error as Error).message,
                    type: 'start'
                }
            });
        }
    }

    /**
     * Handle stop recording
     */
    private async handleStopRecording(): Promise<void> {
        try {
            await this.audioCapture.stopRecording();
        } catch (error) {
            this.logger.error('Failed to stop recording', error);
            this.sendMessage({
                command: 'error',
                data: {
                    message: 'Failed to stop recording: ' + (error as Error).message,
                    type: 'stop'
                }
            });
        }
    }

    /**
     * Handle push-to-talk toggle
     */
    private handleTogglePushToTalk(active: boolean): void {
        if (active) {
            this.audioCapture.startPushToTalk();
        } else {
            this.audioCapture.stopPushToTalk();
        }
    }

    /**
     * Handle settings update
     */
    private handleUpdateSettings(settings: Partial<VoiceInputSettings>): void {
        this.settings = { ...this.settings, ...settings };
        
        // Apply VAD settings
        if (settings.vadEnabled !== undefined) {
            this.audioCapture.setVADEnabled(settings.vadEnabled);
        }
        
        if (settings.vadSensitivity !== undefined) {
            this.audioCapture.updateConfig({
                vadConfig: {
                    energyThresholdMultiplier: settings.vadSensitivity
                }
            });
        }
        
        this.logger.info('Voice input settings updated', this.settings);
    }

    /**
     * Send current state to WebView
     */
    private sendCurrentState(): void {
        this.sendMessage({
            command: 'stateUpdate',
            data: {
                state: this.audioCapture.getState(),
                settings: this.settings,
                isConnected: true
            }
        });
    }

    /**
     * Send message to WebView
     */
    private sendMessage(message: any): void {
        if (this.panel && this.panel.visible) {
            this.protocol.sendMessage(this.panel.webview, message);
        }
    }

    /**
     * Start periodic updates
     */
    private startPeriodicUpdates(): void {
        // Stop any existing timer
        this.stopPeriodicUpdates();
        
        // Send updates every 100ms when visible
        this.updateTimer = setInterval(() => {
            if (this.panel && this.panel.visible) {
                // Updates are now event-driven
            }
        }, 100);
    }

    /**
     * Stop periodic updates
     */
    private stopPeriodicUpdates(): void {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = undefined;
        }
    }

    /**
     * Handle panel visibility change
     */
    protected onDidChangeViewState(visible: boolean): void {
        if (visible) {
            this.startPeriodicUpdates();
            this.sendCurrentState();
        } else {
            this.stopPeriodicUpdates();
        }
    }

    /**
     * Dispose of resources
     */
    public dispose(): void {
        this.stopPeriodicUpdates();
        
        // Don't dispose audio capture service (it's a singleton)
        // Just remove our listeners
        this.audioCapture.removeAllListeners();
        
        super.dispose();
    }
}