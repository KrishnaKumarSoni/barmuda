// Voice conversation handler for ElevenLabs Conversational AI
class VoiceConversation {
  constructor(formId, voiceId, language) {
    this.formId = formId;
    this.voiceId = voiceId;
    this.language = language;
    this.conversation = null;
    this.isActive = false;
    this.sessionId = null;
    this.transcript = [];
  }

  async initialize() {
    try {
      // Get ephemeral token from backend
      const tokenResponse = await fetch("/api/voice/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ form_id: this.formId }),
      });

      if (!tokenResponse.ok) {
        throw new Error("Failed to get voice token");
      }

      const tokenData = await tokenResponse.json();
      this.token = tokenData.token;

      // Request microphone access for voice input
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      if (window?.ElevenLabs?.startConversation) {
        // Use the ElevenLabs SDK when available
        this.conversation = await window.ElevenLabs.startConversation({
          token: this.token,
        });
        this.conversation.on("connect", () => this.onConnect());
        this.conversation.on("disconnect", () => this.onDisconnect());
        this.conversation.on("error", (err) => this.onError(err));
        this.conversation.on("message", (msg) => this.onMessage(msg));
        this.conversation.on("transcript", (t) => this.onTranscript(t));
      } else {
        // Fallback to server-side mock implementation
        this.conversation = new ServerVoiceConversation({
          token: this.token,
          voiceId: this.voiceId,
          formId: this.formId,
          language: this.language,
          onConnect: () => this.onConnect(),
          onDisconnect: () => this.onDisconnect(),
          onMessage: (message) => this.onMessage(message),
          onError: (error) => this.onError(error),
          onTranscript: (transcript) => this.onTranscript(transcript),
        });
      }

      // Start session tracking
      await this.startSession();

      return true;
    } catch (error) {
      console.error("Failed to initialize voice conversation:", error);
      return false;
    }
  }

  async startSession() {
    try {
      // Create a session in the backend
      const response = await fetch("/api/voice/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          form_id: this.formId,
          device_id: await this.getDeviceId(),
        }),
      });

      const data = await response.json();
      this.sessionId = data.session_id;
    } catch (error) {
      console.error("Failed to start session:", error);
    }
  }

  async getDeviceId() {
    // Simple device fingerprinting
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    ctx.textBaseline = "top";
    ctx.font = "14px Arial";
    ctx.fillText("device_id", 2, 2);
    return canvas.toDataURL().slice(-50);
  }

  async start() {
    if (!this.conversation) {
      const initialized = await this.initialize();
      if (!initialized) {
        throw new Error("Failed to initialize conversation");
      }
    }

    // For real ElevenLabs SDK, conversation starts automatically after startSession()
    // For mock, call startConversation
    if (this.conversation.startConversation) {
      await this.conversation.startConversation();
    }
    this.isActive = true;
    this.updateUI("active");
  }

  async pause() {
    if (this.conversation && this.isActive) {
      // ElevenLabs SDK doesn't have pause - use end/start pattern or mock method
      if (this.conversation.pauseConversation) {
        await this.conversation.pauseConversation();
      }
      this.isActive = false;
      this.updateUI("paused");
    }
  }

  async end() {
    if (this.conversation) {
      // Use the correct ElevenLabs SDK method or mock method
      if (this.conversation.endSession) {
        await this.conversation.endSession();
      } else if (this.conversation.endConversation) {
        await this.conversation.endConversation();
      }
      this.isActive = false;
      this.updateUI("ended");

      // Save the conversation
      await this.saveConversation();
    }
  }

  async saveConversation() {
    if (!this.sessionId || this.transcript.length === 0) return;

    try {
      await fetch("/api/voice/session/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this.sessionId,
          form_id: this.formId,
          transcript: this.transcript,
          mode: "voice",
        }),
      });
    } catch (error) {
      console.error("Failed to save conversation:", error);
    }
  }

  onConnect() {
    console.log("Voice conversation connected");
    this.updateUI("connected");
  }

  onDisconnect() {
    console.log("Voice conversation disconnected");
    this.updateUI("disconnected");
  }

  onMessage(message) {
    console.log("Received message:", message);
    // Handle conversation messages
  }

  onError(error) {
    console.error("Voice conversation error:", error);
    this.updateUI("error");
  }

  onTranscript(transcript) {
    // Store transcript for later saving
    this.transcript.push({
      timestamp: new Date().toISOString(),
      speaker: transcript.speaker,
      text: transcript.text,
    });

    // Update UI with transcript
    this.updateTranscript(transcript);
  }

  updateUI(state) {
    const visualizer = document.getElementById("visualizer");
    const rippleEffect = document.getElementById("ripple-effect");
    const startBtn = document.getElementById("start-btn");
    const pauseBtn = document.getElementById("pause-btn");
    const endBtn = document.getElementById("end-btn");

    switch (state) {
      case "active":
      case "connected":
        // Show ripple animation when conversation is active
        if (rippleEffect) rippleEffect.classList.remove("hidden");
        if (visualizer) visualizer.classList.add("voice-active");
        if (startBtn) {
          startBtn.disabled = true;
          startBtn.classList.add("opacity-50");
        }
        if (pauseBtn) {
          pauseBtn.disabled = false;
          pauseBtn.classList.remove("opacity-50");
        }
        if (endBtn) endBtn.disabled = false;
        break;

      case "paused":
        // Hide ripple animation when paused
        if (rippleEffect) rippleEffect.classList.add("hidden");
        if (visualizer) visualizer.classList.remove("voice-active");
        if (startBtn) {
          startBtn.disabled = false;
          startBtn.classList.remove("opacity-50");
          startBtn.querySelector("span").textContent = "Resume";
        }
        if (pauseBtn) {
          pauseBtn.disabled = true;
          pauseBtn.classList.add("opacity-50");
        }
        break;

      case "ended":
      case "disconnected":
        // Hide ripple animation when ended
        if (rippleEffect) rippleEffect.classList.add("hidden");
        if (visualizer) {
          visualizer.classList.remove("voice-active");
          visualizer.classList.add("opacity-50");
        }
        if (startBtn) startBtn.disabled = true;
        if (pauseBtn) pauseBtn.disabled = true;
        if (endBtn) endBtn.disabled = true;
        // Show completion message
        this.showCompletionMessage();
        break;

      case "error":
        // Hide ripple animation on error
        if (rippleEffect) rippleEffect.classList.add("hidden");
        if (visualizer) {
          visualizer.classList.remove("voice-active");
          visualizer.classList.add("bg-red-400");
        }
        break;
    }
  }

  updateTranscript(transcript) {
    // Update transcript display if needed
    const transcriptContainer = document.getElementById("transcript");
    if (transcriptContainer) {
      const entry = document.createElement("div");
      entry.className =
        transcript.speaker === "user" ? "text-right" : "text-left";
      entry.innerHTML = `
        <span class="text-xs text-gray-500">${transcript.speaker}</span>
        <p class="text-sm">${transcript.text}</p>
      `;
      transcriptContainer.appendChild(entry);
      transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
    }
  }

  showCompletionMessage() {
    const container = document.querySelector(".flex-1");
    const message = document.createElement("div");
    message.className = "mt-6 p-4 bg-green-100 rounded-lg text-center";
    message.innerHTML = `
      <h3 class="font-semibold text-green-800">Thank you!</h3>
      <p class="text-sm text-green-600 mt-1">Your response has been recorded.</p>
    `;
    container.appendChild(message);
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  const formId = window.FORM_ID;
  const voiceId = window.VOICE_ID;
  const language = window.VOICE_LANGUAGE;

  if (!voiceId) {
    console.error("No voice ID provided");
    return;
  }

  if (!formId) {
    console.error("No form ID provided");
    return;
  }

  const conversation = new VoiceConversation(formId, voiceId, language);

  // Button handlers
  const startBtn = document.getElementById("start-btn");
  const pauseBtn = document.getElementById("pause-btn");
  const endBtn = document.getElementById("end-btn");

  if (startBtn) {
    startBtn.addEventListener("click", async () => {
      try {
        await conversation.start();
      } catch (error) {
        console.error("Failed to start conversation:", error);
        alert("Failed to start voice conversation. Please try again.");
      }
    });
  }

  if (pauseBtn) {
    pauseBtn.addEventListener("click", async () => {
      await conversation.pause();
    });
  }

  if (endBtn) {
    endBtn.addEventListener("click", async () => {
      if (confirm("Are you sure you want to end the conversation?")) {
        await conversation.end();
      }
    });
  }
});

