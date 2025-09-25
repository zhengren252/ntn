// ScanPulse Web Interface JavaScript

// 全局变量
let refreshInterval;
let notificationPermission = false;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    // 请求通知权限
    requestNotificationPermission();
    
    // 初始化工具提示
    initializeTooltips();
    
    // 初始化移动端菜单
    initializeMobileMenu();
    
    // 设置自动刷新
    setupAutoRefresh();
    
    // 绑定全局事件
    bindGlobalEvents();
    
    // 更新时间显示
    updateTimeDisplay();
    setInterval(updateTimeDisplay, 1000);
}

// 请求通知权限
function requestNotificationPermission() {
    if ('Notification' in window) {
        Notification.requestPermission().then(function(permission) {
            notificationPermission = permission === 'granted';
        });
    }
}

// 初始化工具提示
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// 初始化移动端菜单
function initializeMobileMenu() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
        
        // 点击外部关闭菜单
        document.addEventListener('click', function(e) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }
}

// 设置自动刷新
function setupAutoRefresh() {
    const refreshSelect = document.getElementById('auto-refresh');
    if (refreshSelect) {
        refreshSelect.addEventListener('change', function() {
            const interval = parseInt(this.value);
            setAutoRefresh(interval);
        });
        
        // 默认30秒刷新
        setAutoRefresh(30000);
    }
}

// 设置自动刷新间隔
function setAutoRefresh(interval) {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    if (interval > 0) {
        refreshInterval = setInterval(function() {
            if (typeof refreshData === 'function') {
                refreshData();
            }
        }, interval);
    }
}

// 绑定全局事件
function bindGlobalEvents() {
    // ESC键关闭模态框
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
    
    // 全局错误处理
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        showNotification('系统错误', 'error');
    });
    
    // 网络状态监听
    window.addEventListener('online', function() {
        showNotification('网络连接已恢复', 'success');
    });
    
    window.addEventListener('offline', function() {
        showNotification('网络连接已断开', 'warning');
    });
}

// 更新时间显示
function updateTimeDisplay() {
    const timeElements = document.querySelectorAll('.current-time');
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    timeElements.forEach(element => {
        element.textContent = timeString;
    });
}

// 显示加载状态
function showLoading(elementId, message = '加载中...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center p-4">
                <div class="loading-spinner"></div>
                <div class="mt-2">${message}</div>
            </div>
        `;
    }
}

// 显示错误信息
function showError(elementId, message = '加载失败') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="error-message text-center">
                <i class="fas fa-exclamation-triangle"></i>
                <div class="mt-2">${message}</div>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="location.reload()">
                    <i class="fas fa-redo"></i> 重试
                </button>
            </div>
        `;
    }
}

// 显示成功信息
function showSuccess(elementId, message = '操作成功') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="success-message text-center">
                <i class="fas fa-check-circle"></i>
                <div class="mt-2">${message}</div>
            </div>
        `;
    }
}

// 显示通知
function showNotification(message, type = 'info', duration = 3000) {
    // 桌面通知
    if (notificationPermission && type === 'error') {
        new Notification('ScanPulse', {
            body: message,
            icon: '/static/img/icon.png'
        });
    }
    
    // 页面内通知
    const notification = document.createElement('div');
    notification.className = `alert alert-${getBootstrapAlertType(type)} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // 自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// 获取Bootstrap警告类型
function getBootstrapAlertType(type) {
    const typeMap = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return typeMap[type] || 'info';
}

// 格式化数字
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) {
        return 'N/A';
    }
    
    const number = parseFloat(num);
    
    if (number >= 1e9) {
        return (number / 1e9).toFixed(decimals) + 'B';
    } else if (number >= 1e6) {
        return (number / 1e6).toFixed(decimals) + 'M';
    } else if (number >= 1e3) {
        return (number / 1e3).toFixed(decimals) + 'K';
    } else {
        return number.toFixed(decimals);
    }
}

// 格式化时间
function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // 小于1分钟
    if (diff < 60000) {
        return '刚刚';
    }
    
    // 小于1小时
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}分钟前`;
    }
    
    // 小于24小时
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}小时前`;
    }
    
    // 超过24小时显示具体时间
    return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 格式化百分比
function formatPercentage(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) {
        return 'N/A';
    }
    return (parseFloat(value) * 100).toFixed(decimals) + '%';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 复制到剪贴板
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('已复制到剪贴板', 'success', 1000);
        }).catch(err => {
            console.error('复制失败:', err);
            showNotification('复制失败', 'error');
        });
    } else {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showNotification('已复制到剪贴板', 'success', 1000);
        } catch (err) {
            console.error('复制失败:', err);
            showNotification('复制失败', 'error');
        }
        document.body.removeChild(textArea);
    }
}

// 下载文件
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 防抖函数
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// API请求封装
class ApiClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }
    
    async request(url, options = {}) {
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(this.baseURL + url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }
    
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl);
    }
    
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
}

// 创建API客户端实例
const api = new ApiClient();

// 图表工具类
class ChartHelper {
    static createLineChart(ctx, data, options = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    beginAtZero: true
                }
            }
        };
        
        return new Chart(ctx, {
            type: 'line',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
    
    static createBarChart(ctx, data, options = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    beginAtZero: true
                }
            }
        };
        
        return new Chart(ctx, {
            type: 'bar',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
    
    static createDoughnutChart(ctx, data, options = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                }
            }
        };
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
}

// 数据验证工具
class Validator {
    static isEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    static isNumber(value) {
        return !isNaN(parseFloat(value)) && isFinite(value);
    }
    
    static isPositiveNumber(value) {
        return this.isNumber(value) && parseFloat(value) > 0;
    }
    
    static isInRange(value, min, max) {
        const num = parseFloat(value);
        return this.isNumber(value) && num >= min && num <= max;
    }
    
    static isRequired(value) {
        return value !== null && value !== undefined && value.toString().trim() !== '';
    }
    
    static minLength(value, length) {
        return value && value.toString().length >= length;
    }
    
    static maxLength(value, length) {
        return !value || value.toString().length <= length;
    }
}

// 本地存储工具
class Storage {
    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('存储失败:', error);
            return false;
        }
    }
    
    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('读取存储失败:', error);
            return defaultValue;
        }
    }
    
    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('删除存储失败:', error);
            return false;
        }
    }
    
    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('清空存储失败:', error);
            return false;
        }
    }
}

// 导出全局函数和类
window.ScanPulse = {
    showLoading,
    showError,
    showSuccess,
    showNotification,
    formatNumber,
    formatTime,
    formatPercentage,
    formatFileSize,
    copyToClipboard,
    downloadFile,
    debounce,
    throttle,
    api,
    ChartHelper,
    Validator,
    Storage
};