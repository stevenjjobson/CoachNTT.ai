// VSCode API mocks for testing

export enum ExtensionKind {
  UI = 1,
  Workspace = 2
}

export enum DiagnosticSeverity {
  Error = 0,
  Warning = 1,
  Information = 2,
  Hint = 3
}

export enum ViewColumn {
  Active = -1,
  Beside = -2,
  One = 1,
  Two = 2,
  Three = 3,
  Four = 4,
  Five = 5,
  Six = 6,
  Seven = 7,
  Eight = 8,
  Nine = 9
}

export enum StatusBarAlignment {
  Left = 1,
  Right = 2
}

export enum TreeItemCollapsibleState {
  None = 0,
  Collapsed = 1,
  Expanded = 2
}

export class Uri {
  scheme: string;
  authority: string;
  path: string;
  query: string;
  fragment: string;

  constructor(scheme: string, authority: string, path: string, query: string, fragment: string) {
    this.scheme = scheme;
    this.authority = authority;
    this.path = path;
    this.query = query;
    this.fragment = fragment;
  }

  static file(path: string): Uri {
    return new Uri('file', '', path, '', '');
  }

  static parse(value: string): Uri {
    // Simplified parsing
    const match = /^(\w+):\/\/([^\/]+)(\/[^?#]*)(\?[^#]*)?(#.*)?$/.exec(value);
    if (match) {
      return new Uri(match[1], match[2], match[3] || '', match[4] || '', match[5] || '');
    }
    return new Uri('', '', value, '', '');
  }

  toString(): string {
    return `${this.scheme}://${this.authority}${this.path}${this.query}${this.fragment}`;
  }

  with(change: { scheme?: string; authority?: string; path?: string; query?: string; fragment?: string }): Uri {
    return new Uri(
      change.scheme ?? this.scheme,
      change.authority ?? this.authority,
      change.path ?? this.path,
      change.query ?? this.query,
      change.fragment ?? this.fragment
    );
  }
}

export class Position {
  constructor(public line: number, public character: number) {}
  
  isAfter(other: Position): boolean {
    return this.line > other.line || (this.line === other.line && this.character > other.character);
  }
  
  isBefore(other: Position): boolean {
    return this.line < other.line || (this.line === other.line && this.character < other.character);
  }
  
  isEqual(other: Position): boolean {
    return this.line === other.line && this.character === other.character;
  }
  
  translate(lineDelta?: number, characterDelta?: number): Position {
    return new Position(this.line + (lineDelta || 0), this.character + (characterDelta || 0));
  }
  
  with(line?: number, character?: number): Position {
    return new Position(line ?? this.line, character ?? this.character);
  }
}

export class Range {
  constructor(
    public start: Position | number,
    public end: Position | number,
    endCharacterOrEndLine?: number,
    endCharacter?: number
  ) {
    if (typeof start === 'number' && typeof end === 'number') {
      this.start = new Position(start, end);
      this.end = new Position(endCharacterOrEndLine || start, endCharacter || end);
    }
  }
  
  get isEmpty(): boolean {
    return this.start.isEqual(this.end as Position);
  }
  
  contains(positionOrRange: Position | Range): boolean {
    if (positionOrRange instanceof Position) {
      return !positionOrRange.isBefore(this.start as Position) && !positionOrRange.isAfter(this.end as Position);
    }
    return this.contains(positionOrRange.start as Position) && this.contains(positionOrRange.end as Position);
  }
  
  intersection(range: Range): Range | undefined {
    const start = (this.start as Position).isAfter(range.start as Position) ? this.start : range.start;
    const end = (this.end as Position).isBefore(range.end as Position) ? this.end : range.end;
    return (start as Position).isAfter(end as Position) ? undefined : new Range(start, end);
  }
  
  union(other: Range): Range {
    const start = (this.start as Position).isBefore(other.start as Position) ? this.start : other.start;
    const end = (this.end as Position).isAfter(other.end as Position) ? this.end : other.end;
    return new Range(start, end);
  }
  
  with(start?: Position, end?: Position): Range {
    return new Range(start ?? this.start, end ?? this.end);
  }
}

export class EventEmitter<T> {
  private listeners: Array<(e: T) => void> = [];

  event = (listener: (e: T) => void) => {
    this.listeners.push(listener);
    return {
      dispose: () => {
        const index = this.listeners.indexOf(listener);
        if (index >= 0) {
          this.listeners.splice(index, 1);
        }
      }
    };
  };

  fire(data: T): void {
    this.listeners.forEach(listener => listener(data));
  }

  dispose(): void {
    this.listeners = [];
  }
}

export class TreeItem {
  label?: string;
  collapsibleState?: TreeItemCollapsibleState;
  command?: any;
  iconPath?: any;
  description?: string;
  tooltip?: string;
  contextValue?: string;

  constructor(label: string, collapsibleState?: TreeItemCollapsibleState) {
    this.label = label;
    this.collapsibleState = collapsibleState;
  }
}

export class ThemeIcon {
  constructor(public id: string, public color?: any) {}
}

export class Disposable {
  constructor(private callOnDispose: () => void) {}

  dispose(): void {
    this.callOnDispose();
  }

  static from(...disposables: { dispose(): void }[]): Disposable {
    return new Disposable(() => {
      disposables.forEach(d => d.dispose());
    });
  }
}

export class CancellationTokenSource {
  private _token: CancellationToken;
  
  constructor() {
    let isCancelled = false;
    this._token = {
      isCancellationRequested: false,
      onCancellationRequested: new EventEmitter<void>().event
    };
  }
  
  get token(): CancellationToken {
    return this._token;
  }
  
  cancel(): void {
    this._token.isCancellationRequested = true;
  }
  
  dispose(): void {
    this.cancel();
  }
}

export interface CancellationToken {
  isCancellationRequested: boolean;
  onCancellationRequested: Event<void>;
}

export type Event<T> = (listener: (e: T) => void) => Disposable;

// Mock implementations
const mockExtensionContext = {
  subscriptions: [],
  workspaceState: {
    get: jest.fn(),
    update: jest.fn(),
    keys: jest.fn().mockReturnValue([])
  },
  globalState: {
    get: jest.fn(),
    update: jest.fn(),
    keys: jest.fn().mockReturnValue([]),
    setKeysForSync: jest.fn()
  },
  secrets: {
    get: jest.fn(),
    store: jest.fn(),
    delete: jest.fn(),
    onDidChange: new EventEmitter<any>().event
  },
  extensionUri: Uri.file('/mock/extension'),
  extensionPath: '/mock/extension',
  storagePath: '/mock/storage',
  globalStoragePath: '/mock/global-storage',
  logPath: '/mock/logs',
  extensionMode: 1,
  asAbsolutePath: jest.fn((path: string) => `/mock/extension/${path}`)
};

const mockOutputChannel = {
  name: 'Test',
  append: jest.fn(),
  appendLine: jest.fn(),
  clear: jest.fn(),
  show: jest.fn(),
  hide: jest.fn(),
  dispose: jest.fn()
};

const mockStatusBarItem = {
  text: '',
  tooltip: '',
  color: undefined,
  backgroundColor: undefined,
  command: undefined,
  alignment: StatusBarAlignment.Left,
  priority: 0,
  show: jest.fn(),
  hide: jest.fn(),
  dispose: jest.fn()
};

const mockWebviewPanel = {
  webview: {
    html: '',
    options: {},
    cspSource: 'mock-csp',
    asWebviewUri: jest.fn((uri: Uri) => uri),
    postMessage: jest.fn(),
    onDidReceiveMessage: new EventEmitter<any>().event
  },
  title: '',
  iconPath: undefined,
  options: {},
  viewColumn: ViewColumn.One,
  active: true,
  visible: true,
  onDidChangeViewState: new EventEmitter<any>().event,
  onDidDispose: new EventEmitter<void>().event,
  reveal: jest.fn(),
  dispose: jest.fn()
};

export const window = {
  showInformationMessage: jest.fn(),
  showWarningMessage: jest.fn(),
  showErrorMessage: jest.fn(),
  showQuickPick: jest.fn(),
  showInputBox: jest.fn(),
  createOutputChannel: jest.fn(() => mockOutputChannel),
  createStatusBarItem: jest.fn(() => mockStatusBarItem),
  createTreeView: jest.fn(() => ({
    visible: true,
    onDidChangeVisibility: new EventEmitter<any>().event,
    onDidChangeSelection: new EventEmitter<any>().event,
    onDidExpandElement: new EventEmitter<any>().event,
    onDidCollapseElement: new EventEmitter<any>().event,
    selection: [],
    reveal: jest.fn(),
    dispose: jest.fn()
  })),
  createWebviewPanel: jest.fn(() => mockWebviewPanel),
  registerTreeDataProvider: jest.fn(),
  withProgress: jest.fn((options, task) => task({ report: jest.fn() }, new CancellationTokenSource().token))
};

export const workspace = {
  workspaceFolders: [],
  name: 'Test Workspace',
  getConfiguration: jest.fn(() => ({
    get: jest.fn(),
    has: jest.fn(),
    inspect: jest.fn(),
    update: jest.fn()
  })),
  onDidChangeConfiguration: new EventEmitter<any>().event,
  onDidSaveTextDocument: new EventEmitter<any>().event,
  onDidOpenTextDocument: new EventEmitter<any>().event,
  onDidCloseTextDocument: new EventEmitter<any>().event,
  openTextDocument: jest.fn(),
  findFiles: jest.fn(),
  fs: {
    readFile: jest.fn(),
    writeFile: jest.fn(),
    delete: jest.fn(),
    rename: jest.fn(),
    copy: jest.fn(),
    createDirectory: jest.fn(),
    readDirectory: jest.fn(),
    stat: jest.fn()
  }
};

export const commands = {
  registerCommand: jest.fn((command: string, callback: (...args: any[]) => any) => {
    return new Disposable(() => {});
  }),
  executeCommand: jest.fn(),
  getCommands: jest.fn().mockResolvedValue([])
};

export const env = {
  appName: 'Visual Studio Code',
  appRoot: '/mock/vscode',
  language: 'en',
  clipboard: {
    readText: jest.fn(),
    writeText: jest.fn()
  },
  openExternal: jest.fn()
};

export const languages = {
  registerCodeLensProvider: jest.fn(),
  registerCompletionItemProvider: jest.fn(),
  registerHoverProvider: jest.fn(),
  registerDefinitionProvider: jest.fn(),
  registerDocumentSymbolProvider: jest.fn(),
  registerDocumentFormattingEditProvider: jest.fn(),
  getDiagnostics: jest.fn(),
  createDiagnosticCollection: jest.fn(() => ({
    name: 'Test',
    set: jest.fn(),
    delete: jest.fn(),
    clear: jest.fn(),
    dispose: jest.fn()
  }))
};

export const extensions = {
  getExtension: jest.fn(),
  all: []
};

// Export mock context for testing
export const testContext = mockExtensionContext;