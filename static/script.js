// DOM Elements
const analyzeBtn = document.getElementById("analyzeBtn");
const clearBtn = document.getElementById("clearBtn");
const textInput = document.getElementById("textInput");
const result = document.getElementById("result");
const loadingIndicator = document.getElementById("loadingIndicator");
const enableLiveAnalysis = document.getElementById("enableLiveAnalysis");
const floatingNavLinks = document.querySelectorAll(".floating-nav-link");
const contentTabs = document.querySelectorAll(".content-tab");
const themeSwitch = document.getElementById("checkbox");

let currentAnalysis = null;
const DEBOUNCE_DELAY = 1000;
let liveAnalysisHandler = null;

// Initialize theme
initTheme();

// Navigation tabs
floatingNavLinks.forEach(link => {
    link.addEventListener("click", function() {
        floatingNavLinks.forEach(el => el.classList.remove("active"));
        contentTabs.forEach(el => el.classList.remove("active"));
        this.classList.add("active");
        document.getElementById(this.getAttribute("data-tab") + "-tab").classList.add("active");
        if (this.getAttribute("data-tab") === "dashboard") loadStats();
        if (this.getAttribute("data-tab") === "history") loadHistory();
    });
});

// Theme switcher
themeSwitch.addEventListener("change", function() {
    document.body.classList.toggle("dark-mode", this.checked);
    localStorage.setItem("theme", this.checked ? "dark" : "light");
    if (currentAnalysis) updateVisualizations(currentAnalysis);
    if (document.getElementById("dashboard-tab").classList.contains("active")) updateDashboardCharts();
});

// Initialize theme
function initTheme() {
    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark-mode");
        themeSwitch.checked = true;
    }
}

// Event listeners
analyzeBtn.addEventListener("click", analyzeText);
clearBtn.addEventListener("click", () => {
    textInput.value = "";
    result.classList.add("d-none");
    resetVisualizations();
    currentAnalysis = null;
});

enableLiveAnalysis.addEventListener("change", function() {
    if (this.checked) {
        liveAnalysisHandler = debounce(analyzeText, DEBOUNCE_DELAY);
        textInput.addEventListener("input", liveAnalysisHandler);
    } else {
        if (liveAnalysisHandler) {
            textInput.removeEventListener("input", liveAnalysisHandler);
        }
    }
});

// Debounce function
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Analyze text
async function analyzeText() {
    const text = textInput.value.trim();
    if (!text) {
        showResult("Please enter some text for analysis.", "neutral");
        resetVisualizations();
        return;
    }

    loadingIndicator.classList.remove("d-none");
    result.classList.add("d-none");

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: textInput.value })
        });
        
        const data = await response.json();
        console.log("Analysis data:", data); // Debug log

        loadingIndicator.classList.add("d-none");

        if (data.error) {
            showResult(`Error: ${data.error}`, "neutral");
            resetVisualizations();
        } else {
            currentAnalysis = data;
            const emojiMap = { positive: '😊', neutral: '😐', negative: '😞' };
            const emoji = emojiMap[data.sentiment] || '';
            const sentimentText = data.sentiment.charAt(0).toUpperCase() + data.sentiment.slice(1);
            const confidence = (data.score * 100).toFixed(1);

            result.innerHTML = `
                <div class="d-flex align-items-center mb-2">
                    <span class="sentiment-emoji">${emoji}</span>
                    <strong class="ms-2">Sentiment:</strong> ${sentimentText}
                </div>
                <div class="progress mb-2" style="height: 10px;">
                    <div class="progress-bar bg-${getProgressBarColor(data.sentiment)}" 
                         role="progressbar" 
                         style="width: ${confidence}%" 
                         aria-valuenow="${confidence}" 
                         aria-valuemin="0" 
                         aria-valuemax="100"></div>
                </div>
                <strong>Confidence:</strong> ${confidence}%
            `;
            result.className = `sentiment-result mt-3 ${data.sentiment}`;
            result.classList.remove("d-none");
            updateVisualizations(data);
        }
    } catch (error) {
        loadingIndicator.classList.add("d-none");
        showResult("An error occurred during analysis.", "neutral");
        resetVisualizations();
        console.error("Analysis error:", error);
    }
}

