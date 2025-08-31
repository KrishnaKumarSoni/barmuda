// ElevenLabs Conversational AI Voice Interface
class VoiceConversation {
  constructor() {
    this.conversation = null;
    this.isConnected = false;
    this.isListening = false;
    this.conversationId = null;
    
    // UI Elements
    this.startBtn = document.getElementById('start-btn');
    this.pauseBtn = document.getElementById('pause-btn');
    this.endBtn = document.getElementById('end-btn');
    this.visualizer = document.getElementById('visualizer');
    
    this.initializeUI();
    this.loadElevenLabsSDK();
  }

  async loadElevenLabsSDK() {
    try {
      // Dynamically import the ElevenLabs client SDK
      const { Conversation } = await import('https://cdn.skypack.dev/@elevenlabs/client');
      this.Conversation = Conversation;
      console.log('ElevenLabs SDK loaded successfully');
    } catch (error) {
      console.error('Failed to load ElevenLabs SDK, using fallback:', error);
      this.initializeFallback();
    }
  }

  initializeUI() {
    // Remove the pulse animation initially
    if (this.visualizer) {
      this.visualizer.classList.remove('animate-pulse');
    }

    if (this.startBtn) {
      this.startBtn.addEventListener('click', () => this.startConversation());
    }
    
    if (this.pauseBtn) {
      this.pauseBtn.addEventListener('click', () => this.pauseConversation());
      this.pauseBtn.disabled = true;
    }
    
    if (this.endBtn) {
      this.endBtn.addEventListener('click', () => this.endConversation());
      this.endBtn.disabled = true;
    }
  }

