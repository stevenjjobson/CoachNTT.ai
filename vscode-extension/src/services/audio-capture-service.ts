import { EventEmitter } from 'eventemitter3';
import { Logger } from '../utils/logger';
import { VoiceActivityDetector, VADConfig } from './voice-activity-detector';
import { MCPClient } from './mcp-client';

/**
 * Audio Capture Configuration
 */
export interface AudioCaptureConfig {
    sampleRate: number;
    channels: number;
    echoCancellation: boolean;
    noiseSuppression: boolean;
    autoGainControl: boolean;
    bufferSize: number;
    streamingChunkSize: number;
    maxRecordingDuration: number; // in seconds
    vadConfig?: Partial<VADConfig>;
}

/**
 * Recording State
 */
export enum RecordingState {
    IDLE = 'idle',
    INITIALIZING = 'initializing',
    LISTENING = 'listening',
    RECORDING = 'recording',
    PROCESSING = 'processing',
    ERROR = 'error'
}

/**
 * Audio Capture Events
 */
export interface AudioCaptureEventMap {
    stateChange: (state: RecordingState) => void;
    audioData: (data: Float32Array) => void;
    recordingStart: () => void;
    recordingEnd: (audioBlob: Blob) => void;
    transcriptionResult: (text: string) => void;
    error: (error: Error) => void;
    levelUpdate: (level: number) => void;
    vadStateChange: (vadState: any) => void;
}

/**
 * Audio Capture Service
 * 
 * Manages WebRTC audio capture with streaming support,
 * voice activity detection, and MCP integration.
 */
export class AudioCaptureService extends EventEmitter<AudioCaptureEventMap> {
    private static instance: AudioCaptureService;
    private logger: Logger;
    private config: AudioCaptureConfig;
    
    // Audio context and nodes
    private audioContext: AudioContext | null = null;
    private mediaStream: MediaStream | null = null;
    private source: MediaStreamAudioSourceNode | null = null;
    private processor: ScriptProcessorNode | null = null;
    private analyser: AnalyserNode | null = null;
    
    // Recording state
    private state: RecordingState = RecordingState.IDLE;
    private recordingBuffer: Float32Array[] = [];
    private recordingStartTime: number = 0;
    private pushToTalkActive: boolean = false;
    
    // Voice activity detection
    private vad: VoiceActivityDetector;
    public vadEnabled: boolean = true;
    
    // Streaming
    private streamingBuffer: Float32Array[] = [];
    private streamingCallback?: (chunk: Float32Array) => void;
    
    // MCP integration
    private mcpClient: MCPClient;

    private constructor() {
        super();
        this.logger = Logger.getInstance();
        this.mcpClient = MCPClient.getInstance();
        
        // Default configuration
        this.config = {
            sampleRate: 16000,
            channels: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            bufferSize: 4096,
            streamingChunkSize: 8192,
            maxRecordingDuration: 30,
            vadConfig: {
                frameDuration: 40,
                energyThresholdMultiplier: 1.5,
                preSpeechBuffer: 300,
                postSpeechTimeout: 800
            }
        };
        
        // Initialize VAD
        this.vad = new VoiceActivityDetector(this.config.vadConfig);
        this.setupVADListeners();
        
        this.logger.info('Audio Capture Service initialized');
    }

    /**
     * Get singleton instance
     */
    public static getInstance(): AudioCaptureService {
        if (!AudioCaptureService.instance) {
            AudioCaptureService.instance = new AudioCaptureService();
        }
        return AudioCaptureService.instance;
    }

    /**
     * Setup VAD event listeners
     */
    private setupVADListeners(): void {
        this.vad.on('speechStart', () => {
            if (this.vadEnabled && this.state === RecordingState.LISTENING) {
                this.logger.debug('VAD: Speech detected, starting recording');
                this.startRecording();
            }
        });
        
        this.vad.on('speechEnd', () => {
            if (this.vadEnabled && this.state === RecordingState.RECORDING && !this.pushToTalkActive) {
                this.logger.debug('VAD: Speech ended, stopping recording');
                this.stopRecording();
            }
        });
        
        this.vad.on('stateChange', (state) => {
            this.emit('vadStateChange', state);
        });
        
        this.vad.on('energyUpdate', (energy) => {
            // Convert energy to normalized level (0-1)
            const level = Math.min(1, energy * 10);
            this.emit('levelUpdate', level);
        });
    }

