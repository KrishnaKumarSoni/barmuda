# Voice Mode Feature Requirements

## Overview
Add native voice conversation capability to Barmuda forms using ElevenLabs Conversational AI as an alternative to text chat mode. Forms can be set to either chat mode or voice mode (mutually exclusive).

## Core Requirements

### 1. Form Mode Selection
**Location:** Form Editor (`/edit-form`)

**UI Components:**
- Radio button toggle: Chat Mode | Voice Mode
- Voice settings panel (appears when Voice Mode selected):
  - Language dropdown (English, Spanish, French, Hindi, etc.)
  - Voice selection dropdown (populated based on selected language)
  - Optional: Voice speed/tone controls

**Database Schema Changes:**
```json
{
  "form_id": "...",
  "title": "...",
  "questions": [...],
  "active": true,
  "mode": "chat | voice",  // New field
  "voice_settings": {      // New nested object
    "language": "en",
    "voice_id": "elevenlabs_voice_id",
    "speed": "normal",     // optional
    "tone": "friendly"     // optional
  }
}
```

### 2. Voice Agent Implementation
**Technology:** ElevenLabs Conversational AI 2.0

**Architecture:**
- Agent created via ElevenLabs platform/API with form-specific configuration
- Server Tools via webhook endpoints for form logic
- JavaScript SDK integration for client-side voice interface
- GPT-4 model connection for conversation intelligence

**Agent Configuration:**
```json
{
  "name": "Form Interview Agent",
  "prompt": "You are conducting a voice interview...",
  "voice_id": "selected_voice_based_on_language",
  "model": "gpt-4",
  "tools": [
    {
      "type": "server",
      "name": "save_response",
      "webhook_url": "https://barmuda.in/api/voice/save_response"
    },
    {
      "type": "server", 
      "name": "get_next_question",
      "webhook_url": "https://barmuda.in/api/voice/next_question"
    },
    {
      "type": "server",
      "name": "end_interview", 
      "webhook_url": "https://barmuda.in/api/voice/end_interview"
    }
  ]
}
```

**Voice Agent Features:**
- Natural conversation flow with interruption support (ElevenLabs 2.0 turn-taking)
- Automatic pause detection and speaking turns
- Multi-model support (GPT-4 integration)  
- Real-time webhook calls to our server tools
- Built-in RAG for knowledge base access

### 3. Response Routing
**URL Structure:**
- Chat Mode: `/form/{form_id}` (existing)
- Voice Mode: `/voice/{form_id}` (new)
- Both check `form.mode` and redirect accordingly

**Embed Widget Behavior:**
- Detects form mode automatically
- Renders appropriate interface based on mode

### 4. Voice User Interface

#### 4.1 Web Interface (`/voice/{form_id}`)
**Components:**
- Audio visualization (waveform/bars)
- Large "Start Interview" button
- Real-time transcript display
- Control buttons: Pause | Resume | End Call
- Status indicators: Connecting | Listening | Speaking | Paused

#### 4.2 Embed Widget Transformation
**Chat Mode:** Standard FAB → Modal (existing behavior)

**Voice Mode:** FAB transforms into voice bubble:
```
Initial: [🎤] FAB button
↓ (on click)
Active: [Transcript bubble with "Tell me about..." + ⏸️📞 controls]
```

**Voice Bubble Components:**
- Truncated transcript text (last agent message)
- Pause button (⏸️)
- Hang up button (📞)
- Visual speaking indicator

### 5. Multi-Lingual Support
**Language Selection:** Form creator chooses language in form settings
**Voice Mapping:** Each language maps to appropriate ElevenLabs voice
**Supported Languages (Initial):**
- English (US/UK variants)
- Spanish (ES/LATAM)
- French
- German
- Italian
- Portuguese
- Hindi
- Mandarin
- Japanese

**Voice Quality:** Use ElevenLabs premium voices for natural conversations

### 6. Data Extraction & Storage
**Unified Storage:** Both chat and voice responses save to same Firestore structure
**Additional Fields for Voice:**
```json
{
  "session_id": "...",
  "form_id": "...",
  "mode": "voice",
  "language": "en",
  "responses": {...},
  "transcript": "full conversation text",
  "audio_duration": 180,  // seconds
  "voice_metadata": {
    "interruptions": 3,
    "pause_count": 2,
    "call_quality": "excellent"
  }
}
```

**No Audio Storage:** Only store transcripts, not audio recordings (privacy)

### 7. Dashboard Integration
**Form Management:**
- Mode indicator in forms list
- Voice/Chat icon in form cards
- Mode switching in form editor (can change anytime)

