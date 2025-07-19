/**
 * Mock for ManagedWebViewPanel used in tests
 */

export class ManagedWebViewPanel {
  panel: any;
  disposables: any[] = [];
  isDisposed: boolean = false;
  nonce: string = 'test-nonce';
  
  constructor() {
    this.panel = {
      webview: {
        html: '',
        postMessage: jest.fn().mockResolvedValue(undefined),
        asWebviewUri: jest.fn((uri: any) => uri),
        onDidReceiveMessage: jest.fn(() => ({ dispose: jest.fn() })),
        cspSource: 'test-csp'
      },
      title: '',
      reveal: jest.fn(),
      dispose: jest.fn(),
      onDidDispose: jest.fn(() => ({ dispose: jest.fn() })),
      onDidChangeViewState: jest.fn(() => ({ dispose: jest.fn() })),
      viewColumn: 1,
      active: true,
      visible: true
    };
  }
  
  dispose(): void {
    this.isDisposed = true;
    this.disposables.forEach(d => d.dispose());
  }
  
  getPanelState(): any {
    return {};
  }
  
  restoreState(state: any): void {
    // Mock implementation
  }
  
  protected getHtml(): string {
    return '<html><body>Mock Panel</body></html>';
  }
  
  protected handleMessage(message: any): void {
    // Mock implementation
  }
  
  protected postMessage(message: any): void {
    this.panel.webview.postMessage(message);
  }
}