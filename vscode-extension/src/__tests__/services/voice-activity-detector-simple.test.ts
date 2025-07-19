import { VoiceActivityDetector } from '../../services/voice-activity-detector';

describe('VoiceActivityDetector - Simple Tests', () => {
  let vad: VoiceActivityDetector;

  beforeEach(() => {
    vad = new VoiceActivityDetector();
  });

  afterEach(() => {
    vad.dispose();
  });

  it('should instantiate correctly', () => {
    expect(vad).toBeDefined();
    expect(vad).toBeInstanceOf(VoiceActivityDetector);
  });

  it('should process a frame without throwing', () => {
    const audioData = new Float32Array(1024).fill(0);
    expect(() => {
      vad.processFrame(audioData);
    }).not.toThrow();
  });

  it('should detect silence', () => {
    const silentAudio = new Float32Array(1024).fill(0);
    const isSpeech = vad.processFrame(silentAudio);
    expect(isSpeech).toBe(false);
  });

  it('should detect loud sound', () => {
    const loudAudio = new Float32Array(1024).fill(0.8);
    const isSpeech = vad.processFrame(loudAudio);
    expect(isSpeech).toBe(true);
  });

  it('should return state', () => {
    const state = vad.getState();
    expect(state).toHaveProperty('isSpeaking');
    expect(state).toHaveProperty('energy');
    expect(state).toHaveProperty('threshold');
  });

  it('should reset state', () => {
    vad.reset();
    const state = vad.getState();
    expect(state.isSpeaking).toBe(false);
  });

  it('should update config', () => {
    expect(() => {
      vad.updateConfig({ frameDuration: 30 });
    }).not.toThrow();
  });
});