/**
 * 快捷智能体管理页面 JavaScript
 * 负责页面交互逻辑、数据管理和用户操作处理
 */

// 全局变量
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;
let totalAgents = 0;
let currentCategory = 'all';
let currentSearch = '';
let selectedTemplate = 'simple';
let agents = [];
let agentToDelete = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 等待侧边栏管理器初始化完成
    setTimeout(() => {
        if (window.sidebarManager) {
            window.sidebarManager.setActiveMenuByPage('agent-quick');
        }
    }, 100);
    
    // 初始化页面
    initAgentPage();
});

/**
 * 初始化页面
 */
function initAgentPage() {
    console.log('初始化快捷智能体管理页面');
    
    // 绑定事件监听器
    bindEvents();
    
    // 加载智能体数据
    loadAgents();
    
    // 初始化分页
    initPagination();
}

/**
 * 绑定事件监听器
 */
function bindEvents() {
    // 搜索框事件
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 500));
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    }
    
    // 分类标签事件
    const categoryTabs = document.querySelectorAll('.agent-tab');
    categoryTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            handleCategoryChange(this.dataset.category);
        });
    });
    
    // 创建智能体按钮事件
    const createBtn = document.getElementById('createAgentBtn');
    if (createBtn) {
        createBtn.addEventListener('click', openCreateModal);
    }
    
    // 模板选择事件
    const templateCards = document.querySelectorAll('.agent-template-card');
    templateCards.forEach(card => {
        card.addEventListener('click', function() {
            selectTemplate(this.dataset.template);
        });
    });
    
    // 跳转页面事件
    const gotoInput = document.getElementById('gotoPageInput');
    if (gotoInput) {
        gotoInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                gotoPage();
            }
        });
    }
    
    // ESC键关闭模态框
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

/**
 * 防抖函数
 */
function debounce(func, wait) {
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

/**
 * 搜索处理
 */
function handleSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        loadAgents();
    }
}

/**
 * 分类切换处理
 */
