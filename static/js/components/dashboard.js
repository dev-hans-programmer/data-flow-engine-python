/**
 * Dashboard Component - Handles dashboard view and statistics
 */

class DashboardComponent {
    constructor(apiService, uiUtils) {
        this.apiService = apiService;
        this.uiUtils = uiUtils;
    }

    async load() {
        try {
            const [stats, executions, health] = await Promise.all([
                this.apiService.getStatistics(),
                this.apiService.getExecutions({ limit: 10 }),
                this.apiService.getHealth()
            ]);

            this.updateStats(stats);
            this.displayRecentExecutions(executions.executions || []);
            this.updateSystemStatus(health);
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.uiUtils.showToast('Error', 'Failed to load dashboard data', 'error');
        }
    }

    updateStats(stats) {
        const elements = {
            'total-pipelines': stats.total_pipelines || 0,
            'active-pipelines': stats.active_pipelines || 0,
            'total-executions': stats.total_executions || 0,
            'recent-executions': stats.recent_executions_24h || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    displayRecentExecutions(executions) {
        const container = document.getElementById('recent-executions-list');
        if (!container) return;

        if (!executions || executions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-clock fa-2x mb-2"></i>
                    <p>No recent executions</p>
                </div>
            `;
            return;
        }

        const html = executions.map(execution => `
            <div class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${execution.pipeline_name}</h6>
                    <small class="text-muted">${this.uiUtils.formatDateTime(execution.created_at)}</small>
                </div>
                <p class="mb-1">
                    <span class="status-badge status-${execution.status}">
                        ${this.uiUtils.getStatusIcon(execution.status)} ${execution.status}
                    </span>
                </p>
                <small class="text-muted">
                    ${execution.duration ? `Duration: ${this.uiUtils.formatDuration(execution.duration)}` : 'In progress...'}
                </small>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    updateSystemStatus(health) {
        const statusElement = document.getElementById('system-status');
        if (!statusElement) return;

        const isHealthy = health.status === 'healthy';
        statusElement.innerHTML = `
            <span class="badge ${isHealthy ? 'bg-success' : 'bg-danger'}">
                <i class="fas ${isHealthy ? 'fa-check-circle' : 'fa-exclamation-triangle'}"></i>
                ${health.status}
            </span>
        `;
    }
}

export default DashboardComponent;