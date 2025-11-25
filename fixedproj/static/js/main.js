// Main UI Logic

let currentPaper = null;
let retrievedPapers = [];
let generatedSurvey = '';

// Navigation
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('hidden');
    });

    // Hide feature grid
    document.querySelector('.feature-grid').classList.add('hidden');

    // Show selected section
    const section = document.getElementById(`${sectionName}-section`);
    if (section) {
        section.classList.remove('hidden');
    }
}

function showHome() {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('hidden');
    });

    // Show feature grid
    document.querySelector('.feature-grid').classList.remove('hidden');
}

// Loading overlay
function showLoading(message = 'Processing...') {
    const loading = document.getElementById('loading');
    const loadingText = document.getElementById('loadingText');
    loadingText.textContent = message;
    loading.classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

// Modal
// Modal - Dead code removed
// function closeModal() { ... }
// window.onclick = ...





// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function showNotification(message, type = 'info') {
    // Simple notification using alert (can be enhanced with a toast library)
    alert(message);
}

// Initialize
document.addEventListener('DOMContentLoaded', function () {
    console.log('AI Research Paper Generator v3.0 loaded');

    // Warmup LLM on page load
    fetch('/api/warmup', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('✓ LLM warmed up and ready');
            }
        })
        .catch(err => console.error('Warmup failed:', err));
});
