# CoachNTT VSCode Extension

🧠 **CoachNTT** - Your AI-powered cognitive coding partner with voice interaction and real-time monitoring.

## Features

### ✅ Available Now
- **🧠 Memory Management**: Hierarchical memory tree with three-tier organization
  - Categories: Recent Memories, Important Memories, By Intent
  - 12 Intent Types: Learning, Debugging, Architecture, Configuration, and more
  - Full CRUD operations with context menus
  - Search functionality with semantic similarity
  - Import/Export memories in JSON format
- **🔌 MCP Integration**: WebSocket connection with automatic reconnection
  - JWT authentication with secure token storage
  - Real-time updates for memory operations
  - Channel subscriptions for live data
- **🔒 Safety-First Design**: All data abstracted for security with zero-tolerance for concrete references
  - Automatic abstraction of paths, URLs, and sensitive data
  - Safety score monitoring in status bar
  - Validation at every layer

### 🚧 Coming Soon
- **🎤 Voice Commands**: Natural language interface for hands-free operation (Session 2.3)
- **📊 Real-time Monitoring**: Performance metrics and alerts integrated into your IDE (Session 2.2)
- **🖼️ Rich WebViews**: Advanced UI panels for memory details and monitoring (Session 2.1.4)
- **🎵 Audio Playback**: Voice synthesis and playback controls (Session 2.2.1)

## Installation

### From Marketplace (Coming Soon)
1. Open VSCode Extension Marketplace
2. Search for "CoachNTT"
3. Click Install

### From Source (Development)
1. Clone the repository
2. Navigate to `vscode-extension/` directory
3. Run `npm install`
4. Press `F5` to launch development instance

## Quick Start

1. **Connect to Backend**: Click the CoachNTT status bar item or run command `CoachNTT: Connect to Backend`
2. **Browse Memories**: Click the CoachNTT icon in the activity bar to view your memory tree
3. **Create Memory**: Select code and right-click → "Create Memory from Selection"
4. **Search Memories**: Click the search icon in the Memories view
5. **Configure Settings**: Open settings with `CoachNTT: Open Extension Settings`

## Memory Management

### Creating Memories
- **From Selection**: Select code → Right-click → "Create Memory from Selection"
- **Command Palette**: `Ctrl/Cmd+Shift+P` → "CoachNTT: Create Memory"
- **Tree View**: Click the + icon in the Memories view toolbar

### Memory Operations
- **View**: Click any memory to see full formatted details
- **Edit**: Right-click → "Edit Memory" to modify content
- **Reinforce**: Right-click → "Reinforce Memory" to increase importance
- **Delete**: Right-click → "Delete Memory" with confirmation

### Searching
- Click search icon or use "CoachNTT: Search Memories" command
- Supports semantic search across all memory content
- Results displayed in dedicated search section
- Clear search to return to normal view

### Import/Export
- **Export**: "CoachNTT: Export Memories" → Save as JSON
- **Import**: "CoachNTT: Import Memories" → Load from JSON file

## Configuration

### Connection Settings
| Setting | Description | Default |
|---------|-------------|---------|
| `coachntt.apiUrl` | Backend API URL for local development | `http://localhost:8000` |
| `coachntt.vpsUrl` | VPS API URL for production deployment | `""` |
| `coachntt.websocketUrl` | WebSocket URL for real-time updates | `ws://localhost:8000/ws` |
| `coachntt.safetyValidation` | Enable safety validation for all operations | `true` |
| `coachntt.minSafetyScore` | Minimum safety score required (0.0-1.0) | `0.8` |
| `coachntt.autoConnect` | Automatically connect to backend on startup | `false` |
| `coachntt.logLevel` | Logging level for extension output | `info` |

### Memory View Settings
| Setting | Description | Default |
|---------|-------------|---------|  
| `coachntt.memoryView.groupByIntent` | Group memories by intent type | `true` |
| `coachntt.memoryView.showArchived` | Show archived memories | `false` |
| `coachntt.memoryView.sortBy` | Sort order (timestamp/importance/reinforcement) | `timestamp` |
| `coachntt.memoryView.sortOrder` | Sort direction (asc/desc) | `desc` |
| `coachntt.memoryView.pageSize` | Number of memories per page | `50` |

## Commands

All commands are available through the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`):

### Connection Commands
- `CoachNTT: Connect to Backend` - Establish connection to CoachNTT backend
- `CoachNTT: Disconnect from Backend` - Disconnect from backend services  
- `CoachNTT: Check Connection Status` - Display current connection details

### Memory Commands
- `CoachNTT: Create Memory` - Create a new memory
- `CoachNTT: Create Memory from Selection` - Create memory from selected text
- `CoachNTT: Search Memories` - Search through all memories
- `CoachNTT: Clear Search` - Clear search results
- `CoachNTT: Export Memories` - Export memories to JSON
- `CoachNTT: Import Memories` - Import memories from JSON
- `CoachNTT: Configure Memory View` - Adjust memory view settings

### General Commands
- `CoachNTT: Show Extension Logs` - View extension output logs
- `CoachNTT: Open Extension Settings` - Open extension configuration
- `CoachNTT: Refresh CoachNTT View` - Refresh the sidebar view

## Development

### Prerequisites
- Node.js 18+
- VSCode 1.85.0+
- TypeScript 5.3+

### Setup
```bash
# Clone repository
git clone <repository>

# Navigate to extension directory
cd vscode-extension

# Install dependencies
npm install

# Build extension
npm run compile

# Watch mode for development
npm run watch
```

### Testing
```bash
# Run tests
npm test

# Run linter
npm run lint
```

### Debugging
1. Open the extension folder in VSCode
2. Press `F5` to launch a new VSCode instance with the extension loaded
3. Set breakpoints in the source code
4. Use the Debug Console to inspect variables

## Architecture

The extension follows a modular architecture:

```
src/
├── extension.ts          # Main entry point with MCP integration
├── config/              # Configuration management
│   └── settings.ts      # Type-safe configuration service
├── commands/            # Command handlers
│   ├── index.ts         # Command registry
│   └── memory-commands.ts # Memory operation commands
├── models/              # Data models
│   └── memory.model.ts  # Memory types and tree items
├── providers/           # VSCode providers
│   ├── welcomeView.ts   # Welcome tree view
│   ├── memory-tree-provider.ts # Memory tree data provider
│   └── memory-content-provider.ts # Virtual document provider
├── services/            # Core services
│   ├── mcp-client.ts    # WebSocket MCP client
│   └── connection-manager.ts # Connection lifecycle
├── events/              # Event handling
│   └── mcp-events.ts    # Real-time update events
├── types/               # TypeScript definitions
│   └── mcp.types.ts     # MCP message types
└── utils/               # Utilities
    └── logger.ts        # Logger with abstraction
```

### Safety-First Design

All displayed information is automatically abstracted:
- File paths: `<project>/<module>/<file>`
- URLs: `<url>` or `<api_endpoint>`
- IPs: `<ip_address>`
- Tokens/Keys: `<token>`
- UUIDs: `<uuid>`

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/coachntt/vscode-extension/issues)
- **Documentation**: [GitHub Wiki](https://github.com/coachntt/vscode-extension/wiki)
- **Community**: [Discord Server](https://discord.gg/coachntt)

---

Built with ❤️ by the CoachNTT team