import { Logger } from '../../utils/logger';

export interface VoiceCommand {
    id: string;
    patterns: RegExp[];
    handler: (params: Record<string, any>) => Promise<any>;
    description: string;
    category?: string;
    requiresContext?: string[];
    confirmationRequired?: boolean;
}

export class VoiceCommandRegistry {
    private logger: Logger;
    private commands: Map<string, VoiceCommand> = new Map();
    private categories: Map<string, Set<string>> = new Map();

    constructor() {
        this.logger = Logger.getInstance();
    }

    public register(command: VoiceCommand): void {
        if (this.commands.has(command.id)) {
            this.logger.warn(`Overwriting existing command: ${command.id}`);
        }

        this.commands.set(command.id, command);

        // Add to category index
        const category = command.category || 'general';
        if (!this.categories.has(category)) {
            this.categories.set(category, new Set());
        }
        this.categories.get(category)!.add(command.id);

        this.logger.debug(`Registered voice command: ${command.id}`);
    }

    public unregister(commandId: string): boolean {
        const command = this.commands.get(commandId);
        if (!command) {
            return false;
        }

        this.commands.delete(commandId);

        // Remove from category index
        const category = command.category || 'general';
        this.categories.get(category)?.delete(commandId);

        return true;
    }

    public getCommand(commandId: string): VoiceCommand | undefined {
        return this.commands.get(commandId);
    }

    public findCommandByPattern(text: string): VoiceCommand | undefined {
        for (const command of this.commands.values()) {
            for (const pattern of command.patterns) {
                if (pattern.test(text)) {
                    return command;
                }
            }
        }
        return undefined;
    }

    public getCommandsByCategory(category: string): VoiceCommand[] {
        const commandIds = this.categories.get(category);
        if (!commandIds) {
            return [];
        }

        return Array.from(commandIds)
            .map(id => this.commands.get(id))
            .filter(cmd => cmd !== undefined) as VoiceCommand[];
    }

    public getAllCommands(): VoiceCommand[] {
        return Array.from(this.commands.values());
    }

    public getCategories(): string[] {
        return Array.from(this.categories.keys());
    }

    public getCommandCount(): number {
        return this.commands.size;
    }

    public getCommandDescriptions(): string[] {
        return Array.from(this.commands.values())
            .map(cmd => `${cmd.id}: ${cmd.description}`);
    }

    public searchCommands(query: string): VoiceCommand[] {
        const lowerQuery = query.toLowerCase();
        return Array.from(this.commands.values()).filter(cmd => 
            cmd.id.toLowerCase().includes(lowerQuery) ||
            cmd.description.toLowerCase().includes(lowerQuery) ||
            cmd.patterns.some(p => p.source.toLowerCase().includes(lowerQuery))
        );
    }

    public validateContext(command: VoiceCommand, context: Record<string, any>): boolean {
        if (!command.requiresContext || command.requiresContext.length === 0) {
            return true;
        }

        return command.requiresContext.every(requirement => {
            switch (requirement) {
                case 'activeEditor':
                    return context.activeEditor !== undefined;
                case 'selection':
                    return context.selection !== undefined && !context.selection.isEmpty;
                case 'workspaceOpen':
                    return context.workspaceFolders !== undefined && context.workspaceFolders.length > 0;
                case 'connected':
                    return context.isConnected === true;
                default:
                    return true;
            }
        });
    }

    public exportCommands(): Record<string, any> {
        const exported: Record<string, any> = {
            commands: {},
            categories: {}
        };

        for (const [id, command] of this.commands) {
            exported.commands[id] = {
                patterns: command.patterns.map(p => p.source),
                description: command.description,
                category: command.category,
                requiresContext: command.requiresContext,
                confirmationRequired: command.confirmationRequired
            };
        }

        for (const [category, commandIds] of this.categories) {
            exported.categories[category] = Array.from(commandIds);
        }

        return exported;
    }

    public clear(): void {
        this.commands.clear();
        this.categories.clear();
    }
}