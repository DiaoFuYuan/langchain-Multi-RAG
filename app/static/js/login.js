// 等待DOM完全加载后执行
document.addEventListener('DOMContentLoaded', function() {
    // 获取表单和弹窗元素
    const loginForm = document.getElementById('loginForm');
    const popupOverlay = document.getElementById('popupOverlay');
    const popupIcon = document.getElementById('popupIcon');
    const popupTitle = document.getElementById('popupTitle');
    const popupMessage = document.getElementById('popupMessage');
    const popupButton = document.getElementById('popupButton');
    const popupContainer = document.getElementById('popupContainer');
    
    // 监听表单提交事件
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            // 阻止表单默认提交行为
            event.preventDefault();
            
            // 获取表单数据
            const formData = new FormData(loginForm);
            
            // 发送AJAX请求
            fetch('/auth/login', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                // 处理响应
                if (data.detail) {
                    if (data.detail === '登录成功') {
                        // 登录成功，显示成功弹窗
                        showPopup('登录成功', '欢迎回到智能体平台', 'success');
                        
                        // 保存令牌和用户信息到本地存储
                        if (data.access_token) {
                            localStorage.setItem('access_token', data.access_token);
                            localStorage.setItem('token_type', data.token_type);
                            localStorage.setItem('username', data.username);
                        }
                        
                        // 弹窗关闭后重定向到通用对话页面
                        popupButton.onclick = function() {
                            closePopup();
                            window.location.href = '/chat/home';  // 修改为通用对话页面路径
                        };
                    } else {
                        // 显示错误弹窗
                        showPopup('登录失败', data.detail, 'error');
                    }
                } else {
                    // 未知错误
                    showPopup('未知错误', '登录请求出现未知错误', 'error');
                }
            })
            .catch(error => {
                // 捕获并显示网络或其他错误
                console.error('登录请求出错:', error);
                showPopup('网络错误', '无法连接到服务器，请稍后再试', 'error');
            });
        });
    }
    
    // 重置按钮点击事件 - 清除表单
    const resetButton = document.querySelector('.btn-reset');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            loginForm.reset();
        });
    }
    
    // 绑定弹窗关闭事件
    if (popupButton) {
        popupButton.addEventListener('click', closePopup);
    }
    
    // 点击弹窗背景关闭弹窗
    if (popupOverlay) {
        popupOverlay.addEventListener('click', function(event) {
            if (event.target === popupOverlay) {
                closePopup();
            }
        });
    }
    
    /**
     * 显示弹窗函数
     * @param {string} title - 弹窗标题
     * @param {string} message - 弹窗内容
     * @param {string} type - 弹窗类型 (success 或 error)
     */
    function showPopup(title, message, type) {
        if (popupTitle) popupTitle.textContent = title;
        if (popupMessage) popupMessage.textContent = message;
        
        // 设置图标
        if (popupIcon) {
            const iconElement = popupIcon.querySelector('i');
            if (iconElement) {
                if (type === 'success') {
                    iconElement.className = 'fas fa-check-circle';
                    popupContainer.className = 'popup-container popup-success';
                } else {
                    iconElement.className = 'fas fa-times-circle';
                    popupContainer.className = 'popup-container popup-error';
                }
            }
        }
        
        // 显示弹窗
        if (popupOverlay) {
            popupOverlay.classList.add('show');
        }
        
        // 自动关闭（仅成功消息）
        if (type === 'success') {
            setTimeout(() => {
                closePopup();
                window.location.href = '/chat/home';  // 修改为通用对话页面路径
            }, 2000);
        }
    }
    
    /**
     * 关闭弹窗函数
     */
    function closePopup() {
        if (popupOverlay) {
            popupOverlay.classList.remove('show');
        }
    }
}); 