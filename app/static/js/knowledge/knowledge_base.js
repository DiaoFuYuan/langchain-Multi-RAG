// 知识库管理页面 JavaScript

// 全局变量
let currentTab = 'personal'; // 当前标签页：personal 或 global
let currentPage = 1;
let pageSize = 10;
let totalKnowledgeBases = 0;
let totalPages = 0;
let knowledgeBasesList = [];
let searchTerm = '';
let isLoading = false;

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initKnowledgeBasePage();
    initNotification();
});

// 初始化知识库页面
function initKnowledgeBasePage() {
    setupTabs();
    setupSearch();
    setupCreateButton();
    setupPagination();
    setupModals();
    loadKnowledgeBases();
}

// 设置标签页切换
function setupTabs() {
    const tabs = document.querySelectorAll('.kb-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabType = this.dataset.tab;
            switchTab(tabType);
        });
    });
}

// 切换标签页
function switchTab(tabType) {
    currentTab = tabType;
    currentPage = 1;
    
    // 更新标签页样式
    document.querySelectorAll('.kb-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabType}"]`).classList.add('active');
    
    // 重新加载数据
    loadKnowledgeBases();
}

// 设置搜索功能
function setupSearch() {
    const searchInput = document.querySelector('.kb-search input');
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchTerm = this.value.trim();
            currentPage = 1;
            loadKnowledgeBases();
        }, 300);
    });
}

// 设置新建按钮
function setupCreateButton() {
    const createBtn = document.querySelector('.kb-create-btn');
    createBtn.addEventListener('click', function() {
        showCreateModal();
    });
}

// 设置分页
function setupPagination() {
    // 上一页
    document.querySelector('.kb-page-prev').addEventListener('click', function() {
        if (currentPage > 1 && !this.classList.contains('disabled')) {
            currentPage--;
            loadKnowledgeBases();
        }
    });
    
    // 下一页
    document.querySelector('.kb-page-next').addEventListener('click', function() {
        if (currentPage < totalPages && !this.classList.contains('disabled')) {
            currentPage++;
            loadKnowledgeBases();
        }
    });
    
    // 跳转页面
    const pageInput = document.querySelector('.kb-page-input');
    pageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const page = parseInt(this.value);
            if (page >= 1 && page <= totalPages) {
                currentPage = page;
                loadKnowledgeBases();
            } else {
                this.value = currentPage;
            }
        }
    });
}

// 设置模态框
function setupModals() {
    // 关闭模态框
    document.querySelectorAll('.kb-modal-close, .kb-btn-cancel').forEach(btn => {
        btn.addEventListener('click', function() {
            hideModals();
        });
    });
    
    // 点击背景关闭模态框
    document.querySelectorAll('.kb-modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideModals();
            }
        });
    });
    
    // 创建知识库表单提交
    document.getElementById('createKbForm').addEventListener('submit', function(e) {
        e.preventDefault();
        submitCreateForm();
    });
}