    /**
     * Initialize audio capture
     */
    public async initialize(): Promise<void> {
        try {
            this.setState(RecordingState.INITIALIZING);
            
            // Create audio context
            this.audioContext = new AudioContext({
                sampleRate: this.config.sampleRate
            });
            
            // Get user media
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.config.sampleRate,
                    channelCount: this.config.channels,
                    echoCancellation: this.config.echoCancellation,
                    noiseSuppression: this.config.noiseSuppression,
                    autoGainControl: this.config.autoGainControl
                }
            });
            
            // Create audio nodes
            this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.processor = this.audioContext.createScriptProcessor(
                this.config.bufferSize,
                this.config.channels,
                this.config.channels
            );
            this.analyser = this.audioContext.createAnalyser();
            
            // Connect nodes
            this.source.connect(this.analyser);
            this.analyser.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            
            // Setup audio processing
            this.processor.onaudioprocess = (event) => {
                this.processAudioData(event);
            };
            
            this.setState(RecordingState.LISTENING);
            this.logger.info('Audio capture initialized successfully');
            
        } catch (error) {
            this.logger.error('Failed to initialize audio capture', error);
            this.setState(RecordingState.ERROR);
            this.emit('error', error as Error);
            throw error;
        }
    }

    /**
     * Process audio data from script processor
     */
    private processAudioData(event: AudioProcessingEvent): void {
        const inputData = event.inputBuffer.getChannelData(0);
        const audioData = new Float32Array(inputData);
        
        // Emit raw audio data
        this.emit('audioData', audioData);
        
        // Process with VAD
        if (this.vadEnabled) {
            this.vad.processFrame(audioData);
        }
        
        // Store in recording buffer if recording
        if (this.state === RecordingState.RECORDING) {
            this.recordingBuffer.push(audioData);
            
            // Check max duration
            const duration = (Date.now() - this.recordingStartTime) / 1000;
            if (duration >= this.config.maxRecordingDuration) {
                this.logger.warn('Max recording duration reached');
                this.stopRecording();
            }
        }
        
        // Handle streaming
        if (this.streamingCallback) {
            this.streamingBuffer.push(audioData);
            
            // Check if we have enough data to stream
            const totalSamples = this.streamingBuffer.reduce(
                (sum, chunk) => sum + chunk.length,
                0
            );
            
            if (totalSamples >= this.config.streamingChunkSize) {
                this.flushStreamingBuffer();
            }
        }
    }

    /**
     * Start recording
     */
    public startRecording(): void {
        if (this.state !== RecordingState.LISTENING) {
            this.logger.warn('Cannot start recording in current state', { state: this.state });
            return;
        }
        
        // Include pre-speech buffer if using VAD
        if (this.vadEnabled) {
            const preSpeechBuffer = this.vad.getPreSpeechBuffer();
            this.recordingBuffer = [...preSpeechBuffer];
        } else {
            this.recordingBuffer = [];
        }
        
        this.recordingStartTime = Date.now();
        this.setState(RecordingState.RECORDING);
        this.emit('recordingStart');
        
        this.logger.info('Recording started');
    }

    /**
     * Stop recording
     */
    public async stopRecording(): Promise<void> {
        if (this.state !== RecordingState.RECORDING) {
            this.logger.warn('Not currently recording');
            return;
        }
        
        this.setState(RecordingState.PROCESSING);
        
        try {
            // Convert recording buffer to blob
            const audioBlob = this.createAudioBlob(this.recordingBuffer);
            
            // Clear recording buffer
            this.recordingBuffer = [];
            
            // Emit recording end event
            this.emit('recordingEnd', audioBlob);
            
            // Transcribe if MCP is connected
            if (this.mcpClient.isConnected()) {
                await this.transcribeAudio(audioBlob);
            }
            
            this.setState(RecordingState.LISTENING);
            this.logger.info('Recording stopped');
            
        } catch (error) {
            this.logger.error('Error stopping recording', error);
            this.setState(RecordingState.ERROR);
            this.emit('error', error as Error);
        }
    }

    /**
     * Create audio blob from recording buffer
     */
    private createAudioBlob(buffer: Float32Array[]): Blob {
        // Calculate total length
        const totalLength = buffer.reduce((sum, chunk) => sum + chunk.length, 0);
        
        // Merge all chunks
        const mergedData = new Float32Array(totalLength);
        let offset = 0;
        
        for (const chunk of buffer) {
            mergedData.set(chunk, offset);
            offset += chunk.length;
        }
        
        // Convert to WAV format
        const wavData = this.encodeWAV(mergedData);
        
        return new Blob([wavData], { type: 'audio/wav' });
    }

    /**
     * Encode Float32Array to WAV format
     */
    private encodeWAV(samples: Float32Array): ArrayBuffer {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);
        
        // WAV header
        const writeString = (offset: number, string: string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, this.config.channels, true);
        view.setUint32(24, this.config.sampleRate, true);
        view.setUint32(28, this.config.sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, samples.length * 2, true);
        
        // Convert float samples to 16-bit PCM
        let offset = 44;
        for (let i = 0; i < samples.length; i++) {
            const sample = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(offset, sample * 0x7FFF, true);
            offset += 2;
        }
        
        return buffer;
    }

    /**
     * Transcribe audio using MCP
     */
    private async transcribeAudio(audioBlob: Blob): Promise<void> {
        try {
            // Convert blob to base64
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
            
            // Call MCP transcription tool
            const result = await this.mcpClient.callTool('audio_transcribe', {
                audio_data: base64,
                format: 'wav',
                sample_rate: this.config.sampleRate
            });
            
            if (result.transcription) {
                this.emit('transcriptionResult', result.transcription);
                this.logger.info('Transcription completed', { 
                    text: result.transcription.substring(0, 50) + '...' 
                });
            }
            
        } catch (error) {
            this.logger.error('Transcription failed', error);
            this.emit('error', error as Error);
        }
    }

    /**
     * Enable/disable VAD
     */
    public setVADEnabled(enabled: boolean): void {
        this.vadEnabled = enabled;
        this.logger.info('VAD enabled:', enabled);
    }

    /**
     * Start push-to-talk recording
     */
    public startPushToTalk(): void {
        this.pushToTalkActive = true;
        if (this.state === RecordingState.LISTENING) {
            this.startRecording();
        }
    }

    /**
     * Stop push-to-talk recording
     */
    public stopPushToTalk(): void {
        this.pushToTalkActive = false;
        if (this.state === RecordingState.RECORDING) {
            this.stopRecording();
        }
    }

    /**
     * Set streaming callback
     */
    public setStreamingCallback(callback: (chunk: Float32Array) => void | null): void {
        this.streamingCallback = callback || undefined;
        this.streamingBuffer = [];
    }

    /**
     * Flush streaming buffer
     */
    private flushStreamingBuffer(): void {
        if (!this.streamingCallback || this.streamingBuffer.length === 0) {
            return;
        }
        
        // Merge streaming buffer chunks
        const totalLength = this.streamingBuffer.reduce(
            (sum, chunk) => sum + chunk.length,
            0
        );
        const mergedData = new Float32Array(totalLength);
        
        let offset = 0;
        for (const chunk of this.streamingBuffer) {
            mergedData.set(chunk, offset);
            offset += chunk.length;
        }
        
        // Send to callback
        this.streamingCallback(mergedData);
        
        // Clear buffer
        this.streamingBuffer = [];
    }

    /**
     * Update configuration
     */
    public updateConfig(config: Partial<AudioCaptureConfig>): void {
        this.config = { ...this.config, ...config };
        
        if (config.vadConfig) {
            this.vad.updateConfig(config.vadConfig);
        }
        
        this.logger.info('Audio capture config updated', { config: this.config });
    }

    /**
     * Set recording state
     */
    private setState(state: RecordingState): void {
        const previousState = this.state;
        this.state = state;
        
        if (previousState !== state) {
            this.logger.debug('Recording state changed', { from: previousState, to: state });
            this.emit('stateChange', state);
        }
    }

    /**
     * Get current state
     */
    public getState(): RecordingState {
        return this.state;
    }

    /**
     * Check if recording
     */
    public isRecording(): boolean {
        return this.state === RecordingState.RECORDING;
    }

    /**
     * Cleanup audio resources
     */
    public async cleanup(): Promise<void> {
        try {
            // Stop any active recording
            if (this.state === RecordingState.RECORDING) {
                await this.stopRecording();
            }
            
            // Disconnect audio nodes
            if (this.processor) {
                this.processor.disconnect();
                this.processor.onaudioprocess = null;
                this.processor = null;
            }
            
            if (this.analyser) {
                this.analyser.disconnect();
                this.analyser = null;
            }
            
            if (this.source) {
                this.source.disconnect();
                this.source = null;
            }
            
            // Stop media stream
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }
            
            // Close audio context
            if (this.audioContext) {
                await this.audioContext.close();
                this.audioContext = null;
            }
            
            // Reset state
            this.setState(RecordingState.IDLE);
            this.recordingBuffer = [];
            this.streamingBuffer = [];
            
            this.logger.info('Audio capture cleaned up');
            
        } catch (error) {
            this.logger.error('Error during cleanup', error);
        }
    }

    /**
     * Dispose of service
     */
    public dispose(): void {
        this.cleanup();
        this.vad.dispose();
        this.removeAllListeners();
        this.logger.debug('Audio Capture Service disposed');
    }
}