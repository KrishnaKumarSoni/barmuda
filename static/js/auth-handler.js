// Reliable Authentication Handler for Barmuda
// This script handles all authentication flows with improved reliability

(function() {
    'use strict';
    
    // Configuration
    const AUTH_CONFIG = {
        MAX_RETRIES: 3,
        RETRY_DELAY: 1500,
        TIMEOUT: 30000,
        DEBUG: true
    };
    
    // State management
    let authState = {
        inProgress: false,
        retryCount: 0,
        lastError: null
    };
    
    // Logging utility
    function authLog(message, level = 'info', data = null) {
        if (!AUTH_CONFIG.DEBUG && level === 'debug') return;
        
        const timestamp = new Date().toISOString();
        const prefix = `[AUTH ${timestamp}]`;
        
        switch(level) {
            case 'error':
                console.error(`${prefix} ❌`, message, data || '');
                break;
            case 'success':
                console.log(`${prefix} ✅`, message, data || '');
                break;
            case 'warning':
                console.warn(`${prefix} ⚠️`, message, data || '');
                break;
            case 'debug':
                console.log(`${prefix} 🔍`, message, data || '');
                break;
            default:
                console.log(`${prefix} ℹ️`, message, data || '');
        }
    }
    
    // Visual feedback functions
    function showAuthProgress(message = 'Signing in...', showSpinner = true) {
        authLog(`Showing auth progress: ${message}`, 'debug');
        
        // Try to find existing loading elements
        let overlay = document.getElementById('auth-loading-overlay');
        
        if (!overlay) {
            // Create loading overlay
            overlay = document.createElement('div');
            overlay.id = 'auth-loading-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 999999;
                backdrop-filter: blur(4px);
            `;
            
            const container = document.createElement('div');
            container.style.cssText = `
                background: white;
                padding: 32px;
                border-radius: 16px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
            `;
            
            if (showSpinner) {
                const spinner = document.createElement('div');
                spinner.className = 'auth-spinner';
                spinner.style.cssText = `
                    width: 48px;
                    height: 48px;
                    border: 4px solid #f3f4f6;
                    border-top: 4px solid #cc5500;
                    border-radius: 50%;
                    margin: 0 auto 16px;
                    animation: spin 1s linear infinite;
                `;
                container.appendChild(spinner);
            }
            
            const messageEl = document.createElement('div');
            messageEl.id = 'auth-loading-message';
            messageEl.style.cssText = `
                font-family: 'DM Sans', sans-serif;
                font-size: 18px;
                color: #1f2937;
                margin-bottom: 8px;
                font-weight: 500;
            `;
            messageEl.textContent = message;
            container.appendChild(messageEl);
            
            const subMessage = document.createElement('div');
            subMessage.id = 'auth-loading-submessage';
            subMessage.style.cssText = `
                font-family: 'DM Sans', sans-serif;
                font-size: 14px;
                color: #6b7280;
            `;
            subMessage.textContent = 'Please wait while we authenticate you...';
            container.appendChild(subMessage);
            
            overlay.appendChild(container);
            document.body.appendChild(overlay);
            
            // Add animation styles
            const style = document.createElement('style');
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        } else {
            // Update existing overlay
            const messageEl = document.getElementById('auth-loading-message');
            if (messageEl) messageEl.textContent = message;
        }
        
        // Disable all sign-in buttons
        document.querySelectorAll('button[onclick*="signInWithGoogle"]').forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.6';
            btn.style.cursor = 'not-allowed';
        });
    }
    
    function hideAuthProgress() {
        authLog('Hiding auth progress', 'debug');
        
        const overlay = document.getElementById('auth-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        // Re-enable all sign-in buttons
        document.querySelectorAll('button[onclick*="signInWithGoogle"]').forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        });
    }
    
    function showAuthError(message, details = null) {
        authLog(`Showing auth error: ${message}`, 'error', details);
        hideAuthProgress();
        
        // Create error modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
            z-index: 999999;
            max-width: 400px;
            border: 2px solid #ef4444;
        `;
        
        modal.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
                <div style="width: 40px; height: 40px; background: #fee2e2; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <svg width="24" height="24" fill="#dc2626" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                </div>
                <div>
                    <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: #1f2937;">Authentication Failed</h3>
                </div>
            </div>
            <p style="margin: 0 0 16px 0; color: #4b5563; line-height: 1.5;">${message}</p>
            ${details ? `<p style="margin: 0 0 16px 0; color: #6b7280; font-size: 14px;">Details: ${details}</p>` : ''}
            <button onclick="this.parentElement.remove()" style="
                background: #cc5500;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                width: 100%;
            ">Try Again</button>
        `;
        
        document.body.appendChild(modal);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (modal && modal.parentElement) {
                modal.remove();
            }
        }, 5000);
    }
    
    // Backend sync with improved error handling
    async function syncWithBackend(idToken, attempt = 1) {
        authLog(`Syncing with backend (attempt ${attempt}/${AUTH_CONFIG.MAX_RETRIES})`, 'info');
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), AUTH_CONFIG.TIMEOUT);
            
            const response = await fetch('/firebase-auth', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ idToken }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                authLog('Backend sync successful', 'success', data);
                return { success: true, data };
            } else {
                throw new Error(data.error || `Server error: ${response.status}`);
            }
        } catch (error) {
            authLog(`Backend sync error on attempt ${attempt}`, 'error', error);
            
            // Determine if we should retry
            const shouldRetry = attempt < AUTH_CONFIG.MAX_RETRIES && (
                error.name === 'AbortError' ||
                error.message.includes('NetworkError') ||
                error.message.includes('Failed to fetch') ||
                error.message.includes('500') ||
                error.message.includes('502') ||
                error.message.includes('503')
            );
            
            if (shouldRetry) {
                const delay = AUTH_CONFIG.RETRY_DELAY * attempt;
                authLog(`Retrying in ${delay}ms...`, 'warning');
                showAuthProgress(`Authentication attempt ${attempt + 1}/${AUTH_CONFIG.MAX_RETRIES}...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return syncWithBackend(idToken, attempt + 1);
            }
            
            throw error;
        }
    }
    
    // Main sign-in function
    window.signInWithGoogleReliable = async function() {
        // Prevent multiple simultaneous attempts
        if (authState.inProgress) {
            authLog('Authentication already in progress', 'warning');
            return;
        }
        
        authState.inProgress = true;
        authState.lastError = null;
        
        authLog('Starting Google sign-in process', 'info');
        showAuthProgress('Connecting to Google...');
        
        try {
            // Check if Firebase is initialized
            if (typeof firebase === 'undefined' || !firebase.auth) {
                throw new Error('Firebase is not properly initialized. Please refresh the page.');
            }
            
            const auth = firebase.auth();
            const provider = new firebase.auth.GoogleAuthProvider();
            
            // Add scopes for better user info
            provider.addScope('email');
            provider.addScope('profile');
            
            let user;
            
            // Try popup method first
            try {
                authLog('Attempting popup sign-in', 'debug');
                showAuthProgress('Please complete sign-in in the popup window...');
                
                const result = await auth.signInWithPopup(provider);
                user = result.user;
                authLog('Popup sign-in successful', 'success', { email: user.email });
                
            } catch (popupError) {
                authLog('Popup failed, trying redirect', 'warning', popupError);
                
                // Check if it's a popup blocked error
                if (popupError.code === 'auth/popup-blocked' || 
                    popupError.code === 'auth/popup-closed-by-user' ||
                    popupError.code === 'auth/cancelled-popup-request') {
                    
                    // Store any pending data
                    const pendingData = sessionStorage.getItem('pendingFormDescription');
                    if (pendingData) {
                        localStorage.setItem('pendingFormDescription', pendingData);
                    }
                    
                    showAuthProgress('Redirecting to Google sign-in...');
                    
                    // Use redirect method
                    await auth.signInWithRedirect(provider);
                    return; // Page will redirect
                    
                } else if (popupError.code === 'auth/network-request-failed') {
                    throw new Error('Network error. Please check your internet connection and try again.');
                } else {
                    throw popupError;
                }
            }
            
            // Get fresh ID token
            showAuthProgress('Verifying your account...');
            authLog('Getting ID token', 'debug');
            const idToken = await user.getIdToken(true);
            
            // Sync with backend
            showAuthProgress('Setting up your account...');
            const result = await syncWithBackend(idToken);
            
            if (result.success) {
                authLog('Authentication complete!', 'success');
                showAuthProgress('Success! Redirecting...', false);
                
                // Small delay for user feedback
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Check for pending form data
                const pendingDescription = sessionStorage.getItem('pendingFormDescription');
                if (pendingDescription) {
                    window.location.href = '/create-form';
                } else {
                    window.location.href = '/dashboard';
                }
            } else {
                throw new Error('Failed to complete authentication');
            }
            
        } catch (error) {
            authLog('Authentication failed', 'error', error);
            authState.lastError = error;
            
            // User-friendly error messages
            let userMessage = 'Sign-in failed. Please try again.';
            
            if (error.message.includes('network')) {
                userMessage = 'Network error. Please check your connection and try again.';
            } else if (error.message.includes('Firebase')) {
                userMessage = 'Authentication service error. Please refresh the page and try again.';
            } else if (error.code === 'auth/user-cancelled') {
                userMessage = 'Sign-in cancelled.';
            } else if (error.code === 'auth/too-many-requests') {
                userMessage = 'Too many attempts. Please wait a moment and try again.';
            }
            
            showAuthError(userMessage, error.message);
            
        } finally {
            authState.inProgress = false;
            hideAuthProgress();
        }
    };
    
    // Handle redirect result on page load
    if (typeof firebase !== 'undefined' && firebase.auth) {
        firebase.auth().getRedirectResult()
            .then(async (result) => {
                if (result && result.user) {
                    authLog('Processing redirect sign-in', 'info', { email: result.user.email });
                    showAuthProgress('Completing sign-in...');
                    
                    const idToken = await result.user.getIdToken(true);
                    const syncResult = await syncWithBackend(idToken);
                    
                    if (syncResult.success) {
                        authLog('Redirect sign-in successful', 'success');
                        
                        // Restore pending data
                        const pendingData = localStorage.getItem('pendingFormDescription');
                        if (pendingData) {
                            sessionStorage.setItem('pendingFormDescription', pendingData);
                            localStorage.removeItem('pendingFormDescription');
                            window.location.href = '/create-form';
                        } else {
                            window.location.href = '/dashboard';
                        }
                    } else {
                        throw new Error('Failed to complete redirect authentication');
                    }
                }
            })
            .catch((error) => {
                authLog('Redirect sign-in failed', 'error', error);
                showAuthError('Sign-in failed. Please try again.', error.message);
            });
    }
    
    // Replace existing signInWithGoogle with reliable version
    if (typeof signInWithGoogle !== 'undefined') {
        window.signInWithGoogle = window.signInWithGoogleReliable;
        authLog('Replaced signInWithGoogle with reliable version', 'success');
    }
    
})();