// 加载知识库列表
async function loadKnowledgeBases() {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    try {
        const params = new URLSearchParams({
            tab: currentTab,
            page: currentPage,
            page_size: pageSize,
            search: searchTerm
        });
        
        const response = await fetch(`/knowledge/api/knowledge_bases?${params}`);
        const data = await response.json();
        
        if (data.success) {
            knowledgeBasesList = data.data.knowledge_bases;
            totalKnowledgeBases = data.data.total;
            totalPages = Math.ceil(totalKnowledgeBases / pageSize);
            
            renderKnowledgeBases(knowledgeBasesList);
            updatePagination();
        } else {
            showNotification('加载知识库列表失败：' + data.message, 'error');
        }
    } catch (error) {
        console.error('加载知识库列表失败:', error);
        showNotification('加载知识库列表失败，请稍后重试', 'error');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

// 渲染知识库列表
function renderKnowledgeBases(knowledgeBases) {
    const tbody = document.querySelector('.kb-table-body');
    
    if (knowledgeBases.length === 0) {
        tbody.innerHTML = `
            <div class="kb-empty-state">
                <i class="fas fa-folder-open"></i>
                <h3>暂无知识库</h3>
                <p>点击右上角"新建"按钮创建您的第一个知识库</p>
            </div>
        `;
        return;
    }
    
    tbody.innerHTML = knowledgeBases.map(kb => `
        <div class="kb-table-row" data-id="${kb.id}">
            ${generateRowHTML(kb)}
        </div>
    `).join('');
    
    // 自动加载所有知识库的索引状态
    autoLoadAllIndexStatus(knowledgeBases);
}

// 切换下拉菜单
function toggleDropdown(button) {
    const dropdown = button.nextElementSibling;
    const isOpen = dropdown.classList.contains('show');
    
    // 关闭所有其他下拉菜单
    document.querySelectorAll('.kb-dropdown-menu.show').forEach(menu => {
        menu.classList.remove('show');
    });
    
    // 切换当前下拉菜单
    if (!isOpen) {
        dropdown.classList.add('show');
    }
}

// 点击外部关闭下拉菜单
document.addEventListener('click', function(e) {
    if (!e.target.closest('.kb-action-dropdown')) {
        document.querySelectorAll('.kb-dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});

// 更新分页信息
function updatePagination() {
    // 更新页面信息
    const pageInfo = document.getElementById('pageInfo');
    if (pageInfo) {
        pageInfo.textContent = `共 ${totalKnowledgeBases} 个知识库`;
    }
    
    // 更新当前页码
    const currentPageSpan = document.querySelector('.kb-page-current');
    if (currentPageSpan) {
        currentPageSpan.textContent = currentPage;
    }
    
    // 更新总页数
    const totalPagesSpan = document.getElementById('totalPages');
    if (totalPagesSpan) {
        totalPagesSpan.textContent = `共 ${totalPages} 页`;
    }
    
    // 更新跳转输入框
    const gotoInput = document.querySelector('.kb-page-input');
    if (gotoInput) {
        gotoInput.value = currentPage;
        gotoInput.max = totalPages;
    }
    
    // 更新按钮状态
    const prevBtn = document.querySelector('.kb-page-prev');
    const nextBtn = document.querySelector('.kb-page-next');
    
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

// 显示创建模态框
async function showCreateModal() {
    document.getElementById('createKbModal').classList.add('show');
    document.getElementById('createKbForm').reset();
    await loadEmbeddingModels();
}

// 加载嵌入模型列表
async function loadEmbeddingModels() {
    const embeddingSelect = document.getElementById('embeddingModel');
    
    try {
        // 清空现有选项，只保留默认选项
        embeddingSelect.innerHTML = '<option value="">请选择嵌入模型...</option>';
        
        const response = await fetch('/config/api/model-configs?type=embedding');
        const data = await response.json();
        
        if (data.success && data.data && data.data.length > 0) {
            data.data.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.model_name} (${model.provider})`;
                embeddingSelect.appendChild(option);
            });
        } else {
            // 如果没有可用的embedding模型，显示提示
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '暂无可用的嵌入模型，请先配置';
            option.disabled = true;
            embeddingSelect.appendChild(option);
        }
    } catch (error) {
        console.error('加载嵌入模型失败:', error);
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '加载模型失败，请重试';
        option.disabled = true;
        embeddingSelect.appendChild(option);
    }
}

// 隐藏所有模态框
function hideModals() {
    document.querySelectorAll('.kb-modal').forEach(modal => {
        modal.classList.remove('show');
    });
}

// 提交创建表单
async function submitCreateForm() {
    const form = document.getElementById('createKbForm');
    const formData = new FormData(form);
    
    const embeddingModelId = formData.get('embedding_model_id');
    if (!embeddingModelId) {
        showNotification('请选择嵌入模型', 'error');
        return;
    }
    
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        is_public: formData.get('is_public') === 'on',
        embedding_model_id: parseInt(embeddingModelId)
    };
    
    try {
        const response = await fetch('/knowledge/api/knowledge_bases', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('知识库创建成功', 'success');
            hideModals();
            form.reset();
            loadKnowledgeBases();
        } else {
            showNotification('创建失败：' + result.message, 'error');
        }
    } catch (error) {
        console.error('创建知识库失败:', error);
        showNotification('创建知识库失败，请稍后重试', 'error');
    }
}

// 查看知识库
function viewKnowledgeBase(id) {
    window.location.href = `/knowledge/documents/${id}`;
}

// 编辑知识库 - 改为行内编辑
function editKnowledgeBase(id) {
    const row = document.querySelector(`.kb-table-row[data-id="${id}"]`);
    if (!row) return;
    
    // 如果已经在编辑模式，直接返回
    if (row.classList.contains('editing')) return;
    
    // 获取当前数据
    const kb = knowledgeBasesList.find(item => item.id === id);
    if (!kb) return;
    
    // 保存原始内容
    row.dataset.originalContent = row.innerHTML;
    
    // 切换到编辑模式
    row.classList.add('editing');
    
    // 生成编辑表单
    row.innerHTML = `
        <div class="kb-col kb-col-name">
            <i class="fas fa-folder kb-icon"></i>
            <input type="text" class="kb-edit-input" value="${escapeHtml(kb.name)}" data-field="name">
        </div>
        <div class="kb-col kb-col-description">
            <textarea class="kb-edit-textarea" data-field="description" placeholder="请输入描述">${escapeHtml(kb.description || '')}</textarea>
        </div>
        <div class="kb-col kb-col-permission">
            <select class="kb-permission-select" data-field="is_public">
                <option value="true" ${kb.is_public ? 'selected' : ''}>公共可访问</option>
                <option value="false" ${!kb.is_public ? 'selected' : ''}>私有</option>
            </select>
        </div>
        <div class="kb-col kb-col-type">
            <input type="text" class="kb-edit-input" value="${escapeHtml(kb.type || '通用')}" data-field="type">
        </div>
        <div class="kb-col kb-col-actions">
            <div class="kb-edit-actions">
                <button class="kb-edit-btn save" onclick="saveKnowledgeBase(${id})">
                    <i class="fas fa-check"></i>
                    保存
                </button>
                <button class="kb-edit-btn cancel" onclick="cancelEdit(${id})">
                    <i class="fas fa-times"></i>
                    取消
                </button>
            </div>
        </div>
    `;
    
    // 关闭其他可能打开的下拉菜单
    document.querySelectorAll('.kb-dropdown-menu.show').forEach(menu => {
        menu.classList.remove('show');
    });
}

// 保存知识库编辑
async function saveKnowledgeBase(id) {
    const row = document.querySelector(`.kb-table-row[data-id="${id}"]`);
    if (!row) return;
    
    // 收集表单数据
    const formData = {};
    row.querySelectorAll('[data-field]').forEach(input => {
        const field = input.dataset.field;
        if (field === 'is_public') {
            formData[field] = input.value === 'true';
        } else {
            formData[field] = input.value.trim();
        }
    });
    
    // 验证必填字段
    if (!formData.name) {
        showNotification('知识库名称不能为空', 'error');
        return;
    }
    
    try {
        // 显示保存状态
        const saveBtn = row.querySelector('.kb-edit-btn.save');
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
        saveBtn.disabled = true;
        
        const response = await fetch(`/knowledge/api/knowledge_bases/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('知识库更新成功', 'success');
            // 更新本地数据
            const kbIndex = knowledgeBasesList.findIndex(item => item.id === id);
            if (kbIndex !== -1) {
                knowledgeBasesList[kbIndex] = { ...knowledgeBasesList[kbIndex], ...formData };
            }
            // 退出编辑模式并刷新显示
            exitEditMode(id);
        } else {
            showNotification('更新失败：' + result.message, 'error');
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    } catch (error) {
        console.error('更新知识库失败:', error);
        showNotification('更新知识库失败，请稍后重试', 'error');
        const saveBtn = row.querySelector('.kb-edit-btn.save');
        saveBtn.innerHTML = '<i class="fas fa-check"></i> 保存';
        saveBtn.disabled = false;
    }
}

// 取消编辑
function cancelEdit(id) {
    const row = document.querySelector(`.kb-table-row[data-id="${id}"]`);
    if (!row) return;
    
    // 恢复原始内容
    if (row.dataset.originalContent) {
        row.innerHTML = row.dataset.originalContent;
        delete row.dataset.originalContent;
    }
    
    // 移除编辑模式
    row.classList.remove('editing');
}

// 退出编辑模式
function exitEditMode(id) {
    const row = document.querySelector(`.kb-table-row[data-id="${id}"]`);
    if (!row) return;
    
    // 移除编辑模式
    row.classList.remove('editing');
    delete row.dataset.originalContent;
    
    // 重新渲染这一行
    const kb = knowledgeBasesList.find(item => item.id === id);
    if (kb) {
        row.innerHTML = generateRowHTML(kb);
    }
}

// 生成单行HTML的辅助函数
function generateRowHTML(kb) {
    return `
        <div class="kb-col kb-col-name">
            <i class="fas fa-folder kb-icon"></i>
            <span class="kb-name-link" onclick="viewKnowledgeBase(${kb.id})">${escapeHtml(kb.name)}</span>
        </div>
        <div class="kb-col kb-col-description">
            ${escapeHtml(kb.description || '暂无描述')}
        </div>
        <div class="kb-col kb-col-permission">
            <span class="kb-permission-badge ${kb.is_public ? '' : 'private'}">
                <i class="fas fa-${kb.is_public ? 'users' : 'lock'}"></i>
                ${kb.is_public ? '公共可访问' : '私有'}
            </span>
        </div>
        <div class="kb-col kb-col-embedding">
            ${generateEmbeddingBadge(kb.embedding_model_name || kb.embedding_model)}
        </div>
        <div class="kb-col kb-col-hierarchical">
            ${generateHierarchicalStatusBadge(kb)}
        </div>
        <div class="kb-col kb-col-actions">
            <div class="kb-action-dropdown">
                <button class="kb-action-btn" onclick="toggleDropdown(this)">
                    操作
                    <i class="fas fa-chevron-down"></i>
                </button>
                <div class="kb-dropdown-menu">
                    <div class="kb-dropdown-item" onclick="viewKnowledgeBase(${kb.id})">
                        <i class="fas fa-eye"></i>
                        查看
                    </div>
                    <div class="kb-dropdown-item" onclick="editKnowledgeBase(${kb.id})">
                        <i class="fas fa-edit"></i>
                        编辑
                    </div>
                    <div class="kb-dropdown-item danger" onclick="deleteKnowledgeBase(${kb.id}, '${escapeHtml(kb.name)}')">
                        <i class="fas fa-trash"></i>
                        删除
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 删除知识库
function deleteKnowledgeBase(id, name) {
    if (confirm(`确定要删除知识库"${name}"吗？此操作不可恢复。`)) {
        performDelete(id);
    }
}

// 执行删除操作
async function performDelete(id) {
    try {
        const response = await fetch(`/knowledge/api/knowledge_bases/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('知识库删除成功', 'success');
            hideModals();
            loadKnowledgeBases();
        } else {
            showNotification('删除失败：' + result.message, 'error');
        }
    } catch (error) {
        console.error('删除知识库失败:', error);
        showNotification('删除知识库失败，请稍后重试', 'error');
    }
}

// 显示加载状态
function showLoading() {
    const tbody = document.querySelector('.kb-table-body');
    tbody.innerHTML = `
        <div class="kb-loading">
            <i class="fas fa-spinner"></i>
            加载中...
        </div>
    `;
}

// 隐藏加载状态
function hideLoading() {
    // 加载状态会被渲染结果替换，无需特殊处理
}

// 通知系统
function initNotification() {
    // 通知功能已移至公共组件 app/static/js/common/notification.js
    // 确保通知容器存在
    if (!document.querySelector('#notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 生成嵌入模型标签
function generateEmbeddingBadge(modelName) {
    if (!modelName || modelName === '未配置') {
        return '<span class="kb-embedding-badge unconfigured">未配置</span>';
    }
    
    // 去掉括号内容
    const cleanName = modelName.replace(/\s*\([^)]*\)/g, '').trim();
    
    return `<span class="kb-embedding-badge">${escapeHtml(cleanName)}</span>`;
}

// 自动加载所有知识库的索引状态
async function autoLoadAllIndexStatus(knowledgeBases) {
    // 为每个没有索引状态的知识库自动加载状态
    const loadPromises = knowledgeBases
        .filter(kb => !kb.hierarchical_status)
        .map(kb => loadHierarchicalStatusSilently(kb.id, kb.name));
    
    // 并发加载所有状态
    await Promise.allSettled(loadPromises);
}

// 静默加载索引状态（不显示加载提示）
async function loadHierarchicalStatusSilently(kbId, kbName) {
    try {
        const response = await fetch(`/knowledge/api/documents/hierarchical-status?kb_name=${encodeURIComponent(kbName)}`);
        const result = await response.json();
        
        if (result.success) {
            // 更新知识库数据
            const kbIndex = knowledgeBasesList.findIndex(kb => kb.id === kbId);
            if (kbIndex !== -1) {
                knowledgeBasesList[kbIndex].hierarchical_status = result.data;
                
                // 重新渲染这一行
                const row = document.querySelector(`[data-id="${kbId}"]`);
                if (row) {
                    row.innerHTML = generateRowHTML(knowledgeBasesList[kbIndex]);
                }
            }
        }
    } catch (error) {
        console.error(`加载知识库 ${kbName} 的索引状态失败:`, error);
    }
}

// 生成索引状态标签（包含普通索引和分层索引）
function generateHierarchicalStatusBadge(kb) {
    // 如果没有索引状态信息，显示加载状态
    if (!kb.hierarchical_status) {
        return '<span class="kb-index-badge loading" title="正在加载索引状态..."><i class="fas fa-spinner fa-spin"></i> 加载中...</span>';
    }
    
    const status = kb.hierarchical_status;
    const normalExists = status.normal_index_exists;
    const hierarchicalExists = status.hierarchical_index_exists;
    
    if (status.doc_count === 0) {
        return '<span class="kb-index-badge empty" title="知识库为空"><i class="fas fa-folder-open"></i> 无文档</span>';
    }
    
    // 生成索引状态显示
    let badgeHTML = '<div class="kb-index-status">';
    
    // 普通索引状态
    if (normalExists) {
        badgeHTML += '<span class="index-badge normal ready" title="普通索引已构建"><i class="fas fa-database"></i> 普通</span>';
    } else {
        badgeHTML += '<span class="index-badge normal missing" title="普通索引未构建"><i class="fas fa-database"></i> 普通</span>';
    }
    
    // 分层索引状态
    if (hierarchicalExists) {
        badgeHTML += '<span class="index-badge hierarchical ready" title="分层索引已构建，文档数: ' + status.doc_count + ', 分组数: ' + status.group_count + '"><i class="fas fa-sitemap"></i> 分层</span>';
    } else {
        badgeHTML += '<span class="index-badge hierarchical pending" onclick="rebuildHierarchicalIndex(' + kb.id + ', \'' + escapeHtml(kb.name) + '\')" title="点击构建分层索引，文档数: ' + status.doc_count + '"><i class="fas fa-sitemap"></i> 分层</span>';
    }
    
    badgeHTML += '</div>';
    return badgeHTML;
}

// 加载分层索引状态
async function loadHierarchicalStatus(kbId, kbName) {
    try {
        // 更新按钮状态
        const badge = document.querySelector(`[data-id="${kbId}"] .kb-hierarchical-badge, [data-id="${kbId}"] .kb-index-badge`);
        if (badge) {
            badge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 检查中...';
            badge.classList.add('loading');
        }
        
        const response = await fetch(`/knowledge/api/documents/hierarchical-status?kb_name=${encodeURIComponent(kbName)}`);
        const result = await response.json();
        
        if (result.success) {
            // 更新知识库数据
            const kbIndex = knowledgeBasesList.findIndex(kb => kb.id === kbId);
            if (kbIndex !== -1) {
                knowledgeBasesList[kbIndex].hierarchical_status = result.data;
                
                // 重新渲染这一行
                const row = document.querySelector(`[data-id="${kbId}"]`);
                if (row) {
                    row.innerHTML = generateRowHTML(knowledgeBasesList[kbIndex]);
                }
            }
        } else {
            showNotification('获取索引状态失败：' + result.message, 'error');
            if (badge) {
                badge.innerHTML = '<i class="fas fa-exclamation-circle"></i> 检查失败';
                badge.classList.remove('loading');
                badge.classList.add('error');
            }
        }
    } catch (error) {
        console.error('获取索引状态失败:', error);
        showNotification('获取索引状态失败，请稍后重试', 'error');
        const badge = document.querySelector(`[data-id="${kbId}"] .kb-hierarchical-badge, [data-id="${kbId}"] .kb-index-badge`);
        if (badge) {
            badge.innerHTML = '<i class="fas fa-exclamation-circle"></i> 检查失败';
            badge.classList.remove('loading');
            badge.classList.add('error');
        }
    }
}

// 重建分层索引
async function rebuildHierarchicalIndex(kbId, kbName) {
    if (!confirm(`确定要为知识库"${kbName}"构建分层索引吗？\n\n这可能需要一些时间，请耐心等待。`)) {
        return;
    }
    
    try {
        // 更新按钮状态
        const badge = document.querySelector(`[data-id="${kbId}"] .kb-hierarchical-badge, [data-id="${kbId}"] .kb-index-badge`);
        if (badge) {
            badge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 构建中...';
            badge.classList.add('building');
            badge.onclick = null; // 禁用点击
        }
        
        const formData = new FormData();
        formData.append('kb_name', kbName);
        
        const response = await fetch('/knowledge/api/documents/rebuild-hierarchical-index', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('分层索引构建成功', 'success');
            // 重新加载状态
            await loadHierarchicalStatus(kbId, kbName);
        } else {
            showNotification('分层索引构建失败：' + result.message, 'error');
            if (badge) {
                badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 构建失败';
                badge.classList.remove('building');
                badge.classList.add('error');
                // 恢复点击事件
                badge.onclick = () => rebuildHierarchicalIndex(kbId, kbName);
            }
        }
    } catch (error) {
        console.error('构建分层索引失败:', error);
        showNotification('构建分层索引失败，请稍后重试', 'error');
        const badge = document.querySelector(`[data-id="${kbId}"] .kb-hierarchical-badge, [data-id="${kbId}"] .kb-index-badge`);
        if (badge) {
            badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> 构建失败';
            badge.classList.remove('building');
            badge.classList.add('error');
            // 恢复点击事件
            badge.onclick = () => rebuildHierarchicalIndex(kbId, kbName);
        }
    }
}

// 通知相关的CSS动画已移至公共样式文件 app/static/css/common/notification.css