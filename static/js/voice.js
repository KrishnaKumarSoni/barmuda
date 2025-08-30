// Voice conversation handler for ElevenLabs Conversational AI
class VoiceConversation {
  constructor(formId, agentId) {
    this.formId = formId;
    this.agentId = agentId;
    this.conversation = null;
    this.isActive = false;
    this.sessionId = null;
    this.transcript = [];
  }

  async initialize() {
    try {
      // Get ephemeral token from backend
      const tokenResponse = await fetch('/api/voice/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: this.agentId })
      });
      
      if (!tokenResponse.ok) {
        throw new Error('Failed to get voice token');
      }
      
      const tokenData = await tokenResponse.json();
      
      // Initialize ElevenLabs conversation
      this.conversation = new ElevenLabsConversation({
        agentId: this.agentId,
        apiKey: tokenData.token,
        onConnect: () => this.onConnect(),
        onDisconnect: () => this.onDisconnect(),
        onMessage: (message) => this.onMessage(message),
        onError: (error) => this.onError(error),
        onTranscript: (transcript) => this.onTranscript(transcript)
      });
      
      // Start session tracking
      await this.startSession();
      
      return true;
    } catch (error) {
      console.error('Failed to initialize voice conversation:', error);
      return false;
    }
  }
  
  async startSession() {
    try {
      // Create a session in the backend
      const response = await fetch('/api/voice/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          form_id: this.formId,
          device_id: await this.getDeviceId()
        })
      });
      
      const data = await response.json();
      this.sessionId = data.session_id;
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  }
  
  async getDeviceId() {
    // Simple device fingerprinting
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('device_id', 2, 2);
    return canvas.toDataURL().slice(-50);
  }
  
  async start() {
    if (!this.conversation) {
      const initialized = await this.initialize();
      if (!initialized) {
        throw new Error('Failed to initialize conversation');
      }
    }
    
    await this.conversation.startConversation();
    this.isActive = true;
    this.updateUI('active');
  }
  
  async pause() {
    if (this.conversation && this.isActive) {
      await this.conversation.pauseConversation();
      this.isActive = false;
      this.updateUI('paused');
    }
  }
  
  async end() {
    if (this.conversation) {
      await this.conversation.endConversation();
      this.isActive = false;
      this.updateUI('ended');
      
      // Save the conversation
      await this.saveConversation();
    }
  }
  
  async saveConversation() {
    if (!this.sessionId || this.transcript.length === 0) return;
    
    try {
      await fetch('/api/voice/session/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          form_id: this.formId,
          transcript: this.transcript,
          mode: 'voice'
        })
      });
    } catch (error) {
      console.error('Failed to save conversation:', error);
    }
  }
  
  onConnect() {
    console.log('Voice conversation connected');
    this.updateUI('connected');
  }
  
  onDisconnect() {
    console.log('Voice conversation disconnected');
    this.updateUI('disconnected');
  }
  
  onMessage(message) {
    console.log('Received message:', message);
    // Handle conversation messages
  }
  
  onError(error) {
    console.error('Voice conversation error:', error);
    this.updateUI('error');
  }
  
  onTranscript(transcript) {
    // Store transcript for later saving
    this.transcript.push({
      timestamp: new Date().toISOString(),
      speaker: transcript.speaker,
      text: transcript.text
    });
    
    // Update UI with transcript
    this.updateTranscript(transcript);
  }
  
  updateUI(state) {
    const visualizer = document.getElementById('visualizer');
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const endBtn = document.getElementById('end-btn');
    
    switch(state) {
      case 'active':
        visualizer.classList.add('animate-pulse');
        startBtn.disabled = true;
        startBtn.classList.add('opacity-50');
        pauseBtn.disabled = false;
        pauseBtn.classList.remove('opacity-50');
        endBtn.disabled = false;
        break;
        
      case 'paused':
        visualizer.classList.remove('animate-pulse');
        startBtn.disabled = false;
        startBtn.classList.remove('opacity-50');
        startBtn.textContent = 'Resume';
        pauseBtn.disabled = true;
        pauseBtn.classList.add('opacity-50');
        break;
        
      case 'ended':
        visualizer.classList.remove('animate-pulse');
        visualizer.classList.add('opacity-50');
        startBtn.disabled = true;
        pauseBtn.disabled = true;
        endBtn.disabled = true;
        // Show completion message
        this.showCompletionMessage();
        break;
        
      case 'error':
        visualizer.classList.remove('animate-pulse');
        visualizer.classList.add('bg-red-400');
        break;
    }
  }
  
  updateTranscript(transcript) {
    // Update transcript display if needed
    const transcriptContainer = document.getElementById('transcript');
    if (transcriptContainer) {
      const entry = document.createElement('div');
      entry.className = transcript.speaker === 'user' ? 'text-right' : 'text-left';
      entry.innerHTML = `
        <span class="text-xs text-gray-500">${transcript.speaker}</span>
        <p class="text-sm">${transcript.text}</p>
      `;
      transcriptContainer.appendChild(entry);
      transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
    }
  }
  
  showCompletionMessage() {
    const container = document.querySelector('.flex-1');
    const message = document.createElement('div');
    message.className = 'mt-6 p-4 bg-green-100 rounded-lg text-center';
    message.innerHTML = `
      <h3 class="font-semibold text-green-800">Thank you!</h3>
      <p class="text-sm text-green-600 mt-1">Your response has been recorded.</p>
    `;
    container.appendChild(message);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const formId = window.location.pathname.split('/').pop();
  const agentId = window.AGENT_ID;
  
  if (!agentId) {
    console.error('No agent ID provided');
    return;
  }
  
  const conversation = new VoiceConversation(formId, agentId);
  
  // Button handlers
  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const endBtn = document.getElementById('end-btn');
  
  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      try {
        await conversation.start();
      } catch (error) {
        console.error('Failed to start conversation:', error);
        alert('Failed to start voice conversation. Please try again.');
      }
    });
  }
  
  if (pauseBtn) {
    pauseBtn.addEventListener('click', async () => {
      await conversation.pause();
    });
  }
  
  if (endBtn) {
    endBtn.addEventListener('click', async () => {
      if (confirm('Are you sure you want to end the conversation?')) {
        await conversation.end();
      }
    });
  }
});

// ElevenLabs SDK placeholder (would be loaded from CDN in production)
class ElevenLabsConversation {
  constructor(config) {
    this.config = config;
    console.log('ElevenLabs conversation initialized with config:', config);
  }
  
  async startConversation() {
    console.log('Starting ElevenLabs conversation...');
    this.config.onConnect?.();
    // Simulate conversation start
    setTimeout(() => {
      this.config.onTranscript?.({
        speaker: 'assistant',
        text: 'Hello! I\'m ready to help you with the survey. Shall we begin?'
      });
    }, 1000);
  }
  
  async pauseConversation() {
    console.log('Pausing conversation...');
  }
  
  async endConversation() {
    console.log('Ending conversation...');
    this.config.onDisconnect?.();
  }
}