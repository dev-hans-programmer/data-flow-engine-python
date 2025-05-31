/**
 * API Service - Handles all API communications
 */

export default class ApiService {
    constructor() {
        this.baseUrl = '/api/v1';
        this.notificationService = null;
    }

    setNotificationService(notificationService) {
        this.notificationService = notificationService;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error(`API request failed: ${url}`, error);
            
            // Notify user of API errors
            if (this.notificationService) {
                this.notificationService.error(
                    'API Error',
                    `Failed to ${config.method || 'GET'} ${endpoint}: ${error.message}`,
                    { endpoint, error: error.message }
                );
            }
            
            throw error;
        }
    }

    // Pipeline endpoints
    async getPipelines(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/pipelines${query ? `?${query}` : ''}`);
    }

    async getPipeline(id) {
        return this.request(`/pipelines/${id}`);
    }

    async createPipeline(pipeline) {
        const result = await this.request('/pipelines', {
            method: 'POST',
            body: pipeline
        });
        
        // Notify success
        if (this.notificationService) {
            this.notificationService.success(
                'Pipeline Created',
                `Pipeline "${pipeline.name}" has been created successfully`,
                { pipelineId: result.id, pipelineName: pipeline.name }
            );
        }
        
        return result;
    }

    async updatePipeline(id, pipeline) {
        return this.request(`/pipelines/${id}`, {
            method: 'PUT',
            body: pipeline
        });
    }

    async deletePipeline(id) {
        return this.request(`/pipelines/${id}`, {
            method: 'DELETE'
        });
    }

    async executePipeline(id, parameters = {}) {
        const result = await this.request(`/pipelines/${id}/execute`, {
            method: 'POST',
            body: parameters
        });
        
        // Notify execution started
        if (this.notificationService) {
            this.notificationService.info(
                'Pipeline Execution Started',
                `Pipeline execution has been initiated`,
                { pipelineId: id, executionId: result.id }
            );
        }
        
        return result;
    }

    // Execution endpoints
    async getExecutions(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/executions${query ? `?${query}` : ''}`);
    }

    async getExecution(id) {
        return this.request(`/executions/${id}`);
    }

    async cancelExecution(id) {
        return this.request(`/executions/${id}/cancel`, {
            method: 'POST'
        });
    }

    // File endpoints
    async getFiles() {
        return this.request('/files');
    }

    async uploadFile(formData) {
        const result = await this.request('/files/upload', {
            method: 'POST',
            body: formData,
            headers: {} // Remove Content-Type to let browser set boundary
        });
        
        // Notify success
        if (this.notificationService) {
            const fileName = formData.get('file')?.name || 'Unknown file';
            this.notificationService.success(
                'File Uploaded',
                `File "${fileName}" has been uploaded successfully`,
                { fileName, filePath: result.path }
            );
        }
        
        return result;
    }

    async deleteFile(filePath) {
        return this.request('/files', {
            method: 'DELETE',
            body: { file_path: filePath }
        });
    }

    async previewFile(filePath) {
        return this.request('/files/preview', {
            method: 'POST',
            body: { file_path: filePath }
        });
    }

    async getOutputFiles() {
        return this.request('/files/outputs');
    }

    // System endpoints
    async getStatistics() {
        return this.request('/statistics');
    }

    async getHealth() {
        return this.request('/health');
    }

    async getSchedulerStatus() {
        return this.request('/scheduler/status');
    }

    // Execution monitoring for notifications
    async monitorExecution(executionId, previousStatus = null) {
        try {
            const execution = await this.getExecution(executionId);
            
            // Check if status changed and notify accordingly
            if (this.notificationService && execution.status !== previousStatus) {
                switch (execution.status) {
                    case 'completed':
                        this.notificationService.success(
                            'Pipeline Completed',
                            `Pipeline "${execution.pipeline_name}" completed successfully`,
                            { executionId, pipelineId: execution.pipeline_id }
                        );
                        break;
                    case 'failed':
                        this.notificationService.error(
                            'Pipeline Failed',
                            `Pipeline "${execution.pipeline_name}" failed: ${execution.error_message || 'Unknown error'}`,
                            { executionId, pipelineId: execution.pipeline_id, error: execution.error_message }
                        );
                        break;
                    case 'running':
                        if (previousStatus === 'pending') {
                            this.notificationService.info(
                                'Pipeline Running',
                                `Pipeline "${execution.pipeline_name}" is now running`,
                                { executionId, pipelineId: execution.pipeline_id }
                            );
                        }
                        break;
                }
            }
            
            return execution;
        } catch (error) {
            console.error('Failed to monitor execution:', error);
            return null;
        }
    }
}