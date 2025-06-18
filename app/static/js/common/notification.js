/**
 * 通知组件 - 在右上角显示各种类型的通知消息
 */
class Notification {
    /**
     * 初始化通知组件
     */
    static init() {
        // 检查通知容器是否存在，不存在则创建
        if (!document.querySelector('#notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            document.body.appendChild(container);
        }
    }

    /**
     * 显示通知
     * @param {Object} options - 通知选项
     * @param {string} options.type - 通知类型: success, error, warning, info
     * @param {string} options.title - 通知标题
     * @param {string} options.message - 通知消息内容
     * @param {number} options.duration - 显示时长，单位毫秒，默认3000ms
     * @param {Function} options.onClose - 关闭回调函数
     * @returns {HTMLElement} 通知元素
     */
    static show(options) {
        // 确保通知容器已初始化
        this.init();

        // 默认选项
        const defaultOptions = {
            type: 'info',
            title: '',
            message: '',
            duration: 3000,
            onClose: null
        };

        // 合并选项
        const opts = { ...defaultOptions, ...options };

        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${opts.type}`;

        // 图标映射
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-times-circle',
            warning: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle'
        };

        // 构建通知内容
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="${iconMap[opts.type]}"></i>
            </div>
            <div class="notification-content">
                ${opts.title ? `<div class="notification-title">${opts.title}</div>` : ''}
                ${opts.message ? `<div class="notification-message">${opts.message}</div>` : ''}
            </div>
            <button class="notification-close" title="关闭">
                <i class="fas fa-times"></i>
            </button>
        `;

        // 获取通知容器并添加通知
        const container = document.querySelector('#notification-container');
        container.appendChild(notification);

        // 添加显示动画
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);

        // 绑定关闭按钮事件
        const closeBtn = notification.querySelector('.notification-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close(notification, opts.onClose));
        }

        // 设置自动关闭
        if (opts.duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    this.close(notification, opts.onClose);
                }
            }, opts.duration);
        }

        return notification;
    }

    /**
     * 关闭通知
     * @param {HTMLElement} notification - 通知元素
     * @param {Function} callback - 关闭后的回调函数
     */
    static close(notification, callback) {
        // 添加隐藏动画类
        notification.classList.remove('notification-show');
        notification.classList.add('notification-hide');

        // 动画结束后移除元素
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
                if (typeof callback === 'function') {
                    callback();
                }
            }
        }, 300); // 动画持续时间
    }

    /**
     * 显示成功通知
     * @param {string} message - 通知消息
     * @param {string} title - 通知标题，默认为"成功"
     * @param {number} duration - 显示时长，默认3000ms
     * @param {Function} onClose - 关闭回调函数
     * @returns {HTMLElement} 通知元素
     */
    static success(message, title = '成功', duration = 3000, onClose = null) {
        return this.show({
            type: 'success',
            title,
            message,
            duration,
            onClose
        });
    }

    /**
     * 显示错误通知
     * @param {string} message - 通知消息
     * @param {string} title - 通知标题，默认为"错误"
     * @param {number} duration - 显示时长，默认3000ms
     * @param {Function} onClose - 关闭回调函数
     * @returns {HTMLElement} 通知元素
     */
    static error(message, title = '错误', duration = 3000, onClose = null) {
        return this.show({
            type: 'error',
            title,
            message,
            duration,
            onClose
        });
    }

    /**
     * 显示警告通知
     * @param {string} message - 通知消息
     * @param {string} title - 通知标题，默认为"警告"
     * @param {number} duration - 显示时长，默认3000ms
     * @param {Function} onClose - 关闭回调函数
     * @returns {HTMLElement} 通知元素
     */
    static warning(message, title = '警告', duration = 3000, onClose = null) {
        return this.show({
            type: 'warning',
            title,
            message,
            duration,
            onClose
        });
    }

    /**
     * 显示信息通知
     * @param {string} message - 通知消息
     * @param {string} title - 通知标题，默认为"提示"
     * @param {number} duration - 显示时长，默认3000ms
     * @param {Function} onClose - 关闭回调函数
     * @returns {HTMLElement} 通知元素
     */
    static info(message, title = '提示', duration = 3000, onClose = null) {
        return this.show({
            type: 'info',
            title,
            message,
            duration,
            onClose
        });
    }

    /**
     * 清除所有通知
     */
    static clear() {
        const container = document.querySelector('#notification-container');
        if (container) {
            const notifications = container.querySelectorAll('.notification');
            notifications.forEach(notification => {
                this.close(notification);
            });
        }
    }
}

/**
 * 全局通知函数 - 兼容多种调用方式
 * 支持两种调用方式：
 * 1. showNotification(message, type) - 兼容现有代码
 * 2. showNotification(title, message, type, duration) - 完整参数
 */
function showNotification(arg1, arg2, arg3, arg4) {
    let title, message, type, duration;
    
    // 判断调用方式
    if (typeof arg2 === 'string' && ['success', 'error', 'warning', 'info'].includes(arg2)) {
        // 方式1: showNotification(message, type)
        message = arg1;
        type = arg2;
        title = getNotificationTitle(type);
        duration = 3000;
    } else {
        // 方式2: showNotification(title, message, type, duration)
        title = arg1;
        message = arg2;
        type = arg3 || 'info';
        duration = arg4 || 3000;
    }
    
    return Notification.show({
        title: title,
        message: message,
        type: type,
        duration: duration
    });
}

/**
 * 根据类型获取默认标题
 */
function getNotificationTitle(type) {
    switch (type) {
        case 'success': return '成功';
        case 'error': return '错误';
        case 'warning': return '警告';
        case 'info':
        default: return '提示';
    }
}

// 页面加载时初始化通知系统
document.addEventListener('DOMContentLoaded', () => {
    Notification.init();
});

// 将Notification类和showNotification函数添加到全局作用域
window.Notification = Notification;
window.showNotification = showNotification; 