// Server-based voice conversation using ElevenLabs API via backend
class ServerVoiceConversation {
  constructor(config) {
    this.config = config;
    this.isListening = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.currentAudio = null; // Track current playing audio
    this.isPlaying = false;
    this.ignoreRecognition = false; // Ignore recognition results when needed
    console.log("Server voice conversation initialized:", config);
  }

  async startConversation() {
    console.log("Starting server-based voice conversation...");
    this.config.onConnect?.();

    // Start listening immediately to remain under initial user gesture
    this.ignoreRecognition = true; // Ignore recognizer until greeting completes
    this.startListening();

    // Start with greeting
    await this.speak(
      "Hello! I'm ready to help you with the survey. Shall we begin?",
    );

    // Allow recognition results after greeting finishes
    this.ignoreRecognition = false;
  }

  async speak(text) {
    try {
      // Stop current audio if playing (interruption)
      if (this.currentAudio && !this.currentAudio.paused) {
        this.currentAudio.pause();
        this.currentAudio = null;
      }

      const response = await fetch("/api/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          voice_id: this.config.voiceId,
        }),
      });

      if (response.ok) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        this.currentAudio = audio;
        this.isPlaying = true;

        // Update transcript immediately
        this.config.onTranscript?.({
          speaker: "assistant",
          text: text,
        });

        // Play audio and resolve when finished
        await new Promise((resolve) => {
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            this.isPlaying = false;
            this.currentAudio = null;
            resolve();
          };
          audio.play();
        });
      }
    } catch (error) {
      console.error("TTS error:", error);
      this.isPlaying = false;
    }
  }

  async startListening() {
    console.log("Starting voice recognition...");

    if (
      !("webkitSpeechRecognition" in window) &&
      !("SpeechRecognition" in window)
    ) {
      console.error("Speech recognition not supported");
      const status = document.getElementById('status-message');
      if (status) {
        status.textContent = 'Your browser does not support voice input.';
        status.classList.remove('hidden');
        status.classList.add('text-red-500', 'font-semibold');
      }

      const startBtn = document.getElementById('start-btn');
      const pauseBtn = document.getElementById('pause-btn');
      const endBtn = document.getElementById('end-btn');
      [startBtn, pauseBtn, endBtn].forEach((btn) => {
        if (btn) {
          btn.disabled = true;
          btn.classList.add('opacity-50');
        }
      });
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();

    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    // Map language codes for speech recognition
    const langMap = {
      'hi': 'hi-IN',  // Hindi (India)
      'en': 'en-US',  // English (US)
      'es': 'es-ES',  // Spanish (Spain)
      'fr': 'fr-FR',  // French (France)
    };
    
    const langCode = this.config.language || "en";
    this.recognition.lang = langMap[langCode] || langCode;
    
    console.log(`Setting speech recognition language to: ${this.recognition.lang}`);

    this.recognition.onresult = (event) => {
      if (this.ignoreRecognition) return; // Ignore unwanted early results

      let interimTranscript = "";
      let finalTranscript = ""

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      // Handle interruption - if user starts speaking while AI is talking
      if (interimTranscript && this.isPlaying) {
        console.log("User interrupting...");
        // Stop current audio
        if (this.currentAudio && !this.currentAudio.paused) {
          this.currentAudio.pause();
          this.currentAudio = null;
          this.isPlaying = false;
        }
      }

      if (finalTranscript) {
        console.log("User said:", finalTranscript);
        this.handleUserSpeech(finalTranscript);
      }
    };

    this.recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === "no-speech") {
        // Restart listening after a brief pause
        setTimeout(() => this.startListening(), 1000);
      }
    };

    this.recognition.onend = () => {
      if (this.isListening) {
        // Restart recognition to keep listening
        setTimeout(() => this.recognition.start(), 100);
      }
    };

    this.isListening = true;
    this.recognition.start();
  }

  async handleUserSpeech(transcript) {
    // Add to transcript
    this.config.onTranscript?.({
      speaker: "user",
      text: transcript,
    });

    // Send to conversation API for response
    try {
      const response = await fetch("/api/voice/conversation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          form_id: this.config.formId,
          user_input: transcript,
          voice_id: this.config.voiceId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.response) {
          await this.speak(data.response);
        }
      }
    } catch (error) {
      console.error("Conversation API error:", error);
    }
  }

  async pauseConversation() {
    console.log("Pausing server conversation...");
    this.stopListening();
  }

  async endConversation() {
    console.log("Ending server conversation...");
    this.stopListening();
    this.config.onDisconnect?.();
  }

  stopListening() {
    this.isListening = false;
    if (this.recognition) {
      this.recognition.stop();
    }
    if (this.mediaRecorder) {
      this.mediaRecorder.stop();
    }
  }
}
