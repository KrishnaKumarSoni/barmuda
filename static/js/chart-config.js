/**
 * Chart.js Configuration for Bermuda Forms Responses
 * Matches Figma design specifications
 */

// Bermuda Design System Colors
const BERMUDA_COLORS = {
    primary: ['#233203', '#7e1dc8', '#03abff', '#0eac00', '#ff6b35'],
    yesNo: ['#0eac00', '#233203'], // Green for Yes, Dark for No
    rating: ['#233203', '#7e1dc8', '#03abff', '#0eac00', '#ff6b35'],
    text: '#1e1e1e',
    background: '#ffffff',
    border: '#fce9c1'
};

// Global Chart.js configuration
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: false // We'll create custom legends
        },
        tooltip: {
            backgroundColor: '#ffffff',
            titleColor: '#1e1e1e',
            bodyColor: '#1e1e1e',
            borderColor: '#fce9c1',
            borderWidth: 1,
            cornerRadius: 8,
            displayColors: false,
            titleFont: {
                family: 'DM Sans',
                size: 14,
                weight: '500'
            },
            bodyFont: {
                family: 'DM Sans',
                size: 12,
                weight: '400'
            }
        }
    }
};

/**
 * Create pie chart for multiple choice questions
 */
function createMultipleChoiceChart(canvas, data, options) {
    const ctx = canvas.getContext('2d');
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: options,
            datasets: [{
                data: data,
                backgroundColor: BERMUDA_COLORS.primary.slice(0, data.length),
                borderWidth: 0,
                hoverBorderWidth: 2,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.parsed / total) * 100);
                            return `${context.label}: ${percentage}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create pie chart for yes/no questions
 */
function createYesNoChart(canvas, yesCount, noCount) {
    const ctx = canvas.getContext('2d');
    const total = yesCount + noCount;
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Yes', 'No'],
            datasets: [{
                data: [yesCount, noCount],
                backgroundColor: BERMUDA_COLORS.yesNo,
                borderWidth: 0,
                hoverBorderWidth: 2,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const percentage = Math.round((context.parsed / total) * 100);
                            return `${context.label}: ${percentage}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create pie chart for rating questions (1-5 scale)
 */
function createRatingChart(canvas, ratingData) {
    const ctx = canvas.getContext('2d');
    const labels = Object.keys(ratingData).filter(key => key !== '[SKIP]');
    const data = labels.map(label => ratingData[label].count);
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels.map(label => `${label} Star${label !== '1' ? 's' : ''}`),
            datasets: [{
                data: data,
                backgroundColor: BERMUDA_COLORS.rating.slice(0, data.length),
                borderWidth: 0,
                hoverBorderWidth: 2,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                tooltip: {
                    ...CHART_DEFAULTS.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.parsed / total) * 100);
                            return `${context.label}: ${percentage}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create custom legend HTML that matches Figma design
 */
function createCustomLegend(containerId, labels, data, colors) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const total = data.reduce((a, b) => a + b, 0);
    
    let legendHtml = '<div class="space-y-3">';
    
    labels.forEach((label, index) => {
        if (data[index] > 0) {
            const percentage = Math.round((data[index] / total) * 100);
            const color = colors[index % colors.length];
            
            legendHtml += `
                <div class="flex items-center gap-3">
                    <div class="w-4 h-4 rounded" style="background-color: ${color}"></div>
                    <span class="font-['DM_Sans'] text-[#1e1e1e] text-[14px] tracking-[-0.14px] flex-1">${label}</span>
                    <span class="font-['DM_Sans'] text-[#1e1e1e] text-[14px] tracking-[-0.14px]">${percentage}%</span>
                </div>
            `;
        }
    });
    
    legendHtml += '</div>';
    container.innerHTML = legendHtml;
}

/**
 * Calculate statistics for choice-based questions (multiple choice, yes/no)
 */
function calculateChoiceStats(responses, options) {
    const stats = {};
    const total = responses.length;
    
    options.forEach(option => {
        stats[option] = { count: 0, percentage: 0 };
    });
    stats['other'] = { count: 0, percentage: 0 };
    stats['[SKIP]'] = { count: 0, percentage: 0 };

    responses.forEach(response => {
        const value = response.value;
        if (stats[value]) {
            stats[value].count++;
        } else if (value === '[SKIP]') {
            stats['[SKIP]'].count++;
        } else {
            stats['other'].count++;
        }
    });

    Object.keys(stats).forEach(key => {
        stats[key].percentage = total > 0 ? Math.round((stats[key].count / total) * 100) : 0;
    });

    return stats;
}

/**
 * Calculate statistics for rating questions
 */
function calculateRatingStats(responses) {
    const stats = { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '[SKIP]': 0 };
    const total = responses.length;

    responses.forEach(response => {
        const value = response.value;
        if (stats[value] !== undefined) {
            stats[value]++;
        }
    });

    const result = {};
    Object.keys(stats).forEach(key => {
        result[key] = {
            count: stats[key],
            percentage: total > 0 ? Math.round((stats[key] / total) * 100) : 0
        };
    });

    return result;
}

/**
 * Calculate statistics for number questions
 */
function calculateNumberStats(responses) {
    const stats = {};
    const total = responses.length;

    responses.forEach(response => {
        const value = response.value;
        if (value === '[SKIP]') {
            stats['[SKIP]'] = (stats['[SKIP]'] || 0) + 1;
        } else {
            stats[value] = (stats[value] || 0) + 1;
        }
    });

    const result = {};
    Object.keys(stats).forEach(key => {
        result[key] = {
            count: stats[key],
            percentage: total > 0 ? Math.round((stats[key] / total) * 100) : 0
        };
    });

    return result;
}

/**
 * Initialize chart for a question based on its type
 */
function initializeQuestionChart(questionIndex, questionType, questionData, responses) {
    const canvasId = `chart-${questionIndex}`;
    const legendId = `legend-${questionIndex}`;
    const canvas = document.getElementById(canvasId);
    
    if (!canvas) {
        console.error(`Canvas element ${canvasId} not found`);
        return;
    }
    
    let chart;
    let legendData = { labels: [], data: [], colors: [] };
    
    switch (questionType) {
        case 'multiple_choice':
            const mcStats = calculateChoiceStats(responses, questionData.options || []);
            const mcLabels = Object.keys(mcStats).filter(key => mcStats[key].count > 0);
            const mcData = mcLabels.map(label => mcStats[label].count);
            
            chart = createMultipleChoiceChart(canvas, mcData, mcLabels);
            legendData = {
                labels: mcLabels,
                data: mcData,
                colors: BERMUDA_COLORS.primary.slice(0, mcData.length)
            };
            break;
            
        case 'yes_no':
            const ynStats = calculateChoiceStats(responses, ['Yes', 'No']);
            const yesCount = ynStats['Yes']?.count || 0;
            const noCount = ynStats['No']?.count || 0;
            
            chart = createYesNoChart(canvas, yesCount, noCount);
            legendData = {
                labels: ['Yes', 'No'],
                data: [yesCount, noCount],
                colors: BERMUDA_COLORS.yesNo
            };
            break;
            
        case 'rating':
            const ratingStats = calculateRatingStats(responses);
            chart = createRatingChart(canvas, ratingStats);
            
            const ratingLabels = Object.keys(ratingStats).filter(key => key !== '[SKIP]' && ratingStats[key].count > 0);
            const ratingData = ratingLabels.map(label => ratingStats[label].count);
            
            legendData = {
                labels: ratingLabels.map(label => `${label} Star${label !== '1' ? 's' : ''}`),
                data: ratingData,
                colors: BERMUDA_COLORS.rating.slice(0, ratingData.length)
            };
            break;
            
        case 'number':
            // Treat numbers similar to ratings for visualization
            const numberStats = calculateNumberStats(responses);
            chart = createRatingChart(canvas, numberStats);
            
            const numberLabels = Object.keys(numberStats).filter(key => key !== '[SKIP]' && numberStats[key].count > 0);
            const numberData = numberLabels.map(label => numberStats[label].count);
            
            legendData = {
                labels: numberLabels,
                data: numberData,
                colors: BERMUDA_COLORS.rating.slice(0, numberData.length)
            };
            break;
            
        case 'text':
            // Text responses will be handled by word cloud
            renderTextWordCloud(`wordcloud-${questionIndex}`, responses);
            return; // No legend needed for word clouds
            
        default:
            console.error(`Unsupported question type: ${questionType}`);
            return;
    }
    
    // Create custom legend
    if (legendData.labels.length > 0) {
        createCustomLegend(legendId, legendData.labels, legendData.data, legendData.colors);
    }
    
    return chart;
}


// Export for use in responses.html
window.ChartConfig = {
    BERMUDA_COLORS,
    CHART_DEFAULTS,
    createMultipleChoiceChart,
    createYesNoChart,
    createRatingChart,
    createCustomLegend,
    initializeQuestionChart,
    calculateChoiceStats,
    calculateRatingStats,
    calculateNumberStats
};