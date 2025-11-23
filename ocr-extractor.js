// ============================================
// OCR Extractor Logic - NO CONFLICTS
// ============================================

// Global variables (unique to OCR)
let ocrUploadedImage = null;
let ocrExtractedText = '';
let ocrSelectedTitle = '';

// ============================================
// Image Upload Handler
// ============================================
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(file.type)) {
        showNotification('Please upload a valid image (JPG, PNG)', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showNotification('Image too large. Maximum size: 10MB', 'error');
        return;
    }

    ocrUploadedImage = file;

    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('previewImg').src = e.target.result;
        document.getElementById('uploadPlaceholder').style.display = 'none';
        document.getElementById('imagePreview').style.display = 'block';
        document.getElementById('extractBtn').disabled = false;
    };
    reader.readAsDataURL(file);
    
    console.log('✅ Image uploaded:', file.name);
}

// ============================================
// Remove Image
// ============================================
function removeImage() {
    ocrUploadedImage = null;
    document.getElementById('ocrImage').value = '';
    document.getElementById('previewImg').src = '';
    document.getElementById('uploadPlaceholder').style.display = 'block';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('extractBtn').disabled = true;
    document.getElementById('ocrResults').style.display = 'none';
    document.getElementById('titleSelectionSection').style.display = 'none';
    
    console.log('🗑️ Image removed');
}

// ============================================
// Extract Text via OCR
// ============================================
async function extractText() {
    if (!ocrUploadedImage) {
        showNotification('Please upload an image first', 'error');
        return;
    }

    showLoading('Extracting text from image... This may take 10-20 seconds');

    try {
        const formData = new FormData();
        formData.append('image', ocrUploadedImage);

        const response = await fetch('/api/extract-ocr', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            const extractedText = data.text.trim();

            if (!extractedText) {
                showNotification('No text detected. Try a clearer photo.', 'warning');
                return;
            }

            ocrExtractedText = extractedText;
            document.getElementById('extractedText').value = extractedText;
            document.getElementById('ocrResults').style.display = 'block';
            document.getElementById('ocrResults').scrollIntoView({ behavior: 'smooth' });

            const wordCount = extractedText.match(/\b\w+\b/g)?.length || 0;
            showNotification(`✅ Extracted ${wordCount} words!`, 'success');
        } else {
            showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('OCR Error:', error);
        showNotification('Failed to extract text. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// Copy Text to Clipboard
// ============================================
function copyToClipboard() {
    const text = document.getElementById('extractedText').value;
    if (!text) {
        showNotification('No text to copy', 'error');
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showNotification('✅ Text copied to clipboard!', 'success');
    }).catch(() => {
        showNotification('Failed to copy text', 'error');
    });
}

// ============================================
// Generate Title Options
// ============================================
async function generateTitleOptions() {
    const description = document.getElementById('extractedText').value.trim();
    
    if (!description) {
        showNotification('No text extracted yet', 'error');
        return;
    }

    if (description.length < 20) {
        showNotification('Description too short (min 20 chars)', 'warning');
        return;
    }

    showLoading('Generating 3 title options using AI...');

    try {
        const response = await fetch('/api/generate-titles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: description,
                count: 3
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.titles && data.titles.length > 0) {
            displayTitleOptions(data.titles);
            showNotification(`✅ Generated ${data.titles.length} title options!`, 'success');
        } else {
            showNotification('Failed to generate titles: ' + (data.error || 'Unknown'), 'error');
        }
    } catch (error) {
        console.error('Title Generation Error:', error);
        showNotification('Failed to generate titles. Try again.', 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// Display Title Options
// ============================================
function displayTitleOptions(titles) {
    const container = document.getElementById('titleSelectionSection');
    const optionsDiv = document.getElementById('titleOptionsDiv');
    
    optionsDiv.innerHTML = '';
    
    titles.forEach((title, index) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'title-option';
        
        const input = document.createElement('input');
        input.type = 'radio';
        input.name = 'ocrTitleOption';
        input.id = `ocrTitle${index}`;
        input.value = title;
        input.checked = (index === 0);
        
        input.addEventListener('change', () => {
            selectOCRTitle(title);
        });
        
        const label = document.createElement('label');
        label.setAttribute('for', `ocrTitle${index}`);
        label.innerHTML = `<strong>Option ${index + 1}:</strong> `;
        
        const titleSpan = document.createElement('span');
        titleSpan.textContent = title;
        label.appendChild(titleSpan);
        
        optionDiv.appendChild(input);
        optionDiv.appendChild(label);
        optionsDiv.appendChild(optionDiv);
    });
    
    ocrSelectedTitle = titles[0];
    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth' });
    
    console.log('✅ Displayed', titles.length, 'title options');
}

// ============================================
// Select Title
// ============================================
function selectOCRTitle(title) {
    ocrSelectedTitle = title;
    console.log('Selected OCR title:', ocrSelectedTitle);
}

// ============================================
// Proceed to Literature Survey
// ============================================
function proceedToLiteratureSurvey() {
    if (!ocrSelectedTitle) {
        showNotification('Please generate and select a title first', 'error');
        return;
    }
    
    document.getElementById('surveyTopic').value = ocrSelectedTitle;
    showSection('literature-survey');
    showNotification('✅ Title populated in Literature Survey', 'success');
}

// ============================================
// Proceed to Paper Generation
// ============================================
function proceedToPaperGeneration() {
    if (!ocrSelectedTitle) {
        showNotification('Please generate and select a title first', 'error');
        return;
    }
    
    document.getElementById('paperTitle').value = ocrSelectedTitle;
    showSection('paper-generation');
    showNotification('✅ Title populated in Paper Generation', 'success');
}

console.log('✅ OCR Extractor module loaded');
