(function() {
    'use strict';
    
    // Configuration from script attributes
    const currentScript = document.currentScript || document.querySelector('script[src*="widget.js"]');
    let apiBase = currentScript.src.replace('/widget.js', '');
    
    // Remove query parameters from API base (like cache busting ?v=timestamp)
    if (apiBase.includes('?')) {
        apiBase = apiBase.split('?')[0];
    }
    
    // If the script is loaded from a file:// URL or local context, default to production
    if (apiBase.startsWith('file://') || apiBase === 'file:' || !apiBase.startsWith('http')) {
        apiBase = 'https://barmuda.in';
    }
    
    const config = {
        formId: currentScript.getAttribute('data-form-id'),
        position: currentScript.getAttribute('data-position') || 'bottom-right',
        color: currentScript.getAttribute('data-color') || '#cc5500',
        apiBase: apiBase
    };
    
    console.log('Widget configuration:', config);
    
    // Prevent multiple initialization
    if (window.BarmudaWidget) {
        console.warn('Barmuda Widget already initialized');
        return;
    }
    
    // Widget state
    let isOpen = false;
    let sessionId = null;
    let deviceId = null;
    let messageCount = 0;
    let isEnded = false;
    
    // Create widget namespace
    window.BarmudaWidget = {
        open: openWidget,
        close: closeWidget,
        toggle: toggleWidget
    };
    
    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }
    
    function initWidget() {
        if (!config.formId) {
            console.error('Barmuda Widget: data-form-id is required');
            return;
        }
        
        createWidgetElements();
        initializeDeviceId();
        setupEventListeners();
    }
    
    function createWidgetElements() {
        // Create FAB button
        const fab = document.createElement('div');
        fab.id = 'barmuda-fab';
        fab.innerHTML = `
            <div class="barmuda-fab-button">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H5.17L4 17.17V4H20V16Z" fill="white"/>
                    <circle cx="8" cy="10" r="1" fill="white"/>
                    <circle cx="12" cy="10" r="1" fill="white"/>
                    <circle cx="16" cy="10" r="1" fill="white"/>
                </svg>
            </div>
        `;
        
        // Create modal overlay
        const modal = document.createElement('div');
        modal.id = 'barmuda-modal';
        modal.innerHTML = `
            <div class="barmuda-modal-overlay">
                <div class="barmuda-modal-content">
                    <!-- Modal Header -->
                    <div class="barmuda-modal-header">
                        <div class="barmuda-form-title">Loading...</div>
                        <div class="barmuda-modal-controls">
                            <div class="barmuda-powered-by">powered by barmuda</div>
                            <button class="barmuda-close-btn" onclick="window.BarmudaWidget.close()">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Chat Area -->
                    <div class="barmuda-chat-container">
                        <div id="barmuda-chat-messages" class="barmuda-chat-messages">
                            <!-- Messages will be added here -->
                        </div>
                    </div>
                    
                    <!-- Input Area -->
                    <div class="barmuda-input-container">
                        <div class="barmuda-input-wrapper">
                            <input 
                                type="text" 
                                id="barmuda-message-input" 
                                placeholder="Type your message..."
                                disabled
                            >
                            <button 
                                id="barmuda-send-button" 
                                class="barmuda-send-btn"
                                disabled
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Completion Screen -->
                    <div id="barmuda-completion" class="barmuda-completion hidden">
                        <div class="barmuda-completion-content">
                            <div class="barmuda-completion-icon">
                                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <circle cx="12" cy="12" r="10" fill="${config.color}"/>
                                    <path d="M9 12L11 14L15 10" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </div>
                            <h3>Thanks for the chat! 😊</h3>
                            <p>Your responses have been shared and will help make a real difference.</p>
                            <button onclick="window.BarmudaWidget.close()" class="barmuda-done-btn">Done</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add CSS styles
        const styles = document.createElement('style');
        styles.textContent = getWidgetCSS();
        
        // Append to document
        document.head.appendChild(styles);
        document.body.appendChild(fab);
        document.body.appendChild(modal);
    }
    
    function getWidgetCSS() {
        const position = config.position === 'bottom-left' ? 'left: 24px;' : 'right: 24px;';
        
        return `
            /* FAB Button */
            #barmuda-fab {
                position: fixed;
                bottom: 24px;
                ${position}
                z-index: 999999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .barmuda-fab-button {
                width: 60px;
                height: 60px;
                background: linear-gradient(135deg, ${config.color}, #d12b2e);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(204, 85, 0, 0.3);
                transition: all 0.3s ease;
                animation: barmuda-pulse 2s infinite;
            }
            
            .barmuda-fab-button:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 25px rgba(204, 85, 0, 0.4);
            }
            
            @keyframes barmuda-pulse {
                0% { box-shadow: 0 4px 20px rgba(204, 85, 0, 0.3); }
                50% { box-shadow: 0 4px 20px rgba(204, 85, 0, 0.5), 0 0 0 10px rgba(204, 85, 0, 0.1); }
                100% { box-shadow: 0 4px 20px rgba(204, 85, 0, 0.3); }
            }
            
            /* Modal */
            #barmuda-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 1000000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                pointer-events: none;
            }
            
            #barmuda-modal.open {
                opacity: 1;
                visibility: visible;
                pointer-events: auto;
            }
            
            .barmuda-modal-overlay {
                width: 100%;
                height: 100%;
                background: transparent;
                display: flex;
                align-items: flex-end;
                justify-content: ${config.position === 'bottom-left' ? 'flex-start' : 'flex-end'};
                padding: 20px;
                pointer-events: none;
            }
            
            .barmuda-modal-content {
                background: #fef5e0;
                border-radius: 16px;
                width: 380px;
                height: 500px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                transform: translateY(20px) scale(0.95);
                transition: transform 0.3s ease;
                pointer-events: auto;
                margin-bottom: 80px;
                ${config.position === 'bottom-left' ? 'margin-left: 4px;' : 'margin-right: 4px;'}
            }
            
            #barmuda-modal.open .barmuda-modal-content {
                transform: translateY(0) scale(1);
            }
            
            /* Header */
            .barmuda-modal-header {
                background: white;
                border-bottom: 1px solid #fce9c1;
                padding: 16px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-shrink: 0;
            }
            
            .barmuda-form-title {
                font-size: 18px;
                font-weight: 600;
                color: #cc5500;
                margin: 0;
                flex: 1;
            }
            
            .barmuda-modal-controls {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .barmuda-powered-by {
                font-size: 11px;
                color: #999;
                text-decoration: none !important;
                cursor: default !important;
                pointer-events: none !important;
                user-select: none !important;
                border: none !important;
                background: transparent !important;
                outline: none !important;
            }
            
            .barmuda-powered-by * {
                pointer-events: none !important;
                cursor: default !important;
                text-decoration: none !important;
            }
            
            .barmuda-close-btn {
                background: none;
                border: none;
                cursor: pointer;
                color: #666;
                padding: 4px;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            .barmuda-close-btn:hover {
                background: #f0f0f0;
                color: #333;
            }
            
            /* Chat Area */
            .barmuda-chat-container {
                flex: 1;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            
            .barmuda-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px 20px;
                scroll-behavior: smooth;
            }
            
            .barmuda-message {
                margin-bottom: 16px;
                opacity: 0;
                transform: translateY(10px);
                animation: barmuda-message-enter 0.3s ease forwards;
            }
            
            @keyframes barmuda-message-enter {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .barmuda-message.user {
                display: flex;
                justify-content: flex-end;
            }
            
            .barmuda-message.assistant {
                display: flex;
                justify-content: flex-start;
            }
            
            .barmuda-message-content {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 18px;
                font-size: 14px;
                line-height: 1.4;
            }
            
            .barmuda-message.user .barmuda-message-content {
                background: ${config.color};
                color: white;
                border-bottom-right-radius: 6px;
            }
            
            .barmuda-message.assistant .barmuda-message-content {
                background: white;
                color: #333;
                border: 1px solid #e5e7eb;
                border-bottom-left-radius: 6px;
            }
            
            .barmuda-message-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
            }
            
            /* Typing Indicator */
            .barmuda-typing {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 12px 16px;
            }
            
            .barmuda-typing-dot {
                width: 6px;
                height: 6px;
                background: #666;
                border-radius: 50%;
                animation: barmuda-typing-bounce 1.4s infinite ease-in-out;
            }
            
            .barmuda-typing-dot:nth-child(1) { animation-delay: -0.32s; }
            .barmuda-typing-dot:nth-child(2) { animation-delay: -0.16s; }
            .barmuda-typing-dot:nth-child(3) { animation-delay: 0s; }
            
            @keyframes barmuda-typing-bounce {
                0%, 80%, 100% { 
                    transform: scale(0.8);
                    opacity: 0.5;
                }
                40% { 
                    transform: scale(1.2);
                    opacity: 1;
                }
            }
            
            /* Input Area */
            .barmuda-input-container {
                background: white;
                border-top: 1px solid #fce9c1;
                padding: 16px 20px;
                flex-shrink: 0;
            }
            
            .barmuda-input-wrapper {
                display: flex;
                gap: 12px;
                align-items: center;
                background: #f9f9f9;
                border: 1px solid #e5e7eb;
                border-radius: 25px;
                padding: 8px 16px;
            }
            
            #barmuda-message-input {
                flex: 1;
                border: none;
                background: none;
                outline: none;
                font-size: 14px;
                color: #333;
                font-family: inherit;
            }
            
            #barmuda-message-input::placeholder {
                color: #999;
            }
            
            .barmuda-send-btn {
                background: ${config.color};
                border: none;
                border-radius: 50%;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .barmuda-send-btn:hover:not(:disabled) {
                background: #b84600;
                transform: scale(1.05);
            }
            
            .barmuda-send-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            /* Completion Screen */
            .barmuda-completion {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(254, 245, 224, 0.95);
                backdrop-filter: blur(8px);
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }
            
            .barmuda-completion.show {
                opacity: 1;
                visibility: visible;
            }
            
            .barmuda-completion-content {
                text-align: center;
                padding: 40px;
            }
            
            .barmuda-completion-icon {
                margin-bottom: 20px;
            }
            
            .barmuda-completion h3 {
                font-size: 20px;
                font-weight: 600;
                color: #333;
                margin: 0 0 8px 0;
            }
            
            .barmuda-completion p {
                font-size: 14px;
                color: #666;
                margin: 0 0 24px 0;
                line-height: 1.5;
            }
            
            .barmuda-done-btn {
                background: ${config.color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .barmuda-done-btn:hover {
                background: #b84600;
            }
            
            /* Mobile Responsive */
            @media (max-width: 768px) {
                .barmuda-modal-overlay {
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(4px);
                    align-items: center;
                    justify-content: center;
                    padding: 16px;
                }
                
                .barmuda-modal-content {
                    width: 100%;
                    max-width: 400px;
                    height: 70vh;
                    max-height: 500px;
                    margin: 0;
                    border-radius: 16px;
                }
                
                #barmuda-fab {
                    bottom: 20px;
                    ${config.position === 'bottom-left' ? 'left: 20px;' : 'right: 20px;'}
                }
                
                .barmuda-fab-button {
                    width: 56px;
                    height: 56px;
                }
            }
            
            @media (max-width: 480px) {
                .barmuda-modal-content {
                    width: calc(100% - 32px);
                    height: 65vh;
                    max-height: 450px;
                }
            }
            
            /* Hidden utility class */
            .hidden {
                display: none !important;
            }
        `;
    }
    
    function setupEventListeners() {
        // FAB click handler
        document.getElementById('barmuda-fab').addEventListener('click', toggleWidget);
        
        // Modal overlay click to close (only on mobile with backdrop)
        document.querySelector('.barmuda-modal-overlay').addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            // Only close on overlay click for mobile (when backdrop is visible)
            if (e.target === this && window.innerWidth <= 768) {
                closeWidget();
            }
        });
        
        // Send button and enter key
        document.getElementById('barmuda-send-button').addEventListener('click', sendMessage);
        document.getElementById('barmuda-message-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Escape key to close
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && isOpen) {
                closeWidget();
            }
        });
        
        // Prevent any unwanted navigation from modal content
        document.querySelector('.barmuda-modal-content').addEventListener('click', function(e) {
            // Only prevent default for non-interactive elements
            if (!e.target.matches('button, input, textarea, [onclick], [href]')) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }
    
    async function initializeDeviceId() {
        try {
            // Try to load FingerprintJS dynamically
            if (typeof FingerprintJS === 'undefined') {
                await loadScript('https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs@4/dist/fp.min.js');
            }
            
            if (typeof FingerprintJS !== 'undefined') {
                const fp = await FingerprintJS.load();
                const result = await fp.get();
                deviceId = result.visitorId;
            } else {
                throw new Error('FingerprintJS not available');
            }
        } catch (error) {
            // Fallback to localStorage
            deviceId = localStorage.getItem('barmuda_widget_device_id');
            if (!deviceId) {
                deviceId = 'widget-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('barmuda_widget_device_id', deviceId);
            }
        }
    }
    
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    function openWidget() {
        if (isOpen) return;
        
        isOpen = true;
        document.getElementById('barmuda-modal').classList.add('open');
        // Only prevent body scroll on mobile
        if (window.innerWidth <= 768) {
            document.body.style.overflow = 'hidden';
        }
        
        // Initialize chat if not already done
        if (!sessionId) {
            initializeChat();
        }
        
        // Focus input
        setTimeout(() => {
            const input = document.getElementById('barmuda-message-input');
            if (input && !input.disabled) {
                input.focus();
            }
        }, 300);
    }
    
    function closeWidget() {
        if (!isOpen) return;
        
        isOpen = false;
        document.getElementById('barmuda-modal').classList.remove('open');
        document.body.style.overflow = '';
    }
    
    function toggleWidget() {
        if (isOpen) {
            closeWidget();
        } else {
            openWidget();
        }
    }
    
    async function initializeChat() {
        try {
            showTypingIndicator();
            
            // Start chat session
            const apiUrl = `${config.apiBase}/api/chat/start`;
            console.log('Making request to:', apiUrl);
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    form_id: config.formId,
                    device_id: deviceId,
                    location: {}
                })
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                const errorText = await response.text();
                console.log('Error response text:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const responseText = await response.text();
            console.log('Raw response text:', responseText.substring(0, 200) + '...');
            
            let data;
            try {
                data = JSON.parse(responseText);
                console.log('Parsed response data:', data);
            } catch (parseError) {
                console.error('JSON parsing failed:', parseError);
                console.log('Full response text:', responseText);
                throw new Error(`Invalid JSON response: ${parseError.message}`);
            }
            
            if (data.success) {
                sessionId = data.session_id;
                
                // Get form title from public API
                try {
                    const formResponse = await fetch(`${config.apiBase}/api/form/${config.formId}/public`);
                    console.log('Form title request to:', `${config.apiBase}/api/form/${config.formId}/public`);
                    console.log('Form title response status:', formResponse.status);
                    
                    if (formResponse.ok) {
                        const formData = await formResponse.json();
                        console.log('Form title data:', formData);
                        
                        if (formData.success && formData.form.title) {
                            document.querySelector('.barmuda-form-title').textContent = formData.form.title;
                            console.log('Form title set to:', formData.form.title);
                        } else {
                            console.log('Form title not available in response, using default');
                            document.querySelector('.barmuda-form-title').textContent = 'Survey';
                        }
                    } else {
                        throw new Error(`HTTP ${formResponse.status}`);
                    }
                } catch (error) {
                    console.log('Could not load form title, using default:', error);
                    document.querySelector('.barmuda-form-title').textContent = 'Survey';
                }
                
                hideTypingIndicator();
                
                if (data.ended) {
                    isEnded = true;
                    if (data.chat_history) {
                        data.chat_history.forEach(msg => {
                            const timestamp = msg.timestamp ? new Date(msg.timestamp) : null;
                            if (msg.role === 'user') {
                                addMessage('user', msg.content, timestamp);
                            } else if (msg.role === 'assistant') {
                                addMessage('assistant', msg.content, timestamp);
                            }
                        });
                    }
                    
                    addMessage('assistant', data.greeting);
                    setTimeout(() => {
                        showCompletionScreen();
                    }, 1500);
                    
                    document.getElementById('barmuda-message-input').disabled = true;
                    document.getElementById('barmuda-send-button').disabled = true;
                } else if (data.resumed && data.chat_history) {
                    data.chat_history.forEach(msg => {
                        const timestamp = msg.timestamp ? new Date(msg.timestamp) : null;
                        if (msg.role === 'user') {
                            addMessage('user', msg.content, timestamp);
                        } else if (msg.role === 'assistant') {
                            addMessage('assistant', msg.content, timestamp);
                        }
                    });
                    addMessage('assistant', data.greeting);
                    enableInput();
                } else {
                    addMessage('assistant', data.greeting);
                    enableInput();
                }
            } else {
                hideTypingIndicator();
                throw new Error(data.error || 'Failed to start chat');
            }
            
        } catch (error) {
            console.error('Error initializing chat:', error);
            hideTypingIndicator();
            addMessage('system', 'Sorry, there was an error starting the chat. Please try again.');
        }
    }
    
    function addMessage(sender, message, timestamp = null) {
        const messagesContainer = document.getElementById('barmuda-chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `barmuda-message ${sender}`;
        
        const now = timestamp || new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        if (sender === 'user' || sender === 'assistant') {
            messageDiv.innerHTML = `
                <div class="barmuda-message-content">
                    ${message}
                    <div class="barmuda-message-time">${timeStr}</div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="barmuda-message-content" style="background: #fee; color: #c33; border-color: #fcc;">
                    ${message}
                </div>
            `;
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    async function sendMessage() {
        if (isEnded) return;
        
        const input = document.getElementById('barmuda-message-input');
        const message = input.value.trim();
        
        if (!message || !sessionId) return;
        
        addMessage('user', message);
        input.value = '';
        
        showTypingIndicator();
        disableInput();
        
        try {
            const response = await fetch(`${config.apiBase}/api/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: message
                })
            });
            
            const data = await response.json();
            hideTypingIndicator();
            
            if (data.success) {
                addMessage('assistant', data.response);
                
                if (data.ended) {
                    isEnded = true;
                    setTimeout(() => {
                        showCompletionScreen();
                    }, 1500);
                } else {
                    enableInput();
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
            
        } catch (error) {
            hideTypingIndicator();
            console.error('Chat error:', error);
            addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            enableInput();
        }
    }
    
    function showTypingIndicator() {
        hideTypingIndicator();
        
        const messagesContainer = document.getElementById('barmuda-chat-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'barmuda-message assistant barmuda-typing-message';
        typingDiv.innerHTML = `
            <div class="barmuda-message-content">
                <div class="barmuda-typing">
                    <div class="barmuda-typing-dot"></div>
                    <div class="barmuda-typing-dot"></div>
                    <div class="barmuda-typing-dot"></div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function hideTypingIndicator() {
        const typingMessages = document.querySelectorAll('.barmuda-typing-message');
        typingMessages.forEach(msg => msg.remove());
    }
    
    function enableInput() {
        document.getElementById('barmuda-message-input').disabled = false;
        document.getElementById('barmuda-send-button').disabled = false;
        document.getElementById('barmuda-message-input').focus();
    }
    
    function disableInput() {
        document.getElementById('barmuda-message-input').disabled = true;
        document.getElementById('barmuda-send-button').disabled = true;
    }
    
    function showCompletionScreen() {
        document.getElementById('barmuda-completion').classList.add('show');
    }
    
})();