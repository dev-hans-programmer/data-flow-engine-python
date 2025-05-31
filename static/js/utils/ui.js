/**
 * UI Utils - Common UI utilities and helper functions
 */

class UIUtils {
    constructor() {
        this.toastContainer = null;
        this.init();
    }

    init() {
        // Ensure toast container exists
        this.toastContainer = document.getElementById('toast-container');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            this.toastContainer.style.zIndex = '9999';
            document.body.appendChild(this.toastContainer);
        }
    }

    showToast(title, message, type = 'info') {
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
        
        this.toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
        toast.show();
        
        // Remove from DOM after hiding
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (error) {
            return 'Invalid date';
        }
    }

    formatDuration(seconds) {
        if (seconds == null) return 'N/A';
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
        return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    }

    getStatusIcon(status) {
        const icons = {
            active: 'fas fa-play-circle text-success',
            completed: 'fas fa-check-circle text-success',
            failed: 'fas fa-exclamation-circle text-danger',
            running: 'fas fa-spinner fa-spin text-primary',
            draft: 'fas fa-edit text-secondary',
            paused: 'fas fa-pause-circle text-warning',
            cancelled: 'fas fa-ban text-warning',
            pending: 'fas fa-clock text-info'
        };
        return `<i class="${icons[status] || 'fas fa-question-circle text-muted'}"></i>`;
    }

    getStatusBadge(status) {
        const badges = {
            active: 'badge bg-success',
            completed: 'badge bg-success',
            failed: 'badge bg-danger',
            running: 'badge bg-primary',
            draft: 'badge bg-secondary',
            paused: 'badge bg-warning',
            cancelled: 'badge bg-warning',
            pending: 'badge bg-info'
        };
        const className = badges[status] || 'badge bg-secondary';
        return `<span class="${className}">${this.getStatusIcon(status)} ${status}</span>`;
    }

    showModal(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            return modal;
        }
        console.warn(`Modal with ID ${modalId} not found`);
        return null;
    }

    hideModal(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
    }

    showLoader(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2 text-muted">Loading...</p>
                </div>
            `;
        }
    }

    showError(containerId, message, canRetry = false, retryCallback = null) {
        const container = document.getElementById(containerId);
        if (container) {
            const retryButton = canRetry && retryCallback ? `
                <button class="btn btn-primary btn-sm mt-2" onclick="(${retryCallback})()">
                    <i class="fas fa-redo"></i> Retry
                </button>
            ` : '';

            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                    <h5>Error Loading Data</h5>
                    <p class="text-muted">${message}</p>
                    ${retryButton}
                </div>
            `;
        }
    }

    showEmpty(containerId, message, icon = 'fa-inbox') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas ${icon} fa-3x text-muted mb-3"></i>
                    <h5>No Data Available</h5>
                    <p class="text-muted">${message}</p>
                </div>
            `;
        }
    }

    debounce(func, wait) {
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

    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Success', 'Copied to clipboard', 'success');
            }).catch(() => {
                this.showToast('Error', 'Failed to copy to clipboard', 'error');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                this.showToast('Success', 'Copied to clipboard', 'success');
            } catch (err) {
                this.showToast('Error', 'Failed to copy to clipboard', 'error');
            }
            document.body.removeChild(textArea);
        }
    }

    validateForm(formElement) {
        const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });

        return isValid;
    }

    serializeForm(formElement) {
        const formData = new FormData(formElement);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values with same name
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }
}

export default UIUtils;