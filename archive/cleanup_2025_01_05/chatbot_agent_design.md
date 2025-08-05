# Barmuda Agentic Chatbot Design

## Overview
The Barmuda chatbot is an agentic system powered by OpenAI Agents SDK and GPT-4o-mini that conducts natural, empathetic conversations to collect form responses. It uses tools to handle edge cases, maintain conversation flow, and extract structured data from unstructured chat.

## Core Architecture

### 1. Agent Framework
- **Base**: OpenAI Agents SDK (lightweight, official OpenAI framework)
- **Model**: GPT-4o-mini with function calling
- **Memory**: Session-based conversation history (last 10 messages)
- **State Management**: Firebase Realtime DB for persistence
- **Dependencies**: openai-agents, openai, firebase-admin (minimal footprint)

### 2. Agent Tools

#### FormQuestionTool
**Purpose**: Manages the current question being asked
```python
@tool
def get_next_question(state: dict) -> dict:
    """
    Retrieves the next unanswered question from the form.
    Returns question text, type, and options if applicable.
    """
```

#### SkipQuestionTool
**Purpose**: Handles explicit skip requests
```python
@tool
def skip_current_question(reason: str) -> str:
    """
    Marks current question as [SKIP] and moves to next.
    Acknowledges user's choice empathetically.
    """
```

#### ValidateResponseTool
**Purpose**: Validates responses against question types
```python
@tool
def validate_response(response: str, question_type: str) -> dict:
    """
    Checks if response matches expected type.
    Returns validation status and suggestions.
    """
```

#### ExtractMultiAnswerTool
**Purpose**: Handles pre-answering scenarios
```python
@tool
def extract_multi_answers(response: str) -> dict:
    """
    Parses responses containing multiple answers.
    Stores extras for future questions.
    """
```

#### RedirectTool
**Purpose**: Handles off-topic responses
```python
@tool
def redirect_conversation(attempt_count: int) -> str:
    """
    Redirects off-topic responses back to form.
    Max 3 attempts before [END].
    """
```

#### ClarifyResponseTool
**Purpose**: Handles vague/ambiguous responses
```python
@tool
def clarify_response(original: str, question_type: str) -> str:
    """
    Generates follow-up for unclear responses.
    Maps vague answers to closest valid option.
    """
```

#### EndConversationTool
**Purpose**: Handles conversation completion
```python
@tool
def end_conversation(reason: str) -> dict:
    """
    Tags conversation as [END].
    Triggers data extraction.
    """
```

## Conversation Flow

### 1. Initialization
```python
from agents import Agent, Runner

# Agent setup with tools
agent = Agent(
    name="FormBot",
    model="gpt-4o-mini",
    instructions="""You are a friendly, empathetic chatbot collecting form responses naturally.
    
    Guidelines:
    - Ask ONE question at a time
    - Use casual language with emojis 😊
    - Never show multiple choice options (anti-bias)
    - Handle edge cases gracefully
    - Respect user's privacy and choices""",
    functions=[
        get_next_question,
        skip_current_question,
        validate_response,
        extract_multi_answers,
        redirect_conversation,
        clarify_response,
        end_conversation
    ]
)
```

### 2. Main Prompt Template
```python
CONVERSATION_PROMPT = """
You are a friendly, empathetic chatbot collecting form responses naturally.

Guidelines:
- Ask ONE question at a time
- Use casual language with emojis 😊
- Never show multiple choice options (anti-bias)
- Handle edge cases gracefully
- Respect user's privacy and choices

Current form: {form_title}
Questions: {questions}
Chat history: {chat_history}
Current question: {current_question}

Tools available:
{tools}

Format:
Thought: Analyze user response and decide action
Action: Tool to use
Action Input: Parameters for tool
Observation: Tool result
... (repeat as needed)
Response: Natural message to user
"""
```

## Edge Case Handling

### 1. Off-Topic Responses
**Detection**: Response unrelated to current question
**Tool**: RedirectTool
**Example**:
```
User: "What's the weather like?"
Bot: "That's a bit bananas! 😄 Let's focus on your favorite hobby first."
```
**Limit**: 3 redirects before [END]

### 2. Skip Requests
**Detection**: Keywords like "skip", "pass", "next"
**Tool**: SkipQuestionTool
**Example**:
```
User: "Skip that please"
Bot: "Totally cool! 😊 Moving on..."
```
**Tag**: [SKIP] in response data

### 3. Pre-Answering
**Detection**: Multiple data points in single response
**Tool**: ExtractMultiAnswerTool
**Example**:
```
Bot: "What's your name?"
User: "Alex, 25, from LA"
Bot: "Noted your name, Alex! 😎 I'll remember the age and location for later."
```

### 4. Conflicting Answers
**Detection**: Contradicts previous response
**Tool**: Memory update + acknowledgment
**Example**:
```
User: "Actually, change that to no coffee"
Bot: "Updating that to no—got it! ☕"
```
**Priority**: Latest answer prevails

