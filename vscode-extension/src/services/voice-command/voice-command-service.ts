import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { Logger } from '../../utils/logger';
import { AudioCaptureService } from '../audio-capture-service';
import { AudioPlaybackService } from '../audio-playback-service';
import { CommandParser } from './command-parser';
import { VoiceCommandRegistry } from './voice-command-registry';
import { CommandRouter } from './command-router';
import { VoiceFeedbackService } from './voice-feedback-service';

export interface VoiceCommandEvent {
    transcription: string;
    command?: ParsedCommand;
    result?: CommandResult;
    error?: Error;
}

export interface ParsedCommand {
    intent: string;
    action: string;
    target?: string;
    parameters?: Record<string, any>;
    confidence: number;
    raw: string;
}

export interface CommandResult {
    success: boolean;
    message?: string;
    data?: any;
    requiresConfirmation?: boolean;
}

export class VoiceCommandService extends EventEmitter {
    private static instance: VoiceCommandService;
    private logger: Logger;
    private audioCapture: AudioCaptureService;
    private audioPlayback: AudioPlaybackService;
    private parser: CommandParser;
    private registry: VoiceCommandRegistry;
    private router: CommandRouter;
    private feedback: VoiceFeedbackService;
    private isEnabled: boolean = false;
    private commandHistory: ParsedCommand[] = [];
    private maxHistorySize: number = 50;

    private constructor() {
        super();
        this.logger = Logger.getInstance();
        this.audioCapture = AudioCaptureService.getInstance();
        this.audioPlayback = AudioPlaybackService.getInstance();
        this.parser = new CommandParser();
        this.registry = new VoiceCommandRegistry();
        this.router = new CommandRouter(this.registry);
        this.feedback = new VoiceFeedbackService(this.audioPlayback);
        
        this.initialize();
    }

    public static getInstance(): VoiceCommandService {
        if (!VoiceCommandService.instance) {
            VoiceCommandService.instance = new VoiceCommandService();
        }
        return VoiceCommandService.instance;
    }

    private initialize(): void {
        // Listen for transcription results
        this.audioCapture.on('transcriptionComplete', (result: any) => {
            if (this.isEnabled && result.text) {
                this.processTranscription(result.text);
            }
        });

        // Register default commands
        this.registerDefaultCommands();
    }

    public enable(): void {
        this.isEnabled = true;
        this.logger.info('Voice commands enabled');
        this.feedback.speak('Voice commands activated');
    }

    public disable(): void {
        this.isEnabled = false;
        this.logger.info('Voice commands disabled');
        this.feedback.speak('Voice commands deactivated');
    }

    public async processTranscription(text: string): Promise<void> {
        this.logger.info(`Processing voice command: "${text}"`);
        
        const event: VoiceCommandEvent = { transcription: text };
        this.emit('commandReceived', event);

        try {
            // Parse the command
            const command = await this.parser.parse(text);
            event.command = command;

            if (!command || command.confidence < 0.5) {
                throw new Error('Could not understand command');
            }

            // Log to history
            this.addToHistory(command);

            // Execute the command
            const result = await this.router.execute(command);
            event.result = result;

            if (result.success) {
                this.feedback.confirmSuccess(result.message || 'Command executed');
                this.emit('commandExecuted', event);
            } else {
                this.feedback.reportError(result.message || 'Command failed');
                this.emit('commandFailed', event);
            }

        } catch (error) {
            event.error = error as Error;
            this.logger.error('Voice command processing failed', error);
            this.feedback.reportError(error.message || 'Command processing failed');
            this.emit('commandError', event);
        }
    }

    private registerDefaultCommands(): void {
        // Navigation commands
        this.registry.register({
            id: 'voice.goToLine',
            patterns: [
                /go to line (\d+)/i,
                /jump to line (\d+)/i,
                /line (\d+)/i
            ],
            handler: async (params) => {
                const line = parseInt(params.line);
                return await vscode.commands.executeCommand('workbench.action.gotoLine', line);
            },
            description: 'Navigate to a specific line number'
        });

        // File operations
        this.registry.register({
            id: 'voice.openFile',
            patterns: [
                /open file ([\w\-\.]+)/i,
                /open ([\w\-\.]+)/i
            ],
            handler: async (params) => {
                const files = await vscode.workspace.findFiles(`**/${params.file}*`);
                if (files.length > 0) {
                    return await vscode.window.showTextDocument(files[0]);
                }
                throw new Error(`File not found: ${params.file}`);
            },
            description: 'Open a file by name'
        });

        // Editor commands
        this.registry.register({
            id: 'voice.selectLine',
            patterns: [
                /select line (\d+)/i,
                /highlight line (\d+)/i
            ],
            handler: async (params) => {
                const editor = vscode.window.activeTextEditor;
                if (!editor) throw new Error('No active editor');
                
                const line = parseInt(params.line) - 1;
                const range = editor.document.lineAt(line).range;
                editor.selection = new vscode.Selection(range.start, range.end);
                editor.revealRange(range);
            },
            description: 'Select a specific line'
        });

        // Code modification
        this.registry.register({
            id: 'voice.commentLine',
            patterns: [
                /comment line/i,
                /comment this line/i,
                /add comment/i
            ],
            handler: async () => {
                return await vscode.commands.executeCommand('editor.action.commentLine');
            },
            description: 'Comment the current line'
        });

        // Extension specific
        this.registry.register({
            id: 'voice.connectBackend',
            patterns: [
                /connect to backend/i,
                /connect backend/i,
                /start connection/i
            ],
            handler: async () => {
                return await vscode.commands.executeCommand('coachntt.connect');
            },
            description: 'Connect to CoachNTT backend'
        });

        this.logger.info(`Registered ${this.registry.getCommandCount()} default voice commands`);
    }

    private addToHistory(command: ParsedCommand): void {
        this.commandHistory.unshift(command);
        if (this.commandHistory.length > this.maxHistorySize) {
            this.commandHistory.pop();
        }
    }

    public getHistory(): ParsedCommand[] {
        return [...this.commandHistory];
    }

    public getLastCommand(): ParsedCommand | undefined {
        return this.commandHistory[0];
    }

    public async repeatLastCommand(): Promise<void> {
        const lastCommand = this.getLastCommand();
        if (lastCommand) {
            const result = await this.router.execute(lastCommand);
            if (result.success) {
                this.feedback.confirmSuccess('Command repeated');
            } else {
                this.feedback.reportError('Failed to repeat command');
            }
        } else {
            this.feedback.reportError('No command to repeat');
        }
    }

    public getAvailableCommands(): string[] {
        return this.registry.getCommandDescriptions();
    }

    public dispose(): void {
        this.isEnabled = false;
        this.commandHistory = [];
        this.removeAllListeners();
    }
}