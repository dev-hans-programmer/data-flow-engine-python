/**
 * Main Application Controller - Orchestrates all components
 */

// Import components and templates
import ApiService from './services/api.js';
import UIUtils from './utils/ui.js';
import DashboardComponent from './components/dashboard.js';
import PipelinesComponent from './components/pipelines.js';
import ExecutionsComponent from './components/executions.js';
import FilesComponent from './components/files.js';
import TransformationBuilder from './components/transformation-builder.js';
import LayoutTemplates from './templates/layout.js';

class PipelineSystemApp {
    constructor() {
        this.currentSection = 'dashboard';
        this.refreshInterval = null;
        
        // Initialize services
        this.apiService = new ApiService();
        this.uiUtils = new UIUtils();
        
        // Initialize components
        this.dashboard = new DashboardComponent(this.apiService, this.uiUtils);
        this.pipelines = new PipelinesComponent(this.apiService, this.uiUtils);
        this.executions = new ExecutionsComponent(this.apiService, this.uiUtils);
        this.files = new FilesComponent(this.apiService, this.uiUtils);
        this.transformationBuilder = new TransformationBuilder(this.apiService, this.uiUtils);
        
        // Global component managers for backward compatibility
        window.pipelineManager = this.pipelines;
        window.executionManager = this.executions;
        window.fileManager = this.files;
        window.transformationBuilder = this.transformationBuilder;
        
        this.init();
    }

    init() {
        this.injectLayout();
        this.setupEventListeners();
        this.setupNavigation();
        this.loadInitialContent();
        this.startAutoRefresh();
    }

    injectLayout() {
        // Inject main layout and modals
        const appContainer = document.getElementById('app');
        if (appContainer) {
            appContainer.innerHTML = LayoutTemplates.getMainLayout();
            document.body.insertAdjacentHTML('beforeend', LayoutTemplates.getModalsTemplate());
        }
    }

    setupEventListeners() {
        // Navigation
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-section]')) {
                e.preventDefault();
                const section = e.target.getAttribute('data-section');
                this.showSection(section);
            }
        });

        // Modal events
        document.addEventListener('click', (e) => {
            // Pipeline execution from modal
            if (e.target.matches('#execute-pipeline-btn')) {
                this.pipelines.executePipelineFromModal();
            }
            
            // File upload
            if (e.target.matches('#upload-files-btn')) {
                const fileInput = document.getElementById('file-upload-input');
                this.files.uploadFiles(fileInput);
            }
        });

        // File input change
        const fileInput = document.getElementById('file-upload-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const uploadBtn = document.getElementById('upload-files-btn');
                if (uploadBtn) {
                    uploadBtn.disabled = e.target.files.length === 0;
                }
            });
        }

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link[data-section]');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.showSection(section);
            });
        });
    }

    async loadInitialContent() {
        // Load dashboard by default
        await this.showSection('dashboard');
    }

    async showSection(section) {
        // Update navigation
        this.updateNavigation(section);
        
        // Update content
        this.updateSectionVisibility(section);
        
        // Load section data
        await this.loadSectionData(section);
        
        this.currentSection = section;
    }

    updateNavigation(activeSection) {
        const navLinks = document.querySelectorAll('.nav-link[data-section]');
        navLinks.forEach(link => {
            const section = link.getAttribute('data-section');
            if (section === activeSection) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    updateSectionVisibility(activeSection) {
        const sections = ['dashboard', 'pipelines', 'executions', 'files', 'transformations', 'monitoring'];
        sections.forEach(section => {
            const element = document.getElementById(`${section}-section`);
            if (element) {
                element.style.display = section === activeSection ? 'block' : 'none';
            }
        });
    }

    async loadSectionData(section) {
        try {
            switch (section) {
                case 'dashboard':
                    await this.dashboard.load();
                    break;
                case 'pipelines':
                    await this.pipelines.load();
                    break;
                case 'executions':
                    await this.executions.load();
                    break;
                case 'files':
                    await this.files.load();
                    break;
                case 'transformations':
                    await this.transformationBuilder.load();
                    break;
                case 'monitoring':
                    await this.loadMonitoring();
                    break;
                default:
                    console.warn(`Unknown section: ${section}`);
            }
        } catch (error) {
            console.error(`Error loading section ${section}:`, error);
            this.uiUtils.showToast('Error', `Failed to load ${section}`, 'error');
        }
    }

    async loadMonitoring() {
        // Placeholder for monitoring implementation
        const container = document.getElementById('monitoring-content');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-chart-line fa-3x text-primary mb-3"></i>
                    <h5>Real-time Monitoring</h5>
                    <p class="text-muted">Advanced monitoring features will be available soon</p>
                </div>
            `;
        }
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            this.refreshCurrentSection();
        }, 30000); // Refresh every 30 seconds
    }

    async refreshCurrentSection() {
        if (this.currentSection === 'dashboard') {
            await this.dashboard.load();
        } else if (this.currentSection === 'executions') {
            await this.executions.refresh();
        }
    }

    cleanup() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.executions) {
            this.executions.destroy();
        }
    }

    // Public methods for external access
    async executePipeline(pipelineId) {
        return await this.pipelines.execute(pipelineId);
    }

    async refreshData() {
        await this.loadSectionData(this.currentSection);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PipelineSystemApp();
});

export default PipelineSystemApp;