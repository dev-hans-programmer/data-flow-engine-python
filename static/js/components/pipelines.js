/**
 * Pipelines Component - Handles pipeline management
 */

class PipelinesComponent {
    constructor(apiService, uiUtils) {
        this.apiService = apiService;
        this.uiUtils = uiUtils;
        this.currentPipelineId = null;
    }

    async load() {
        this.uiUtils.showLoader('pipelines-content');
        
        try {
            const response = await this.apiService.getPipelines({ limit: 100 });
            this.displayPipelines(response.pipelines || []);
        } catch (error) {
            console.error('Error loading pipelines:', error);
            this.uiUtils.showError('pipelines-content', 'Failed to load pipelines', true, () => this.load());
        }
    }

    displayPipelines(pipelines) {
        const container = document.getElementById('pipelines-content');
        if (!container) return;

        if (!pipelines || pipelines.length === 0) {
            this.uiUtils.showEmpty('pipelines-content', 'No pipelines found. Create your first pipeline to get started.', 'fa-project-diagram');
            return;
        }

        const html = `
            <div class="row">
                ${pipelines.map(pipeline => this.renderPipelineCard(pipeline)).join('')}
            </div>
        `;

        container.innerHTML = html;
    }

    renderPipelineCard(pipeline) {
        return `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">${pipeline.name}</h6>
                        <span class="status-badge status-${pipeline.status}">
                            ${this.uiUtils.getStatusIcon(pipeline.status)} ${pipeline.status}
                        </span>
                    </div>
                    <div class="card-body">
                        <p class="card-text text-muted small mb-3">
                            ${pipeline.description || 'No description provided'}
                        </p>
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-tasks"></i> ${pipeline.steps?.length || 0} steps
                            </small>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-clock"></i> Updated ${this.uiUtils.formatDateTime(pipeline.updated_at)}
                            </small>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent">
                        <div class="btn-group w-100" role="group">
                            <button class="btn btn-outline-primary btn-sm" onclick="pipelineManager.viewDetails('${pipeline.id}')">
                                <i class="fas fa-eye"></i> Details
                            </button>
                            <button class="btn btn-outline-success btn-sm" onclick="pipelineManager.execute('${pipeline.id}')">
                                <i class="fas fa-play"></i> Run
                            </button>
                            <button class="btn btn-outline-secondary btn-sm" onclick="pipelineManager.edit('${pipeline.id}')">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async viewDetails(pipelineId) {
        try {
            const pipeline = await this.apiService.getPipeline(pipelineId);
            this.currentPipelineId = pipelineId;
            
            const content = document.getElementById('pipeline-details-content');
            if (!content) return;

            content.innerHTML = `
                <div class="row mb-4">
                    <div class="col-md-8">
                        <h4>${pipeline.name}</h4>
                        <p class="text-muted">${pipeline.description || 'No description provided'}</p>
                    </div>
                    <div class="col-md-4 text-end">
                        <span class="status-badge status-${pipeline.status} fs-6">
                            ${this.uiUtils.getStatusIcon(pipeline.status)} ${pipeline.status}
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
                        <p class="text-muted">${this.uiUtils.formatDateTime(pipeline.created_at)}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>Updated</h6>
                        <p class="text-muted">${this.uiUtils.formatDateTime(pipeline.updated_at)}</p>
                    </div>
                    <div class="col-md-3">
                        <h6>Steps</h6>
                        <p class="text-muted">${pipeline.steps?.length || 0} steps</p>
                    </div>
                </div>

                <div class="mb-4">
                    <h5>Pipeline Steps</h5>
                    <div class="pipeline-steps">
                        ${this.renderPipelineSteps(pipeline.steps || [])}
                    </div>
                </div>

                ${pipeline.schedule ? `
                    <div class="mb-4">
                        <h5>Schedule Configuration</h5>
                        <div class="bg-light p-3 rounded">
                            <pre class="mb-0">${JSON.stringify(pipeline.schedule, null, 2)}</pre>
                        </div>
                    </div>
                ` : ''}
            `;

            this.uiUtils.showModal('pipelineDetailsModal');
        } catch (error) {
            console.error('Error loading pipeline details:', error);
            this.uiUtils.showToast('Error', 'Failed to load pipeline details', 'error');
        }
    }

    renderPipelineSteps(steps) {
        if (!steps || steps.length === 0) {
            return '<p class="text-muted">No steps configured</p>';
        }

        return steps.map((step, index) => `
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span class="badge bg-primary me-2">${index + 1}</span>
                    <h6 class="mb-0 flex-grow-1">${step.name || `Step ${index + 1}`}</h6>
                    <span class="badge bg-secondary">${step.type}</span>
                </div>
                <div class="card-body">
                    ${step.description ? `<p class="text-muted mb-2">${step.description}</p>` : ''}
                    <div class="row">
                        <div class="col-12">
                            <strong>Configuration:</strong>
                            <pre class="bg-light p-2 rounded mt-1"><code>${JSON.stringify(step.config || {}, null, 2)}</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async execute(pipelineId) {
        try {
            this.uiUtils.showToast('Info', 'Starting pipeline execution...', 'info');
            const execution = await this.apiService.executePipeline(pipelineId);
            this.uiUtils.showToast('Success', `Pipeline execution started. Execution ID: ${execution.id}`, 'success');
            
            // Optionally switch to executions view to show progress
            if (window.app && window.app.showSection) {
                window.app.showSection('executions');
            }
        } catch (error) {
            console.error('Error executing pipeline:', error);
            this.uiUtils.showToast('Error', `Failed to execute pipeline: ${error.message}`, 'error');
        }
    }

    edit(pipelineId) {
        this.uiUtils.showToast('Info', 'Pipeline editing will be available in a future version', 'info');
    }

    async executePipelineFromModal() {
        if (!this.currentPipelineId) return;
        
        this.uiUtils.hideModal('pipelineDetailsModal');
        await this.execute(this.currentPipelineId);
    }
}

export default PipelinesComponent;