**Response Viewing:**
- Unified view for both chat and voice responses
- Voice responses show transcript
- Mode indicator in response metadata

### 8. Technical Implementation

#### 8.1 Backend Components - Server Tools Architecture
**New Files:**
- `voice_agent.py` - ElevenLabs agent creation and management
- `voice_webhooks.py` - Webhook endpoints for ElevenLabs server tools

**Webhook Endpoints (Server Tools):**
```python
# voice_webhooks.py
@app.route('/api/voice/save_response', methods=['POST'])
def voice_save_response():
    """Server Tool: Save user response to current question"""
    data = request.json
    session_id = data['session_id']
    response_text = data['response']
    # Reuse existing session management
    return {"status": "saved", "next_action": "continue"}

@app.route('/api/voice/next_question', methods=['POST']) 
def voice_next_question():
    """Server Tool: Get next question in form"""
    data = request.json
    session_id = data['session_id']
    # Use existing form logic
    return {"question": "What's your favorite color?", "type": "text"}

@app.route('/api/voice/end_interview', methods=['POST'])
def voice_end_interview():
    """Server Tool: End conversation and extract data"""
    data = request.json
    session_id = data['session_id'] 
    # Trigger existing extraction pipeline
    return {"status": "completed", "message": "Thank you for your time!"}
```

**Modified Files:**
- `app.py` - Add webhook routes and agent creation endpoints
- `templates/dashboard.html` - Add mode toggle UI
- `templates/edit-form.html` - Add voice settings panel

#### 8.2 Frontend Components - JavaScript SDK Integration
**New Files:**
- `static/js/voice-interface.js` - ElevenLabs JS SDK integration
- `templates/voice.html` - Voice conversation interface
- `static/css/voice-ui.css` - Voice-specific styles

**JavaScript SDK Usage:**
```javascript
// voice-interface.js
import { ElevenLabsSDK } from '@elevenlabs/js-sdk';

const sdk = new ElevenLabsSDK({
    apiKey: 'public_api_key' // Client-side key
});

async function startVoiceInterview(formId) {
    const agent = await sdk.createAgent({
        agentId: `form_agent_${formId}`,
        onMessage: (transcript) => updateTranscriptBubble(transcript),
        onToolCall: (tool) => console.log('Tool executed:', tool)
    });
    
    await agent.startConversation();
}
```

**Modified Files:**
- `static/widget.js` - Voice mode detection and FAB transformation

### 9. Error Handling & Edge Cases
**Connection Issues:**
- Fallback to retry with clear user feedback
- Graceful degradation to chat mode option

**Voice Quality Issues:**
- Background noise detection
- Poor audio quality warnings
- Microphone permission handling

