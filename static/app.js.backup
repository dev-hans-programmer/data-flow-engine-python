/**
 * Data Processing Pipeline System - Frontend JavaScript
 */

// Global variables
let currentSection = 'dashboard';
let refreshInterval = null;
let charts = {};

// API Base URL
const API_BASE = '/api/v1';

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupNavigation();
    setupEventListeners();
    loadDashboard();
    startAutoRefresh();
    
    // Show toast notification
    showToast('System Ready', 'Pipeline system loaded successfully', 'success');
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link[data-section]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            showSection(section);
        });
    });
}

function setupEventListeners() {
    // Pipeline search
    const pipelineSearch = document.getElementById('pipeline-search');
    if (pipelineSearch) {
        pipelineSearch.addEventListener('input', debounce(searchPipelines, 300));
    }
    
    // Filter changes
    const pipelineStatusFilter = document.getElementById('pipeline-status-filter');
    if (pipelineStatusFilter) {
        pipelineStatusFilter.addEventListener('change', refreshPipelines);
    }
    
    const executionStatusFilter = document.getElementById('execution-status-filter');
    if (executionStatusFilter) {
        executionStatusFilter.addEventListener('change', refreshExecutions);
    }
    
    const executionPipelineFilter = document.getElementById('execution-pipeline-filter');
    if (executionPipelineFilter) {
        executionPipelineFilter.addEventListener('change', refreshExecutions);
    }
    
    // File tab changes
    const fileTabs = document.querySelectorAll('#file-tabs .nav-link');
    fileTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function() {
            if (this.getAttribute('href') === '#uploaded-files') {
                loadUploadedFiles();
            } else if (this.getAttribute('href') === '#output-files') {
                loadOutputFiles();
            }
        });
    });
}

function showSection(section) {
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`[data-section="${section}"]`).classList.add('active');
    
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // Show target section
    const targetSection = document.getElementById(`${section}-section`);
    if (targetSection) {
        targetSection.style.display = 'block';
        targetSection.classList.add('fade-in');
    }
    
    currentSection = section;
    
    // Load section-specific data
    switch (section) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'pipelines':
            loadPipelines();
            break;
        case 'executions':
            loadExecutions();
            break;
        case 'files':
            loadUploadedFiles();
            break;
        case 'monitoring':
            loadMonitoring();
            break;
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        // Load system statistics
        const stats = await fetchJSON('/api/v1/statistics');
        updateDashboardStats(stats);
        
        // Load recent executions
        const executions = await fetchJSON('/api/v1/executions?limit=10');
        displayRecentExecutions(executions.executions);
        
        // Load system health
        const health = await fetchJSON('/health');
        updateSystemStatus(health);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error', 'Failed to load dashboard data', 'error');
    }
}

function updateDashboardStats(stats) {
    document.getElementById('total-pipelines').textContent = stats.total_executions || '0';
    document.getElementById('running-executions').textContent = '0'; // Will be updated by health check
    document.getElementById('success-rate').textContent = `${stats.success_rate || 0}%`;
    document.getElementById('system-load').textContent = 'Normal'; // Will be updated by monitoring
}

