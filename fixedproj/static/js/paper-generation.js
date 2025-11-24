// Paper Generation Logic

// Toggle Experimental Data Section
function toggleUserData() {
    const hasData = document.getElementById('hasUserData').checked;
    const section = document.getElementById('userDataSection');
    if (hasData) {
        section.classList.remove('hidden');
    } else {
        section.classList.add('hidden');
    }
}

// Generate Research Paper (manual title support)
async function generatePaper() {
    // Always get the current value from the paperTitle input field
    const paperTitle = document.getElementById('paperTitle').value.trim();
    const authorName = document.getElementById('authorName').value.trim();
    const authorEmail = document.getElementById('authorEmail').value.trim();
    const affiliation = document.getElementById('authorAffiliation').value.trim();
    const useRAG = document.getElementById('useRAG').checked;
    const hasUserData = document.getElementById('hasUserData').checked;


    const authors = [{
        name: authorName,
        email: authorEmail,
        affiliation: affiliation
    }];

    // Validate topic (title) - works for both manual and autofilled entry
    if (!paperTitle) {
        showNotification('Please enter a paper topic', 'error');
        return;
    }
    if (paperTitle.length < 10) {
        showNotification('Topic too short. Minimum 10 characters.', 'warning');
        return;
    }

    // Validate author details
    if (!authorName) {
        showNotification('Please enter author name', 'error');
        return;
    }

    // Optional experimental data
    let userExperimentalData = null;
    if (hasUserData) {
        const methodology = document.getElementById('methodology').value.trim();
        const results = document.getElementById('results').value.trim();
        if (methodology || results) {
            userExperimentalData = { methodology, results };
        }
    }

    // IMPORTANT: Use 'topic' key for backend!
    const payload = {
        topic: paperTitle,
        authors: authors, // backend expects this!
        use_rag: useRAG,
        user_data: userExperimentalData
    };

    showLoading('Generating research paper. This may take a few minutes...');
    try {
        const response = await fetch('/api/generate-paper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.success) {
            currentPaper = data.paper;
            displayGeneratedPaper(data.paper);
            showNotification('✅ Research paper generated successfully!', 'success');
        } else {
            showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showNotification('Failed to generate paper. Please try again.', 'error');
        console.error(error);
    } finally {
        hideLoading();
    }
}

// Show/hide user data fields on load (optional fallback)
document.addEventListener('DOMContentLoaded', () => {
    toggleUserData();
});

function displayGeneratedPaper(data) {
    const preview = document.getElementById('paperResults');
    const content = document.getElementById('paperContent');

    let html = `
        <div class="paper-header">
            <h1>${data.title}</h1>
            <div class="authors">
                ${data.authors.map(a => `
                    <div class="author">
                        <strong>${a.name}</strong><br>
                        ${a.affiliation}<br>
                        ${a.email}
                    </div>
                `).join('')}
            </div>
            <div class="date">Generated: ${formatDate(data.generated_date)}</div>
        </div>
    `;

    // Add sections
    const sections = ['abstract', 'introduction', 'literature_review',
        'methodology', 'results', 'discussion', 'conclusion'];

    sections.forEach(section => {
        if (data.sections[section]) {
            const title = section.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="paper-section">
                    <h2>${title}</h2>
                    <p>${data.sections[section]}</p>
                </div>
            `;
        }
    });

    // Add references if present
    if (data.references && data.references.length > 0) {
        html += '<div class="paper-section"><h2>References</h2><ol class="references">';
        data.references.forEach(ref => {
            html += `<li>${ref}</li>`;
        });
        html += '</ol></div>';
    }

    content.innerHTML = html;
    preview.classList.remove('hidden');

    // Scroll to preview
    preview.scrollIntoView({ behavior: 'smooth' });
}

async function downloadPaper(format = 'pdf') {
    if (!currentPaper) {
        showNotification('No paper to download', 'error');
        return;
    }

    showLoading(`Preparing ${format.toUpperCase()} download...`);

    const endpoint = format === 'pdf' ? '/api/download-pdf' : '/api/download-docx';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper: currentPaper
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentPaper.title.replace(/[^a-z0-9]/gi, '_')}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showNotification(`Paper downloaded as ${format.toUpperCase()}!`, 'success');
        } else {
            showNotification('Download failed', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Download failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

async function recoverLastPaper() {
    showLoading('Recovering last generated paper...');
    try {
        const response = await fetch('/api/latest-paper');
        const data = await response.json();

        if (data.success) {
            currentPaper = data.paper; // Update global state
            displayGeneratedPaper({
                title: data.paper.title,
                authors: data.paper.authors,
                content: null,
                ...data.paper
            });
            showNotification('✅ Paper recovered successfully!', 'success');
        } else {
            showNotification('No saved paper found to recover', 'warning');
        }
    } catch (error) {
        console.error('Recovery Error:', error);
        showNotification('Failed to recover paper', 'error');
    } finally {
        hideLoading();
    }
}
