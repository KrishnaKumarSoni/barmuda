/**
 * Word Cloud Configuration for Text Responses
 * Uses wordcloud library for text response visualization
 */

/**
 * Generate word frequency data from text responses
 */
function generateWordFrequency(responses) {
    const wordCount = {};
    const stopWords = new Set([
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'this', 'that', 'these', 'those', 'am', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
    ]);
    
    responses.forEach(response => {
        if (response.value && response.value !== '[SKIP]') {
            // Clean and split text
            const words = response.value
                .toLowerCase()
                .replace(/[^\w\s]/g, ' ') // Remove punctuation
                .split(/\s+/)
                .filter(word => word.length > 2 && !stopWords.has(word));
            
            words.forEach(word => {
                wordCount[word] = (wordCount[word] || 0) + 1;
            });
        }
    });
    
    // Convert to array format expected by wordcloud library
    return Object.entries(wordCount)
        .sort(([,a], [,b]) => b - a) // Sort by frequency
        .slice(0, 50) // Limit to top 50 words
        .map(([word, count]) => [word, count * 10]); // Scale for better visualization
}

/**
 * Generate color function for word cloud
 */
function getWordCloudColor() {
    const colors = ['#233203', '#7e1dc8', '#03abff', '#0eac00', '#ff6b35', '#d12b2e', '#cc5500'];
    return function() {
        return colors[Math.floor(Math.random() * colors.length)];
    };
}

/**
 * Render word cloud for text responses
 */
function renderTextWordCloud(containerId, responses) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container ${containerId} not found`);
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Check if we have valid text responses
    const validResponses = responses.filter(r => r.value && r.value !== '[SKIP]' && r.value.trim().length > 0);
    
    if (validResponses.length === 0) {
        container.innerHTML = `
            <div class="flex items-center justify-center h-32 text-[#797878]">
                <p class="font-['DM_Sans'] text-[14px]">No text responses to display</p>
            </div>
        `;
        return;
    }
    
    // Generate word frequency
    const wordFrequency = generateWordFrequency(validResponses);
    
    if (wordFrequency.length === 0) {
        container.innerHTML = `
            <div class="flex items-center justify-center h-32 text-[#797878]">
                <p class="font-['DM_Sans'] text-[14px]">No significant words found</p>
            </div>
        `;
        return;
    }
    
    // Create canvas for word cloud
    const canvas = document.createElement('canvas');
    canvas.width = 290;
    canvas.height = 164;
    canvas.style.width = '100%';
    canvas.style.height = '164px';
    container.appendChild(canvas);
    
    // Configure word cloud
    const options = {
        list: wordFrequency,
        gridSize: Math.round(16 * canvas.width / 1024),
        weightFactor: function(size) {
            return Math.pow(size, 2.3) * canvas.width / 1024;
        },
        fontFamily: 'DM Sans, sans-serif',
        color: getWordCloudColor(),
        rotateRatio: 0.5,
        backgroundColor: 'transparent',
        shape: 'circle',
        ellipticity: 0.65,
        minSize: 12,
        drawOutOfBound: false
    };
    
    try {
        // Generate word cloud
        if (typeof WordCloud !== 'undefined') {
            WordCloud(canvas, options);
        } else {
            // Fallback if WordCloud library isn't loaded
            renderTextFallback(container, validResponses);
        }
    } catch (error) {
        console.error('Error generating word cloud:', error);
        renderTextFallback(container, validResponses);
    }
}

/**
 * Fallback rendering for text responses when word cloud fails
 */
function renderTextFallback(container, responses) {
    let html = '<div class="space-y-2">';
    
    // Show first 5 responses
    responses.slice(0, 5).forEach((response, index) => {
        html += `
            <div class="bg-[#f9f9f9] rounded p-3">
                <p class="font-['DM_Sans'] text-[#1e1e1e] text-[14px]">"${response.value}"</p>
            </div>
        `;
    });
    
    if (responses.length > 5) {
        html += `<p class="text-[#797878] text-[12px] text-center">... and ${responses.length - 5} more responses</p>`;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

/**
 * Initialize word cloud for a text question
 */
function initializeTextVisualization(questionIndex, responses) {
    const containerId = `wordcloud-${questionIndex}`;
    renderTextWordCloud(containerId, responses);
}

// Export for use in responses.html
window.WordCloudConfig = {
    generateWordFrequency,
    getWordCloudColor,
    renderTextWordCloud,
    renderTextFallback,
    initializeTextVisualization
};