function displayRecentExecutions(executions) {
    const container = document.getElementById('recent-executions');
    
    if (!executions || executions.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-info-circle fa-2x text-muted"></i>
                <p class="text-muted mt-2">No recent executions found</p>
            </div>
        `;
        return;
    }
    
    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Pipeline</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${executions.map(execution => `
                    <tr>
                        <td>
                            <strong>${execution.pipeline_name}</strong><br>
                            <small class="text-muted">${execution.id.substring(0, 8)}...</small>
                        </td>
                        <td>
                            <span class="status-badge status-${execution.status}">
                                ${getStatusIcon(execution.status)} ${execution.status}
                            </span>
                        </td>
                        <td>
                            ${execution.start_time ? formatDateTime(execution.start_time) : 'Not started'}
                        </td>
                        <td>
                            ${execution.duration ? formatDuration(execution.duration) : '-'}
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-primary" onclick="showExecutionDetails('${execution.id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                ${execution.status === 'running' ? 
                                    `<button class="btn btn-outline-danger" onclick="cancelExecution('${execution.id}')">
                                        <i class="fas fa-stop"></i>
                                    </button>` : ''
                                }
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function updateSystemStatus(health) {
    const statusElement = document.getElementById('system-status');
    const isHealthy = health.status === 'healthy';
    
    statusElement.className = `badge ${isHealthy ? 'bg-success' : 'bg-warning'}`;
    statusElement.innerHTML = `
        <i class="fas fa-circle"></i> 
        ${isHealthy ? 'System Healthy' : 'System Warning'}
    `;
}

// Pipeline Functions
async function loadPipelines() {
    try {
        const statusFilter = document.getElementById('pipeline-status-filter').value;
        const searchTerm = document.getElementById('pipeline-search').value;
        
        let url = '/api/v1/pipelines?limit=100';
        if (statusFilter) url += `&status=${statusFilter}`;
        
        const data = await fetchJSON(url);
        let pipelines = data.pipelines || [];
        
        // Client-side search filtering
        if (searchTerm) {
            pipelines = pipelines.filter(pipeline => 
                pipeline.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (pipeline.description && pipeline.description.toLowerCase().includes(searchTerm.toLowerCase()))
            );
        }
        
        displayPipelines(pipelines);
        
        // Update execution filter dropdown
        updateExecutionPipelineFilter(pipelines);
        
    } catch (error) {
        console.error('Error loading pipelines:', error);
        showToast('Error', 'Failed to load pipelines', 'error');
    }
}

function displayPipelines(pipelines) {
    const container = document.getElementById('pipelines-table');
    
    if (!pipelines || pipelines.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-sitemap fa-3x text-muted"></i>
                <h5 class="mt-3 text-muted">No pipelines found</h5>
                <p class="text-muted">Create your first pipeline to get started</p>
                <button class="btn btn-primary" onclick="showCreatePipelineModal()">
                    <i class="fas fa-plus"></i> Create Pipeline
                </button>
            </div>
        `;
        return;
    }
    
    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Steps</th>
                    <th>Schedule</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${pipelines.map(pipeline => `
                    <tr>
                        <td>
                            <strong>${pipeline.name}</strong><br>
                            <small class="text-muted text-truncate-2">${pipeline.description || 'No description'}</small>
                        </td>
                        <td>
                            <span class="status-badge status-${pipeline.status}">
                                ${getStatusIcon(pipeline.status)} ${pipeline.status}
                            </span>
                        </td>
                        <td>
                            <span class="badge bg-secondary">${pipeline.steps ? pipeline.steps.length : 0} steps</span>
                        </td>
                        <td>
                            ${pipeline.schedule ? 
                                `<span class="badge bg-info">${pipeline.schedule.type}</span>` : 
                                '<span class="text-muted">Manual</span>'
                            }
                        </td>
                        <td>
                            ${formatDateTime(pipeline.created_at)}
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-success" onclick="executePipeline('${pipeline.id}')" 
                                        ${pipeline.status !== 'active' ? 'disabled' : ''}>
                                    <i class="fas fa-play"></i>
                                </button>
                                <button class="btn btn-outline-primary" onclick="editPipeline('${pipeline.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-outline-info" onclick="viewPipelineDetails('${pipeline.id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="deletePipeline('${pipeline.id}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function updateExecutionPipelineFilter(pipelines) {
    const filter = document.getElementById('execution-pipeline-filter');
    if (!filter) return;
    
    const currentValue = filter.value;
    filter.innerHTML = '<option value="">All Pipelines</option>';
    
    pipelines.forEach(pipeline => {
        const option = document.createElement('option');
        option.value = pipeline.id;
        option.textContent = pipeline.name;
        if (option.value === currentValue) option.selected = true;
        filter.appendChild(option);
    });
}

async function executePipeline(pipelineId) {
    try {
        const response = await fetchJSON(`/api/v1/pipelines/${pipelineId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        showToast('Success', 'Pipeline execution started', 'success');
        
        // Switch to executions view to see the running pipeline
        showSection('executions');
        
    } catch (error) {
        console.error('Error executing pipeline:', error);
        showToast('Error', 'Failed to execute pipeline', 'error');
    }
}

async function viewPipelineDetails(pipelineId) {
    try {
        const pipeline = await fetchJSON(`/api/v1/pipelines/${pipelineId}`);
        const modal = new bootstrap.Modal(document.getElementById('pipelineDetailsModal'));
        
        // Store pipeline ID for execute button
        window.currentPipelineId = pipelineId;
        
        const content = document.getElementById('pipeline-details-content');
        content.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-8">
                    <h4>${pipeline.name}</h4>
                    <p class="text-muted">${pipeline.description || 'No description provided'}</p>
                </div>
                <div class="col-md-4 text-end">
                    <span class="status-badge status-${pipeline.status} fs-6">
                        ${getStatusIcon(pipeline.status)} ${pipeline.status}
                    </span>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <h6>Pipeline ID</h6>
                    <p class="text-muted small">${pipeline.id}</p>
                </div>
                <div class="col-md-3">
                    <h6>Created</h6>
                    <p class="text-muted">${formatDateTime(pipeline.created_at)}</p>
                </div>
                <div class="col-md-3">
                    <h6>Updated</h6>
                    <p class="text-muted">${formatDateTime(pipeline.updated_at)}</p>
                </div>
                <div class="col-md-3">
                    <h6>Created By</h6>
                    <p class="text-muted">${pipeline.created_by || 'System'}</p>
                </div>
            </div>
            
            ${pipeline.schedule ? `
                <div class="mb-4">
                    <h6>Schedule Configuration</h6>
                    <div class="bg-light p-3 rounded">
                        <span class="badge bg-info">${pipeline.schedule.type}</span>
                        ${pipeline.schedule.cron_expression ? ` - ${pipeline.schedule.cron_expression}` : ''}
                        ${pipeline.schedule.interval ? ` - Every ${pipeline.schedule.interval} minutes` : ''}
                    </div>
                </div>
            ` : ''}
            
            <div class="mb-4">
                <h6>Pipeline Steps (${pipeline.steps ? pipeline.steps.length : 0})</h6>
                <div class="pipeline-flow">
                    ${pipeline.steps && pipeline.steps.length > 0 ? 
                        pipeline.steps.map((step, index) => `
                            <div class="step-card">
                                <div class="step-number">${index + 1}</div>
                                <div class="step-content">
                                    <h6>${step.name}</h6>
                                    <span class="badge bg-secondary">${step.type}</span>
                                    ${step.description ? `<p class="text-muted small mt-1">${step.description}</p>` : ''}
                                    ${getStepConfiguration(step)}
                                </div>
                            </div>
                            ${index < pipeline.steps.length - 1 ? '<div class="step-arrow"><i class="fas fa-arrow-down"></i></div>' : ''}
                        `).join('') : 
                        '<div class="text-center text-muted py-3">No steps configured</div>'
                    }
                </div>
            </div>
            
            ${pipeline.tags && pipeline.tags.length > 0 ? `
                <div class="mb-3">
                    <h6>Tags</h6>
                    ${pipeline.tags.map(tag => `<span class="badge bg-light text-dark me-1">${tag}</span>`).join('')}
                </div>
            ` : ''}
        `;
        
        modal.show();
        
    } catch (error) {
        console.error('Error loading pipeline details:', error);
        showToast('Error', 'Failed to load pipeline details', 'error');
    }
}

function getStepConfiguration(step) {
    let config = '';
    
    switch (step.type) {
        case 'load':
            config = `
                <div class="step-config">
                    <small class="text-muted">Source: ${step.source_path}</small><br>
                    <small class="text-muted">Format: ${step.format}</small>
                </div>
            `;
            break;
        case 'save':
            config = `
                <div class="step-config">
                    <small class="text-muted">Output: ${step.output_path}</small><br>
                    <small class="text-muted">Format: ${step.format}</small>
                </div>
            `;
            break;
        case 'transform':
            config = `
                <div class="step-config">
                    <small class="text-muted">Operations: ${step.operations ? step.operations.length : 0}</small>
                    ${step.operations && step.operations.length > 0 ? 
                        step.operations.map(op => `<br><small class="text-muted">• ${op.type}</small>`).join('') : ''
                    }
                </div>
            `;
            break;
        case 'filter':
            config = `
                <div class="step-config">
                    <small class="text-muted">Conditions: ${step.conditions ? step.conditions.length : 0}</small>
                </div>
            `;
            break;
        case 'aggregate':
            config = `
                <div class="step-config">
                    <small class="text-muted">Group by: ${step.group_by ? step.group_by.join(', ') : 'None'}</small>
                </div>
            `;
            break;
        case 'join':
            config = `
                <div class="step-config">
                    <small class="text-muted">Join with: ${step.right_dataset}</small><br>
                    <small class="text-muted">Type: ${step.join_type}</small>
                </div>
            `;
            break;
    }
    
    return config;
}

async function executePipelineFromModal() {
    if (window.currentPipelineId) {
        await executePipeline(window.currentPipelineId);
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('pipelineDetailsModal'));
        if (modal) modal.hide();
    }
}

async function deletePipeline(pipelineId) {
    if (!confirm('Are you sure you want to delete this pipeline?')) return;
    
    try {
        await fetchJSON(`/api/v1/pipelines/${pipelineId}`, { method: 'DELETE' });
        showToast('Success', 'Pipeline deleted successfully', 'success');
        refreshPipelines();
    } catch (error) {
        console.error('Error deleting pipeline:', error);
        showToast('Error', 'Failed to delete pipeline', 'error');
    }
}

function refreshPipelines() {
    loadPipelines();
}

function searchPipelines() {
    loadPipelines();
}

// Execution Functions
async function loadExecutions() {
    try {
        const statusFilter = document.getElementById('execution-status-filter').value;
        const pipelineFilter = document.getElementById('execution-pipeline-filter').value;
        
        let url = '/api/v1/executions?limit=100';
        if (statusFilter) url += `&status=${statusFilter}`;
        if (pipelineFilter) url += `&pipeline_id=${pipelineFilter}`;
        
        const data = await fetchJSON(url);
        displayExecutions(data.executions || []);
        
    } catch (error) {
        console.error('Error loading executions:', error);
        showToast('Error', 'Failed to load executions', 'error');
    }
}

function displayExecutions(executions) {
    const container = document.getElementById('executions-table');
    
    if (!executions || executions.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-play-circle fa-3x text-muted"></i>
                <h5 class="mt-3 text-muted">No executions found</h5>
                <p class="text-muted">Execute a pipeline to see results here</p>
            </div>
        `;
        return;
    }
    
    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Pipeline</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Steps</th>
                    <th>Trigger</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${executions.map(execution => `
                    <tr>
                        <td>
                            <strong>${execution.pipeline_name}</strong><br>
                            <small class="text-muted">${execution.id.substring(0, 8)}...</small>
                        </td>
                        <td>
                            <span class="status-badge status-${execution.status}">
                                ${getStatusIcon(execution.status)} ${execution.status}
                            </span>
                        </td>
                        <td>
                            ${execution.start_time ? formatDateTime(execution.start_time) : 'Not started'}
                        </td>
                        <td>
                            ${execution.duration ? formatDuration(execution.duration) : 
                              execution.status === 'running' ? 'Running...' : '-'
                            }
                        </td>
                        <td>
                            <span class="badge bg-info">${execution.steps ? execution.steps.length : 0}</span>
                            ${execution.steps ? 
                                `<small class="text-muted">
                                    (${execution.steps.filter(s => s.status === 'completed').length} completed)
                                </small>` : ''
                            }
                        </td>
                        <td>
                            <span class="badge bg-secondary">${execution.triggered_by || 'manual'}</span>
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-primary" onclick="showExecutionDetails('${execution.id}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                ${execution.status === 'running' ? 
                                    `<button class="btn btn-outline-danger" onclick="cancelExecution('${execution.id}')">
                                        <i class="fas fa-stop"></i>
                                    </button>` : ''
                                }
                                ${execution.output_files && execution.output_files.length > 0 ?
                                    `<button class="btn btn-outline-success" onclick="downloadExecutionOutputs('${execution.id}')">
                                        <i class="fas fa-download"></i>
                                    </button>` : ''
                                }
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

async function showExecutionDetails(executionId) {
    try {
        const execution = await fetchJSON(`/api/v1/executions/${executionId}`);
        const modal = new bootstrap.Modal(document.getElementById('executionDetailsModal'));
        
        const content = document.getElementById('execution-details-content');
        content.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6>Execution ID</h6>
                    <p class="text-muted">${execution.id}</p>
                </div>
                <div class="col-md-6">
                    <h6>Pipeline</h6>
                    <p class="text-muted">${execution.pipeline_name}</p>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-4">
                    <h6>Status</h6>
                    <span class="status-badge status-${execution.status}">
                        ${getStatusIcon(execution.status)} ${execution.status}
                    </span>
                </div>
                <div class="col-md-4">
                    <h6>Started</h6>
                    <p class="text-muted">${execution.start_time ? formatDateTime(execution.start_time) : 'Not started'}</p>
                </div>
                <div class="col-md-4">
                    <h6>Duration</h6>
                    <p class="text-muted">${execution.duration ? formatDuration(execution.duration) : '-'}</p>
                </div>
            </div>
            
            ${execution.error_message ? `
                <div class="alert alert-danger">
                    <h6><i class="fas fa-exclamation-triangle"></i> Error</h6>
                    <p class="mb-0">${execution.error_message}</p>
                </div>
            ` : ''}
            
            <h6>Steps</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Status</th>
                            <th>Duration</th>
                            <th>Retries</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${execution.steps ? execution.steps.map(step => `
                            <tr>
                                <td>${step.step_name}</td>
                                <td>
                                    <span class="status-badge status-${step.status}">
                                        ${getStatusIcon(step.status)} ${step.status}
                                    </span>
                                </td>
                                <td>${step.duration ? formatDuration(step.duration) : '-'}</td>
                                <td>${step.retry_count || 0}</td>
                            </tr>
                        `).join('') : '<tr><td colspan="4" class="text-center text-muted">No steps found</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            ${execution.output_files && execution.output_files.length > 0 ? `
                <h6>Output Files</h6>
                <ul class="list-group">
                    ${execution.output_files.map(file => `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            ${file}
                            <button class="btn btn-sm btn-outline-primary" onclick="downloadFile('${file}')">
                                <i class="fas fa-download"></i>
                            </button>
                        </li>
                    `).join('')}
                </ul>
            ` : ''}
        `;
        
        modal.show();
        
    } catch (error) {
        console.error('Error loading execution details:', error);
        showToast('Error', 'Failed to load execution details', 'error');
    }
}

async function cancelExecution(executionId) {
    if (!confirm('Are you sure you want to cancel this execution?')) return;
    
    try {
        await fetchJSON(`/api/v1/executions/${executionId}/cancel`, { method: 'POST' });
        showToast('Success', 'Execution cancelled', 'success');
        refreshExecutions();
    } catch (error) {
        console.error('Error cancelling execution:', error);
        showToast('Error', 'Failed to cancel execution', 'error');
    }
}

function refreshExecutions() {
    loadExecutions();
}

// File Functions
async function loadUploadedFiles() {
    try {
        const files = await fetchJSON('/api/v1/files');
        displayUploadedFiles(files);
    } catch (error) {
        console.error('Error loading uploaded files:', error);
        showToast('Error', 'Failed to load uploaded files', 'error');
    }
}

function displayUploadedFiles(files) {
    const container = document.getElementById('uploaded-files-table');
    
    if (!files || files.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-file-upload fa-3x text-muted"></i>
                <h5 class="mt-3 text-muted">No files uploaded</h5>
                <p class="text-muted">Upload data files to use in your pipelines</p>
                <button class="btn btn-primary" onclick="showUploadModal()">
                    <i class="fas fa-upload"></i> Upload File
                </button>
            </div>
        `;
        return;
    }
    
    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Format</th>
                    <th>Size</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${files.map(file => `
                    <tr>
                        <td>
                            <strong>${file.name}</strong><br>
                            ${file.metadata && file.metadata.rows ? 
                                `<small class="text-muted">${file.metadata.rows} rows, ${file.metadata.columns} cols</small>` :
                                '<small class="text-muted">No metadata</small>'
                            }
                        </td>
                        <td>
                            ${file.format ? `<span class="badge bg-info">${file.format}</span>` : '-'}
                        </td>
                        <td>
                            ${formatFileSize(file.size)}
                        </td>
                        <td>
                            ${formatDateTime(file.uploaded_at)}
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-primary" onclick="previewFile('${file.path}')">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-outline-success" onclick="downloadFile('${file.path}')">
                                    <i class="fas fa-download"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="deleteFile('${file.path}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

async function loadOutputFiles() {
    try {
        const data = await fetchJSON('/api/v1/files/outputs');
        displayOutputFiles(data.output_files || []);
    } catch (error) {
        console.error('Error loading output files:', error);
        showToast('Error', 'Failed to load output files', 'error');
    }
}

function displayOutputFiles(files) {
    const container = document.getElementById('output-files-table');
    
    if (!files || files.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-file-export fa-3x text-muted"></i>
                <h5 class="mt-3 text-muted">No output files</h5>
                <p class="text-muted">Files generated by pipeline executions will appear here</p>
            </div>
        `;
        return;
    }
    
    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Path</th>
                    <th>Size</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${files.map(file => `
                    <tr>
                        <td>
                            <strong>${file.name}</strong>
                        </td>
                        <td>
                            <small class="text-muted">${file.path}</small>
                        </td>
                        <td>
                            ${formatFileSize(file.size)}
                        </td>
                        <td>
                            ${formatDateTime(new Date(file.created_at * 1000).toISOString())}
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-success" onclick="downloadOutputFile('${file.path}')">
                                    <i class="fas fa-download"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function showUploadModal() {
    const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
    modal.show();
}

async function uploadFile() {
    const form = document.getElementById('upload-form');
    const fileInput = form.querySelector('input[type="file"]');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('Error', 'Please select a file to upload', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const progressContainer = document.getElementById('upload-progress');
        progressContainer.style.display = 'block';
        
        const response = await fetch('/api/v1/files/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        const result = await response.json();
        
        showToast('Success', 'File uploaded successfully', 'success');
        bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
        
        // Refresh files if on files section
        if (currentSection === 'files') {
            loadUploadedFiles();
        }
        
    } catch (error) {
        console.error('Error uploading file:', error);
        showToast('Error', 'Failed to upload file', 'error');
    } finally {
        document.getElementById('upload-progress').style.display = 'none';
    }
}

async function previewFile(filePath) {
    try {
        const data = await fetchJSON(`/api/v1/files/${encodeURIComponent(filePath)}/preview?rows=20`);
        const modal = new bootstrap.Modal(document.getElementById('filePreviewModal'));
        
        const content = document.getElementById('file-preview-content');
        content.innerHTML = `
            <div class="mb-3">
                <h6>File: ${data.file_path}</h6>
                <p class="text-muted">
                    ${data.total_rows} rows, ${data.total_columns} columns 
                    (showing first ${data.preview_rows} rows)
                </p>
            </div>
            
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            ${data.columns.map(col => `<th>${col}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.data.map(row => `
                            <tr>
                                ${data.columns.map(col => `<td>${row[col] !== null ? row[col] : '-'}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        modal.show();
        
    } catch (error) {
        console.error('Error previewing file:', error);
        showToast('Error', 'Failed to preview file', 'error');
    }
}

async function deleteFile(filePath) {
    if (!confirm('Are you sure you want to delete this file?')) return;
    
    try {
        await fetchJSON(`/api/v1/files/${encodeURIComponent(filePath)}`, { method: 'DELETE' });
        showToast('Success', 'File deleted successfully', 'success');
        loadUploadedFiles();
    } catch (error) {
        console.error('Error deleting file:', error);
        showToast('Error', 'Failed to delete file', 'error');
    }
}

function downloadFile(filePath) {
    window.open(`/api/v1/files/${encodeURIComponent(filePath)}/download`, '_blank');
}

function downloadOutputFile(filePath) {
    window.open(`/api/v1/files/outputs/${encodeURIComponent(filePath)}/download`, '_blank');
}

// Monitoring Functions
async function loadMonitoring() {
    try {
        // Load current metrics
        const metrics = await fetchJSON('/health');
        updateMonitoringDisplay(metrics);
        
        // Initialize charts if not already done
        if (!charts.cpu) {
            initializeCharts();
        }
        
        // Load performance history
        const history = await fetchJSON('/api/v1/executions/statistics');
        updatePerformanceChart(history);
        
    } catch (error) {
        console.error('Error loading monitoring data:', error);
        showToast('Error', 'Failed to load monitoring data', 'error');
    }
}

function updateMonitoringDisplay(metrics) {
    // Update CPU and memory gauges
    document.getElementById('cpu-percentage').textContent = `${metrics.cpu_percent || 0}%`;
    document.getElementById('memory-percentage').textContent = `${metrics.memory_percent || 0}%`;
    
    // Update disk usage
    const diskProgress = document.getElementById('disk-progress');
    const diskPercentage = document.getElementById('disk-percentage');
    const diskPercent = metrics.disk_percent || 0;
    
    diskProgress.style.width = `${diskPercent}%`;
    diskPercentage.textContent = `${diskPercent}%`;
    
    // Update progress bar color based on usage
    diskProgress.className = `progress-bar ${
        diskPercent > 80 ? 'bg-danger' : 
        diskPercent > 60 ? 'bg-warning' : 'bg-success'
    }`;
    
    // Update execution counts
    document.getElementById('active-executions-count').textContent = metrics.active_executions || 0;
    document.getElementById('execution-queue-size').textContent = '0'; // Will be updated by real metrics
}

function initializeCharts() {
    // CPU Chart
    const cpuCtx = document.getElementById('cpu-chart').getContext('2d');
    charts.cpu = new Chart(cpuCtx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#007bff', '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '70%',
            responsive: true,
            plugins: {
                legend: { display: false }
            }
        }
    });
    
    // Memory Chart
    const memoryCtx = document.getElementById('memory-chart').getContext('2d');
    charts.memory = new Chart(memoryCtx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#17a2b8', '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '70%',
            responsive: true,
            plugins: {
                legend: { display: false }
            }
        }
    });
    
    // Performance History Chart
    const perfCtx = document.getElementById('performance-chart').getContext('2d');
    charts.performance = new Chart(perfCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Executions',
                data: [],
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updatePerformanceChart(data) {
    if (!charts.performance) return;
    
    // This is a simplified implementation
    // In a real system, you would get time-series data
    const labels = ['6h ago', '5h ago', '4h ago', '3h ago', '2h ago', '1h ago', 'Now'];
    const values = [2, 5, 3, 8, 4, 6, data.recent_executions_24h || 0];
    
    charts.performance.data.labels = labels;
    charts.performance.data.datasets[0].data = values;
    charts.performance.update();
}

// Pipeline Creation Functions
function showCreatePipelineModal() {
    const modal = new bootstrap.Modal(document.getElementById('createPipelineModal'));
    
    // Reset form
    document.getElementById('create-pipeline-form').reset();
    document.getElementById('pipeline-steps').innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            Click "Add Step" to start building your pipeline. Steps will be executed in order.
        </div>
    `;
    
    modal.show();
}

function addPipelineStep() {
    const stepsContainer = document.getElementById('pipeline-steps');
    const stepIndex = stepsContainer.children.length;
    
    // Remove info message if it's the first step
    if (stepIndex === 1) {
        stepsContainer.innerHTML = '';
    }
    
    const stepHtml = `
        <div class="pipeline-step" data-step-index="${stepIndex}">
            <div class="step-header">
                <h6>Step ${stepIndex}</h6>
                <div>
                    <span class="step-type-badge" id="step-type-${stepIndex}">Select Type</span>
                    <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="removeStep(${stepIndex})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">Step Name</label>
                    <input type="text" class="form-control" name="steps[${stepIndex}][name]" required>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Step Type</label>
                    <select class="form-select" name="steps[${stepIndex}][type]" onchange="updateStepForm(${stepIndex}, this.value)" required>
                        <option value="">Select Type</option>
                        <option value="load">Load Data</option>
                        <option value="transform">Transform</option>
                        <option value="filter">Filter</option>
                        <option value="aggregate">Aggregate</option>
                        <option value="join">Join</option>
                        <option value="save">Save</option>
                    </select>
                </div>
            </div>
            
            <div class="mt-3">
                <label class="form-label">Description</label>
                <textarea class="form-control" name="steps[${stepIndex}][description]" rows="2"></textarea>
            </div>
            
            <div id="step-config-${stepIndex}" class="mt-3">
                <!-- Step-specific configuration will be added here -->
            </div>
        </div>
    `;
    
    stepsContainer.insertAdjacentHTML('beforeend', stepHtml);
}

function removeStep(stepIndex) {
    const step = document.querySelector(`[data-step-index="${stepIndex}"]`);
    if (step) {
        step.remove();
        
        // If no steps left, show info message
        const stepsContainer = document.getElementById('pipeline-steps');
        if (stepsContainer.children.length === 0) {
            stepsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    Click "Add Step" to start building your pipeline. Steps will be executed in order.
                </div>
            `;
        }
    }
}

function updateStepForm(stepIndex, stepType) {
    const badge = document.getElementById(`step-type-${stepIndex}`);
    const configContainer = document.getElementById(`step-config-${stepIndex}`);
    
    badge.textContent = stepType || 'Select Type';
    
    let configHtml = '';
    
    switch (stepType) {
        case 'load':
            configHtml = `
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label">Source Path</label>
                        <input type="text" class="form-control" name="steps[${stepIndex}][source_path]" 
                               placeholder="e.g., data/input.csv" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Format</label>
                        <select class="form-select" name="steps[${stepIndex}][format]" required>
                            <option value="">Select Format</option>
                            <option value="csv">CSV</option>
                            <option value="json">JSON</option>
                            <option value="parquet">Parquet</option>
                            <option value="xlsx">Excel</option>
                        </select>
                    </div>
                </div>
            `;
            break;
        case 'save':
            configHtml = `
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label">Output Path</label>
                        <input type="text" class="form-control" name="steps[${stepIndex}][output_path]" 
                               placeholder="e.g., output/result.csv" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Format</label>
                        <select class="form-select" name="steps[${stepIndex}][format]" required>
                            <option value="">Select Format</option>
                            <option value="csv">CSV</option>
                            <option value="json">JSON</option>
                            <option value="parquet">Parquet</option>
                            <option value="xlsx">Excel</option>
                        </select>
                    </div>
                </div>
            `;
            break;
        default:
            configHtml = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    Configuration options for ${stepType} steps will be available in a future version.
                    For now, you can create the pipeline and edit the step configuration via the API.
                </div>
            `;
    }
    
    configContainer.innerHTML = configHtml;
}

async function createPipeline() {
    const form = document.getElementById('create-pipeline-form');
    const formData = new FormData(form);
    
    // Extract pipeline data
    const pipeline = {
        name: formData.get('name'),
        description: formData.get('description'),
        status: formData.get('status'),
        steps: []
    };
    
    // Extract steps
    const stepElements = document.querySelectorAll('.pipeline-step');
    stepElements.forEach((element, index) => {
        const stepType = formData.get(`steps[${index}][type]`);
        if (stepType) {
            const step = {
                name: formData.get(`steps[${index}][name]`),
                type: stepType,
                description: formData.get(`steps[${index}][description]`)
            };
            
            // Add type-specific configuration
            if (stepType === 'load') {
                step.source_path = formData.get(`steps[${index}][source_path]`);
                step.format = formData.get(`steps[${index}][format]`);
                step.options = {};
            } else if (stepType === 'save') {
                step.output_path = formData.get(`steps[${index}][output_path]`);
                step.format = formData.get(`steps[${index}][format]`);
                step.options = {};
            }
            
            pipeline.steps.push(step);
        }
    });
    
    try {
        const response = await fetchJSON('/api/v1/pipelines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pipeline)
        });
        
        showToast('Success', 'Pipeline created successfully', 'success');
        bootstrap.Modal.getInstance(document.getElementById('createPipelineModal')).hide();
        
        // Refresh pipelines if on pipelines section
        if (currentSection === 'pipelines') {
            refreshPipelines();
        }
        
    } catch (error) {
        console.error('Error creating pipeline:', error);
        showToast('Error', 'Failed to create pipeline', 'error');
    }
}

// Utility Functions
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(error.detail || error.error || 'Request failed');
    }
    
    return response.json();
}

function formatDateTime(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch {
        return 'Invalid date';
    }
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getStatusIcon(status) {
    const icons = {
        active: 'fas fa-check-circle',
        draft: 'fas fa-edit',
        inactive: 'fas fa-pause-circle',
        running: 'fas fa-spinner fa-spin',
        completed: 'fas fa-check-circle',
        failed: 'fas fa-times-circle',
        cancelled: 'fas fa-ban',
        pending: 'fas fa-clock'
    };
    return `<i class="${icons[status] || 'fas fa-question-circle'}"></i>`;
}

function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toastId = `toast-${Date.now()}`;
    
    const bgClass = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info'
    }[type] || 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert">
            <div class="toast-header ${bgClass} text-white">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove from DOM after hiding
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function startAutoRefresh() {
    // Refresh data every 30 seconds
    refreshInterval = setInterval(() => {
        if (currentSection === 'dashboard') {
            loadDashboard();
        } else if (currentSection === 'executions') {
            refreshExecutions();
        } else if (currentSection === 'monitoring') {
            loadMonitoring();
        }
    }, 30000);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// Additional functions that might be called from other parts
function editPipeline(pipelineId) {
    showToast('Info', 'Pipeline editing will be available in a future version', 'info');
}

function downloadExecutionOutputs(executionId) {
    showToast('Info', 'Bulk download will be available in a future version', 'info');
}
