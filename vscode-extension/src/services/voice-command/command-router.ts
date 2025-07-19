import * as vscode from 'vscode';
import { Logger } from '../../utils/logger';
import { VoiceCommandRegistry, VoiceCommand } from './voice-command-registry';
import { ParsedCommand, CommandResult } from './voice-command-service';

export interface CommandContext {
    activeEditor?: vscode.TextEditor;
    selection?: vscode.Selection;
    workspaceFolders?: readonly vscode.WorkspaceFolder[];
    isConnected?: boolean;
}

export interface ExecutionOptions {
    requireConfirmation?: boolean;
    dryRun?: boolean;
}

export class CommandRouter {
    private logger: Logger;
    private registry: VoiceCommandRegistry;
    private executionHistory: Array<{
        command: ParsedCommand;
        result: CommandResult;
        timestamp: Date;
    }> = [];
    private maxHistorySize: number = 100;

    constructor(registry: VoiceCommandRegistry) {
        this.logger = Logger.getInstance();
        this.registry = registry;
    }

    public async execute(
        parsedCommand: ParsedCommand, 
        options: ExecutionOptions = {}
    ): Promise<CommandResult> {
        this.logger.info(`Executing command: ${parsedCommand.action}`);

        try {
            // Find the command in registry
            const command = this.findCommand(parsedCommand);
            if (!command) {
                return {
                    success: false,
                    message: `Unknown command: ${parsedCommand.action}`
                };
            }

            // Get current context
            const context = this.getCurrentContext();

            // Validate context requirements
            if (!this.registry.validateContext(command, context)) {
                return {
                    success: false,
                    message: this.getContextErrorMessage(command, context)
                };
            }

            // Check if confirmation is required
            if ((command.confirmationRequired || options.requireConfirmation) && !options.dryRun) {
                const confirmed = await this.requestConfirmation(parsedCommand);
                if (!confirmed) {
                    return {
                        success: false,
                        message: 'Command cancelled by user'
                    };
                }
            }

            // Execute in dry run mode if requested
            if (options.dryRun) {
                return {
                    success: true,
                    message: 'Command validated successfully (dry run)',
                    data: { command, context }
                };
            }

            // Execute the command
            const result = await this.executeCommand(command, parsedCommand.parameters || {}, context);
            
            // Log to history
            this.addToHistory(parsedCommand, result);

            return result;

        } catch (error) {
            this.logger.error('Command execution failed', error);
            return {
                success: false,
                message: error.message || 'Command execution failed'
            };
        }
    }

    private findCommand(parsedCommand: ParsedCommand): VoiceCommand | undefined {
        // First try to find by exact action match
        const commandId = `voice.${parsedCommand.action}`;
        let command = this.registry.getCommand(commandId);

        // If not found, search by pattern
        if (!command) {
            command = this.registry.findCommandByPattern(parsedCommand.raw);
        }

        // If still not found, try fuzzy matching
        if (!command) {
            const searchResults = this.registry.searchCommands(parsedCommand.action);
            if (searchResults.length > 0) {
                command = searchResults[0];
            }
        }

        return command;
    }

    private getCurrentContext(): CommandContext {
        return {
            activeEditor: vscode.window.activeTextEditor,
            selection: vscode.window.activeTextEditor?.selection,
            workspaceFolders: vscode.workspace.workspaceFolders,
            isConnected: this.checkConnectionStatus()
        };
    }

    private checkConnectionStatus(): boolean {
        // Check if the extension is connected to backend
        try {
            return vscode.commands.executeCommand('coachntt.getConnectionStatus') as any;
        } catch {
            return false;
        }
    }

    private getContextErrorMessage(command: VoiceCommand, context: CommandContext): string {
        if (!command.requiresContext) {
            return 'Command cannot be executed in current context';
        }

        for (const requirement of command.requiresContext) {
            switch (requirement) {
                case 'activeEditor':
                    if (!context.activeEditor) {
                        return 'No active editor. Please open a file first.';
                    }
                    break;
                case 'selection':
                    if (!context.selection || context.selection.isEmpty) {
                        return 'No text selected. Please select some text first.';
                    }
                    break;
                case 'workspaceOpen':
                    if (!context.workspaceFolders || context.workspaceFolders.length === 0) {
                        return 'No workspace open. Please open a folder first.';
                    }
                    break;
                case 'connected':
                    if (!context.isConnected) {
                        return 'Not connected to backend. Please connect first.';
                    }
                    break;
            }
        }

        return 'Command requirements not met';
    }

    private async requestConfirmation(command: ParsedCommand): Promise<boolean> {
        const message = `Execute command: ${command.action}?`;
        const choice = await vscode.window.showWarningMessage(
            message,
            'Yes',
            'No'
        );
        return choice === 'Yes';
    }

    private async executeCommand(
        command: VoiceCommand,
        parameters: Record<string, any>,
        context: CommandContext
    ): Promise<CommandResult> {
        try {
            // Add context to parameters
            const enrichedParams = {
                ...parameters,
                _context: context
            };

            // Execute the command handler
            const result = await command.handler(enrichedParams);

            return {
                success: true,
                message: `Command executed: ${command.description}`,
                data: result
            };

        } catch (error) {
            this.logger.error(`Command handler failed: ${command.id}`, error);
            throw error;
        }
    }

    private addToHistory(command: ParsedCommand, result: CommandResult): void {
        this.executionHistory.unshift({
            command,
            result,
            timestamp: new Date()
        });

        // Trim history if too large
        if (this.executionHistory.length > this.maxHistorySize) {
            this.executionHistory = this.executionHistory.slice(0, this.maxHistorySize);
        }
    }

    public getHistory(): typeof this.executionHistory {
        return [...this.executionHistory];
    }

    public async undoLastCommand(): Promise<CommandResult> {
        const lastExecution = this.executionHistory[0];
        if (!lastExecution) {
            return {
                success: false,
                message: 'No command to undo'
            };
        }

        // For now, just execute the undo command
        // In future, we could store undo actions with each command
        try {
            await vscode.commands.executeCommand('undo');
            return {
                success: true,
                message: 'Command undone'
            };
        } catch (error) {
            return {
                success: false,
                message: 'Failed to undo command'
            };
        }
    }

    public clearHistory(): void {
        this.executionHistory = [];
    }
}