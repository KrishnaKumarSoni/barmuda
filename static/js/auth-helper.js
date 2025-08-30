// Shared authentication helper for Firebase Google Sign-In
// Handles popup blocking with automatic fallback to redirect method

window.initializeFirebaseAuth = function(firebaseConfig) {
    // Initialize Firebase if not already done
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }
    
    const auth = firebase.auth();
    
    // Handle redirect result on page load
    auth.getRedirectResult().then(async (result) => {
        if (result && result.user) {
            console.log('Redirect sign-in successful:', result.user.email);
            await handleSuccessfulAuth(result.user);
        }
    }).catch((error) => {
        console.error('Redirect result error:', error);
        if (error.code && error.code !== 'auth/popup-blocked') {
            alert(`Sign-in error: ${error.message}`);
        }
    });
    
    return auth;
};

// Main sign-in function with popup/redirect fallback
window.signInWithGoogleUniversal = async function(auth, redirectUrl = '/dashboard') {
    try {
        console.log('Starting Google sign in...');
        const provider = new firebase.auth.GoogleAuthProvider();
        provider.addScope('email');
        provider.addScope('profile');
        
        // Store redirect URL for after successful auth
        sessionStorage.setItem('authRedirectUrl', redirectUrl);
        
        // Try popup first
        console.log('Attempting popup sign-in...');
        let result;
        try {
            result = await auth.signInWithPopup(provider);
            console.log('Popup successful, user:', result.user.email);
            await handleSuccessfulAuth(result.user);
        } catch (popupError) {
            // Check if it's a popup blocked error
            if (popupError.code === 'auth/popup-blocked' || 
                popupError.code === 'auth/popup-closed-by-user' ||
                popupError.code === 'auth/cancelled-popup-request' ||
                popupError.code === 'auth/unauthorized-domain') {
                
                console.log('Popup blocked/failed, using redirect method instead...');
                console.log('Error code:', popupError.code);
                
                // Preserve any pending form data
                const pendingDescription = sessionStorage.getItem('pendingFormDescription');
                if (pendingDescription) {
                    localStorage.setItem('pendingFormDescription', pendingDescription);
                }
                
                // Show user-friendly message
                const loadingDiv = document.createElement('div');
                loadingDiv.innerHTML = `
                    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                         background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                         z-index: 10000; text-align: center;">
                        <p style="margin: 0 0 10px 0;">Redirecting to Google Sign-In...</p>
                        <small style="color: #666;">You'll be redirected back after signing in.</small>
                    </div>
                `;
                document.body.appendChild(loadingDiv);
                
                // Use redirect method as fallback
                await auth.signInWithRedirect(provider);
                return; // This won't execute as page redirects
            }
            throw popupError;
        }
    } catch (error) {
        console.error('Sign-in error:', error);
        
        // Show specific error messages
        let errorMessage = 'Sign-in failed. ';
        if (error.code === 'auth/network-request-failed') {
            errorMessage += 'Please check your internet connection.';
        } else if (error.code === 'auth/too-many-requests') {
            errorMessage += 'Too many attempts. Please try again later.';
        } else if (error.code === 'auth/user-disabled') {
            errorMessage += 'This account has been disabled.';
        } else {
            errorMessage += error.message || 'Please try again.';
        }
        
        alert(errorMessage);
        throw error;
    }
};

// Handle successful authentication
async function handleSuccessfulAuth(user) {
    try {
        const idToken = await user.getIdToken();
        console.log('Got ID token, sending to backend...');
        
        // Try multiple backend endpoints for compatibility
        const endpoints = ['/firebase-auth', '/auth/google'];
        let response;
        let success = false;
        
        for (const endpoint of endpoints) {
            try {
                response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify({ idToken })
                });
                
                if (response.ok) {
                    success = true;
                    break;
                }
            } catch (e) {
                console.log(`Endpoint ${endpoint} failed:`, e);
            }
        }
        
        if (success) {
            console.log('Backend authentication successful!');
            
            // Track login event if analytics available
            if (typeof gtag !== 'undefined') {
                gtag('event', 'login', {
                    method: 'google'
                });
            }
            
            // Restore any pending form data
            const pendingDescription = localStorage.getItem('pendingFormDescription');
            if (pendingDescription) {
                sessionStorage.setItem('pendingFormDescription', pendingDescription);
                localStorage.removeItem('pendingFormDescription');
            }
            
            // Redirect to intended page
            const redirectUrl = sessionStorage.getItem('authRedirectUrl') || '/dashboard';
            sessionStorage.removeItem('authRedirectUrl');
            window.location.href = redirectUrl;
        } else {
            console.error('Backend authentication failed');
            alert('Authentication failed. Please try again.');
        }
    } catch (error) {
        console.error('Error handling authentication:', error);
        alert('Authentication error. Please try again.');
    }
}

// Universal sign-out helper
window.signOut = async function() {
    try {
        await firebase.auth().signOut();
        await fetch('/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = '/';
    } catch (error) {
        console.error('Sign-out error:', error);
        alert('Sign-out failed. Please try again.');
    }
};
