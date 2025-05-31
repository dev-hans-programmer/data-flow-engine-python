/**
 * Layout Templates - Dynamic HTML template injection
 */

class LayoutTemplates {
    static getMainLayout() {
        return `
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <div class="container-fluid">
                    <a class="navbar-brand" href="#">
                        <i class="fas fa-project-diagram"></i>
                        Pipeline System
                    </a>
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    <div class="collapse navbar-collapse" id="navbarNav">
                        <ul class="navbar-nav me-auto">
                            <li class="nav-item">
                                <a class="nav-link active" data-section="dashboard" href="#">
                                    <i class="fas fa-chart-bar"></i> Dashboard
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" data-section="pipelines" href="#">
                                    <i class="fas fa-project-diagram"></i> Pipelines
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" data-section="executions" href="#">
                                    <i class="fas fa-play-circle"></i> Executions
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" data-section="files" href="#">
                                    <i class="fas fa-folder"></i> Files
                                </a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" data-section="monitoring" href="#">
                                    <i class="fas fa-chart-line"></i> Monitoring
                                </a>
                            </li>
                        </ul>
                        <div class="navbar-nav">
                            <span class="navbar-text me-3">
                                Status: <span id="system-status">Loading...</span>
                            </span>
                        </div>
                    </div>
                </div>
            </nav>

            <div class="container-fluid mt-4">
                <div id="dashboard-section" class="section-content">
                    <div id="dashboard-content"></div>
                </div>
                
                <div id="pipelines-section" class="section-content" style="display: none;">
                    <div id="pipelines-content"></div>
                </div>
                
                <div id="executions-section" class="section-content" style="display: none;">
                    <div id="executions-content"></div>
                </div>
                
                <div id="files-section" class="section-content" style="display: none;">
                    <div id="files-content"></div>
                </div>
                
                <div id="monitoring-section" class="section-content" style="display: none;">
                    <div id="monitoring-content"></div>
                </div>
            </div>
        `;
    }

    static getDashboardTemplate() {
        return `
            <div class="row mb-4">
                <div class="col-12">
                    <h2><i class="fas fa-chart-bar text-primary"></i> Dashboard</h2>
                    <p class="text-muted">System overview and recent activity</p>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h3 id="total-pipelines">0</h3>
                                    <p class="mb-0">Total Pipelines</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-project-diagram fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h3 id="active-pipelines">0</h3>
                                    <p class="mb-0">Active Pipelines</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-play-circle fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card bg-info text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h3 id="total-executions">0</h3>
                                    <p class="mb-0">Total Executions</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-tasks fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h3 id="recent-executions">0</h3>
                                    <p class="mb-0">Recent (24h)</p>
                                </div>
                                <div class="align-self-center">
                                    <i class="fas fa-clock fa-2x"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-history"></i> Recent Executions</h5>
                        </div>
                        <div class="card-body">
                            <div id="recent-executions-list"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    static getModalsTemplate() {
        return `
            <!-- Pipeline Details Modal -->
            <div class="modal fade" id="pipelineDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Pipeline Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="pipeline-details-content"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" id="execute-pipeline-btn">
                                <i class="fas fa-play"></i> Execute Pipeline
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Execution Details Modal -->
            <div class="modal fade" id="executionDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Execution Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="execution-details-content"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- File Upload Modal -->
            <div class="modal fade" id="fileUploadModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Upload Files</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label for="file-upload-input" class="form-label">Select Files</label>
                                <input type="file" class="form-control" id="file-upload-input" multiple 
                                       accept=".csv,.json,.xlsx,.parquet">
                                <div class="form-text">Supported formats: CSV, JSON, Excel, Parquet</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="upload-files-btn" disabled>
                                <i class="fas fa-upload"></i> Upload
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- File Preview Modal -->
            <div class="modal fade" id="filePreviewModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">File Preview</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="file-preview-content"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Results Modal -->
            <div class="modal fade" id="resultsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Execution Results</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Results content will be populated dynamically -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Toast Container -->
            <div class="toast-container position-fixed top-0 end-0 p-3" id="toast-container"></div>
        `;
    }
}

export default LayoutTemplates;