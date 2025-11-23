// Main UI Logic

let currentPaper = null;
let retrievedPapers = [];
let generatedSurvey = '';

// Navigation
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // Hide feature grid
    document.querySelector('.feature-grid').style.display = 'none';
    
    // Show selected section
    const section = document.getElementById(`${sectionName}-section`);
    if (section) {
        section.style.display = 'block';
    }
}

function showHome() {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // Show feature grid
    document.querySelector('.feature-grid').style.display = 'grid';
}

// Loading overlay
function showLoading(message = 'Processing...') {
    const loading = document.getElementById('loading');
    const loadingText = document.getElementById('loadingText');
    loadingText.textContent = message;
    loading.style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Modal
function closeModal() {
    document.getElementById('paperModal').style.display = 'none';
}

// Close modal on outside click
window.onclick = function(event) {
    const modal = document.getElementById('paperModal');
    if (event.target === modal) {
        closeModal();
    }
}

// Author management
function addAuthor() {
    const container = document.getElementById('authorsContainer');
    const authorEntry = document.createElement('div');
    authorEntry.className = 'author-entry';
    authorEntry.innerHTML = `
        <input type="text" class="input author-name" placeholder="Full Name">
        <input type="email" class="input author-email" placeholder="Email">
        <input type="text" class="input author-affiliation" placeholder="University/Institution">
    `;
    container.appendChild(authorEntry);
}

// Toggle user data section
function toggleUserData() {
    const checkbox = document.getElementById('hasUserData');
    const form = document.getElementById('userDataForm');
    
    if (checkbox.checked) {
        form.style.display = 'block';
    } else {
        form.style.display = 'none';
    }
}

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
document.addEventListener('DOMContentLoaded', function() {
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