// Helper functions
function showResult(message, sentimentClass) {
    result.textContent = message;
    result.className = `sentiment-result mt-3 ${sentimentClass}`;
    result.classList.remove("d-none");
}

function getProgressBarColor(sentiment) {
    return { positive: 'success', negative: 'danger' }[sentiment] || 'warning';
}

function updateVisualizations(data) {
    console.log("Updating visualizations with:", data);  // Add this
    renderWordCloud(data.word_sentiments);
    renderEmotionPieChart(data);
    updateSentimentMeter(data.positive_score);
}

function resetVisualizations() {
    updateSentimentMeter(0);
    document.getElementById('wordCloud').innerHTML = '<div class="text-center p-4">No data available</div>';
    renderEmotionPieChart({ word_sentiments: [] });
}

function updateSentimentMeter(score) {
    const isDark = isDarkMode();
    Plotly.newPlot('sentimentMeter', [{
        type: 'indicator',
        mode: 'gauge+number',
        value: score,
        title: { text: 'Positivity Score', font: { color: isDark ? '#fff' : '#000' } },
        number: { suffix: '%', valueformat: '.1f', font: { size: 24, color: isDark ? '#fff' : '#000' } },
        gauge: {
            axis: { range: [0, 1], tickwidth: 1, tickcolor: isDark ? '#aaa' : 'darkblue', tickfont: { color: isDark ? '#fff' : '#000' } },
            bar: { color: isDark ? '#4f8' : 'darkblue' },
            bgcolor: isDark ? '#333' : 'white',
            borderwidth: 2,
            bordercolor: isDark ? '#777' : 'gray',
            steps: [
                { range: [0, 0.33], color: isDark ? '#a33' : 'red' },
                { range: [0.33, 0.66], color: isDark ? '#aa3' : 'yellow' },
                { range: [0.66, 1], color: isDark ? '#3a3' : 'green' }
            ],
            threshold: { line: { color: isDark ? 'white' : 'black', width: 4 }, thickness: 0.75, value: 0.5 }
        }
    }], getPlotlyLayout('sentimentMeter'));
}

function renderWordCloud(wordSentiments) {
    if (!wordSentiments || !wordSentiments.length) {
        document.getElementById('wordCloud').innerHTML = '<div class="text-center p-4">No data available</div>';
        return;
    }
    
    // Limit to top 50 words by score
    let limitedSentiments = wordSentiments;
    if (wordSentiments.length > 50) {
        limitedSentiments = wordSentiments.sort((a, b) => b.score - a.score).slice(0, 50);
    }
    
    const isDark = isDarkMode();
    const maxScore = Math.max(...limitedSentiments.map(d => d.score)) || 1;
    const words = limitedSentiments.map(d => ({
        text: d.text,
        size: 12 + ((d.score / maxScore) * 28),
        color: { positive: isDark ? '#7f7' : 'green', negative: isDark ? '#f77' : 'red', neutral: isDark ? '#ff7' : '#cc7700' }[d.sentiment]
    }));
    
    const xValues = [], yValues = [];
    words.forEach((_, i) => {
        const angle = (i / words.length) * 2 * Math.PI;
        const radius = 0.4 + Math.random() * 0.2;
        xValues.push(0.5 + Math.cos(angle) * radius * (1 + Math.random() * 0.3));
        yValues.push(0.5 + Math.sin(angle) * radius * (1 + Math.random() * 0.3));
    });
    
    Plotly.newPlot('wordCloud', [{
        type: 'scatter',
        mode: 'text',
        text: words.map(d => d.text),
        x: xValues,
        y: yValues,
        textfont: { size: words.map(d => d.size), color: words.map(d => d.color) },
        hoverinfo: 'text',
        hovertext: words.map(d => `${d.text} (${d.sentiment})`)
    }], { ...getPlotlyLayout('wordCloud'), height: 300, margin: { t: 10, b: 10, l: 10, r: 10 } });
}

function renderEmotionPieChart(data) {
    const counts = { positive: 0, neutral: 0, negative: 0 };
    (data.word_sentiments || []).forEach(word => counts[word.sentiment]++);
    const isDark = isDarkMode();
    Plotly.newPlot('emotionPieChart', [{
        type: 'pie',
        labels: ['Positive', 'Neutral', 'Negative'],
        values: [counts.positive, counts.neutral, counts.negative],
        textinfo: 'label+percent',
        insidetextorientation: 'radial',
        textfont: { color: isDark ? '#fff' : '#000' },
        marker: { colors: isDark ? ['#7f7', '#ff7', '#f77'] : ['green', '#cc7700', 'red'] },
        hole: 0.4
    }], getPlotlyLayout('emotionPieChart'));
}

