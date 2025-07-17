# CoachNTT VSCode Extension

🧠 **CoachNTT** - Your AI-powered cognitive coding partner with voice interaction and real-time monitoring.

## Features

- **🧠 Memory Management**: Three-tier memory system (Working, Session, Long-term) for organizing development knowledge
- **🎤 Voice Commands**: Natural language interface for hands-free operation (Coming in Session 2.3)
- **📊 Real-time Monitoring**: Performance metrics and alerts integrated into your IDE (Coming in Session 2.2)
- **🔒 Safety-First Design**: All data abstracted for security with zero-tolerance for concrete references
- **🔌 MCP Integration**: Seamless connection to CoachNTT backend services (Coming in Session 2.1.2)

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
2. **Configure Settings**: Open settings with `CoachNTT: Open Extension Settings`
3. **View Logs**: Check connection status with `CoachNTT: Show Extension Logs`

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `coachntt.apiUrl` | Backend API URL for local development | `http://localhost:8000` |
| `coachntt.vpsUrl` | VPS API URL for production deployment | `""` |
| `coachntt.websocketUrl` | WebSocket URL for real-time updates | `ws://localhost:8000/ws` |
| `coachntt.safetyValidation` | Enable safety validation for all operations | `true` |
| `coachntt.minSafetyScore` | Minimum safety score required (0.0-1.0) | `0.8` |
| `coachntt.autoConnect` | Automatically connect to backend on startup | `false` |
| `coachntt.logLevel` | Logging level for extension output | `info` |

## Commands

All commands are available through the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`):

- `CoachNTT: Connect to Backend` - Establish connection to CoachNTT backend
- `CoachNTT: Disconnect from Backend` - Disconnect from backend services
- `CoachNTT: Show Extension Logs` - View extension output logs
- `CoachNTT: Open Extension Settings` - Open extension configuration
- `CoachNTT: Refresh CoachNTT View` - Refresh the sidebar view
- `CoachNTT: Check Connection Status` - Display current connection details

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
├── extension.ts       # Main entry point
├── config/           # Configuration management
├── commands/         # Command handlers
├── providers/        # VSCode providers (tree views, etc.)
└── utils/           # Utilities (logger, etc.)
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