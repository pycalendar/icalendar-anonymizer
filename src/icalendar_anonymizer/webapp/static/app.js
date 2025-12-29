// SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

'use strict';

// Store blobs per section
const blobs = {};

// Tab switching
function initTabs() {
    const tabs = document.querySelectorAll('[role="tab"]');

    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
            const panelId = tab.getAttribute('aria-controls');
            switchTab(panelId);
        });

        tab.addEventListener('keydown', (e) => {
            let targetTab = null;

            if (e.key === 'ArrowRight') {
                e.preventDefault();
                targetTab = tabs[(index + 1) % tabs.length];
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                targetTab = tabs[(index - 1 + tabs.length) % tabs.length];
            } else if (e.key === 'Home') {
                e.preventDefault();
                targetTab = tabs[0];
            } else if (e.key === 'End') {
                e.preventDefault();
                targetTab = tabs[tabs.length - 1];
            }

            if (targetTab) {
                targetTab.focus();
                switchTab(targetTab.getAttribute('aria-controls'));
            }
        });
    });
}

function switchTab(panelId) {
    const tabs = document.querySelectorAll('[role="tab"]');
    const panels = document.querySelectorAll('[role="tabpanel"]');

    tabs.forEach(tab => {
        const isSelected = tab.getAttribute('aria-controls') === panelId;
        tab.setAttribute('aria-selected', isSelected);
        tab.setAttribute('tabindex', isSelected ? '0' : '-1');
    });

    panels.forEach(panel => {
        const isVisible = panel.id === panelId;
        panel.setAttribute('aria-hidden', !isVisible);
    });
}

// Drag and drop
function initDragDrop() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e => {
        dropzone.addEventListener(e, evt => {
            evt.preventDefault();
            evt.stopPropagation();
        });
    });

    ['dragenter', 'dragover'].forEach(e => {
        dropzone.addEventListener(e, () => dropzone.classList.add('dragover'));
    });

    ['dragleave', 'drop'].forEach(e => {
        dropzone.addEventListener(e, () => dropzone.classList.remove('dragover'));
    });

    dropzone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            updateDropzoneText(files[0].name);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            updateDropzoneText(fileInput.files[0].name);
        }
    });
}

function updateDropzoneText(filename) {
    const text = document.querySelector('.dropzone-text');
    text.textContent = filename;
}

// Form handlers
async function handleUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('file-input');

    if (!fileInput.files.length) {
        showResult('upload', 'error', 'Select a file');
        return;
    }

    const file = fileInput.files[0];
    if (file.size > 10 * 1024 * 1024) {
        showResult('upload', 'error', 'File exceeds 10 MB');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    await submit('upload', '/upload', formData);
}

async function handlePaste(e) {
    e.preventDefault();
    const content = document.getElementById('ics-textarea').value.trim();

    if (!content) {
        showResult('paste', 'error', 'Enter iCalendar content');
        return;
    }

    if (!content.includes('BEGIN:VCALENDAR')) {
        showResult('paste', 'error', 'Invalid iCalendar format');
        return;
    }

    await submit('paste', '/anonymize', JSON.stringify({ ics: content }), 'application/json');
}

async function handleFetch(e) {
    e.preventDefault();
    const url = document.getElementById('url-input').value.trim();

    if (!url) {
        showResult('fetch', 'error', 'Enter a URL');
        return;
    }

    try {
        new URL(url);
    } catch {
        showResult('fetch', 'error', 'Invalid URL');
        return;
    }

    await submit('fetch', `/fetch?url=${encodeURIComponent(url)}`);
}

// Generic submit
async function submit(section, endpoint, body, contentType) {
    showResult(section, 'loading', 'Processing...');

    try {
        const options = {
            method: endpoint.startsWith('/fetch') ? 'GET' : 'POST'
        };

        if (body && options.method === 'POST') {
            options.body = body;
            if (contentType) {
                options.headers = { 'Content-Type': contentType };
            }
        }

        const response = await fetch(endpoint, options);

        if (!response.ok) {
            let msg = `Error ${response.status}`;
            try {
                const data = await response.json();
                if (data.detail) msg = data.detail;
            } catch {}
            throw new Error(msg);
        }

        blobs[section] = await response.blob();
        showResult(section, 'success', 'Done', true);
    } catch (err) {
        const msg = err.message.includes('Failed to fetch')
            ? 'Network error'
            : err.message;
        showResult(section, 'error', msg);
    }
}

// Show result inline
function showResult(section, type, message, withDownload = false) {
    const result = document.getElementById(`${section}-result`);
    result.className = `result ${type}`;
    result.hidden = false;

    if (withDownload) {
        result.innerHTML = `
            <div class="result-content">
                <span><strong>Success!</strong> Your calendar has been anonymized.</span>
                <button class="download-btn" onclick="download('${section}')" aria-label="Download anonymized calendar">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M8 11L4 7h2.5V2h3v5H12L8 11z" fill="currentColor"/>
                        <path d="M14 13v1H2v-1h12z" fill="currentColor"/>
                    </svg>
                </button>
            </div>
        `;
    } else {
        result.textContent = message;
    }
}

// Download
function download(section) {
    const blob = blobs[section];
    if (!blob) return;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `anonymized-${Date.now()}.ics`;
    a.click();
    URL.revokeObjectURL(url);
}

// Make download globally accessible
window.download = download;

// Update copyright year
function updateCopyrightYear() {
    const startYear = 2025;
    const currentYear = new Date().getFullYear();
    const yearElement = document.getElementById('copyright-year');

    if (currentYear > startYear) {
        yearElement.textContent = `${startYear}-${currentYear}`;
    } else {
        yearElement.textContent = startYear;
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDragDrop();
    updateCopyrightYear();
    document.getElementById('upload-form').addEventListener('submit', handleUpload);
    document.getElementById('paste-form').addEventListener('submit', handlePaste);
    document.getElementById('fetch-form').addEventListener('submit', handleFetch);
});
