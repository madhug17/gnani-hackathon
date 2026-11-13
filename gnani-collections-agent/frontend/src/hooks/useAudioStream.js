import { useRef, useState, useCallback, useEffect } from 'react';

/**
 * High-performance Web Audio API Hook for bidirectional voice streaming.
 * Handles continuous 16kHz PCM capture and instant sub-10ms FLUSH_AUDIO buffer clearing.
 */
export function useAudioStream(sendWebSocketMessage) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [noiseSimulated, setNoiseSimulated] = useState(false);

  // Audio Contexts & Streams
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const scriptProcessorRef = useRef(null);
  
  // Playback queue & Active Source Nodes for instantaneous FLUSH
  const playbackContextRef = useRef(null);
  const activeSourcesRef = useRef([]);
  const nextPlayTimeRef = useRef(0);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  // 8kHz Noise simulator nodes
  const noiseNodeRef = useRef(null);
  const noiseGainRef = useRef(null);

  // Initialize playback AudioContext
  const getPlaybackContext = useCallback(() => {
    if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      playbackContextRef.current = new AudioCtx();
    }
    if (playbackContextRef.current.state === 'suspended') {
      playbackContextRef.current.resume();
    }
    return playbackContextRef.current;
  }, []);

  /**
   * INSTANT SUB-10MS BUFFER FLUSH.
   * Stops all currently playing AudioBufferSourceNodes and empties the queue.
   */
  const flushAudioPlayback = useCallback(() => {
    // 1. Stop and disconnect every active source node immediately
    activeSourcesRef.current.forEach((source) => {
      try {
        source.stop(0);
        source.disconnect();
      } catch (err) {
        // Node might have already finished
      }
    });
    activeSourcesRef.current = [];

    // 2. Clear pending queue
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    
    // 3. Reset playback timing cursor
    if (playbackContextRef.current) {
      nextPlayTimeRef.current = playbackContextRef.current.currentTime;
    }
  }, []);

  /**
   * Enqueues and plays an incoming base64 audio chunk.
   */
  const enqueueAudioChunk = useCallback(async (base64Audio) => {
    try {
      const ctx = getPlaybackContext();
      
      // Decode base64 to ArrayBuffer
      const binaryStr = atob(base64Audio);
      const len = binaryStr.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      // Decode audio data into AudioBuffer
      const audioBuffer = await ctx.decodeAudioData(bytes.buffer.slice(0));
      
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const currentTime = ctx.currentTime;
      // Schedule contiguous streaming
      if (nextPlayTimeRef.current < currentTime) {
        nextPlayTimeRef.current = currentTime;
      }

      source.start(nextPlayTimeRef.current);
      activeSourcesRef.current.push(source);

      nextPlayTimeRef.current += audioBuffer.duration;

      source.onended = () => {
        activeSourcesRef.current = activeSourcesRef.current.filter((s) => s !== source);
      };
    } catch (err) {
      console.warn("Audio decoding error (likely tiny fragment or flush race):", err);
    }
  }, [getPlaybackContext]);

  /**
   * Starts capturing microphone audio and streams 16kHz PCM chunks over WebSocket.
   */
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      micStreamRef.current = stream;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      
      // ScriptProcessorNode for raw PCM extraction (buffer size 1024 = 64ms frames)
      const processor = ctx.createScriptProcessor(1024, 1, 1);
      scriptProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calculate audio visualizer level
        let sumSquares = 0;
        const int16Array = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          sumSquares += s * s;
        }
        const rms = Math.sqrt(sumSquares / inputData.length);
        setAudioLevel(Math.min(100, Math.round(rms * 250)));

        // Base64 encode PCM and transmit to backend
        const uint8Bytes = new Uint8Array(int16Array.buffer);
        let binary = '';
        for (let i = 0; i < uint8Bytes.byteLength; i++) {
          binary += String.fromCharCode(uint8Bytes[i]);
        }
        const pcmBase64 = btoa(binary);

        sendWebSocketMessage({
          type: "AUDIO_FRAME",
          pcm_base64: pcmBase64
        });
      };

      source.connect(processor);
      processor.connect(ctx.destination);
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access error:", err);
      alert("Microphone permission denied or device not found: " + err.message);
    }
  }, [sendWebSocketMessage]);

  /**
   * Stops microphone streaming and dispatches END_OF_SPEECH.
   */
  const stopRecording = useCallback(() => {
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsRecording(false);
    setAudioLevel(0);

    // Notify backend that user finished speaking
    sendWebSocketMessage({
      type: "END_OF_SPEECH"
    });
  }, [sendWebSocketMessage]);

  /**
   * Toggles 8kHz Street / Traffic noise simulation in audio graph.
   */
  const toggleStreetNoiseSimulation = useCallback((enable) => {
    const ctx = getPlaybackContext();
    if (enable) {
      // Create noise buffer (2 seconds loop)
      const bufferSize = ctx.sampleRate * 2;
      const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = Math.random() * 2 - 1;
      }

      const whiteNoise = ctx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;
      whiteNoise.loop = true;

      // Bandpass filter to simulate 8kHz telephonic street ambience
      const bandpass = ctx.createBiquadFilter();
      bandpass.type = "bandpass";
      bandpass.frequency.value = 2400;
      bandpass.Q.value = 1.2;

      const gain = ctx.createGain();
      gain.gain.value = 0.08; // subtle realistic background noise

      whiteNoise.connect(bandpass);
      bandpass.connect(gain);
      gain.connect(ctx.destination);

      whiteNoise.start();
      noiseNodeRef.current = whiteNoise;
      noiseGainRef.current = gain;
      setNoiseSimulated(true);
    } else {
      if (noiseNodeRef.current) {
        try {
          noiseNodeRef.current.stop();
          noiseNodeRef.current.disconnect();
        } catch (e) {}
        noiseNodeRef.current = null;
      }
      setNoiseSimulated(false);
    }
  }, [getPlaybackContext]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      flushAudioPlayback();
      if (playbackContextRef.current && playbackContextRef.current.state !== 'closed') {
        playbackContextRef.current.close();
      }
    };
  }, [flushAudioPlayback]);

  return {
    isRecording,
    audioLevel,
    noiseSimulated,
    startRecording,
    stopRecording,
    enqueueAudioChunk,
    flushAudioPlayback,
    toggleStreetNoiseSimulation
  };
}
