/**
 * Audio test fixtures
 */

/**
 * VAD test scenarios
 */
export const vadTestScenarios = {
  silence: {
    description: 'Complete silence',
    amplitude: 0,
    expectedSpeech: false,
    expectedConfidence: 0
  },
  
  quietNoise: {
    description: 'Quiet background noise',
    amplitude: 0.05,
    expectedSpeech: false,
    expectedConfidence: 0.1
  },
  
  normalSpeech: {
    description: 'Normal speech volume',
    amplitude: 0.3,
    expectedSpeech: true,
    expectedConfidence: 0.8
  },
  
  loudSpeech: {
    description: 'Loud speech',
    amplitude: 0.8,
    expectedSpeech: true,
    expectedConfidence: 0.95
  },
  
  intermittentSpeech: {
    description: 'Speech with pauses',
    pattern: [0.3, 0.05, 0.35, 0.02, 0.4],
    expectedSpeechFrames: [true, false, true, false, true]
  }
};

/**
 * Audio capture test scenarios
 */
export const captureTestScenarios = {
  shortCapture: {
    description: 'Short audio capture (1 second)',
    duration: 1,
    sampleRate: 16000,
    expectedSamples: 16000
  },
  
  longCapture: {
    description: 'Long audio capture (5 seconds)',
    duration: 5,
    sampleRate: 16000,
    expectedSamples: 80000
  },
  
  maxDurationCapture: {
    description: 'Maximum duration capture (30 seconds)',
    duration: 30,
    sampleRate: 16000,
    expectedSamples: 480000
  },
  
  withPreSpeech: {
    description: 'Capture with pre-speech buffer',
    preSpeechDuration: 0.3,
    speechDuration: 2,
    sampleRate: 16000,
    expectedMinSamples: 36800 // (0.3 + 2) * 16000
  }
};

/**
 * Audio playback test scenarios
 */
export const playbackTestScenarios = {
  singleItem: {
    description: 'Single audio item playback',
    items: [{
      id: 'test-1',
      content: 'Test audio content',
      priority: 'medium' as const,
      duration: 2000
    }]
  },
  
  queueWithPriorities: {
    description: 'Queue with different priorities',
    items: [
      {
        id: 'low-1',
        content: 'Low priority content',
        priority: 'low' as const,
        duration: 1000
      },
      {
        id: 'high-1',
        content: 'High priority content',
        priority: 'high' as const,
        duration: 1500
      },
      {
        id: 'medium-1',
        content: 'Medium priority content',
        priority: 'medium' as const,
        duration: 2000
      }
    ],
    expectedOrder: ['high-1', 'medium-1', 'low-1']
  },
  
  largeQueue: {
    description: 'Large queue management',
    itemCount: 50,
    maxQueueSize: 100
  }
};

/**
 * WebRTC constraints for testing
 */
export const webRTCConstraints = {
  audio: {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    sampleRate: 16000,
    channelCount: 1
  },
  video: false
};

/**
 * Mock audio processing events
 */
export const audioProcessingEvents = {
  scriptProcessor: {
    inputBuffer: {
      sampleRate: 44100,
      length: 4096,
      duration: 0.093,
      numberOfChannels: 1,
      getChannelData: (channel: number) => new Float32Array(4096)
    },
    outputBuffer: {
      sampleRate: 44100,
      length: 4096,
      duration: 0.093,
      numberOfChannels: 1,
      getChannelData: (channel: number) => new Float32Array(4096)
    },
    playbackTime: 0
  }
};

/**
 * Expected VAD metrics
 */
export const expectedVADMetrics = {
  processingTime: {
    max: 10, // ms
    average: 5 // ms
  },
  
  accuracy: {
    truePositiveRate: 0.95,
    falsePositiveRate: 0.05
  },
  
  latency: {
    speechDetection: 100, // ms
    silenceDetection: 800 // ms
  }
};

/**
 * Audio encoding test data
 */
export const encodingTestData = {
  wav: {
    sampleRate: 16000,
    bitDepth: 16,
    channels: 1,
    expectedHeaderSize: 44
  },
  
  compression: {
    inputSize: 32000, // 1 second at 16kHz, 16-bit
    expectedOutputRange: {
      min: 30000,
      max: 34000
    }
  }
};