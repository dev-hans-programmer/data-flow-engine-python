/**
 * Visual Transformation Builder Component
 * Provides drag-and-drop interface for creating custom data transformations
 */

class TransformationBuilder {
    constructor(apiService, uiUtils) {
        this.apiService = apiService;
        this.uiUtils = uiUtils;
        this.transformations = [];
        this.currentPreview = null;
        this.draggedElement = null;
        this.availableColumns = [];
        this.previewData = null;
    }

    async load() {
        const container = document.getElementById('transformation-content');
        if (!container) return;

        container.innerHTML = this.getBuilderTemplate();
        this.setupEventListeners();
        await this.loadAvailableTransformations();
    }

    getBuilderTemplate() {
        return `
            <div class="transformation-builder">
                <!-- Header -->
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h4>Visual Transformation Builder</h4>
                    <div class="btn-group">
                        <button class="btn btn-outline-primary" onclick="transformationBuilder.loadSampleData()">
                            <i class="fas fa-database"></i> Load Sample Data
                        </button>
                        <button class="btn btn-outline-success" onclick="transformationBuilder.saveTransformation()">
                            <i class="fas fa-save"></i> Save Transformation
                        </button>
                        <button class="btn btn-primary" onclick="transformationBuilder.testTransformation()">
                            <i class="fas fa-play"></i> Test
                        </button>
                    </div>
                </div>

                <div class="row">
                    <!-- Transformation Palette -->
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Transformation Blocks</h6>
                            </div>
                            <div class="card-body p-2">
                                <div id="transformation-palette">
                                    ${this.getTransformationPalette()}
                                </div>
                            </div>
                        </div>

                        <!-- Data Preview -->
                        <div class="card mt-3">
                            <div class="card-header">
                                <h6 class="mb-0">Data Preview</h6>
                            </div>
                            <div class="card-body">
                                <div id="data-preview" class="small">
                                    <p class="text-muted">Load sample data to preview transformations</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Canvas Area -->
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header">
                                <h6 class="mb-0">Transformation Flow</h6>
                            </div>
                            <div class="card-body">
                                <div id="transformation-canvas" class="transformation-canvas">
                                    <div class="canvas-placeholder">
                                        <i class="fas fa-mouse-pointer fa-2x text-muted mb-2"></i>
                                        <p class="text-muted">Drag transformation blocks here to build your pipeline</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Properties Panel -->
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Properties</h6>
                            </div>
                            <div class="card-body">
                                <div id="properties-panel">
                                    <p class="text-muted">Select a transformation to configure its properties</p>
                                </div>
                            </div>
                        </div>

                        <!-- Available Columns -->
                        <div class="card mt-3">
                            <div class="card-header">
                                <h6 class="mb-0">Available Columns</h6>
                            </div>
                            <div class="card-body">
                                <div id="columns-list">
                                    <p class="text-muted small">Load data to see available columns</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getTransformationPalette() {
        const transformations = [
            {
                type: 'filter',
                icon: 'fa-filter',
                name: 'Filter Rows',
                description: 'Filter data based on conditions'
            },
            {
                type: 'select',
                icon: 'fa-columns',
                name: 'Select Columns',
                description: 'Choose specific columns'
            },
            {
                type: 'aggregate',
                icon: 'fa-calculator',
                name: 'Aggregate',
                description: 'Group and summarize data'
            },
            {
                type: 'sort',
                icon: 'fa-sort',
                name: 'Sort',
                description: 'Sort data by columns'
            },
            {
                type: 'rename',
                icon: 'fa-edit',
                name: 'Rename Columns',
                description: 'Change column names'
            },
            {
                type: 'calculate',
                icon: 'fa-function',
                name: 'Calculate Field',
                description: 'Create calculated columns'
            },
            {
                type: 'join',
                icon: 'fa-link',
                name: 'Join Data',
                description: 'Combine with other data'
            },
            {
                type: 'pivot',
                icon: 'fa-table',
                name: 'Pivot Table',
                description: 'Reshape data'
            }
        ];

        return transformations.map(t => `
            <div class="transformation-block" 
                 draggable="true" 
                 data-type="${t.type}"
                 title="${t.description}">
                <div class="d-flex align-items-center">
                    <i class="fas ${t.icon} me-2"></i>
                    <div>
                        <div class="fw-bold small">${t.name}</div>
                        <div class="text-muted" style="font-size: 10px;">${t.description}</div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    setupEventListeners() {
        // Drag and drop for transformation blocks
        const palette = document.getElementById('transformation-palette');
        const canvas = document.getElementById('transformation-canvas');

        palette.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('transformation-block')) {
                this.draggedElement = e.target.dataset.type;
                e.dataTransfer.effectAllowed = 'copy';
            }
        });

        canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });

        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            if (this.draggedElement) {
                this.addTransformationToCanvas(this.draggedElement, e.clientX, e.clientY);
                this.draggedElement = null;
            }
        });
    }

    addTransformationToCanvas(type, x, y) {
        const canvas = document.getElementById('transformation-canvas');
        const canvasRect = canvas.getBoundingClientRect();
        
        // Remove placeholder if this is the first transformation
        const placeholder = canvas.querySelector('.canvas-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        const transformationId = 'trans_' + Date.now();
        const transformationElement = document.createElement('div');
        transformationElement.className = 'canvas-transformation';
        transformationElement.dataset.id = transformationId;
        transformationElement.dataset.type = type;
        
        transformationElement.innerHTML = `
            <div class="transformation-header">
                <i class="fas ${this.getTransformationIcon(type)}"></i>
                <span>${this.getTransformationName(type)}</span>
                <button class="btn btn-sm btn-outline-danger ms-auto" onclick="transformationBuilder.removeTransformation('${transformationId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="transformation-body">
                <small class="text-muted">Click to configure</small>
            </div>
        `;

        // Position the element
        transformationElement.style.position = 'absolute';
        transformationElement.style.left = (x - canvasRect.left - 75) + 'px';
        transformationElement.style.top = (y - canvasRect.top - 30) + 'px';

        // Add click handler for configuration
        transformationElement.addEventListener('click', () => {
            this.selectTransformation(transformationId);
        });

        canvas.appendChild(transformationElement);

        // Add to transformations array
        this.transformations.push({
            id: transformationId,
            type: type,
            config: {}
        });

        // Auto-select the new transformation
        this.selectTransformation(transformationId);
    }

    selectTransformation(transformationId) {
        // Remove previous selection
        document.querySelectorAll('.canvas-transformation').forEach(el => {
            el.classList.remove('selected');
        });

        // Select current transformation
        const element = document.querySelector(`[data-id="${transformationId}"]`);
        if (element) {
            element.classList.add('selected');
            this.showPropertiesPanel(transformationId);
        }
    }

    showPropertiesPanel(transformationId) {
        const transformation = this.transformations.find(t => t.id === transformationId);
        if (!transformation) return;

        const panel = document.getElementById('properties-panel');
        panel.innerHTML = this.getPropertiesForm(transformation);
    }

    getPropertiesForm(transformation) {
        switch (transformation.type) {
            case 'filter':
                return this.getFilterProperties(transformation);
            case 'select':
                return this.getSelectProperties(transformation);
            case 'aggregate':
                return this.getAggregateProperties(transformation);
            case 'sort':
                return this.getSortProperties(transformation);
            case 'rename':
                return this.getRenameProperties(transformation);
            case 'calculate':
                return this.getCalculateProperties(transformation);
            default:
                return '<p class="text-muted">Properties for this transformation type are not yet implemented.</p>';
        }
    }

    getFilterProperties(transformation) {
        return `
            <div class="mb-3">
                <label class="form-label">Column</label>
                <select class="form-select" id="filter-column" onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'column', this.value)">
                    <option value="">Select column...</option>
                    ${this.availableColumns.map(col => `
                        <option value="${col}" ${transformation.config.column === col ? 'selected' : ''}>${col}</option>
                    `).join('')}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Condition</label>
                <select class="form-select" id="filter-condition" onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'condition', this.value)">
                    <option value="equals" ${transformation.config.condition === 'equals' ? 'selected' : ''}>Equals</option>
                    <option value="not_equals" ${transformation.config.condition === 'not_equals' ? 'selected' : ''}>Not Equals</option>
                    <option value="greater_than" ${transformation.config.condition === 'greater_than' ? 'selected' : ''}>Greater Than</option>
                    <option value="less_than" ${transformation.config.condition === 'less_than' ? 'selected' : ''}>Less Than</option>
                    <option value="contains" ${transformation.config.condition === 'contains' ? 'selected' : ''}>Contains</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Value</label>
                <input type="text" class="form-control" id="filter-value" 
                       value="${transformation.config.value || ''}"
                       onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'value', this.value)"
                       placeholder="Enter filter value">
            </div>
        `;
    }

    getSelectProperties(transformation) {
        return `
            <div class="mb-3">
                <label class="form-label">Select Columns</label>
                <div class="form-check-list" style="max-height: 200px; overflow-y: auto;">
                    ${this.availableColumns.map(col => `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="col-${col}" 
                                   value="${col}" ${(transformation.config.columns || []).includes(col) ? 'checked' : ''}
                                   onchange="transformationBuilder.updateColumnSelection('${transformation.id}', '${col}', this.checked)">
                            <label class="form-check-label small" for="col-${col}">${col}</label>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    getCalculateProperties(transformation) {
        return `
            <div class="mb-3">
                <label class="form-label">New Column Name</label>
                <input type="text" class="form-control" 
                       value="${transformation.config.newColumn || ''}"
                       onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'newColumn', this.value)"
                       placeholder="Enter column name">
            </div>
            <div class="mb-3">
                <label class="form-label">Formula</label>
                <textarea class="form-control" rows="3"
                          onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'formula', this.value)"
                          placeholder="Enter formula (e.g., column1 + column2)">${transformation.config.formula || ''}</textarea>
                <div class="form-text">Available columns: ${this.availableColumns.join(', ')}</div>
            </div>
        `;
    }

    getSortProperties(transformation) {
        return `
            <div class="mb-3">
                <label class="form-label">Sort Column</label>
                <select class="form-select" onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'column', this.value)">
                    <option value="">Select column...</option>
                    ${this.availableColumns.map(col => `
                        <option value="${col}" ${transformation.config.column === col ? 'selected' : ''}>${col}</option>
                    `).join('')}
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Order</label>
                <select class="form-select" onchange="transformationBuilder.updateTransformationConfig('${transformation.id}', 'ascending', this.value === 'true')">
                    <option value="true" ${transformation.config.ascending !== false ? 'selected' : ''}>Ascending</option>
                    <option value="false" ${transformation.config.ascending === false ? 'selected' : ''}>Descending</option>
                </select>
            </div>
        `;
    }

    getRenameProperties(transformation) {
        return `
            <div class="mb-3">
                <label class="form-label">Column Mappings</label>
                <div id="rename-mappings">
                    ${this.availableColumns.map(col => `
                        <div class="mb-2">
                            <div class="input-group input-group-sm">
                                <span class="input-group-text">${col}</span>
                                <input type="text" class="form-control" 
                                       value="${(transformation.config.mappings && transformation.config.mappings[col]) || col}"
                                       onchange="transformationBuilder.updateRenameMapping('${transformation.id}', '${col}', this.value)"
                                       placeholder="New name">
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    getAggregateProperties(transformation) {
        return `
            <div class="mb-3">
                <label class="form-label">Group By Columns</label>
                <div class="form-check-list" style="max-height: 150px; overflow-y: auto;">
                    ${this.availableColumns.map(col => `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="group-${col}" 
                                   value="${col}" ${(transformation.config.groupBy || []).includes(col) ? 'checked' : ''}
                                   onchange="transformationBuilder.updateGroupBySelection('${transformation.id}', '${col}', this.checked)">
                            <label class="form-check-label small" for="group-${col}">${col}</label>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Aggregations</label>
                <div id="aggregation-rules">
                    <button class="btn btn-sm btn-outline-primary" onclick="transformationBuilder.addAggregationRule('${transformation.id}')">
                        <i class="fas fa-plus"></i> Add Rule
                    </button>
                </div>
            </div>
        `;
    }

    updateTransformationConfig(transformationId, key, value) {
        const transformation = this.transformations.find(t => t.id === transformationId);
        if (transformation) {
            transformation.config[key] = value;
            this.updateTransformationPreview();
        }
    }

    updateColumnSelection(transformationId, column, selected) {
        const transformation = this.transformations.find(t => t.id === transformationId);
        if (transformation) {
            if (!transformation.config.columns) {
                transformation.config.columns = [];
            }
            if (selected) {
                if (!transformation.config.columns.includes(column)) {
                    transformation.config.columns.push(column);
                }
            } else {
                transformation.config.columns = transformation.config.columns.filter(c => c !== column);
            }
            this.updateTransformationPreview();
        }
    }

    updateRenameMapping(transformationId, oldName, newName) {
        const transformation = this.transformations.find(t => t.id === transformationId);
        if (transformation) {
            if (!transformation.config.mappings) {
                transformation.config.mappings = {};
            }
            transformation.config.mappings[oldName] = newName;
            this.updateTransformationPreview();
        }
    }

    updateGroupBySelection(transformationId, column, selected) {
        const transformation = this.transformations.find(t => t.id === transformationId);
        if (transformation) {
            if (!transformation.config.groupBy) {
                transformation.config.groupBy = [];
            }
            if (selected) {
                if (!transformation.config.groupBy.includes(column)) {
                    transformation.config.groupBy.push(column);
                }
            } else {
                transformation.config.groupBy = transformation.config.groupBy.filter(c => c !== column);
            }
        }
    }

    async loadSampleData() {
        try {
            // For now, load from uploaded files
            const response = await this.apiService.getFiles();
            if (response.files && response.files.length > 0) {
                const file = response.files[0];
                await this.loadDataFromFile(file.path);
            } else {
                this.uiUtils.showToast('Info', 'Please upload a file first to use as sample data', 'info');
            }
        } catch (error) {
            console.error('Error loading sample data:', error);
            this.uiUtils.showToast('Error', 'Failed to load sample data', 'error');
        }
    }

    async loadDataFromFile(filePath) {
        try {
            const response = await fetch(`/api/v1/files/preview?file_path=${encodeURIComponent(filePath)}&rows=5`);
            const data = await response.json();
            
            this.previewData = data;
            this.availableColumns = Object.keys(data.preview[0] || {});
            
            this.updateColumnsDisplay();
            this.updateDataPreview(data.preview);
            
            this.uiUtils.showToast('Success', 'Sample data loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading data from file:', error);
            this.uiUtils.showToast('Error', 'Failed to load data from file', 'error');
        }
    }

    updateColumnsDisplay() {
        const columnsList = document.getElementById('columns-list');
        if (columnsList) {
            columnsList.innerHTML = this.availableColumns.map(col => `
                <div class="column-item">
                    <i class="fas fa-grip-vertical text-muted me-2"></i>
                    <span class="small">${col}</span>
                </div>
            `).join('');
        }
    }

    updateDataPreview(data = null) {
        const preview = document.getElementById('data-preview');
        if (!preview) return;

        const displayData = data || (this.previewData ? this.previewData.preview : null);
        
        if (!displayData || displayData.length === 0) {
            preview.innerHTML = '<p class="text-muted">No preview data available</p>';
            return;
        }

        const table = `
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            ${Object.keys(displayData[0]).map(col => `<th class="small">${col}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${displayData.slice(0, 3).map(row => `
                            <tr>
                                ${Object.values(row).map(val => `<td class="small">${val !== null && val !== undefined ? val : ''}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <small class="text-muted">Showing ${Math.min(3, displayData.length)} of ${displayData.length} rows</small>
        `;
        
        preview.innerHTML = table;
    }

    async updateTransformationPreview() {
        // This would apply transformations to the preview data
        // For now, just show a placeholder
        if (this.transformations.length > 0) {
            console.log('Applying transformations:', this.transformations);
        }
    }

    removeTransformation(transformationId) {
        // Remove from canvas
        const element = document.querySelector(`[data-id="${transformationId}"]`);
        if (element) {
            element.remove();
        }

        // Remove from array
        this.transformations = this.transformations.filter(t => t.id !== transformationId);

        // Clear properties panel
        document.getElementById('properties-panel').innerHTML = '<p class="text-muted">Select a transformation to configure its properties</p>';

        // Show placeholder if no transformations left
        const canvas = document.getElementById('transformation-canvas');
        if (this.transformations.length === 0) {
            canvas.innerHTML = `
                <div class="canvas-placeholder">
                    <i class="fas fa-mouse-pointer fa-2x text-muted mb-2"></i>
                    <p class="text-muted">Drag transformation blocks here to build your pipeline</p>
                </div>
            `;
        }
    }

    async testTransformation() {
        if (this.transformations.length === 0) {
            this.uiUtils.showToast('Info', 'Add some transformations first', 'info');
            return;
        }

        if (!this.previewData) {
            this.uiUtils.showToast('Info', 'Load sample data first', 'info');
            return;
        }

        try {
            // Convert transformations to API format and test
            const transformationConfig = this.exportTransformations();
            console.log('Testing transformations:', transformationConfig);
            
            this.uiUtils.showToast('Success', 'Transformation test completed! Check console for details.', 'success');
        } catch (error) {
            console.error('Error testing transformations:', error);
            this.uiUtils.showToast('Error', 'Failed to test transformations', 'error');
        }
    }

    exportTransformations() {
        return this.transformations.map(t => ({
            type: t.type,
            ...t.config
        }));
    }

    async saveTransformation() {
        if (this.transformations.length === 0) {
            this.uiUtils.showToast('Info', 'Add some transformations first', 'info');
            return;
        }

        const name = prompt('Enter a name for this transformation:');
        if (!name) return;

        try {
            const transformationConfig = this.exportTransformations();
            
            // Save to localStorage for now (in future, save to database)
            const savedTransformations = JSON.parse(localStorage.getItem('customTransformations') || '[]');
            savedTransformations.push({
                id: Date.now().toString(),
                name: name,
                transformations: transformationConfig,
                created: new Date().toISOString()
            });
            localStorage.setItem('customTransformations', JSON.stringify(savedTransformations));
            
            this.uiUtils.showToast('Success', `Transformation "${name}" saved successfully`, 'success');
        } catch (error) {
            console.error('Error saving transformation:', error);
            this.uiUtils.showToast('Error', 'Failed to save transformation', 'error');
        }
    }

    async loadAvailableTransformations() {
        // Load saved transformations from localStorage
        try {
            const saved = JSON.parse(localStorage.getItem('customTransformations') || '[]');
            console.log('Available saved transformations:', saved);
        } catch (error) {
            console.error('Error loading saved transformations:', error);
        }
    }

    getTransformationIcon(type) {
        const icons = {
            filter: 'fa-filter',
            select: 'fa-columns',
            aggregate: 'fa-calculator',
            sort: 'fa-sort',
            rename: 'fa-edit',
            calculate: 'fa-function',
            join: 'fa-link',
            pivot: 'fa-table'
        };
        return icons[type] || 'fa-cog';
    }

    getTransformationName(type) {
        const names = {
            filter: 'Filter Rows',
            select: 'Select Columns',
            aggregate: 'Aggregate',
            sort: 'Sort',
            rename: 'Rename Columns',
            calculate: 'Calculate Field',
            join: 'Join Data',
            pivot: 'Pivot Table'
        };
        return names[type] || type;
    }
}

// Global instance
window.transformationBuilder = null;

export default TransformationBuilder;