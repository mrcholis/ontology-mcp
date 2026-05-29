// ============================================================================
// Payment Intelligence MVP - Frontend JavaScript
// ============================================================================

// Theme Management
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update icon
    document.getElementById('themeIcon').textContent = newTheme === 'dark' ? '☀️' : '🌙';
}

// Load saved theme
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.getElementById('themeIcon').textContent = savedTheme === 'dark' ? '☀️' : '🌙';
});

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const results = document.getElementById('results');

// ============================================================================
// Drag and Drop Handlers
// ============================================================================

dropzone.addEventListener('click', () => {
    fileInput.click();
});

dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dropzone-active');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dropzone-active');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dropzone-active');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        analyzeFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    const files = e.target.files;
    if (files.length > 0) {
        analyzeFile(files[0]);
    }
});

// ============================================================================
// File Analysis
// ============================================================================

async function analyzeFile(file) {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.xml')) {
        showError('Please upload an XML file');
        return;
    }
    
    // Show loading state
    hideError();
    hideResults();
    dropzone.classList.add('hidden');
    loading.classList.remove('hidden');
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Upload and analyze
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to analyze file');
        }
        
        if (data.success) {
            displayResults(data);
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
        
    } catch (err) {
        console.error('Analysis error:', err);
        showError(err.message);
        loading.classList.add('hidden');
        dropzone.classList.remove('hidden');
    }
}

// ============================================================================
// Display Results
// ============================================================================

function displayResults(data) {
    // Hide loading
    loading.classList.add('hidden');
    
    // Show results
    results.classList.remove('hidden');
    
    // File name
    document.getElementById('fileName').textContent = data.filename;
    
    // Summary cards
    document.getElementById('messageCount').textContent = data.summary.message_count;
    document.getElementById('totalAmount').textContent = formatCurrency(data.summary.total_amount);
    document.getElementById('alertCount').textContent = data.alerts.length;
    document.getElementById('relationshipCount').textContent = data.relationships;
    
    // Semantic / RDF section
    if (data.semantic) {
        document.getElementById('signalsExtracted').textContent = data.semantic.signals_extracted;
        document.getElementById('rdfTriples').textContent = data.semantic.rdf_triples;
        document.getElementById('ontologyMapped').textContent = data.semantic.ontology_mapped ? '✅ Yes' : '❌ No';
        document.getElementById('rdfPreview').textContent = data.semantic.rdf_preview;
    }
    
    // Alerts
    displayAlerts(data.alerts);
    
    // Timeline
    displayTimeline(data.timeline);
    
    // Institutions
    displayInstitutions(data.summary.institutions);
    
    // Message types
    displayMessageTypes(data.summary.message_types);
}

