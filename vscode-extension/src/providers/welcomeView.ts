import * as vscode from 'vscode';
import { Logger } from '../utils/logger';
import { ConfigurationService } from '../config/settings';
import { CommandRegistry } from '../commands';

/**
 * Tree item for welcome view
 */
export class WelcomeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly command?: vscode.Command,
        public readonly icon?: string,
        public readonly description?: string
    ) {
        super(label, collapsibleState);
        
        if (icon) {
            this.iconPath = new vscode.ThemeIcon(icon);
        }
        
        this.tooltip = this.description || this.label;
    }
}

/**
 * Welcome view data provider
 */
export class WelcomeViewProvider implements vscode.TreeDataProvider<WelcomeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<WelcomeItem | undefined | null | void> = 
        new vscode.EventEmitter<WelcomeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<WelcomeItem | undefined | null | void> = 
        this._onDidChangeTreeData.event;

    private logger: Logger;
    private config: ConfigurationService;
    private commands: CommandRegistry;

    constructor() {
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        this.commands = CommandRegistry.getInstance();
        
        // Listen for configuration changes
        this.config.onConfigChange(() => {
            this.refresh();
        });
    }

    /**
     * Refresh the tree view
     */
    refresh(): void {
        this.logger.debug('Refreshing welcome view');
        this._onDidChangeTreeData.fire();
    }

    /**
     * Get tree item
     */
    getTreeItem(element: WelcomeItem): vscode.TreeItem {
        return element;
    }

    /**
     * Get children for tree item
     */
    getChildren(element?: WelcomeItem): Thenable<WelcomeItem[]> {
        if (!element) {
            // Root level items
            return Promise.resolve(this.getRootItems());
        }
        
        // Child items based on parent
        switch (element.label) {
            case 'Getting Started':
                return Promise.resolve(this.getGettingStartedItems());
            case 'Features':
                return Promise.resolve(this.getFeaturesItems());
            case 'Resources':
                return Promise.resolve(this.getResourcesItems());
            default:
                return Promise.resolve([]);
        }
    }

    /**
     * Get root level items
     */
    private getRootItems(): WelcomeItem[] {
        const isConnected = this.commands.getConnectionStatus();
        const items: WelcomeItem[] = [];

        // Connection status
        items.push(new WelcomeItem(
            isConnected ? 'Connected' : 'Disconnected',
            vscode.TreeItemCollapsibleState.None,
            {
                command: isConnected ? 'coachntt.disconnect' : 'coachntt.connect',
                title: isConnected ? 'Disconnect' : 'Connect'
            },
            isConnected ? 'pass-filled' : 'circle-slash',
            isConnected ? 'Click to disconnect' : 'Click to connect'
        ));

        // Main sections
        items.push(new WelcomeItem(
            'Getting Started',
            vscode.TreeItemCollapsibleState.Expanded,
            undefined,
            'rocket'
        ));

        items.push(new WelcomeItem(
            'Features',
            vscode.TreeItemCollapsibleState.Collapsed,
            undefined,
            'star'
        ));

        items.push(new WelcomeItem(
            'Resources',
            vscode.TreeItemCollapsibleState.Collapsed,
            undefined,
            'book'
        ));

        return items;
    }

    /**
     * Get getting started items
     */
    private getGettingStartedItems(): WelcomeItem[] {
        return [
            new WelcomeItem(
                'Connect to Backend',
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'coachntt.connect',
                    title: 'Connect'
                },
                'plug',
                'Establish connection to CoachNTT backend'
            ),
            new WelcomeItem(
                'Configure Settings',
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'coachntt.openSettings',
                    title: 'Open Settings'
                },
                'settings-gear',
                'Configure extension settings'
            ),
            new WelcomeItem(
                'View Logs',
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'coachntt.showLogs',
                    title: 'Show Logs'
                },
                'output',
                'View extension output logs'
            )
        ];
    }

    /**
     * Get features items
     */
    private getFeaturesItems(): WelcomeItem[] {
        return [
            new WelcomeItem(
                '🧠 Memory Management',
                vscode.TreeItemCollapsibleState.None,
                undefined,
                undefined,
                'Three-tier memory system (Coming in Session 2.1.3)'
            ),
            new WelcomeItem(
                '🎤 Voice Commands',
                vscode.TreeItemCollapsibleState.None,
                undefined,
                undefined,
                'Natural language interface (Coming in Session 2.3.1)'
            ),
            new WelcomeItem(
                '📊 Real-time Monitoring',
                vscode.TreeItemCollapsibleState.None,
                undefined,
                undefined,
                'Performance metrics and alerts (Coming in Session 2.2.2)'
            ),
            new WelcomeItem(
                '🔒 Safety-First Design',
                vscode.TreeItemCollapsibleState.None,
                undefined,
                undefined,
                'All data abstracted for security'
            )
        ];
    }

    /**
     * Get resources items
     */
    private getResourcesItems(): WelcomeItem[] {
        return [
            new WelcomeItem(
                'Documentation',
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'vscode.open',
                    title: 'Open Documentation',
                    arguments: [vscode.Uri.parse('https://github.com/coachntt/vscode-extension#readme')]
                },
                'github',
                'View extension documentation'
            ),
            new WelcomeItem(
                'Report Issue',
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'vscode.open',
                    title: 'Report Issue',
                    arguments: [vscode.Uri.parse('https://github.com/coachntt/vscode-extension/issues')]
                },
                'bug',
                'Report a bug or request a feature'
            ),
            new WelcomeItem(
                'Check Status',
                vscode.TreeItemCollapsibleState.None,
                {
                    command: 'coachntt.checkStatus',
                    title: 'Check Status'
                },
                'info',
                'View current connection status'
            )
        ];
    }
}