/**
 * DOM and Browser API mocks for tests
 */

// MediaStream and related types
export class MediaStreamTrack {
    kind: 'audio' | 'video' = 'audio';
    enabled: boolean = true;
    readyState: 'live' | 'ended' = 'live';
    
    stop(): void {
        this.readyState = 'ended';
    }
    
    addEventListener(event: string, handler: Function): void {}
    removeEventListener(event: string, handler: Function): void {}
}

export class MediaStream {
    active: boolean = true;
    id: string = 'mock-stream-' + Math.random();
    
    private tracks: MediaStreamTrack[] = [];
    
    constructor() {
        this.tracks.push(new MediaStreamTrack());
    }
    
    getTracks(): MediaStreamTrack[] {
        return this.tracks;
    }
    
    getAudioTracks(): MediaStreamTrack[] {
        return this.tracks.filter(t => t.kind === 'audio');
    }
    
    getVideoTracks(): MediaStreamTrack[] {
        return this.tracks.filter(t => t.kind === 'video');
    }
    
    addTrack(track: MediaStreamTrack): void {
        this.tracks.push(track);
    }
    
    removeTrack(track: MediaStreamTrack): void {
        this.tracks = this.tracks.filter(t => t !== track);
    }
}

// Audio API types
export type AudioContextState = 'suspended' | 'running' | 'closed';
export type MediaStreamTrackState = 'live' | 'ended';

export class AudioNode {
    connect(destination: AudioNode | AudioParam): AudioNode {
        return destination as AudioNode;
    }
    
    disconnect(): void {}
}

export class AudioParam {
    value: number = 0;
    defaultValue: number = 0;
    
    setValueAtTime(value: number, time: number): AudioParam {
        this.value = value;
        return this;
    }
}

export class GainNode extends AudioNode {
    gain: AudioParam = new AudioParam();
}

export class AnalyserNode extends AudioNode {
    fftSize: number = 2048;
    frequencyBinCount: number = 1024;
    
    getByteFrequencyData(array: Uint8Array): void {
        array.fill(128);
    }
    
    getFloatFrequencyData(array: Float32Array): void {
        array.fill(0);
    }
}

export class MediaStreamAudioSourceNode extends AudioNode {
    mediaStream: MediaStream;
    
    constructor(context: AudioContext, options: { mediaStream: MediaStream }) {
        super();
        this.mediaStream = options.mediaStream;
    }
}

export class AudioBuffer {
    duration: number = 0;
    length: number = 0;
    numberOfChannels: number = 1;
    sampleRate: number = 44100;
    
    getChannelData(channel: number): Float32Array {
        return new Float32Array(this.length);
    }
}

export class ScriptProcessorNode extends AudioNode {
    bufferSize: number;
    onaudioprocess: ((event: AudioProcessingEvent) => void) | null = null;
    
    constructor(bufferSize: number = 4096) {
        super();
        this.bufferSize = bufferSize;
    }
}

export class AudioProcessingEvent extends Event {
    inputBuffer: AudioBuffer;
    outputBuffer: AudioBuffer;
    playbackTime: number = 0;
    
    constructor() {
        super('audioprocess');
        this.inputBuffer = new AudioBuffer();
        this.outputBuffer = new AudioBuffer();
    }
}

export class AudioContext {
    state: AudioContextState = 'running';
    sampleRate: number = 44100;
    currentTime: number = 0;
    destination: AudioNode = new AudioNode();
    
    createGain(): GainNode {
        return new GainNode();
    }
    
    createAnalyser(): AnalyserNode {
        return new AnalyserNode();
    }
    
    createMediaStreamSource(stream: MediaStream): MediaStreamAudioSourceNode {
        return new MediaStreamAudioSourceNode(this, { mediaStream: stream });
    }
    
    createScriptProcessor(bufferSize?: number): ScriptProcessorNode {
        return new ScriptProcessorNode(bufferSize);
    }
    
    close(): Promise<void> {
        this.state = 'closed';
        return Promise.resolve();
    }
    
    suspend(): Promise<void> {
        this.state = 'suspended';
        return Promise.resolve();
    }
    
    resume(): Promise<void> {
        this.state = 'running';
        return Promise.resolve();
    }
}

// Navigator mock
export const navigator = {
    mediaDevices: {
        getUserMedia: jest.fn().mockResolvedValue(new MediaStream()),
        enumerateDevices: jest.fn().mockResolvedValue([
            { deviceId: 'default', kind: 'audioinput', label: 'Default Microphone' }
        ])
    },
    userAgent: 'Mozilla/5.0 (Test Environment)'
};

// Global assignments for tests
(global as any).MediaStream = MediaStream;
(global as any).MediaStreamTrack = MediaStreamTrack;
(global as any).AudioContext = AudioContext;
(global as any).AudioProcessingEvent = AudioProcessingEvent;
(global as any).navigator = navigator;

// Type exports
export type { AudioContextState, MediaStreamTrackState };