function handleCategoryChange(category) {
    // 更新活跃标签
    document.querySelectorAll('.agent-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-category="${category}"]`).classList.add('active');
    
    currentCategory = category;
    currentPage = 1;
    loadAgents();
}

/**
 * 加载智能体数据
 */
async function loadAgents() {
    try {
        showLoading(true);
        
        const params = new URLSearchParams({
            page: currentPage,
            page_size: pageSize
        });
        
        if (currentSearch) {
            params.append('search', currentSearch);
        }
        
        // 根据分类筛选
        if (currentCategory !== 'all') {
            if (currentCategory === 'personal') {
                // 这里应该根据当前用户ID筛选，暂时跳过
            } else if (currentCategory === 'public') {
                params.append('is_public', 'true');
            }
        }
        
        const response = await fetch(`/agent/api/agents?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        agents = data.agents || [];
        totalAgents = data.total || 0;
        totalPages = data.pages || 1;
        
        renderAgents();
        updatePagination();
        
    } catch (error) {
        console.error('加载智能体列表失败:', error);
        showError('加载智能体列表失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * 渲染智能体表格
 */
function renderAgents() {
    const tableBody = document.getElementById('agentTableBody');
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    
    if (!tableBody) return;
    
    // 清空现有内容
    tableBody.innerHTML = '';
    
    // 重新添加加载和空状态元素
    tableBody.appendChild(loadingState);
    tableBody.appendChild(emptyState);
    
    if (agents.length === 0) {
        emptyState.style.display = 'flex';
        return;
    }
    
    emptyState.style.display = 'none';
    
    // 渲染智能体行
    agents.forEach(agent => {
        const row = createAgentRow(agent);
        tableBody.appendChild(row);
    });
}

/**
 * 创建智能体表格行
 */
function createAgentRow(agent) {
    const row = document.createElement('div');
    row.className = 'agent-table-row';
    
    // 格式化时间
    const updatedAt = agent.updated_at ? new Date(agent.updated_at).toLocaleString('zh-CN') : '未知';
    
    // 获取分类样式类
    const categoryClass = getCategoryClass(agent.category);
    const statusClass = getStatusClass(agent.status);
    
    row.innerHTML = `
        <div class="agent-col agent-col-name">
            <i class="fas fa-robot agent-icon"></i>
            <span class="agent-name-link" onclick="viewAgent(${agent.id})">${escapeHtml(agent.name)}</span>
        </div>
        <div class="agent-col agent-col-description">${escapeHtml(agent.description || '')}</div>
        <div class="agent-col">
            <span class="agent-category-badge ${categoryClass}">${escapeHtml(agent.category_display || '其他')}</span>
        </div>
        <div class="agent-col">
            <span class="agent-status ${statusClass}">${escapeHtml(agent.status_display || '未知')}</span>
        </div>
        <div class="agent-col">${updatedAt}</div>
        <div class="agent-col">
            <div class="agent-action-dropdown">
                <button class="agent-action-btn">
                    <i class="fas fa-ellipsis-v"></i>
                </button>
                <div class="agent-dropdown-menu">
                    <div class="agent-dropdown-item" onclick="editAgent(${agent.id})">
                        <i class="fas fa-edit"></i>编辑
                    </div>
                    <div class="agent-dropdown-item" onclick="copyAgent(${agent.id})">
                        <i class="fas fa-copy"></i>复制
                    </div>
                    <div class="agent-dropdown-item" onclick="exportAgent(${agent.id})">
                        <i class="fas fa-download"></i>导出
                    </div>
                    <div class="agent-dropdown-item danger" onclick="deleteAgent(${agent.id}, '${escapeHtml(agent.name)}')">
                        <i class="fas fa-trash"></i>删除
                    </div>
                </div>
            </div>
        </div>
    `;
    
    return row;
}

/**
 * 获取分类样式类
 */
function getCategoryClass(category) {
    const classMap = {
        'customer_service': 'customer-service',
        'analysis': 'analysis',
        'writing': 'writing',
        'coding': 'coding',
        'translation': 'translation',
        'other': 'other'
    };
    return classMap[category] || 'other';
}

/**
 * 获取状态样式类
 */
function getStatusClass(status) {
    const classMap = {
        'active': 'active',
        'inactive': 'inactive',
        'error': 'error'
    };
    return classMap[status] || 'inactive';
}

/**
 * 打开创建模态框
 */
function openCreateModal() {
    const modal = document.getElementById('createAgentModal');
    if (modal) {
        modal.classList.add('show');
        
        // 重置表单
        const form = document.getElementById('createAgentForm');
        if (form) {
            form.reset();
        }
        
        // 重置模板选择
        selectedTemplate = 'simple';
        updateTemplateSelection();
    }
}

/**
 * 关闭模态框
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * 关闭所有模态框
 */
function closeAllModals() {
    document.querySelectorAll('.agent-modal').forEach(modal => {
        modal.classList.remove('show');
    });
}

/**
 * 模板选择
 */
function selectTemplate(template) {
    selectedTemplate = template;
    updateTemplateSelection();
}

/**
 * 更新模板选择UI
 */
function updateTemplateSelection() {
    document.querySelectorAll('.agent-template-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    const selectedCard = document.querySelector(`[data-template="${selectedTemplate}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
}

/**
 * 创建智能体
 */
async function createAgent() {
    try {
        const form = document.getElementById('createAgentForm');
        if (!form) return;
        
        const formData = new FormData(form);
        
        // 验证必填字段
        const name = formData.get('name');
        if (!name || name.trim() === '') {
            showError('请输入智能体名称');
            return;
        }
        
        // 构建请求数据
        const agentData = {
            name: name.trim(),
            description: formData.get('description') || '',
            problem_description: formData.get('problem_description') || '',
            answer_description: formData.get('answer_description') || '',
            template: selectedTemplate,
            category: 'other', // 可以根据模板自动分类
            is_public: false
        };
        
        const response = await fetch('/agent/api/agents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(agentData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '创建失败');
        }
        
        const result = await response.json();
        
        showSuccess(`智能体 "${result.name}" 创建成功！`);
        closeModal('createAgentModal');
        
        // 跳转到配置页面
        window.location.href = `/agent/config/${result.id}`;
        
    } catch (error) {
        console.error('创建智能体失败:', error);
        showError('创建智能体失败: ' + error.message);
    }
}

/**
 * 查看智能体详情
 */
function viewAgent(agentId) {
    console.log('查看智能体:', agentId);
    // 导航到配置页面
    window.location.href = `/agent/config/${agentId}`;
}

/**
 * 编辑智能体
 */
function editAgent(agentId) {
    console.log('编辑智能体:', agentId);
    // 导航到配置页面
    window.location.href = `/agent/config/${agentId}`;
}

/**
 * 复制智能体
 */
async function copyAgent(agentId) {
    try {
        const response = await fetch(`/agent/api/agents/${agentId}/copy`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '复制失败');
        }
        
        const result = await response.json();
        
        showSuccess(result.message);
        
        // 重新加载列表
        loadAgents();
        
    } catch (error) {
        console.error('复制智能体失败:', error);
        showError('复制智能体失败: ' + error.message);
    }
}

/**
 * 导出智能体
 */
function exportAgent(agentId) {
    console.log('导出智能体:', agentId);
    showInfo('导出功能正在开发中...');
}

/**
 * 删除智能体
 */
function deleteAgent(agentId, agentName) {
    agentToDelete = agentId;
    
    const nameSpan = document.getElementById('deleteAgentName');
    if (nameSpan) {
        nameSpan.textContent = agentName;
    }
    
    const modal = document.getElementById('deleteAgentModal');
    if (modal) {
        modal.classList.add('show');
    }
}

/**
 * 确认删除智能体
 */
async function confirmDeleteAgent() {
    if (!agentToDelete) return;
    
    try {
        const response = await fetch(`/agent/api/agents/${agentToDelete}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '删除失败');
        }
        
        const result = await response.json();
        
        showSuccess(result.message);
        closeModal('deleteAgentModal');
        
        // 重新加载列表
        loadAgents();
        
        agentToDelete = null;
        
    } catch (error) {
        console.error('删除智能体失败:', error);
        showError('删除智能体失败: ' + error.message);
    }
}

/**
 * 分页控制
 */
function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        loadAgents();
    }
}

/**
 * 跳转页面
 */
function gotoPage() {
    const input = document.getElementById('gotoPageInput');
    if (input) {
        const page = parseInt(input.value);
        if (page >= 1 && page <= totalPages) {
            currentPage = page;
            loadAgents();
        } else {
            input.value = currentPage;
        }
    }
}

/**
 * 更新分页信息
 */
function updatePagination() {
    // 更新页面信息
    const pageInfo = document.getElementById('pageInfo');
    if (pageInfo) {
        pageInfo.textContent = `共 ${totalAgents} 个智能体`;
    }
    
    // 更新当前页
    const currentPageSpan = document.getElementById('currentPage');
    if (currentPageSpan) {
        currentPageSpan.textContent = currentPage;
    }
    
    // 更新总页数
    const totalPagesSpan = document.getElementById('totalPages');
    if (totalPagesSpan) {
        totalPagesSpan.textContent = `共 ${totalPages} 页`;
    }
    
    // 更新跳转输入框
    const gotoInput = document.getElementById('gotoPageInput');
    if (gotoInput) {
        gotoInput.value = currentPage;
        gotoInput.max = totalPages;
    }
    
    // 更新按钮状态
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    
    if (prevBtn) {
        if (currentPage <= 1) {
            prevBtn.classList.add('disabled');
        } else {
            prevBtn.classList.remove('disabled');
        }
    }
    
    if (nextBtn) {
        if (currentPage >= totalPages) {
            nextBtn.classList.add('disabled');
        } else {
            nextBtn.classList.remove('disabled');
        }
    }
}

/**
 * 显示加载状态
 */
function showLoading(show) {
    const loadingState = document.getElementById('loadingState');
    if (loadingState) {
        loadingState.style.display = show ? 'flex' : 'none';
    }
}

/**
 * 消息提示函数
 */
function showSuccess(message) {
    showMessage(message, 'success');
}

function showError(message) {
    showMessage(message, 'error');
}

function showInfo(message) {
    showMessage(message, 'info');
}

function showMessage(message, type = 'info') {
    // 创建消息提示元素
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-toast message-${type}`;
    messageDiv.textContent = message;
    
    // 样式
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-size: 14px;
        z-index: 9999;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    // 根据类型设置背景色
    const colors = {
        success: '#52c41a',
        error: '#f5222d',
        info: '#1890ff'
    };
    messageDiv.style.backgroundColor = colors[type] || colors.info;
    
    document.body.appendChild(messageDiv);
    
    // 显示动画
    setTimeout(() => {
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateX(0)';
    }, 100);
    
    // 自动隐藏
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 300);
    }, 3000);
}

/**
 * HTML转义函数
 */
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * 点击模态框外部关闭
 */
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('agent-modal')) {
        e.target.classList.remove('show');
    }
});

console.log('快捷智能体管理脚本加载完成'); 