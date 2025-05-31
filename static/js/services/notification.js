/**
 * Notification Service
 * Manages in-app notifications with persistent storage and UI updates
 */

export default class NotificationService {
    constructor() {
        this.notifications = [];
        this.unreadCount = 0;
        this.maxNotifications = 50;
        this.storageKey = 'pipeline_notifications';
        
        this.loadNotifications();
        this.initializeNotificationIcon();
    }

    /**
     * Add a new notification
     */
    addNotification(type, title, message, data = {}) {
        const notification = {
            id: this.generateId(),
            type: type, // 'success', 'error', 'warning', 'info'
            title: title,
            message: message,
            timestamp: new Date().toISOString(),
            read: false,
            data: data
        };

        // Add to beginning of array
        this.notifications.unshift(notification);
        
        // Limit notifications count
        if (this.notifications.length > this.maxNotifications) {
            this.notifications = this.notifications.slice(0, this.maxNotifications);
        }

        this.unreadCount++;
        this.saveNotifications();
        this.updateNotificationIcon();
        this.showToastNotification(notification);
        
        return notification.id;
    }

    /**
     * Mark notification as read
     */
    markAsRead(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification && !notification.read) {
            notification.read = true;
            this.unreadCount = Math.max(0, this.unreadCount - 1);
            this.saveNotifications();
            this.updateNotificationIcon();
        }
    }

    /**
     * Mark all notifications as read
     */
    markAllAsRead() {
        this.notifications.forEach(n => n.read = true);
        this.unreadCount = 0;
        this.saveNotifications();
        this.updateNotificationIcon();
    }

    /**
     * Remove a notification
     */
    removeNotification(notificationId) {
        const index = this.notifications.findIndex(n => n.id === notificationId);
        if (index !== -1) {
            const notification = this.notifications[index];
            if (!notification.read) {
                this.unreadCount = Math.max(0, this.unreadCount - 1);
            }
            this.notifications.splice(index, 1);
            this.saveNotifications();
            this.updateNotificationIcon();
        }
    }

    /**
     * Clear all notifications
     */
    clearAll() {
        this.notifications = [];
        this.unreadCount = 0;
        this.saveNotifications();
        this.updateNotificationIcon();
    }

    /**
     * Get all notifications
     */
    getNotifications() {
        return this.notifications;
    }

    /**
     * Get unread notifications count
     */
    getUnreadCount() {
        return this.unreadCount;
    }

    /**
     * Initialize notification icon in the navbar
     */
    initializeNotificationIcon() {
        // Wait for DOM to be ready
        setTimeout(() => {
            this.setupEventListeners();
            this.updateNotificationIcon();
        }, 500);
    }

    /**
     * Setup event listeners for notification interactions
     */
    setupEventListeners() {
        // Mark all as read
        const markAllReadBtn = document.getElementById('mark-all-read');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.markAllAsRead();
                this.renderNotificationList();
            });
        }

        // Clear all notifications
        const clearAllBtn = document.getElementById('clear-all-notifications');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearAll();
                this.renderNotificationList();
            });
        }

        // Update list when dropdown is opened
        const notificationIcon = document.getElementById('notification-icon');
        if (notificationIcon) {
            notificationIcon.addEventListener('click', () => {
                this.renderNotificationList();
            });
        }
    }

    /**
     * Update notification icon badge
     */
    updateNotificationIcon() {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (this.unreadCount > 0) {
                badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    /**
     * Render notification list in dropdown
     */
    renderNotificationList() {
        const listContainer = document.getElementById('notification-list');
        if (!listContainer) return;

        if (this.notifications.length === 0) {
            listContainer.innerHTML = `
                <li class="dropdown-item text-muted text-center">
                    No notifications
                </li>
            `;
            return;
        }

        const notificationItems = this.notifications.map(notification => {
            const timeAgo = this.getTimeAgo(notification.timestamp);
            const iconClass = this.getNotificationIcon(notification.type);
            const bgClass = notification.read ? '' : 'bg-light';
            
            return `
                <li class="dropdown-item ${bgClass}" data-notification-id="${notification.id}">
                    <div class="d-flex">
                        <div class="flex-shrink-0 me-2">
                            <i class="${iconClass} text-${notification.type === 'error' ? 'danger' : notification.type === 'success' ? 'success' : notification.type === 'warning' ? 'warning' : 'info'}"></i>
                        </div>
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${notification.title}</h6>
                            <p class="mb-1 small">${notification.message}</p>
                            <small class="text-muted">${timeAgo}</small>
                        </div>
                        <div class="flex-shrink-0">
                            <button class="btn btn-sm btn-outline-secondary" onclick="notificationService.removeNotification('${notification.id}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </li>
            `;
        }).join('');

        listContainer.innerHTML = notificationItems;

        // Add click handlers to mark as read
        listContainer.querySelectorAll('.dropdown-item[data-notification-id]').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('button')) {
                    const notificationId = item.dataset.notificationId;
                    this.markAsRead(notificationId);
                    this.renderNotificationList();
                }
            });
        });
    }

    /**
     * Show toast notification for new notifications
     */
    showToastNotification(notification) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        const toastId = `toast-${notification.id}`;
        const iconClass = this.getNotificationIcon(notification.type);
        const bgClass = notification.type === 'error' ? 'bg-danger' : 
                       notification.type === 'success' ? 'bg-success' : 
                       notification.type === 'warning' ? 'bg-warning' : 'bg-info';

        const toastHtml = `
            <div class="toast ${bgClass} text-white" id="${toastId}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header ${bgClass} text-white border-0">
                    <i class="${iconClass} me-2"></i>
                    <strong class="me-auto">${notification.title}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${notification.message}
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Initialize and show toast
        const toastElement = document.getElementById(toastId);
        if (toastElement && window.bootstrap) {
            const toast = new bootstrap.Toast(toastElement, {
                delay: notification.type === 'error' ? 8000 : 4000
            });
            toast.show();
            
            // Remove toast element after it's hidden
            toastElement.addEventListener('hidden.bs.toast', () => {
                toastElement.remove();
            });
        }
    }

    /**
     * Get notification icon based on type
     */
    getNotificationIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-triangle',
            warning: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    /**
     * Get human-readable time ago
     */
    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }

    /**
     * Generate unique ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    /**
     * Load notifications from localStorage
     */
    loadNotifications() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const data = JSON.parse(stored);
                this.notifications = data.notifications || [];
                this.unreadCount = this.notifications.filter(n => !n.read).length;
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
            this.notifications = [];
            this.unreadCount = 0;
        }
    }

    /**
     * Save notifications to localStorage
     */
    saveNotifications() {
        try {
            const data = {
                notifications: this.notifications,
                lastUpdated: new Date().toISOString()
            };
            localStorage.setItem(this.storageKey, JSON.stringify(data));
        } catch (error) {
            console.error('Failed to save notifications:', error);
        }
    }

    // Convenience methods for different notification types
    success(title, message, data = {}) {
        return this.addNotification('success', title, message, data);
    }

    error(title, message, data = {}) {
        return this.addNotification('error', title, message, data);
    }

    warning(title, message, data = {}) {
        return this.addNotification('warning', title, message, data);
    }

    info(title, message, data = {}) {
        return this.addNotification('info', title, message, data);
    }
}