**Conversation Edge Cases:**
- Off-topic responses (redirect max 3 times)
- Long pauses (prompt to continue)
- Premature ending (save partial responses)
- Language detection mismatch (use form's set language)

### 10. Performance & Scalability
**Latency Targets:**
- <200ms response time for voice interactions
- Smooth real-time audio streaming
- Efficient transcript processing

**Resource Management:**
- Connection pooling for ElevenLabs API
- Proper session cleanup
- Rate limiting per form/IP

### 11. Security & Privacy
**Data Protection:**
- No audio recording storage
- Encrypted transcript transmission
- GDPR/privacy compliance for voice data
- Clear privacy disclosures for voice mode

**API Security:**
- Secure ElevenLabs API key management
- Input validation for voice commands
- Protection against voice injection attacks

### 12. Testing Requirements
**Voice Conversation Testing:**
- Multi-lingual voice quality validation
- Interruption handling verification
- Turn-taking accuracy testing
- Edge case conversation flows

**UI/UX Testing:**
- Widget transformation behavior
- Cross-device voice interface testing
- Accessibility compliance for voice features

### 13. Deployment Considerations
**Environment Variables:**
- `ELEVENLABS_API_KEY`
- `VOICE_WEBHOOK_URL`
- Voice feature toggle flags

**Monitoring:**
- Voice conversation success rates
- Audio quality metrics
- Language detection accuracy
- User preference analytics (chat vs voice adoption)

## Implementation Phases

### Phase 1: Core Voice Infrastructure  
- ElevenLabs API key setup and agent creation endpoints
- Webhook server tools implementation (`/api/voice/*` endpoints)
- Form mode toggle in editor UI
- Database schema updates for voice mode

### Phase 2: Voice Interface Development
- ElevenLabs JavaScript SDK integration
- Voice conversation interface (`/voice/{form_id}`)
- Widget FAB transformation for voice mode
- Multi-lingual voice settings and voice selection

### Phase 3: Data Integration & Session Management
- Unified response storage (reuse existing Firestore structure)
- Voice session management with existing session logic
- Data extraction pipeline integration
- Comprehensive edge case testing

### Phase 4: Production Deployment & Optimization
- Security hardening for webhook endpoints
- Performance optimization for real-time voice
- Monitoring and analytics for voice conversations
- User documentation and gradual rollout

## Corrected Integration Patterns

### Agent Creation Flow
```python
# voice_agent.py - Correct ElevenLabs integration
import elevenlabs
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

def create_form_voice_agent(form_id, form_data):
    """Create ElevenLabs agent for specific form"""
    
    # Transform form questions into conversation prompt
    prompt = generate_interview_prompt(form_data)
    
    # Create agent with server tools
    agent = client.conversational_ai.create_agent(
        name=f"Form Interview: {form_data['title']}",
        prompt=prompt,
        voice_id=form_data.get('voice_settings', {}).get('voice_id', 'default'),
        model='gpt-4',
        tools=[
            {
                "type": "server",
                "name": "save_response", 
                "description": "Save user's response to current question",
                "webhook_url": f"https://barmuda.in/api/voice/save_response",
                "parameters": {
                    "session_id": {"type": "string"},
                    "response": {"type": "string"}
                }
            },
            {
                "type": "server",
                "name": "get_next_question",
                "description": "Get the next question to ask", 
                "webhook_url": f"https://barmuda.in/api/voice/next_question",
                "parameters": {
                    "session_id": {"type": "string"}
                }
            }
        ]
    )
    
    return agent.agent_id
```

### Session Management Integration
```python
# Reuse existing session logic with voice mode
def start_voice_session(form_id, device_id, location=None):
    """Initialize voice session using existing ChatSession"""
    
    form = get_form(form_id)
    if form['mode'] != 'voice':
        raise ValueError("Form not configured for voice mode")
    
    # Reuse existing session management
    session = ChatSession(
        session_id=generate_session_id(),
        form_id=form_id,
        form_data=form,
        metadata={
            'mode': 'voice',
            'device_id': device_id,
            'location': location,
            'language': form.get('voice_settings', {}).get('language', 'en')
        }
    )
    
    # Create ElevenLabs agent for this session
    agent_id = create_form_voice_agent(form_id, form)
    session.metadata['agent_id'] = agent_id
    
    return session
```

### Widget Integration Pattern
```javascript
// static/widget.js - Corrected voice mode handling
class BarmudaWidget {
    constructor(config) {
        this.formId = config.formId;
        this.mode = null; // Will be detected from form data
    }
    
    async init() {
        // Fetch form configuration to determine mode
        const formData = await fetch(`/api/form/${this.formId}`).then(r => r.json());
        this.mode = formData.mode;
        
        if (this.mode === 'voice') {
            await this.initVoiceMode(formData);
        } else {
            this.initChatMode(formData); // existing
        }
    }
    
    async initVoiceMode(formData) {
        // Import ElevenLabs SDK dynamically
        const { ElevenLabs } = await import('@elevenlabs/js-sdk');
        
        this.elevenlabs = new ElevenLabs({
            apiKey: formData.elevenlabs_public_key
        });
        
        // Create voice FAB
        this.createVoiceFAB();
    }
    
    createVoiceFAB() {
        this.fab = document.createElement('div');
        this.fab.className = 'barmuda-voice-fab';
        this.fab.innerHTML = `
            <div class="fab-button" onclick="this.startVoiceInterview()">
                <i class="ph ph-microphone"></i>
            </div>
        `;
        
        document.body.appendChild(this.fab);
    }
    
    async startVoiceInterview() {
        // Start voice session
        const session = await fetch(`/api/voice/start/${this.formId}`, {
            method: 'POST',
            body: JSON.stringify({
                device_id: await this.getDeviceId(),
                location: this.getLocation()
            })
        }).then(r => r.json());
        
        // Transform FAB to transcript bubble
        this.transformToTranscriptBubble();
        
        // Start ElevenLabs conversation
        await this.elevenlabs.startConversation({
            agentId: session.agent_id,
            onTranscript: (text) => this.updateTranscript(text),
            onEnd: () => this.endInterview()
        });
    }
    
    transformToTranscriptBubble() {
        this.fab.innerHTML = `
            <div class="transcript-bubble">
                <div class="transcript-text">Starting interview...</div>
                <div class="voice-controls">
                    <button class="pause-btn" onclick="this.pauseInterview()">⏸️</button>
                    <button class="end-btn" onclick="this.endInterview()">📞</button>
                </div>
            </div>
        `;
    }
}
```

This corrected approach properly uses ElevenLabs' actual API patterns and integrates with our existing session management system.