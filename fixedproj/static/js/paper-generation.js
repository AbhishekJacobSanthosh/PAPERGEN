// Paper Generation Logic

// Toggle Experimental Data Section
function toggleUserData() {
    const hasData = document.getElementById('hasUserData').checked;
    const section = document.getElementById('userDataSection');
    if (hasData) {
        section.classList.remove('hidden');
        section.style.setProperty('display', 'block', 'important');
    } else {
        section.classList.add('hidden');
        section.style.setProperty('display', 'none', 'important');
    }
}

// Author Management
function addAuthorField(name = '', email = '', affiliation = '') {
    const container = document.getElementById('authorsContainer');
    const authorId = Date.now();

    const authorDiv = document.createElement('div');
    authorDiv.className = 'author-entry';
    authorDiv.id = `author-${authorId}`;
    authorDiv.innerHTML = `
        <div class="author-header">
            <h4>Author Details</h4>
            ${container.children.length > 0 ? `<button type="button" class="btn-remove" onclick="removeAuthorField('${authorId}')">Remove</button>` : ''}
        </div>
        <div class="author-fields">
            <div class="form-group">
                <label>Name</label>
                <input type="text" class="input author-name" placeholder="Author Name" value="${name}">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" class="input author-email" placeholder="Email" value="${email}">
            </div>
            <div class="form-group full-width">
                <label>Affiliation</label>
                <input type="text" class="input author-affiliation" placeholder="Affiliation" value="${affiliation}">
            </div>
        </div>
    `;

    container.appendChild(authorDiv);
}

function removeAuthorField(id) {
    const element = document.getElementById(`author-${id}`);
    if (element) {
        element.remove();
    }
}

// Generate Research Paper (manual title support)
async function generatePaper() {
    // Always get the current value from the paperTitle input field
    const paperTitle = document.getElementById('paperTitle').value.trim();
    const useRAG = document.getElementById('useRAG').checked;
    const hasUserData = document.getElementById('hasUserData').checked;

    // Collect authors
    const authorEntries = document.querySelectorAll('.author-entry');
    const authors = [];

    authorEntries.forEach(entry => {
        const name = entry.querySelector('.author-name').value.trim();
        const email = entry.querySelector('.author-email').value.trim();
        const affiliation = entry.querySelector('.author-affiliation').value.trim();

        if (name && email && affiliation) {
            authors.push({ name, email, affiliation });
        }
    });

    // Validate topic (title)
    if (!paperTitle) {
        showNotification('Please enter a paper topic', 'error');
        return;
    }
    if (paperTitle.length < 10) {
        showNotification('Topic too short. Minimum 10 characters.', 'warning');
        return;
    }

    // Validate author details
    if (authors.length === 0) {
        showNotification('Please add at least one author with complete details', 'error');
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

    const payload = {
        topic: paperTitle,
        authors: authors,
        use_rag: useRAG,
        user_data: userExperimentalData
    };

    // UI Setup
    const loading = document.getElementById('loading');
    const loadingText = document.getElementById('loadingText');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');

    loading.classList.remove('hidden');
    progressContainer.classList.remove('hidden');
    loadingText.textContent = 'Generating Research Paper...';
    progressBar.style.width = '5%';
    progressMessage.textContent = 'Starting...';

    try {
        const response = await fetch('/api/generate-paper-stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Keep incomplete chunk

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        // Handle events
                        if (data.status === 'start') {
                            progressBar.style.width = '10%';
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'title') {
                            progressBar.style.width = '20%';
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'rag_start') {
                            progressBar.style.width = '30%';
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'rag_complete') {
                            progressBar.style.width = '40%';
                            progressMessage.textContent = `Retrieved ${data.count} papers`;
                        } else if (data.status === 'abstract') {
                            progressBar.style.width = '50%';
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'section_start') {
                            const sectionMap = {
                                'introduction': 55,
                                'literature_review': 62,
                                'methodology': 69,
                                'results': 76,
                                'discussion': 83,
                                'conclusion': 90
                            };
                            if (sectionMap[data.section]) {
                                progressBar.style.width = `${sectionMap[data.section]}%`;
                            }
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'references') {
                            progressBar.style.width = '95%';
                            progressMessage.textContent = data.message;
                        } else if (data.status === 'complete') {
                            progressBar.style.width = '100%';
                            progressMessage.textContent = 'Done!';
                            currentPaper = data.paper;
                            displayGeneratedPaper(data.paper);
                            showNotification('✅ Research paper generated successfully!', 'success');
                        } else if (data.status === 'error') {
                            throw new Error(data.message);
                        }
                    } catch (e) {
                        console.error('Error parsing stream:', e);
                    }
                }
            }
        }
    } catch (error) {
        showNotification('Failed to generate paper: ' + error.message, 'error');
        console.error(error);
    } finally {
        loading.classList.add('hidden');
        progressContainer.classList.add('hidden');
    }
}

// Show/hide user data fields on load (optional fallback)
document.addEventListener('DOMContentLoaded', () => {
    toggleUserData();
    // Add initial author field
    addAuthorField('Your Name', 'your.email@university.edu', 'Department of CSE, University');
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
    // Add sections
    const sections = ['abstract', 'introduction', 'literature_review',
        'methodology', 'results', 'discussion', 'conclusion'];

    sections.forEach(section => {
        if (data.sections[section]) {
            const title = section.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="paper-section">
                    <h2>${title}</h2>
                    <p>${data.sections[section].replace(/\n/g, '<br>')}</p>
                </div>
            `;
        }
    });

    // Add Figures and Tables
    if (data.figures) {
        Object.values(data.figures).forEach(fig => {
            if (fig.type === 'table') {
                html += `
                    <div class="paper-figure">
                        <h4>Table ${fig.number}: ${fig.caption}</h4>
                        <table class="generated-table">
                            <thead>
                                <tr>${fig.data[0].map(h => `<th>${h}</th>`).join('')}</tr>
                            </thead>
                            <tbody>
                                ${fig.data.slice(1).map(row => `
                                    <tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            } else if (fig.type === 'chart') {
                // Placeholder for charts (could use a library, but for now just text description)
                html += `
                    <div class="paper-figure">
                        <h4>Figure ${fig.number}: ${fig.caption}</h4>
                        <div class="chart-placeholder">[Chart Data: ${fig.data.substring(0, 50)}...]</div>
                    </div>
                `;
            }
        });
    }

    // Add references
    if (data.references && data.references.length > 0) {
        html += '<div class="paper-section"><h2>References</h2><ol class="references">';
        data.references.forEach(ref => {
            if (typeof ref === 'string') {
                html += `<li>${ref}</li>`;
            } else {
                // Format object: Authors, "Title", Venue, Year.
                const authors = Array.isArray(ref.authors) ? ref.authors.join(', ') : ref.authors;
                html += `<li>${authors}, "${ref.title}", <em>${ref.venue}</em>, ${ref.year}.</li>`;
            }
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

    let endpoint;
    if (format === 'pdf') endpoint = '/api/download-pdf';
    else if (format === 'docx') endpoint = '/api/download-docx';
    else if (format === 'pptx') endpoint = '/api/download-pptx';

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
