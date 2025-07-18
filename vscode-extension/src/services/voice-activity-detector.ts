import { EventEmitter } from 'eventemitter3';
import { Logger } from '../utils/logger';

/**
 * Voice Activity Detection Configuration
 */
export interface VADConfig {
    // Energy threshold multiplier for speech detection
    energyThresholdMultiplier: number;
    // Number of frames to smooth detection
    smoothingFrames: number;
    // Pre-speech buffer duration in ms
    preSpeechBuffer: number;
    // Post-speech timeout in ms
    postSpeechTimeout: number;
    // Frame duration in ms
    frameDuration: number;
    // Minimum speech duration in ms
    minSpeechDuration: number;
    // Noise floor adaptation rate (0-1)
    noiseAdaptationRate: number;
}

/**
 * VAD State
 */
export interface VADState {
    isSpeaking: boolean;
    energy: number;
    noiseFloor: number;
    threshold: number;
    confidence: number;
}

/**
 * VAD Events
 */
export interface VADEventMap {
    speechStart: () => void;
    speechEnd: () => void;
    energyUpdate: (energy: number) => void;
    stateChange: (state: VADState) => void;
}

/**
 * Voice Activity Detector
 * 
 * Implements energy-based voice activity detection with
 * adaptive thresholds and smoothing.
 */
export class VoiceActivityDetector extends EventEmitter<VADEventMap> {
    private logger: Logger;
    private config: VADConfig;
    
    // Detection state
    private energy: number = 0;
    private noiseFloor: number = 0;
    private energyThreshold: number = 0;
    private isSpeaking: boolean = false;
    private speechFrames: number = 0;
    private silenceFrames: number = 0;
    
    // Buffers
    private energyHistory: number[] = [];
    private preSpeechBuffer: Float32Array[] = [];
    private isCalibrating: boolean = true;
    private calibrationFrames: number = 0;
    
    // Constants
    private readonly CALIBRATION_FRAMES = 50; // ~2 seconds at 40ms frames
    private readonly MAX_ENERGY_HISTORY = 100;
    private readonly PRE_SPEECH_FRAMES: number;
    private readonly POST_SPEECH_FRAMES: number;
    private readonly MIN_SPEECH_FRAMES: number;

    constructor(config: Partial<VADConfig> = {}) {
        super();
        this.logger = Logger.getInstance();
        
        // Default configuration
        this.config = {
            energyThresholdMultiplier: 1.5,
            smoothingFrames: 3,
            preSpeechBuffer: 300,
            postSpeechTimeout: 800,
            frameDuration: 40,
            minSpeechDuration: 200,
            noiseAdaptationRate: 0.01,
            ...config
        };
        
        // Calculate frame counts
        this.PRE_SPEECH_FRAMES = Math.ceil(this.config.preSpeechBuffer / this.config.frameDuration);
        this.POST_SPEECH_FRAMES = Math.ceil(this.config.postSpeechTimeout / this.config.frameDuration);
        this.MIN_SPEECH_FRAMES = Math.ceil(this.config.minSpeechDuration / this.config.frameDuration);
        
        this.logger.info('Voice Activity Detector initialized', { config: this.config });
    }

    /**
     * Process audio frame for voice activity
     */
    public processFrame(audioData: Float32Array): boolean {
        // Calculate frame energy
        this.energy = this.calculateEnergy(audioData);
        this.energyHistory.push(this.energy);
        
        // Limit history size
        if (this.energyHistory.length > this.MAX_ENERGY_HISTORY) {
            this.energyHistory.shift();
        }
        
        // Update pre-speech buffer
        this.updatePreSpeechBuffer(audioData);
        
        // Handle calibration phase
        if (this.isCalibrating) {
            this.calibrate();
            return false;
        }
        
        // Adapt noise floor during silence
        if (!this.isSpeaking && this.silenceFrames > this.POST_SPEECH_FRAMES) {
            this.adaptNoiseFloor();
        }
        
        // Detect speech
        const speechDetected = this.detectSpeech();
        
        // Update state
        this.updateState(speechDetected);
        
        // Emit events
        this.emit('energyUpdate', this.energy);
        this.emit('stateChange', this.getState());
        
        return this.isSpeaking;
    }

