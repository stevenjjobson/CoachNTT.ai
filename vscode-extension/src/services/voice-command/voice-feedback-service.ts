import { AudioPlaybackService } from '../audio-playback-service';
import { Logger } from '../../utils/logger';
import * as vscode from 'vscode';

export interface FeedbackOptions {
    priority?: 'high' | 'normal' | 'low';
    visual?: boolean;
    audio?: boolean;
    duration?: number;
}

export class VoiceFeedbackService {
    private logger: Logger;
    private audioService: AudioPlaybackService;
    private defaultOptions: FeedbackOptions = {
        priority: 'normal',
        visual: true,
        audio: true,
        duration: 3000
    };
    private soundEffects: Map<string, string> = new Map();

    constructor(audioService: AudioPlaybackService) {
        this.logger = Logger.getInstance();
        this.audioService = audioService;
        this.initializeSoundEffects();
    }

    private initializeSoundEffects(): void {
        // Map feedback types to sound effect descriptions
        this.soundEffects.set('success', 'short pleasant chime');
        this.soundEffects.set('error', 'short error buzz');
        this.soundEffects.set('info', 'soft notification ping');
        this.soundEffects.set('listening', 'rising tone');
        this.soundEffects.set('processing', 'thinking sound');
    }

    public async speak(
        text: string, 
        options: FeedbackOptions = {}
    ): Promise<void> {
        const opts = { ...this.defaultOptions, ...options };

        // Visual feedback
        if (opts.visual) {
            this.showVisualFeedback(text, 'info', opts.duration);
        }

        // Audio feedback
        if (opts.audio) {
            try {
                await this.audioService.synthesizeAndPlay(text, {
                    priority: opts.priority === 'high' ? 100 : 
                             opts.priority === 'low' ? 1 : 50
                });
            } catch (error) {
                this.logger.error('Failed to provide audio feedback', error);
            }
        }
    }

    public async confirmSuccess(
        message: string = 'Command executed successfully',
        options: FeedbackOptions = {}
    ): Promise<void> {
        const opts = { ...this.defaultOptions, ...options };

        // Play success sound
        if (opts.audio) {
            await this.playSound('success');
        }

        // Show success message
        if (opts.visual) {
            this.showVisualFeedback(message, 'success', opts.duration);
        }

        // Speak success message if longer than a few words
        if (opts.audio && message.split(' ').length > 3) {
            await this.speak(message, { ...opts, visual: false });
        }
    }

    public async reportError(
        message: string = 'Command failed',
        options: FeedbackOptions = {}
    ): Promise<void> {
        const opts = { ...this.defaultOptions, ...options, priority: 'high' as const };

        // Play error sound
        if (opts.audio) {
            await this.playSound('error');
        }

        // Show error message
        if (opts.visual) {
            this.showVisualFeedback(message, 'error', opts.duration);
        }

        // Always speak error messages
        if (opts.audio) {
            await this.speak(message, { ...opts, visual: false });
        }
    }

    public async provideInfo(
        message: string,
        options: FeedbackOptions = {}
    ): Promise<void> {
        const opts = { ...this.defaultOptions, ...options };

        // Play info sound
        if (opts.audio) {
            await this.playSound('info');
        }

        // Show and speak message
        await this.speak(message, opts);
    }

    public async indicateListening(start: boolean = true): Promise<void> {
        if (start) {
            await this.playSound('listening');
            this.showVisualFeedback('Listening...', 'info', 0); // Persistent
        } else {
            // Clear listening indicator
            vscode.window.setStatusBarMessage('', 0);
        }
    }

    public async indicateProcessing(start: boolean = true): Promise<void> {
        if (start) {
            await this.playSound('processing');
            this.showVisualFeedback('Processing command...', 'info', 0); // Persistent
        } else {
            // Clear processing indicator
            vscode.window.setStatusBarMessage('', 0);
        }
    }

    private async playSound(type: string): Promise<void> {
        const soundDescription = this.soundEffects.get(type);
        if (!soundDescription) {
            return;
        }

        try {
            // Generate a short sound effect using TTS
            // In a real implementation, we'd use actual sound files
            await this.audioService.synthesizeAndPlay(`[${soundDescription}]`, {
                priority: 100,
                volume: 0.5,
                speed: 1.5
            });
        } catch (error) {
            this.logger.debug(`Failed to play sound effect: ${type}`, error);
        }
    }

    private showVisualFeedback(
        message: string, 
        type: 'success' | 'error' | 'info',
        duration: number
    ): void {
        switch (type) {
            case 'success':
                if (duration === 0) {
                    vscode.window.setStatusBarMessage(`$(check) ${message}`);
                } else {
                    vscode.window.setStatusBarMessage(`$(check) ${message}`, duration);
                }
                break;
            case 'error':
                vscode.window.showErrorMessage(message);
                break;
            case 'info':
            default:
                if (duration === 0) {
                    vscode.window.setStatusBarMessage(`$(info) ${message}`);
                } else {
                    vscode.window.setStatusBarMessage(`$(info) ${message}`, duration);
                }
                break;
        }
    }

    public async provideCommandSuggestions(suggestions: string[]): Promise<void> {
        if (suggestions.length === 0) {
            return;
        }

        const message = suggestions.length === 1 
            ? `Did you mean: ${suggestions[0]}?`
            : `Did you mean one of these: ${suggestions.slice(0, 3).join(', ')}?`;

        await this.provideInfo(message, {
            priority: 'normal',
            duration: 5000
        });
    }

    public async requestConfirmation(
        action: string,
        details?: string
    ): Promise<void> {
        const message = details 
            ? `Confirm ${action}: ${details}`
            : `Please confirm: ${action}`;

        await this.speak(message, {
            priority: 'high',
            visual: true,
            duration: 0 // Persistent until action taken
        });
    }

    public clearFeedback(): void {
        vscode.window.setStatusBarMessage('', 0);
    }
}