function displayAlerts(alerts) {
    const alertsList = document.getElementById('alertsList');
    alertsList.innerHTML = '';
    
    if (alerts.length === 0) {
        alertsList.innerHTML = `
            <div class="text-gray-500 text-center py-8">
                <div class="text-4xl mb-2">✅</div>
                <p>No alerts - everything looks good!</p>
            </div>
        `;
        return;
    }
    
    alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert-${alert.severity} p-4 rounded-lg mb-3`;
        alertDiv.innerHTML = `
            <div class="flex items-start">
                <div class="text-2xl mr-3">${alert.icon}</div>
                <div class="flex-1">
                    <p class="font-semibold text-gray-800">${alert.title}</p>
                    <p class="text-gray-700 text-sm mt-1">${alert.message}</p>
                </div>
            </div>
        `;
        alertsList.appendChild(alertDiv);
    });
}

function displayTimeline(timeline) {
    const timelineDiv = document.getElementById('timeline');
    timelineDiv.innerHTML = '';
    
    if (timeline.length === 0) {
        timelineDiv.innerHTML = '<p class="text-gray-500 text-center py-8">No timeline events</p>';
        return;
    }
    
    timeline.forEach((event, index) => {
        const eventDiv = document.createElement('div');
        eventDiv.className = `timeline-item mb-6`;
        eventDiv.innerHTML = `
            <div class="flex items-start">
                <div class="absolute left-0 w-10 h-10 rounded-full flex items-center justify-center text-2xl severity-${event.severity}">
                    ${event.icon}
                </div>
                <div class="flex-1 bg-gray-50 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-bold text-lg text-gray-800">${event.title}</span>
                        <span class="text-sm text-gray-500">${event.short_time}</span>
                    </div>
                    <p class="text-gray-700">${event.description}</p>
                    <p class="text-xs text-gray-500 mt-2">${event.time}</p>
                </div>
            </div>
        `;
        timelineDiv.appendChild(eventDiv);
    });
}

function displayInstitutions(institutions) {
    const institutionsList = document.getElementById('institutionsList');
    institutionsList.innerHTML = '';
    
    if (institutions.length === 0) {
        institutionsList.innerHTML = '<p class="text-gray-500 text-sm">None found</p>';
        return;
    }
    
    institutions.forEach(institution => {
        const institutionDiv = document.createElement('div');
        institutionDiv.className = 'flex items-center bg-gray-50 px-4 py-2 rounded';
        institutionDiv.innerHTML = `
            <div class="text-xl mr-2">🏦</div>
            <span class="font-mono text-sm font-semibold">${institution}</span>
        `;
        institutionsList.appendChild(institutionDiv);
    });
}

function displayMessageTypes(messageTypes) {
    const messageTypesList = document.getElementById('messageTypesList');
    messageTypesList.innerHTML = '';
    
    const typeLabels = {
        'PaymentCancellation': '📤 Payment Cancellation (camt.056)',
        'InvestigationResolution': '✅ Investigation Resolution (camt.029)',
        'UnableToApply': '⚠️ Unable to Apply (camt.026)',
        'AccountStatement': '📊 Account Statement (camt.053)'
    };
    
    if (messageTypes.length === 0) {
        messageTypesList.innerHTML = '<p class="text-gray-500 text-sm">None found</p>';
        return;
    }
    
    messageTypes.forEach(type => {
        const typeDiv = document.createElement('div');
        typeDiv.className = 'flex items-center bg-gray-50 px-4 py-2 rounded';
        typeDiv.innerHTML = `
            <span class="text-sm">${typeLabels[type] || type}</span>
        `;
        messageTypesList.appendChild(typeDiv);
    });
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatCurrency(amount) {
    if (amount === 0) {
        return '$0';
    }
    return '$' + amount.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

function showError(message) {
    errorMessage.textContent = message;
    error.classList.remove('hidden');
}

function hideError() {
    error.classList.add('hidden');
}

function hideResults() {
    results.classList.add('hidden');
}

function reset() {
    // Reset file input
    fileInput.value = '';
    
    // Hide results and error
    hideResults();
    hideError();
    
    // Show dropzone
    dropzone.classList.remove('hidden');
}

function showRdfExplanation() {
    // Update triple count in modal
    const tripleCount = document.getElementById('rdfTriples').textContent;
    document.getElementById('modalTripleCount').textContent = tripleCount;
    
    // Show modal
    document.getElementById('rdfModal').classList.remove('hidden');
}

function closeRdfModal() {
    document.getElementById('rdfModal').classList.add('hidden');
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('rdfModal');
    if (e.target === modal) {
        closeRdfModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeRdfModal();
    }
});

function loadFullDemo() {
    // Show loading
    hideError();
    hideResults();
    dropzone.classList.add('hidden');
    loading.classList.remove('hidden');
    
    // Call the full demo API endpoint
    fetch('/api/demo/full')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayResults(data);
            } else {
                throw new Error(data.error || 'Failed to load demo');
            }
        })
        .catch(error => {
            console.error('Demo load error:', error);
            
            // Fallback to static demo data if API fails
            displayResults({
                "success": true,
                "filename": "Complete Payment Lifecycle (4 Messages)",
                "summary": {
                    "message_count": 4,
                    "total_amount": 249850.0,
                    "institutions": ["BLUEUSNY001", "GRENCHZZ002"],
                    "institution_count": 2,
                    "message_types": ["UnableToApply", "PaymentCancellation", "InvestigationResolution", "AccountStatement"],
                    "date_range": "2022-07-18"
                },
                "timeline": [
                    {
                        "time": "2022-07-18 13:27:55",
                        "short_time": "13:27:55",
                        "type": "UnableToApply",
                        "icon": "⚠️",
                        "title": "Unable to Apply",
                        "description": "$124,850.00 USD • Issue: IN39 (Incorrect info) • GRENCHZZ002 → BLUEUSNY001",
                        "severity": "error"
                    },
                    {
                        "time": "2022-07-18 13:28:33",
                        "short_time": "13:28:33",
                        "type": "PaymentCancellation",
                        "icon": "📤",
                        "title": "Payment Cancellation Request",
                        "description": "$125,000.00 USD • Reason: CUST (Customer request) • BLUEUSNY001 → GRENCHZZ002",
                        "severity": "warning"
                    },
                    {
                        "time": "2022-07-18 13:29:48",
                        "short_time": "13:29:48",
                        "type": "InvestigationResolution",
                        "icon": "❌",
                        "title": "Investigation Resolution",
                        "description": "Status: REJECTED - Payment will proceed • GRENCHZZ002 → BLUEUSNY001",
                        "severity": "error"
                    },
                    {
                        "time": "2022-07-18 14:00:00",
                        "short_time": "14:00:00",
                        "type": "AccountStatement",
                        "icon": "📊",
                        "title": "Account Statement",
                        "description": "Balance check: ❌ Mismatch • Discrepancy: $100.00",
                        "severity": "critical"
                    }
                ],
                "alerts": [
                    {
                        "severity": "warning",
                        "icon": "🟡",
                        "title": "High Value Transaction",
                        "message": "Transaction amount: $125,000.00 USD detected in cancellation request"
                    },
                    {
                        "severity": "error",
                        "icon": "🟠",
                        "title": "Unable to Apply",
                        "message": "Payment cannot be processed: Incorrect beneficiary information (IN39)"
                    },
                    {
                        "severity": "error",
                        "icon": "🟠",
                        "title": "Cancellation Rejected",
                        "message": "Payment cancellation request was rejected - payment will proceed despite issues"
                    },
                    {
                        "severity": "critical",
                        "icon": "🔴",
                        "title": "Balance Mismatch Detected",
                        "message": "Account balance discrepancy: $100.00 - Critical reconciliation issue!"
                    }
                ],
                "relationships": 3,
                "semantic": {
                    "signals_extracted": 4,
                    "rdf_triples": 185,
                    "rdf_preview": "@prefix fin: <http://example.org/financial/ontology#> .\n@prefix inst: <http://example.org/financial/instance#> .\n@prefix iso20022: <http://example.org/iso20022/ontology#> .\n\ninst:payment_cancellation_CASE_001 a fin:PaymentCancellation, iso20022:camt_056 ;\n    fin:hasAmount inst:amount_CASE_001 ;\n    fin:fromInstitution inst:institution_BLUEUSNY001 ;\n    fin:toInstitution inst:institution_GRENCHZZ002 .\n...",
                    "ontology_mapped": true
                }
            });
        })
        .finally(() => {
            loading.classList.add('hidden');
        });
}

// ============================================================================
// Demo Data (for testing without backend)
// ============================================================================

// Uncomment this to test frontend without backend
// setTimeout(() => {
//     displayResults({
//         "success": true,
//         "filename": "demo_payment.xml",
//         "summary": {
//             "message_count": 4,
//             "total_amount": 249850.0,
//             "institutions": ["BLUEUSNY001", "GRENCHZZ002"],
//             "message_types": ["PaymentCancellation", "InvestigationResolution", "UnableToApply", "AccountStatement"]
//         },
//         "timeline": [
//             {
//                 "time": "2022-07-18 13:27:55",
//                 "short_time": "13:27:55",
//                 "icon": "⚠️",
//                 "title": "Unable to Apply",
//                 "description": "$124,850.00 USD • Issue: IN39 • GRENCHZZ002 → BLUEUSNY001",
//                 "severity": "error"
//             },
//             {
//                 "time": "2022-07-18 13:28:33",
//                 "short_time": "13:28:33",
//                 "icon": "📤",
//                 "title": "Payment Cancellation Request",
//                 "description": "$125,000.00 USD • Reason: CUST • BLUEUSNY001 → GRENCHZZ002",
//                 "severity": "warning"
//             }
//         ],
//         "alerts": [
//             {
//                 "severity": "critical",
//                 "icon": "🔴",
//                 "title": "Balance Mismatch Detected",
//                 "message": "Account balance discrepancy: $100.00"
//             }
//         ],
//         "relationships": 3
//     });
// }, 1000);

console.log('🚀 Payment Intelligence MVP loaded');
console.log('📤 Ready to analyze ISO 20022 files!');