    /**
     * Calculate RMS energy of audio frame
     */
    private calculateEnergy(audioData: Float32Array): number {
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
            sum += audioData[i] * audioData[i];
        }
        return Math.sqrt(sum / audioData.length);
    }

    /**
     * Update pre-speech circular buffer
     */
    private updatePreSpeechBuffer(audioData: Float32Array): void {
        // Clone the audio data
        const frameCopy = new Float32Array(audioData);
        
        this.preSpeechBuffer.push(frameCopy);
        
        // Maintain buffer size
        if (this.preSpeechBuffer.length > this.PRE_SPEECH_FRAMES) {
            this.preSpeechBuffer.shift();
        }
    }

    /**
     * Calibrate noise floor during initial frames
     */
    private calibrate(): void {
        this.calibrationFrames++;
        
        if (this.calibrationFrames >= this.CALIBRATION_FRAMES) {
            // Calculate noise floor as average of calibration frames
            const sum = this.energyHistory.reduce((a, b) => a + b, 0);
            this.noiseFloor = sum / this.energyHistory.length;
            
            // Set initial threshold
            this.energyThreshold = this.noiseFloor * this.config.energyThresholdMultiplier;
            
            this.isCalibrating = false;
            this.logger.info('VAD calibration complete', {
                noiseFloor: this.noiseFloor,
                threshold: this.energyThreshold
            });
        }
    }

    /**
     * Adapt noise floor based on recent energy levels
     */
    private adaptNoiseFloor(): void {
        // Calculate recent average energy
        const recentFrames = Math.min(10, this.energyHistory.length);
        const recentEnergy = this.energyHistory
            .slice(-recentFrames)
            .reduce((a, b) => a + b, 0) / recentFrames;
        
        // Slowly adapt noise floor
        this.noiseFloor = (1 - this.config.noiseAdaptationRate) * this.noiseFloor +
                          this.config.noiseAdaptationRate * recentEnergy;
        
        // Update threshold
        this.energyThreshold = this.noiseFloor * this.config.energyThresholdMultiplier;
    }

    /**
     * Detect speech using energy and smoothing
     */
    private detectSpeech(): boolean {
        // Apply smoothing to reduce false positives
        const smoothedEnergy = this.getSmoothedEnergy();
        
        // Basic energy threshold detection
        const energyAboveThreshold = smoothedEnergy > this.energyThreshold;
        
        // Additional frequency-based detection could be added here
        // for more sophisticated VAD
        
        return energyAboveThreshold;
    }

    /**
     * Get smoothed energy over recent frames
     */
    private getSmoothedEnergy(): number {
        const framesToSmooth = Math.min(
            this.config.smoothingFrames,
            this.energyHistory.length
        );
        
        if (framesToSmooth === 0) {
            return this.energy;
        }
        
        const recentEnergy = this.energyHistory.slice(-framesToSmooth);
        const sum = recentEnergy.reduce((a, b) => a + b, 0);
        
        return sum / framesToSmooth;
    }

    /**
     * Update speech state with hysteresis
     */
    private updateState(speechDetected: boolean): void {
        if (speechDetected) {
            this.speechFrames++;
            this.silenceFrames = 0;
            
            // Start speech if enough consecutive frames
            if (!this.isSpeaking && this.speechFrames >= this.config.smoothingFrames) {
                this.startSpeech();
            }
        } else {
            this.silenceFrames++;
            this.speechFrames = 0;
            
            // End speech if enough silence
            if (this.isSpeaking && this.silenceFrames >= this.POST_SPEECH_FRAMES) {
                // Only end if speech was long enough
                if (this.speechFrames >= this.MIN_SPEECH_FRAMES) {
                    this.endSpeech();
                }
            }
        }
    }

    /**
     * Handle speech start
     */
    private startSpeech(): void {
        this.isSpeaking = true;
        this.logger.debug('Speech started');
        this.emit('speechStart');
    }

    /**
     * Handle speech end
     */
    private endSpeech(): void {
        this.isSpeaking = false;
        this.logger.debug('Speech ended');
        this.emit('speechEnd');
    }

    /**
     * Get pre-speech buffer
     */
    public getPreSpeechBuffer(): Float32Array[] {
        return [...this.preSpeechBuffer];
    }

    /**
     * Get current VAD state
     */
    public getState(): VADState {
        const confidence = this.calculateConfidence();
        
        return {
            isSpeaking: this.isSpeaking,
            energy: this.energy,
            noiseFloor: this.noiseFloor,
            threshold: this.energyThreshold,
            confidence
        };
    }

    /**
     * Calculate speech confidence (0-1)
     */
    private calculateConfidence(): number {
        if (this.isCalibrating) {
            return 0;
        }
        
        // Base confidence on energy ratio
        const energyRatio = this.energy / this.energyThreshold;
        
        // Clamp to 0-1 range
        const confidence = Math.max(0, Math.min(1, (energyRatio - 0.8) / 0.4));
        
        return confidence;
    }

    /**
     * Reset detector state
     */
    public reset(): void {
        this.energy = 0;
        this.noiseFloor = 0;
        this.energyThreshold = 0;
        this.isSpeaking = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
        this.energyHistory = [];
        this.preSpeechBuffer = [];
        this.isCalibrating = true;
        this.calibrationFrames = 0;
        
        this.logger.debug('VAD reset');
    }

    /**
     * Update configuration
     */
    public updateConfig(config: Partial<VADConfig>): void {
        this.config = { ...this.config, ...config };
        
        // Recalculate frame counts
        this.PRE_SPEECH_FRAMES = Math.ceil(this.config.preSpeechBuffer / this.config.frameDuration);
        this.POST_SPEECH_FRAMES = Math.ceil(this.config.postSpeechTimeout / this.config.frameDuration);
        this.MIN_SPEECH_FRAMES = Math.ceil(this.config.minSpeechDuration / this.config.frameDuration);
        
        this.logger.info('VAD config updated', { config: this.config });
    }

    /**
     * Dispose of resources
     */
    public dispose(): void {
        this.removeAllListeners();
        this.reset();
        this.logger.debug('Voice Activity Detector disposed');
    }
}