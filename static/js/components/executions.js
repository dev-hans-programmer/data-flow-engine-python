/**
 * Executions Component - Handles execution monitoring and management
 */

class ExecutionsComponent {
    constructor(apiService, uiUtils) {
        this.apiService = apiService;
        this.uiUtils = uiUtils;
        this.refreshInterval = null;
    }

    async load() {
        this.uiUtils.showLoader('executions-content');
        
        try {
            const response = await this.apiService.getExecutions({ limit: 50 });
            this.displayExecutions(response.executions || []);
            this.startAutoRefresh();
        } catch (error) {
            console.error('Error loading executions:', error);
            this.uiUtils.showError('executions-content', 'Failed to load executions', true, () => this.load());
        }
    }

    displayExecutions(executions) {
        const container = document.getElementById('executions-content');
        if (!container) return;

        if (!executions || executions.length === 0) {
            this.uiUtils.showEmpty('executions-content', 'No executions found. Run a pipeline to see execution history.', 'fa-play-circle');
            return;
        }

        const html = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Pipeline</th>
                            <th>Status</th>
                            <th>Started</th>
                            <th>Duration</th>
                            <th>Triggered By</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${executions.map(execution => this.renderExecutionRow(execution)).join('')}
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    renderExecutionRow(execution) {
        const statusClass = this.getStatusClass(execution.status);
        const duration = execution.duration ? this.uiUtils.formatDuration(execution.duration) : 
                        (execution.status === 'running' ? 'In progress...' : 'N/A');

        return `
            <tr class="${statusClass}">
                <td>
                    <strong>${execution.pipeline_name}</strong>
                    <br>
                    <small class="text-muted">${execution.id}</small>
                </td>
                <td>
                    <span class="status-badge status-${execution.status}">
                        ${this.uiUtils.getStatusIcon(execution.status)} ${execution.status}
                    </span>
                </td>
                <td>
                    ${execution.start_time ? this.uiUtils.formatDateTime(execution.start_time) : 'Not started'}
                </td>
                <td>${duration}</td>
                <td>${execution.triggered_by || 'Manual'}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" onclick="executionManager.viewDetails('${execution.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${execution.status === 'running' ? `
                            <button class="btn btn-outline-warning" onclick="executionManager.cancel('${execution.id}')">
                                <i class="fas fa-stop"></i>
                            </button>
                        ` : ''}
                        ${execution.output_files && execution.output_files.length > 0 ? `
                            <button class="btn btn-outline-info" onclick="executionManager.viewResults('${execution.id}')" title="View Results">
                                <i class="fas fa-chart-bar"></i>
                            </button>
                            <button class="btn btn-outline-success" onclick="executionManager.downloadOutputs('${execution.id}')" title="Download">
                                <i class="fas fa-download"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }

    getStatusClass(status) {
        const classes = {
            completed: 'table-success',
            failed: 'table-danger',
            running: 'table-warning',
            cancelled: 'table-secondary'
        };
        return classes[status] || '';
    }

    async viewDetails(executionId) {
        try {
            const execution = await this.apiService.getExecution(executionId);
            
            const content = document.getElementById('execution-details-content');
            if (!content) return;

            content.innerHTML = `
                <div class="row mb-4">
                    <div class="col-md-8">
                        <h4>${execution.pipeline_name}</h4>
                        <p class="text-muted">Execution ID: ${execution.id}</p>
                    </div>
                    <div class="col-md-4 text-end">
                        <span class="status-badge status-${execution.status} fs-6">
                            ${this.uiUtils.getStatusIcon(execution.status)} ${execution.status}
                        </span>
                    </div>
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-3">
                        <h6>Started</h6>
                        <p class="text-muted">${execution.start_time ? this.uiUtils.formatDateTime(execution.start_time) : 'Not started'}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>Completed</h6>
                        <p class="text-muted">${execution.end_time ? this.uiUtils.formatDateTime(execution.end_time) : 'Not completed'}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>Duration</h6>
                        <p class="text-muted">${execution.duration ? this.uiUtils.formatDuration(execution.duration) : 'N/A'}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>Triggered By</h6>
                        <p class="text-muted">${execution.triggered_by || 'Manual'}</p>
                    </div>
                </div>

                ${execution.error_message ? `
                    <div class="alert alert-danger mb-4">
                        <h6><i class="fas fa-exclamation-triangle"></i> Error</h6>
                        <pre class="mb-0">${execution.error_message}</pre>
                    </div>
                ` : ''}

                ${execution.steps && execution.steps.length > 0 ? `
                    <div class="mb-4">
                        <h5>Step Execution Details</h5>
                        ${this.renderExecutionSteps(execution.steps)}
                    </div>
                ` : ''}

                ${execution.output_files && execution.output_files.length > 0 ? `
                    <div class="mb-4">
                        <h5>Output Files</h5>
                        <ul class="list-group">
                            ${execution.output_files.map(file => `
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    <span><i class="fas fa-file"></i> ${file}</span>
                                    <button class="btn btn-sm btn-outline-primary" onclick="executionManager.downloadFile('${file}')">
                                        <i class="fas fa-download"></i> Download
                                    </button>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${execution.logs && execution.logs.length > 0 ? `
                    <div class="mb-4">
                        <h5>Execution Logs</h5>
                        <div class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">
                            ${execution.logs.map(log => `<div>${log}</div>`).join('')}
                        </div>
                    </div>
                ` : ''}
            `;

            this.uiUtils.showModal('executionDetailsModal');
        } catch (error) {
            console.error('Error loading execution details:', error);
            this.uiUtils.showToast('Error', 'Failed to load execution details', 'error');
        }
    }

    renderExecutionSteps(steps) {
        return steps.map((step, index) => `
            <div class="card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span>
                            <span class="badge bg-primary me-2">${index + 1}</span>
                            ${step.name || `Step ${index + 1}`}
                        </span>
                        <span class="status-badge status-${step.status}">
                            ${this.uiUtils.getStatusIcon(step.status)} ${step.status}
                        </span>
                    </div>
                    ${step.error ? `
                        <div class="mt-2">
                            <small class="text-danger">${step.error}</small>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    async cancel(executionId) {
        if (!confirm('Are you sure you want to cancel this execution?')) return;

        try {
            await this.apiService.cancelExecution(executionId);
            this.uiUtils.showToast('Success', 'Execution cancelled successfully', 'success');
            this.load(); // Refresh the list
        } catch (error) {
            console.error('Error cancelling execution:', error);
            this.uiUtils.showToast('Error', 'Failed to cancel execution', 'error');
        }
    }

    async viewResults(executionId) {
        try {
            const execution = await this.apiService.getExecution(executionId);
            
            if (!execution.output_files || execution.output_files.length === 0) {
                this.uiUtils.showToast('Info', 'No output files available for this execution', 'info');
                return;
            }

            // Show results in a modal
            this.showResultsModal(execution);
            
        } catch (error) {
            console.error('Error loading execution results:', error);
            this.uiUtils.showToast('Error', 'Failed to load execution results', 'error');
        }
    }

    async showResultsModal(execution) {
        const modal = new bootstrap.Modal(document.getElementById('resultsModal'));
        const modalTitle = document.querySelector('#resultsModal .modal-title');
        const modalBody = document.querySelector('#resultsModal .modal-body');
        
        modalTitle.textContent = `Results: ${execution.pipeline_name}`;
        modalBody.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';
        
        modal.show();

        try {
            // Load and display the first output file
            const outputFile = execution.output_files[0];
            const response = await fetch(`/api/v1/files/preview?file_path=${encodeURIComponent(outputFile)}`);
            
            if (!response.ok) {
                throw new Error('Failed to load file preview');
            }
            
            const previewData = await response.json();
            
            modalBody.innerHTML = `
                <div class="mb-3">
                    <h6>Output File: ${outputFile}</h6>
                    <p class="text-muted">Execution completed: ${new Date(execution.end_time).toLocaleString()}</p>
                </div>
                
                <div class="mb-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><strong>Rows:</strong> ${previewData.rows || 'N/A'}</span>
                        <span><strong>Columns:</strong> ${previewData.columns || 'N/A'}</span>
                        <button class="btn btn-sm btn-outline-primary" onclick="window.open('/api/v1/files/download?file_path=${encodeURIComponent(outputFile)}', '_blank')">
                            <i class="fas fa-download"></i> Download
                        </button>
                    </div>
                </div>
                
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                ${previewData.preview && previewData.preview.length > 0 ? 
                                    Object.keys(previewData.preview[0]).map(col => `<th>${col}</th>`).join('') : 
                                    '<th>No data</th>'
                                }
                            </tr>
                        </thead>
                        <tbody>
                            ${previewData.preview ? previewData.preview.slice(0, 10).map(row => `
                                <tr>
                                    ${Object.values(row).map(val => `<td>${val !== null && val !== undefined ? val : ''}</td>`).join('')}
                                </tr>
                            `).join('') : '<tr><td colspan="100%">No preview available</td></tr>'}
                        </tbody>
                    </table>
                </div>
                
                ${previewData.preview && previewData.preview.length > 10 ? 
                    '<p class="text-muted small">Showing first 10 rows. Download the full file to see all data.</p>' : ''
                }
            `;
            
        } catch (error) {
            modalBody.innerHTML = `
                <div class="alert alert-warning">
                    <h6>Preview not available</h6>
                    <p>Unable to preview the results file. You can still download it using the button below.</p>
                    <button class="btn btn-primary" onclick="window.open('/api/v1/files/download?file_path=${encodeURIComponent(execution.output_files[0])}', '_blank')">
                        <i class="fas fa-download"></i> Download Results
                    </button>
                </div>
            `;
        }
    }

    downloadOutputs(executionId) {
        this.uiUtils.showToast('Info', 'Bulk download will be available in a future version', 'info');
    }

    downloadFile(filePath) {
        window.open(`/api/v1/files/download?file_path=${encodeURIComponent(filePath)}`, '_blank');
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            this.refresh();
        }, 10000); // Refresh every 10 seconds
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async refresh() {
        try {
            const response = await this.apiService.getExecutions({ limit: 50 });
            this.displayExecutions(response.executions || []);
        } catch (error) {
            console.error('Error refreshing executions:', error);
        }
    }

    destroy() {
        this.stopAutoRefresh();
    }
}

export default ExecutionsComponent;