function isDarkMode() {
    return document.body.classList.contains('dark-mode');
}

function getPlotlyLayout(containerId) {
    const isDark = isDarkMode();
    return {
        paper_bgcolor: isDark ? '#222' : '#fff',
        plot_bgcolor: isDark ? '#222' : '#fff',
        font: { color: isDark ? '#fff' : '#000' },
        margin: { t: 30, b: 0, l: 30, r: 30 },
        height: containerId === 'wordCloud' ? 300 : 250
    };
}

async function loadStats() {
    try {
        const response = await fetch('/stats');
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        document.getElementById('totalAnalyses').textContent = data.total;
        document.getElementById('positiveCount').textContent = data.positive;
        document.getElementById('neutralCount').textContent = data.neutral;
        document.getElementById('negativeCount').textContent = data.negative;
        updateDashboardCharts(data);
    } catch (error) {
        console.error('Stats error:', error);
    }
}

function updateDashboardCharts(data = {total: 0, positive: 0, neutral: 0, negative: 0}) {
    const isDark = isDarkMode();
    Plotly.newPlot('sentimentDistribution', [{
        type: 'bar',
        x: ['Positive', 'Neutral', 'Negative'],
        y: [data.positive || 0, data.neutral || 0, data.negative || 0],
        marker: { color: isDark ? ['#7f7', '#ff7', '#f77'] : ['green', '#cc7700', 'red'] }
    }], { ...getPlotlyLayout('sentimentDistribution'), height: 300, xaxis: { title: 'Sentiment' }, yaxis: { title: 'Count' } });

    const dates = Array.from({ length: 7 }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - i);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }).reverse();
    Plotly.newPlot('sentimentTrends', [
        { type: 'scatter', mode: 'lines+markers', name: 'Positive', x: dates, y: dates.map(() => Math.floor((data.positive || 1) * (0.7 + Math.random() * 0.3))), line: { color: isDark ? '#7f7' : 'green' } },
        { type: 'scatter', mode: 'lines+markers', name: 'Neutral', x: dates, y: dates.map(() => Math.floor((data.neutral || 1) * (0.7 + Math.random() * 0.3))), line: { color: isDark ? '#ff7' : '#cc7700' } },
        { type: 'scatter', mode: 'lines+markers', name: 'Negative', x: dates, y: dates.map(() => Math.floor((data.negative || 1) * (0.7 + Math.random() * 0.3))), line: { color: isDark ? '#f77' : 'red' } }
    ], { ...getPlotlyLayout('sentimentTrends'), height: 300, xaxis: { title: 'Date' }, yaxis: { title: 'Count' }, legend: { orientation: 'h', y: 1.1 } });
}

function loadHistory() {
    fetch('/stats')
        .then(response => response.json())
        .then(data => data.error ? console.error(data.error) : updateHistoryTable(data.recent))
        .catch(error => console.error('History error:', error));
}

function updateHistoryTable(recentAnalyses = []) {
    const tableBody = document.getElementById('historyTableBody');
    tableBody.innerHTML = recentAnalyses && recentAnalyses.length ? 
        recentAnalyses.map(a => `
            <tr>
                <td>${a.text}</td>
                <td><span class="badge bg-${getProgressBarColor(a.sentiment)}">${a.sentiment}</span></td>
                <td>${(a.score * 100).toFixed(1)}%</td>
                <td>${new Date(a.timestamp).toLocaleString()}</td>
            </tr>`).join('') : 
        '<tr><td colspan="4" class="text-center">No analysis history available</td></tr>';
}

// Initialize visualizations on page load
window.addEventListener('load', function() {
    resetVisualizations();
    // Set up initial active tab
    const activeTab = document.querySelector('.floating-nav-link.active');
    if (activeTab && activeTab.getAttribute('data-tab') === 'dashboard') {
        loadStats();
    } else if (activeTab && activeTab.getAttribute('data-tab') === 'history') {
        loadHistory();
    }
});