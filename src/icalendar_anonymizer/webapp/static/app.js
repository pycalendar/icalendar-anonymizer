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

/**
 * Extract field configuration from the Advanced Options form for a specific section.
 * Uses DOM queries to discover all field selects, avoiding hardcoded field lists.
 *
 * @param {string} section - The section identifier ('upload', 'paste', or 'fetch')
 * @returns {Object|null} Object mapping field names to their modes, or null if all fields use default (randomize)
 */
function getFieldConfig(section) {
    const config = {};

    // Query all select elements within the field-config-grid for this section
    const selects = document.querySelectorAll(`#${section}-panel .field-config-grid select`);

    for (const select of selects) {
        // Extract field name from select ID (format: "{section}-{field}")
        const fieldName = select.id.replace(`${section}-`, '');
        if (select.value && select.value !== 'randomize') {
            config[fieldName] = select.value;
        }
    }

    return Object.keys(config).length > 0 ? config : null;
}

// Form handlers
async function handleUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('file-input');
    const shareCheckbox = document.getElementById('upload-share');

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

    const config = getFieldConfig('upload');
    if (config) {
        formData.append('config', JSON.stringify(config));
    }

    if (shareCheckbox.checked) {
        await shareFile('upload', formData);
    } else {
        await submit('upload', '/upload', formData);
    }
}

async function handlePaste(e) {
    e.preventDefault();
    const content = document.getElementById('ics-textarea').value.trim();
    const shareCheckbox = document.getElementById('paste-share');

    if (!content) {
        showResult('paste', 'error', 'Enter iCalendar content');
        return;
    }

    if (!content.includes('BEGIN:VCALENDAR')) {
        showResult('paste', 'error', 'Invalid iCalendar format');
        return;
    }

    const config = getFieldConfig('paste');

    if (shareCheckbox.checked) {
        // Convert content to file for /share endpoint
        const blob = new Blob([content], { type: 'text/calendar' });
        const formData = new FormData();
        formData.append('file', blob, 'calendar.ics');
        if (config) {
            formData.append('config', JSON.stringify(config));
        }
        await shareFile('paste', formData);
    } else {
        const payload = { ics: content };
        if (config) {
            payload.config = config;
        }
        await submit('paste', '/anonymize', JSON.stringify(payload), 'application/json');
    }
}

async function handleFetch(e) {
    e.preventDefault();
    const url = document.getElementById('url-input').value.trim();
    const shareCheckbox = document.getElementById('fetch-share');

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

    const config = getFieldConfig('fetch');

    if (shareCheckbox.checked) {
        // Fetch and share workflow
        await fetchAndShare('fetch', url, config);
    } else {
        let fetchUrl = `/fetch?url=${encodeURIComponent(url)}`;
        if (config) {
            for (const [field, mode] of Object.entries(config)) {
                fetchUrl += `&${field}=${mode}`;
            }
        }
        await submit('fetch', fetchUrl);
    }
}

// Share file (upload to R2)
async function shareFile(section, formData) {
    showResult(section, 'loading', 'Generating shareable link...');

    try {
        const response = await fetch('/share', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            let msg = `Error ${response.status}`;
            try {
                const data = await response.json();
                if (data.detail) msg = data.detail;
            } catch {}
            throw new Error(msg);
        }

        const { url } = await response.json();
        showShareResult(section, url);
    } catch (err) {
        const msg = err.message.includes('Failed to fetch')
            ? 'Network error'
            : err.message;
        showResult(section, 'error', msg);
    }
}

