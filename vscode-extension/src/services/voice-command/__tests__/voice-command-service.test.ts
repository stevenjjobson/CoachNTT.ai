import { VoiceCommandService } from '../voice-command-service';
import { AudioCaptureService } from '../../audio-capture-service';
import { AudioPlaybackService } from '../../audio-playback-service';
import * as vscode from 'vscode';

jest.mock('vscode');
jest.mock('../../audio-capture-service');
jest.mock('../../audio-playback-service');

describe('VoiceCommandService', () => {
    let service: VoiceCommandService;
    let mockAudioCapture: jest.Mocked<AudioCaptureService>;
    let mockAudioPlayback: jest.Mocked<AudioPlaybackService>;

    beforeEach(() => {
        jest.clearAllMocks();
        
        // Reset singleton instances
        (VoiceCommandService as any).instance = undefined;
        
        // Create service instance
        service = VoiceCommandService.getInstance();
        
        // Get mocked dependencies
        mockAudioCapture = AudioCaptureService.getInstance() as any;
        mockAudioPlayback = AudioPlaybackService.getInstance() as any;
    });

    afterEach(() => {
        service.dispose();
    });

    describe('Service Lifecycle', () => {
        test('should create singleton instance', () => {
            const instance1 = VoiceCommandService.getInstance();
            const instance2 = VoiceCommandService.getInstance();
            expect(instance1).toBe(instance2);
        });

        test('should initialize with disabled state', () => {
            expect((service as any).isEnabled).toBe(false);
        });

        test('should enable/disable voice commands', () => {
            service.enable();
            expect((service as any).isEnabled).toBe(true);

            service.disable();
            expect((service as any).isEnabled).toBe(false);
        });

        test('should register default commands on initialization', () => {
            const commands = service.getAvailableCommands();
            expect(commands.length).toBeGreaterThan(0);
            expect(commands).toContain(expect.stringContaining('goToLine'));
        });
    });

    describe('Transcription Processing', () => {
        beforeEach(() => {
            service.enable();
        });

        test('should process valid go to line command', async () => {
            const mockExecute = jest.spyOn(vscode.commands, 'executeCommand')
                .mockResolvedValue(undefined);

            await service.processTranscription('go to line 42');

            expect(mockExecute).toHaveBeenCalledWith('workbench.action.gotoLine', 42);
        });

        test('should handle file open command', async () => {
            const mockFindFiles = jest.spyOn(vscode.workspace, 'findFiles')
                .mockResolvedValue([vscode.Uri.file('/test/file.ts')]);
            const mockShowTextDocument = jest.spyOn(vscode.window, 'showTextDocument')
                .mockResolvedValue({} as any);

            await service.processTranscription('open file test.ts');

            expect(mockFindFiles).toHaveBeenCalledWith('**/test.ts*');
            expect(mockShowTextDocument).toHaveBeenCalled();
        });

        test('should emit events for command lifecycle', async () => {
            const receivedSpy = jest.fn();
            const executedSpy = jest.fn();
            const failedSpy = jest.fn();
            const errorSpy = jest.fn();

            service.on('commandReceived', receivedSpy);
            service.on('commandExecuted', executedSpy);
            service.on('commandFailed', failedSpy);
            service.on('commandError', errorSpy);

            jest.spyOn(vscode.commands, 'executeCommand').mockResolvedValue(undefined);

            await service.processTranscription('save file');

            expect(receivedSpy).toHaveBeenCalledWith(
                expect.objectContaining({ transcription: 'save file' })
            );
            expect(executedSpy).toHaveBeenCalled();
            expect(failedSpy).not.toHaveBeenCalled();
            expect(errorSpy).not.toHaveBeenCalled();
        });

        test('should handle unrecognized commands', async () => {
            const errorSpy = jest.fn();
            service.on('commandError', errorSpy);

            await service.processTranscription('random gibberish command');

            expect(errorSpy).toHaveBeenCalledWith(
                expect.objectContaining({
                    error: expect.objectContaining({
                        message: expect.stringContaining('Could not understand')
                    })
                })
            );
        });

        test('should not process when disabled', async () => {
            service.disable();
            const executeSpy = jest.spyOn(vscode.commands, 'executeCommand');

            // Simulate transcription event
            mockAudioCapture.emit('transcriptionComplete', { text: 'save file' });

            expect(executeSpy).not.toHaveBeenCalled();
        });
    });

    describe('Command History', () => {
        test('should maintain command history', async () => {
            jest.spyOn(vscode.commands, 'executeCommand').mockResolvedValue(undefined);

            await service.processTranscription('save file');
            await service.processTranscription('go to line 10');

            const history = service.getHistory();
            expect(history).toHaveLength(2);
            expect(history[0].raw).toBe('go to line 10');
            expect(history[1].raw).toBe('save file');
        });

        test('should limit history size', async () => {
            jest.spyOn(vscode.commands, 'executeCommand').mockResolvedValue(undefined);

            // Add more commands than max history size
            for (let i = 0; i < 60; i++) {
                await service.processTranscription(`go to line ${i}`);
            }

            const history = service.getHistory();
            expect(history).toHaveLength(50); // Default max size
        });

        test('should repeat last command', async () => {
            const executeSpy = jest.spyOn(vscode.commands, 'executeCommand')
                .mockResolvedValue(undefined);

            await service.processTranscription('save file');
            executeSpy.mockClear();

            await service.repeatLastCommand();

            expect(executeSpy).toHaveBeenCalledWith('coachntt.saveFile');
        });

        test('should handle repeat with no history', async () => {
            await service.repeatLastCommand();
            // Should not throw, just report error via feedback
        });
    });

    describe('Command Registration', () => {
        test('should register navigation commands', () => {
            const registry = (service as any).registry;
            const command = registry.getCommand('voice.goToLine');
            
            expect(command).toBeDefined();
            expect(command.patterns).toHaveLength(3);
            expect(command.description).toContain('Navigate to');
        });

        test('should register file operation commands', () => {
            const registry = (service as any).registry;
            const openCommand = registry.getCommand('voice.openFile');
            const saveCommand = registry.getCommand('voice.save');
            
            expect(openCommand).toBeDefined();
            expect(saveCommand).toBeDefined();
        });

        test('should register editor commands', () => {
            const registry = (service as any).registry;
            const selectCommand = registry.getCommand('voice.selectLine');
            const commentCommand = registry.getCommand('voice.commentLine');
            
            expect(selectCommand).toBeDefined();
            expect(commentCommand).toBeDefined();
        });

        test('should register extension-specific commands', () => {
            const registry = (service as any).registry;
            const connectCommand = registry.getCommand('voice.connectBackend');
            
            expect(connectCommand).toBeDefined();
            expect(connectCommand.patterns).toHaveLength(3);
        });
    });

    describe('Audio Integration', () => {
        test('should listen to transcription events when enabled', () => {
            const onSpy = jest.spyOn(mockAudioCapture, 'on');
            
            // Create new instance to test initialization
            (VoiceCommandService as any).instance = undefined;
            const newService = VoiceCommandService.getInstance();
            
            expect(onSpy).toHaveBeenCalledWith('transcriptionComplete', expect.any(Function));
        });

        test('should provide audio feedback on enable/disable', () => {
            service.enable();
            expect(mockAudioPlayback.synthesizeAndPlay)
                .toHaveBeenCalledWith('Voice commands activated', expect.any(Object));

            service.disable();
            expect(mockAudioPlayback.synthesizeAndPlay)
                .toHaveBeenCalledWith('Voice commands deactivated', expect.any(Object));
        });
    });
});