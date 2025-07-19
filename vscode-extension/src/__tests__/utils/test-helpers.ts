/**
 * Test utilities and helper functions
 */

import { EventEmitter } from 'events';
import * as vscode from 'vscode';

/**
 * Create mock audio data for testing
 */
export function createTestAudioData(options: {
  amplitude?: number;
  duration?: number;
  sampleRate?: number;
} = {}): Float32Array {
  const {
    amplitude = 0.5,
    duration = 1, // seconds
    sampleRate = 44100
  } = options;

  const samples = duration * sampleRate;
  const data = new Float32Array(samples);
  
  // Generate sine wave
  const frequency = 440; // A4 note
  for (let i = 0; i < samples; i++) {
    data[i] = amplitude * Math.sin(2 * Math.PI * frequency * i / sampleRate);
  }
  
  return data;
}

/**
 * Create mock speech audio data
 */
export function createTestSpeechAudio(text: string): ArrayBuffer {
  // Create a simple WAV header
  const sampleRate = 16000;
  const duration = text.length * 0.1; // Rough estimate
  const numSamples = Math.floor(sampleRate * duration);
  
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);
  
  // WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // Byte rate
  view.setUint16(32, 2, true); // Block align
  view.setUint16(34, 16, true); // Bits per sample
  writeString(36, 'data');
  view.setUint32(40, numSamples * 2, true);
  
  // Generate mock audio data
  for (let i = 0; i < numSamples; i++) {
    const value = Math.floor(Math.sin(i * 0.01) * 10000);
    view.setInt16(44 + i * 2, value, true);
  }
  
  return buffer;
}

/**
 * Create mock MediaStream for testing
 */
export function createMockMediaStream(): MediaStream {
  const audioContext = {
    sampleRate: 44100,
    currentTime: 0,
    state: 'running' as AudioContextState,
    createMediaStreamSource: jest.fn(),
    createScriptProcessor: jest.fn(() => ({
      connect: jest.fn(),
      disconnect: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    })),
    createAnalyser: jest.fn(() => ({
      fftSize: 2048,
      frequencyBinCount: 1024,
      getByteFrequencyData: jest.fn(),
      getFloatFrequencyData: jest.fn(),
      getByteTimeDomainData: jest.fn(),
      getFloatTimeDomainData: jest.fn(),
      connect: jest.fn(),
      disconnect: jest.fn()
    }))
  };

  const mockTrack = {
    kind: 'audio',
    id: 'mock-audio-track',
    enabled: true,
    muted: false,
    readyState: 'live' as MediaStreamTrackState,
    stop: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn()
  };

  return {
    id: 'mock-stream',
    active: true,
    getAudioTracks: jest.fn(() => [mockTrack]),
    getVideoTracks: jest.fn(() => []),
    getTracks: jest.fn(() => [mockTrack]),
    addTrack: jest.fn(),
    removeTrack: jest.fn(),
    clone: jest.fn(),
    getTrackById: jest.fn()
  } as any;
}

/**
 * Create mock WebSocket for testing
 */
export class MockWebSocket extends EventEmitter {
  public readyState: number = 0; // CONNECTING
  public url: string;
  
  constructor(url: string) {
    super();
    this.url = url;
    
    // Simulate connection after a delay
    setTimeout(() => {
      this.readyState = 1; // OPEN
      this.emit('open');
    }, 10);
  }
  
  send(data: string | ArrayBuffer | Blob): void {
    if (this.readyState !== 1) {
      throw new Error('WebSocket is not open');
    }
    
    // Echo back for testing
    setTimeout(() => {
      this.emit('message', { data });
    }, 5);
  }
  
  close(code?: number, reason?: string): void {
    this.readyState = 2; // CLOSING
    setTimeout(() => {
      this.readyState = 3; // CLOSED
      this.emit('close', { code, reason });
    }, 5);
  }
  
  addEventListener(event: string, listener: Function): void {
    this.on(event, listener as any);
  }
  
  removeEventListener(event: string, listener: Function): void {
    this.off(event, listener as any);
  }
}

/**
 * Create mock memory data
 */
export function createMockMemory(overrides: any = {}) {
  return {
    id: 'test-memory-id',
    content: 'Test memory content',
    abstract_content: '<memory_content>',
    intent: {
      type: 'learn',
      subtype: 'concept',
      confidence: 0.9
    },
    metadata: {
      timestamp: new Date().toISOString(),
      importance: 0.8,
      reinforcement_count: 0,
      safety_score: 0.95,
      ...overrides.metadata
    },
    ...overrides
  };
}

/**
 * Wait for a condition to be true
 */
export async function waitFor(
  condition: () => boolean | Promise<boolean>,
  timeout: number = 5000,
  interval: number = 50
): Promise<void> {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const result = await condition();
    if (result) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  throw new Error(`Timeout waiting for condition after ${timeout}ms`);
}

/**
 * Flush all pending promises
 */
export async function flushPromises(): Promise<void> {
  await new Promise(resolve => setImmediate(resolve));
}

/**
 * Create a deferred promise
 */
export interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: any) => void;
}

export function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: any) => void;
  
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  
  return { promise, resolve, reject };
}

/**
 * Mock VSCode extension context
 */
export function createMockExtensionContext(): vscode.ExtensionContext {
  const subscriptions: vscode.Disposable[] = [];
  
  return {
    subscriptions,
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
      onDidChange: new vscode.EventEmitter<any>().event
    },
    extensionUri: vscode.Uri.file('/mock/extension'),
    extensionPath: '/mock/extension',
    storagePath: '/mock/storage',
    globalStoragePath: '/mock/global-storage',
    logPath: '/mock/logs',
    extensionMode: vscode.ExtensionMode.Test,
    asAbsolutePath: jest.fn((path: string) => `/mock/extension/${path}`)
  } as any;
}

/**
 * Mock configuration values
 */
export const mockConfig = {
  apiUrl: 'http://localhost:8000',
  websocketUrl: 'ws://localhost:8000/ws',
  safetyValidation: true,
  minSafetyScore: 0.8,
  autoConnect: false,
  logLevel: 'info',
  authToken: 'mock-jwt-token'
};

/**
 * Create mock configuration
 */
export function createMockConfiguration() {
  return {
    get: jest.fn((key: string) => {
      const path = key.split('.');
      let value: any = mockConfig;
      for (const p of path) {
        value = value[p];
      }
      return value;
    }),
    has: jest.fn(() => true),
    inspect: jest.fn(),
    update: jest.fn()
  };
}