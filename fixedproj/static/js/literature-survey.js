// ============================================
// Literature Survey Logic - NO CONFLICTS
// ============================================

// Global variables (unique to literature survey)
let surveyRetrievedPapers = [];
let surveyGeneratedContent = '';
let surveyTopic = '';

// ============================================
// Generate Survey (Auto-retrieves papers)
// ============================================
async function generateSurvey() {
    const topic = document.getElementById('surveyTopic').value.trim();
    if (!topic) {
        showNotification('Please enter a research topic', 'error');
        return;
    }
    if (topic.length < 10) {
        showNotification('Topic too short. Please provide at least 10 characters.', 'warning');
        return;
    }
    surveyTopic = topic;
    showLoading('Step 1/2: Retrieving papers from Semantic Scholar...');

    try {
        // Step 1: Retrieve papers from Semantic Scholar
        const retrieveResponse = await fetch('/api/retrieve-papers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, count: 10 })
        });

        if (!retrieveResponse.ok) throw new Error(`HTTP ${retrieveResponse.status}`);

        const retrieveData = await retrieveResponse.json();

        if (!retrieveData.success) {
            showNotification('Failed to retrieve papers: ' + (retrieveData.error || 'Unknown error'), 'error');
            hideLoading();
            return;
        }

        surveyRetrievedPapers = retrieveData.papers || [];
        console.log(`✅ Retrieved ${surveyRetrievedPapers.length} papers`);

        // Step 2: Generate survey with the retrieved papers
        showLoading('Step 2/2: Generating literature survey...');

        const surveyResponse = await fetch('/api/generate-survey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                papers: surveyRetrievedPapers
            })
        });

        if (!surveyResponse.ok) throw new Error(`HTTP ${surveyResponse.status}`);

        const surveyData = await surveyResponse.json();

        if (surveyData.success) {
            surveyGeneratedContent = surveyData.survey || surveyData.content;
            displaySurvey(surveyData);
            showNotification('✅ Literature survey generated successfully!', 'success');
        } else {
            showNotification('Error generating survey: ' + (surveyData.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Survey Generation Error:', error);
        showNotification('Failed to generate survey. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// Display Survey Results
// ============================================
function displaySurvey(data) {
    const surveyContent = document.getElementById('surveyContent');
    const surveyResults = document.getElementById('surveyResults');

    if (!surveyContent || !surveyResults) {
        console.error('Survey display elements not found');
        return;
    }

    // Format the survey content with proper HTML
    let formattedContent = data.survey || data.content || '';

    // Add line breaks and formatting
    formattedContent = formattedContent
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    surveyContent.innerHTML = `
        <div class="survey-header">
            <h2>${data.title || 'Literature Survey: ' + surveyTopic}</h2>
            <p class="survey-meta">
                <strong>Papers Retrieved:</strong> ${surveyRetrievedPapers.length} | 
                <strong>Generated:</strong> ${new Date().toLocaleDateString()}
            </p>
        </div>
        <div class="survey-body">
            <p>${formattedContent}</p>
        </div>
        <div class="button-group mt-2">
            <button class="btn-primary btn-large" onclick="proceedToPaperGenerationFromSurvey()">
                ➡️ Generate Research Paper with This Title
            </button>
        </div>
    `;

    // Show results section
    surveyResults.classList.remove('hidden');
    surveyResults.scrollIntoView({ behavior: 'smooth' });
}

// ============================================
// Download Survey as PDF
// ============================================
async function downloadSurvey() {
    if (!surveyGeneratedContent) {
        showNotification('No survey to download. Generate one first.', 'error');
        return;
    }

    showLoading('Generating PDF...');

    try {
        const response = await fetch('/api/download-survey-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: surveyTopic,
                survey: surveyGeneratedContent
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Get the PDF as a blob
        const blob = await response.blob();

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `literature_survey_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification('✅ PDF downloaded successfully!', 'success');
    } catch (error) {
        console.error('Download Error:', error);
        showNotification('Failed to download PDF. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// Proceed to Paper Generation with Title
// ============================================
function proceedToPaperGenerationFromSurvey() {
    if (!surveyTopic) {
        showNotification('No topic available', 'error');
        return;
    }

    // Set the title input in the paper generator
    const titleInput = document.getElementById('paperTitle');
    if (titleInput) {
        titleInput.value = surveyTopic;
    }

    // Show the paper-generation section
    showSection('paper-generation');

    // Scroll to top
    window.scrollTo(0, 0);

    showNotification('✅ Topic populated in Paper Generation', 'success');
    console.log(`Proceeding to paper generation with topic: ${surveyTopic}`);
}

console.log('✅ Literature Survey module loaded');
