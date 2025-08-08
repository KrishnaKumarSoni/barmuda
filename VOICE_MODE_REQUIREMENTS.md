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
- Separate voice agent system (parallel to existing chat agent)
- Form data transformation for voice conversations
- Custom tools for ElevenLabs agent integration

**Voice Agent Features:**
- Natural conversation flow with interruption support
- Automatic turn-taking and pause detection
- One question at a time approach
- Context-aware follow-ups for vague responses
- Graceful handling of off-topic responses

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

#### 8.1 Backend Components
**New Files:**
- `voice_agent.py` - ElevenLabs integration
- `voice_handler.py` - Voice-specific endpoints
- `voice_tools.py` - ElevenLabs function tools

**Modified Files:**
- `app.py` - Add voice routes and mode detection
- `templates/dashboard.html` - Add mode toggle UI
- `templates/edit-form.html` - Add voice settings panel

#### 8.2 Frontend Components
**New Files:**
- `static/js/voice-interface.js` - Voice UI handling
- `templates/voice.html` - Voice conversation interface
- `static/css/voice-ui.css` - Voice-specific styles

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
- ElevenLabs integration setup
- Basic voice agent implementation
- Form mode toggle in editor

### Phase 2: Voice Interface Development
- Voice conversation UI
- Widget transformation for embed
- Multi-lingual voice support

### Phase 3: Data Integration & Testing
- Unified response storage
- Comprehensive edge case testing
- Performance optimization

### Phase 4: Production Deployment
- Security hardening
- Monitoring implementation
- User documentation and rollout