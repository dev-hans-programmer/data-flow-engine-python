/**
 * Files Component - Handles file management and uploads
 */

class FilesComponent {
    constructor(apiService, uiUtils) {
        this.apiService = apiService;
        this.uiUtils = uiUtils;
    }

    async load() {
        this.uiUtils.showLoader('files-content');
        
        try {
            const files = await this.apiService.getFiles();
            this.displayFiles(files);
        } catch (error) {
            console.error('Error loading files:', error);
            this.uiUtils.showError('files-content', 'Failed to load files', true, () => this.load());
        }
    }

    displayFiles(files) {
        const container = document.getElementById('files-content');
        if (!container) return;

        if (!files || files.length === 0) {
            this.uiUtils.showEmpty('files-content', 'No files uploaded yet. Use the upload button to add files for processing.', 'fa-file-upload');
            return;
        }

        const html = `
            <div class="row mb-3">
                <div class="col-12">
                    <button class="btn btn-primary" onclick="fileManager.showUploadModal()">
                        <i class="fas fa-upload"></i> Upload Files
                    </button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Name</th>
                            <th>Format</th>
                            <th>Size</th>
                            <th>Uploaded</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${files.map(file => this.renderFileRow(file)).join('')}
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    renderFileRow(file) {
        const formatIcon = this.getFormatIcon(file.format);
        const size = this.formatFileSize(file.size);

        return `
            <tr>
                <td>
                    <i class="${formatIcon}"></i>
                    <strong>${file.name}</strong>
                </td>
                <td>
                    <span class="badge bg-secondary">${file.format || 'unknown'}</span>
                </td>
                <td>${size}</td>
                <td>${this.uiUtils.formatDateTime(file.uploaded_at)}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" onclick="fileManager.preview('${file.path}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="fileManager.download('${file.path}')">
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="fileManager.delete('${file.path}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    getFormatIcon(format) {
        const icons = {
            csv: 'fas fa-file-csv text-success',
            json: 'fas fa-file-code text-info',
            xlsx: 'fas fa-file-excel text-success',
            parquet: 'fas fa-file-alt text-primary'
        };
        return icons[format] || 'fas fa-file text-muted';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showUploadModal() {
        this.uiUtils.showModal('fileUploadModal');
    }

    async uploadFiles(fileInput) {
        const files = fileInput.files;
        if (!files || files.length === 0) return;

        const uploadPromises = Array.from(files).map(file => this.uploadSingleFile(file));
        
        try {
            await Promise.all(uploadPromises);
            this.uiUtils.showToast('Success', 'Files uploaded successfully', 'success');
            this.uiUtils.hideModal('fileUploadModal');
            this.load(); // Refresh file list
        } catch (error) {
            console.error('Error uploading files:', error);
            this.uiUtils.showToast('Error', 'Some files failed to upload', 'error');
        }
    }

    async uploadSingleFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            return await this.apiService.uploadFile(formData);
        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
            throw error;
        }
    }

    async preview(filePath) {
        try {
            const preview = await this.apiService.previewFile(filePath);
            
            const content = document.getElementById('file-preview-content');
            if (!content) return;

            content.innerHTML = `
                <h5>${filePath}</h5>
                <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                    <table class="table table-sm table-striped">
                        <thead class="table-dark sticky-top">
                            <tr>
                                ${preview.columns.map(col => `<th>${col}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${preview.data.map(row => `
                                <tr>
                                    ${preview.columns.map(col => `<td>${row[col] || ''}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    <small class="text-muted">
                        Showing ${preview.data.length} rows of ${preview.total_rows || preview.data.length} total
                    </small>
                </div>
            `;

            this.uiUtils.showModal('filePreviewModal');
        } catch (error) {
            console.error('Error previewing file:', error);
            this.uiUtils.showToast('Error', 'Failed to preview file', 'error');
        }
    }

    download(filePath) {
        window.open(`/api/v1/files/download?file_path=${encodeURIComponent(filePath)}`, '_blank');
    }

    async delete(filePath) {
        if (!confirm(`Are you sure you want to delete ${filePath}?`)) return;

        try {
            await this.apiService.deleteFile(filePath);
            this.uiUtils.showToast('Success', 'File deleted successfully', 'success');
            this.load(); // Refresh file list
        } catch (error) {
            console.error('Error deleting file:', error);
            this.uiUtils.showToast('Error', 'Failed to delete file', 'error');
        }
    }
}

export default FilesComponent;