// Fetch URL then share
async function fetchAndShare(section, url, config) {
    showResult(section, 'loading', 'Fetching and generating shareable link...');

    try {
        // First fetch the calendar
        let fetchUrl = `/fetch?url=${encodeURIComponent(url)}`;
        if (config) {
            for (const [field, mode] of Object.entries(config)) {
                fetchUrl += `&${field}=${mode}`;
            }
        }
        const fetchResponse = await fetch(fetchUrl);

        if (!fetchResponse.ok) {
            let msg = `Error ${fetchResponse.status}`;
            try {
                const data = await fetchResponse.json();
                if (data.detail) msg = data.detail;
            } catch {}
            throw new Error(msg);
        }

        // Convert response to file
        const blob = await fetchResponse.blob();
        const formData = new FormData();
        formData.append('file', blob, 'calendar.ics');

        // Share it (already anonymized, so no config needed)
        const shareResponse = await fetch('/share', {
            method: 'POST',
            body: formData
        });

        if (!shareResponse.ok) {
            let msg = `Error ${shareResponse.status}`;
            try {
                const data = await shareResponse.json();
                if (data.detail) msg = data.detail;
            } catch {}
            throw new Error(msg);
        }

        const { url: shareUrl } = await shareResponse.json();
        showShareResult(section, shareUrl);
    } catch (err) {
        const msg = err.message.includes('Failed to fetch')
            ? 'Network error'
            : err.message;
        showResult(section, 'error', msg);
    }
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
                <button class="download-btn" data-section="${section}" aria-label="Download anonymized calendar">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M8 11L4 7h2.5V2h3v5H12L8 11z" fill="currentColor"/>
                        <path d="M14 13v1H2v-1h12z" fill="currentColor"/>
                    </svg>
                </button>
            </div>
        `;

        // Add event listener to the download button
        const downloadBtn = result.querySelector('.download-btn');
        downloadBtn.addEventListener('click', () => download(section));
    } else {
        result.textContent = message;
    }
}

// Show share result with URL
function showShareResult(section, url) {
    const result = document.getElementById(`${section}-result`);
    result.className = 'result success share-result';
    result.hidden = false;

    result.innerHTML = `
        <div class="share-result-content">
            <div class="share-result-header">
                <svg class="share-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 0C4.477 0 0 4.477 0 10c0 5.523 4.477 10 10 10 5.523 0 10-4.477 10-10 0-5.523-4.477-10-10-10zm-1 15l-5-5 1.41-1.41L9 12.17l6.59-6.59L17 7l-8 8z" fill="currentColor"/>
                </svg>
                <span><strong>Shareable link generated!</strong> Expires in 30 days.</span>
            </div>
            <div class="share-url-box">
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="share-url-link" id="${section}-share-url">${url}</a>
                <button class="copy-btn" data-section="${section}" aria-label="Copy link">Copy</button>
            </div>
        </div>
    `;

    // Add event listener to the copy button
    const copyBtn = result.querySelector('.copy-btn');
    copyBtn.addEventListener('click', () => copyShareUrl(section));
}

// Copy share URL to clipboard
async function copyShareUrl(section) {
    const link = document.getElementById(`${section}-share-url`);
    const copyBtn = document.querySelector(`[data-section="${section}"].copy-btn`);

    try {
        await navigator.clipboard.writeText(link.href);

        // Show feedback
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.disabled = true;

        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.disabled = false;
        }, 2000);
    } catch (err) {
        // Fallback: select text for manual copy
        const range = document.createRange();
        range.selectNodeContents(link);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
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

// Check if shareable links are available
async function checkShareableLinks() {
    try {
        const response = await fetch('/health');
        if (response.ok) {
            const data = await response.json();
            if (!data.r2_enabled) {
                // Hide all share checkboxes when R2 is not available
                document.querySelectorAll('.share-checkbox').forEach(el => {
                    el.hidden = true;
                });
            }
        }
    } catch {
        // If health check fails, hide share options to be safe
        document.querySelectorAll('.share-checkbox').forEach(el => {
            el.hidden = true;
        });
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDragDrop();
    updateCopyrightYear();
    checkShareableLinks();
    document.getElementById('upload-form').addEventListener('submit', handleUpload);
    document.getElementById('paste-form').addEventListener('submit', handlePaste);
    document.getElementById('fetch-form').addEventListener('submit', handleFetch);
});