### 5. Vague Responses
**Detection**: Unclear answer for typed questions
**Tool**: ClarifyResponseTool
**Example**:
```
Bot: "Rate 1-5?"
User: "Meh"
Bot: "Meh—like a 2 or 3? 😅"
```

### 6. No-Fit Responses
**Detection**: Answer outside predefined options
**Tool**: Accept + backend bucketing
**Example**:
```
Bot: "Favorite color?"
User: "Yellow" (not in options)
Bot: "Yellow's sunny! 🌞"
```
**Backend**: Maps to "other"

### 7. Abandonment
**Detection**: 5+ min inactivity
**Tool**: EndConversationTool
**Action**: Save partial with flag

### 8. Early Exit
**Detection**: "I'm done", "stop", etc.
**Tool**: EndConversationTool
**Example**:
```
User: "I'm done now"
Bot: "Sure thing! Thanks for your time. 👋"
```

## Technical Implementation

### 1. Session Management
```python
session_data = {
    'session_id': generate_session_id(),
    'form_id': form_id,
    'device_id': fingerprint_js_id,
    'location': geo_location,
    'start_time': timestamp,
    'messages': [],
    'responses': {},
    'metadata': {
        'partial': False,
        'skip_count': 0,
        'redirect_count': 0
    }
}
```

### 2. Message Flow
```python
async def process_message(user_input, session_id):
    # 1. Load session state
    session = await load_session(session_id)
    
    # 2. Run agent
    response = await agent.ainvoke({
        'input': user_input,
        'session_state': session
    })
    
    # 3. Update Firebase
    await update_chat_history(session_id, response)
    
    # 4. Check for extraction triggers
    if should_extract(response):
        await trigger_extraction(session_id)
    
    return response
```

### 3. Data Extraction
```python
async def extract_responses(session_id):
    # Get full chat transcript
    transcript = await get_transcript(session_id)
    
    # Use LLM for extraction
    extraction_prompt = """
    Extract structured responses from chat:
    - Map answers to questions
    - Handle [SKIP] tags
    - Bucket no-fit responses
    - Prioritize latest for conflicts
    """
    
    structured_data = await extraction_llm.ainvoke({
        'transcript': transcript,
        'form_structure': form_data
    })
    
    return structured_data
```

## Performance Constraints

### 1. Response Time
- Target: <2s per response
- Optimization: Tool parallelization

### 2. Token Limits
- Max conversation: 30 messages
- Memory window: Last 10 messages

### 3. Rate Limiting
- 50 messages/hour per device_id
- IP-based fallback

## Security Measures

### 1. Prompt Injection Protection
- Input sanitization
- Response validation
- System prompt isolation

### 2. Data Privacy
- No PII in logs
- Encrypted Firebase storage
- Anonymous session IDs

### 3. Abuse Prevention
- Device fingerprinting
- Rate limiting
- Duplicate detection

## Monitoring & Metrics

### 1. Conversation Metrics
- Completion rate
- Skip rate per question
- Average conversation length
- Edge case frequency

### 2. Performance Metrics
- Response latency
- Token usage
- Error rates
- Tool usage patterns

### 3. Quality Metrics
- Extraction accuracy
- User satisfaction (inferred)
- Redirect effectiveness

## Integration Points

### 1. Frontend (React/Tailwind)
- Real-time chat UI
- Typing indicators
- Message status

### 2. Backend (Flask)
- `/api/chat_message` endpoint
- Session management
- Tool execution

### 3. Firebase
- Realtime DB for chat sync
- Firestore for responses
- Authentication state

### 4. OpenAI
- GPT-4o-mini for conversation
- Structured output mode
- Function calling

## Testing Strategy

### 1. Unit Tests
- Individual tool functionality
- Edge case detection
- Response validation

### 2. Integration Tests
- Full conversation flows
- Multi-turn interactions
- Extraction accuracy

### 3. Edge Case Tests
All scenarios from EdgeCases.md:
- Off-topic (3x redirect)
- Skips
- Pre-answers
- Conflicts
- Vague responses
- No-fit answers
- Abandonment
- Early exit
- Invalid types
- Multi-language
- Abuse attempts

## Deployment Considerations

### 1. Environment Variables
```
OPENAI_API_KEY=
FIREBASE_CONFIG=
RATE_LIMIT_CONFIG=
```

### 2. Scaling
- Stateless agent design
- Firebase auto-scaling
- Vercel edge functions

### 3. Cost Optimization
- GPT-4o-mini for efficiency
- Smart prompt caching
- Batch extractions

## Future Enhancements

### 1. Advanced Tools
- Sentiment analysis tool
- Language detection tool
- Context retrieval tool

### 2. Multi-Modal
- Image uploads
- Voice responses
- File attachments

### 3. Analytics
- Real-time dashboards
- ML-based insights
- Conversion optimization