  async startConversation() {
    try {
      console.log('Starting voice conversation...');
      this.updateStatus('Requesting microphone permission...');
      
      // Request microphone permission
      await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('Microphone permission granted');
      
      // Get voice token
      this.updateStatus('Getting voice token...');
      const tokenRes = await fetch('/api/voice/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          voice_id: window.VOICE_ID,
          form_id: window.FORM_ID 
        })
      });
      
      const tokenData = await tokenRes.json();
      console.log('Voice token received:', tokenData);

      if (!tokenData.success) {
        throw new Error(tokenData.error || 'Failed to get voice token');
      }

      // Initialize conversation with ElevenLabs SDK
      if (this.Conversation) {
        this.updateStatus('Connecting to voice agent...');
        await this.startElevenLabsConversation(window.VOICE_ID, tokenData.token);
      } else {
        // Fallback implementation
        await this.startFallbackConversation();
      }

    } catch (error) {
      console.error('Failed to start conversation:', error);
      this.updateStatus(`Error: ${error.message}`);
      this.resetButtons();
    }
  }

  async startElevenLabsConversation(agentId, token) {
    try {
      this.conversation = new this.Conversation();
      
      // Start session with WebRTC for best quality
      this.conversationId = await this.conversation.startSession({
        agentId: agentId,
        connectionType: 'webrtc', // Use WebRTC for low latency
        onConnect: () => {
          console.log('Connected to ElevenLabs');
          this.onConnected();
        },
        onDisconnect: () => {
          console.log('Disconnected from ElevenLabs');
          this.onDisconnected();
        },
        onMessage: (message) => {
          console.log('Agent message:', message);
          this.onMessage(message);
        },
        onError: (error) => {
          console.error('Conversation error:', error);
          this.onError(error);
        },
        onStatusChange: (status) => {
          console.log('Status changed:', status);
          this.onStatusChange(status);
        }
      });
      
      console.log('Conversation session started:', this.conversationId);
      
    } catch (error) {
      console.error('ElevenLabs conversation error:', error);
      throw new Error(`Voice connection failed: ${error.message}`);
    }
  }

  async startFallbackConversation() {
    // Fallback to basic speech recognition when SDK is not available
    this.updateStatus('Using fallback speech recognition...');
    
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      this.speechRecognition = new SpeechRecognition();
      
      this.speechRecognition.continuous = true;
      this.speechRecognition.interimResults = true;
      this.speechRecognition.lang = window.LANGUAGE || 'hi-IN'; // Use Hindi or fallback
      
      this.speechRecognition.onstart = () => this.onConnected();
      this.speechRecognition.onend = () => this.onDisconnected();
      this.speechRecognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        this.onMessage({ transcript });
      };
      this.speechRecognition.onerror = (event) => this.onError(event.error);
      
      this.speechRecognition.start();
    } else {
      throw new Error('Speech recognition not supported in this browser');
    }
  }

  onConnected() {
    this.isConnected = true;
    this.isListening = true;
    this.updateStatus('Connected! Start speaking...');
    this.updateButtons();
    this.startVisualizer();
  }

  onDisconnected() {
    this.isConnected = false;
    this.isListening = false;
    this.updateStatus('Disconnected');
    this.resetButtons();
    this.stopVisualizer();
  }

  onMessage(message) {
    console.log('Conversation message:', message);
    if (message.transcript) {
      this.updateStatus(`You said: "${message.transcript}"`);
    }
  }

  onError(error) {
    console.error('Conversation error:', error);
    this.updateStatus(`Error: ${error}`);
    this.resetButtons();
    this.stopVisualizer();
  }

  onStatusChange(status) {
    console.log('Status change:', status);
    this.updateStatus(`Status: ${status}`);
  }

  pauseConversation() {
    if (this.conversation && this.isConnected) {
      // Note: ElevenLabs SDK might not have pause, so we'll implement as mute
      console.log('Pausing conversation...');
      this.isListening = !this.isListening;
      this.pauseBtn.textContent = this.isListening ? 'Pause' : 'Resume';
      this.updateStatus(this.isListening ? 'Listening...' : 'Paused');
      
      if (this.isListening) {
        this.startVisualizer();
      } else {
        this.stopVisualizer();
      }
    }
  }

  async endConversation() {
    try {
      console.log('Ending conversation...');
      this.updateStatus('Ending conversation...');
      
      if (this.conversation && this.conversation.endSession) {
        await this.conversation.endSession();
      }
      
      if (this.speechRecognition) {
        this.speechRecognition.stop();
      }
      
      this.onDisconnected();
      this.updateStatus('Conversation ended');
      
    } catch (error) {
      console.error('Error ending conversation:', error);
      this.onDisconnected();
    }
  }

  updateButtons() {
    if (this.isConnected) {
      this.startBtn.disabled = true;
      this.pauseBtn.disabled = false;
      this.endBtn.disabled = false;
      this.startBtn.textContent = 'Connected';
    }
  }

  resetButtons() {
    this.startBtn.disabled = false;
    this.pauseBtn.disabled = true;
    this.endBtn.disabled = true;
    this.startBtn.textContent = 'Start';
    this.pauseBtn.textContent = 'Pause';
  }

  startVisualizer() {
    if (this.visualizer) {
      this.visualizer.classList.remove('animate-pulse');
      this.visualizer.classList.add('animate-bounce');
      this.visualizer.style.background = 'linear-gradient(135deg, #10b981, #059669)';
    }
  }

  stopVisualizer() {
    if (this.visualizer) {
      this.visualizer.classList.remove('animate-bounce');
      this.visualizer.style.background = 'linear-gradient(135deg, #f97316, #ea580c)';
    }
  }

  updateStatus(message) {
    console.log('Status:', message);
    // Could add a status element to show this to user
    if (document.getElementById('status')) {
      document.getElementById('status').textContent = message;
    }
  }

  initializeFallback() {
    console.log('Using fallback implementation without ElevenLabs SDK');
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  console.log('Initializing voice conversation interface...');
  console.log('Voice ID:', window.VOICE_ID);
  console.log('Language:', window.LANGUAGE);
  
  if (!window.VOICE_ID) {
    console.error('No voice ID provided');
    return;
  }
  
  new VoiceConversation();
});
