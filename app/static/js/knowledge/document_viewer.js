// 文档查看器的JavaScript逻辑
let currentKbId = null;
let currentKbName = null;
let documentsList = [];
let currentPage = 1;
let limit = 10;
let totalPages = 1;
let totalDocs = 0;
let searchKeyword = '';

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 从URL获取知识库ID和名称
    initializeFromUrl();
    
    // 初始化事件监听器
    initEventListeners();
    
    // 加载文档列表
    loadDocumentsList();
    
    // 延迟启动状态监控，等待初始加载完成
    setTimeout(startStatusMonitoring, 1000);
    
    // 延迟检查分层索引状态
    setTimeout(checkHierarchicalIndexStatus, 2000);
    
    // 启动实时分层索引状态监控
    setTimeout(startRealtimeHierarchicalStatusMonitoring, 3000);
});

// 从URL和模板变量获取知识库信息
function initializeFromUrl() {
    // 从URL获取知识库ID
    const urlParams = new URLSearchParams(window.location.search);
    
    // 尝试从URL获取kb_id
    let kbIdFromUrl = window.location.pathname.match(/\/documents\/(\d+)/);
    if (kbIdFromUrl && kbIdFromUrl[1]) {
        currentKbId = parseInt(kbIdFromUrl[1]);
        console.log('从URL获取到知识库ID:', currentKbId);
    }
    
    // 尝试从模板传递的变量获取知识库名称
    const kbNameElement = document.getElementById('currentKbName');
    if (kbNameElement && kbNameElement.dataset.kbName) {
        currentKbName = kbNameElement.dataset.kbName.trim();
        if (currentKbName) {
            kbNameElement.textContent = currentKbName;
            console.log('从模板获取到知识库名称:', currentKbName);
            return; // 如果成功获取到名称，直接返回
        }
    }
    
    // 如果模板中没有知识库名称，尝试通过API获取
    if (currentKbId) {
        console.log('模板中没有知识库名称，尝试通过API获取...');
        fetchKnowledgeBaseInfo(currentKbId);
    } else {
        // 如果连ID都没有，尝试从URL路径中提取知识库名称
        console.warn('无法获取知识库ID，尝试其他方式...');
        handleMissingKnowledgeBaseInfo();
    }
}

// 处理缺少知识库信息的情况
function handleMissingKnowledgeBaseInfo() {
    // 显示错误信息
    showNotification('知识库信息获取失败，请返回知识库列表重新选择', 'error');
    
    // 3秒后自动跳转到知识库列表页面
    setTimeout(() => {
        window.location.href = '/knowledge/knowledge_base';
    }, 3000);
}

// 获取知识库详细信息
async function fetchKnowledgeBaseInfo(kbId) {
    try {
        console.log('正在获取知识库信息，ID:', kbId);
        const response = await fetch(`/knowledge/api/knowledge_bases/${kbId}`);
        
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.data) {
                currentKbName = result.data.name;
                const kbNameElement = document.getElementById('currentKbName');
                if (kbNameElement) {
                    kbNameElement.textContent = currentKbName;
                }
                console.log('成功获取知识库信息:', currentKbName);
            } else {
                console.error('API返回失败:', result);
                handleKnowledgeBaseNotFound(kbId);
            }
        } else {
            console.error('API请求失败，状态码:', response.status);
            if (response.status === 404) {
                handleKnowledgeBaseNotFound(kbId);
            } else {
                showNotification('获取知识库信息失败', 'error');
                handleMissingKnowledgeBaseInfo();
            }
        }
    } catch (error) {
        console.error('获取知识库信息失败:', error);
        showNotification('获取知识库信息失败', 'error');
        handleMissingKnowledgeBaseInfo();
    }
}

// 处理知识库不存在的情况
function handleKnowledgeBaseNotFound(kbId) {
    console.warn('知识库不存在，ID:', kbId);
    showNotification(`知识库 (ID: ${kbId}) 不存在，可能已被删除`, 'warning');
    
    // 3秒后自动跳转到知识库列表页面
    setTimeout(() => {
        window.location.href = '/knowledge/knowledge_base';
    }, 3000);
}

// 初始化事件监听器
function initEventListeners() {
    // 返回按钮
    document.getElementById('backToKnowledgeBase').addEventListener('click', function() {
        window.location.href = '/knowledge/knowledge_base';
    });
    
    // 上传按钮
    document.getElementById('uploadDocumentBtn').addEventListener('click', function() {
        console.log('上传按钮被点击');
        console.log('window.uploadManager:', window.uploadManager);
        console.log('currentKbName:', currentKbName);
        
        // 打开上传文档模态框
        if (window.uploadManager && currentKbName) {
            console.log('条件满足，打开上传模态框');
            window.uploadManager.openUploadModal(currentKbName);
        } else {
            console.log('条件不满足，显示错误通知');
            if (!window.uploadManager) {
                console.error('uploadManager 不存在');
            }
            if (!currentKbName) {
                console.error('currentKbName 为空:', currentKbName);
            }
            showNotification('无法打开上传界面：缺少知识库信息', 'error');
        }
    });
    
    // 搜索功能
    const searchInput = document.querySelector('.doc-search input');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            searchKeyword = e.target.value.trim();
        });
        
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                currentPage = 1;
                loadDocumentsList();
            }
        });
    }
    
    // 模态框关闭按钮
    document.querySelectorAll('.doc-modal-close, .doc-btn-cancel').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.doc-modal');
            if (modal) {
                modal.classList.remove('show');
            }
        });
    });
    
    // 分页按钮事件监听器
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const gotoPageInput = document.getElementById('gotoPageInput');
    
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', function() {
            if (!this.classList.contains('disabled') && currentPage > 1) {
                currentPage--;
                loadDocumentsList();
            }
        });
    }
    
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', function() {
            if (!this.classList.contains('disabled') && currentPage < totalPages) {
                currentPage++;
                loadDocumentsList();
            }
        });
    }
    
    // 跳转页面输入框
    if (gotoPageInput) {
        gotoPageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const page = parseInt(this.value);
                if (page >= 1 && page <= totalPages) {
                    currentPage = page;
                    loadDocumentsList();
                } else {
                    this.value = currentPage;
                }
            }
        });
    }
}

// 加载文档列表
async function loadDocumentsList() {
    if (!currentKbId && !currentKbName) {
        showNotification('无法加载文档：缺少知识库信息', 'error');
        return;
    }
    
    try {
        // 显示加载状态
        const docTableBody = document.querySelector('.doc-table-body');
        if (docTableBody) {
            docTableBody.innerHTML = `
                <div class="doc-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>正在加载文档...</span>
                </div>
            `;
        }
        
        // 构建API URL
        let apiUrl = `/knowledge/api/documents/list?page=${currentPage}&limit=${limit}`;
        
        // 添加知识库参数
        if (currentKbName) {
            apiUrl += `&kb_name=${encodeURIComponent(currentKbName)}`;
        } else if (currentKbId) {
            apiUrl += `&kb_id=${currentKbId}`;
        }
        
        // 添加搜索参数
        if (searchKeyword) {
            apiUrl += `&search=${encodeURIComponent(searchKeyword)}`;
        }
        
        const response = await fetch(apiUrl);
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                documentsList = result.data || [];
                totalDocs = result.pagination?.total || 0;
                totalPages = result.pagination?.total_pages || 1;
                
                // 更新文档列表UI
                renderDocumentsList();
                
                // 更新分页组件
                updatePagination();
                
                // 如果有分层索引状态，重新渲染文档列表以更新分层索引列
                if (window.hierarchicalIndexStatus) {
                    renderDocumentsList();
                }
            } else {
                showNotification('加载文档列表失败: ' + (result.message || '未知错误'), 'error');
                renderEmptyState('加载失败', result.message || '加载文档列表时发生错误');
            }
        } else {
            showNotification('加载文档列表失败: 服务器错误', 'error');
            renderEmptyState('服务器错误', '加载文档列表时发生服务器错误');
        }
    } catch (error) {
        console.error('加载文档列表失败:', error);
        showNotification('加载文档列表失败', 'error');
        renderEmptyState('加载错误', '加载文档列表时发生错误');
    }
}

// 渲染文档列表
function renderDocumentsList() {
    const docTableBody = document.querySelector('.doc-table-body');
    if (!docTableBody) return;
    
    if (documentsList.length === 0) {
        renderEmptyState();
        return;
    }
    
    let html = '';
    
    documentsList.forEach(doc => {
        // 确定文档图标类型
        let iconClass = 'fa-file-alt';
        let iconTypeClass = '';
        
        if (doc.file_type) {
            const fileType = doc.file_type.toLowerCase();
            if (fileType.includes('pdf')) {
                iconClass = 'fa-file-pdf';
                iconTypeClass = 'icon-pdf';
            } else if (fileType.includes('word') || fileType.includes('docx')) {
                iconClass = 'fa-file-word';
                iconTypeClass = 'icon-word';
            } else if (fileType.includes('excel') || fileType.includes('xlsx')) {
                iconClass = 'fa-file-excel';
                iconTypeClass = 'icon-excel';
            } else if (fileType.includes('image') || fileType.includes('png') || fileType.includes('jpg')) {
                iconClass = 'fa-file-image';
                iconTypeClass = 'icon-image';
            }
        }
        
        // 确定文档状态
        let statusHtml = '';
        const vectorStatus = doc.vector_status || doc.status; // 兼容两种字段名
        
        if (vectorStatus) {
            const status = vectorStatus.toLowerCase();
            if (status === 'processing') {
                statusHtml = `<div class="doc-status processing"><i class="fas fa-spinner fa-spin"></i> 处理中</div>`;
            } else if (status === 'completed') {
                statusHtml = `<div class="doc-status completed"><i class="fas fa-check-circle"></i> 已完成</div>`;
            } else if (status === 'waiting' || status === 'pending') {
                statusHtml = `<div class="doc-status pending"><i class="fas fa-clock"></i> 等待中</div>`;
            } else if (status === 'error') {
                statusHtml = `<div class="doc-status error"><i class="fas fa-exclamation-circle"></i> 错误</div>`;
            } else {
                statusHtml = `<div class="doc-status"><i class="fas fa-question-circle"></i> ${escapeHtml(vectorStatus)}</div>`;
            }
        } else {
            // 如果没有状态信息，根据has_vector判断
            if (doc.has_vector) {
                statusHtml = `<div class="doc-status completed"><i class="fas fa-check-circle"></i> 已完成</div>`;
            } else {
                statusHtml = `<div class="doc-status pending"><i class="fas fa-clock"></i> 等待中</div>`;
            }
        }
        
        // 获取分层索引状态
        const hierarchicalStatusHtml = getHierarchicalStatusHtml(doc);
        
        html += `
            <div class="doc-table-row" data-id="${doc.id}">
                <div class="doc-col">
                    <div class="doc-name-cell">
                        <i class="fas ${iconClass} doc-icon ${iconTypeClass}"></i>
                        <span class="doc-name">${escapeHtml(doc.filename || '未命名文档')}</span>
                    </div>
                </div>
                <div class="doc-col">
                    ${escapeHtml(doc.description || '暂无介绍')}
                </div>
                <div class="doc-col">
                    ${escapeHtml(doc.file_type || '未知类型')}
                </div>
                <div class="doc-col">
                    ${formatDateTime(doc.upload_time)}
                </div>
                <div class="doc-col">
                    ${hierarchicalStatusHtml}
                </div>
                <div class="doc-col">
                    ${statusHtml}
                </div>
                <div class="doc-col">
                    <div class="doc-action-buttons">
                        <button class="doc-action-btn" onclick="viewDocument('${doc.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="doc-action-btn doc-download-btn" onclick="downloadDocument('${doc.id}')">
                            <i class="fas fa-download"></i>
                        </button>
                        ${doc.vector_status === 'error' ? `
                        <button class="doc-action-btn doc-retry-btn" onclick="retryVectorizeDocument('${doc.id}', '${escapeHtml(doc.filename || '未命名文档')}')" title="重新向量化">
                            <i class="fas fa-redo"></i>
                        </button>
                        ` : ''}
                        <button class="doc-action-btn doc-delete-btn" onclick="confirmDeleteDocument('${doc.id}', '${escapeHtml(doc.filename || '未命名文档')}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    docTableBody.innerHTML = html;
    updateProcessingQueue();
}

// 获取分层索引状态HTML
function getHierarchicalStatusHtml(doc) {
    // 检查全局分层索引状态
    const globalHierarchicalStatus = window.hierarchicalIndexStatus;
    
    if (!globalHierarchicalStatus) {
        return `<div class="hierarchical-status-cell checking"><i class="fas fa-spinner"></i> 检查中</div>`;
    }
    
    // 如果分层索引不存在，显示不可用
    if (!globalHierarchicalStatus.hierarchical_index_exists) {
        return `<div class="hierarchical-status-cell unavailable"><i class="fas fa-times-circle"></i> 不可用</div>`;
    }
    
    // 如果文档向量化未完成，显示等待中
    const vectorStatus = doc.vector_status || doc.status;
    if (vectorStatus && vectorStatus.toLowerCase() !== 'completed' && !doc.has_vector) {
        return `<div class="hierarchical-status-cell checking"><i class="fas fa-clock"></i> 等待中</div>`;
    }
    
    // 如果分层索引存在且文档已向量化，显示可用
    return `<div class="hierarchical-status-cell available"><i class="fas fa-layer-group"></i> 可用</div>`;
}

// 启动实时状态监控
function startRealtimeHierarchicalStatusMonitoring() {
    // 每5秒检查一次分层索引状态
    setInterval(async () => {
        await checkHierarchicalIndexStatus();
    }, 5000);
}

// 渲染空状态
function renderEmptyState(title = '没有文档', message = '当前知识库中还没有文档，请点击上传按钮添加文档') {
    const docTableBody = document.querySelector('.doc-table-body');
    if (!docTableBody) return;
    
    docTableBody.innerHTML = `
        <div class="doc-empty-state">
            <i class="fas fa-file-alt"></i>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

// 更新分页组件
function updatePagination() {
    // 更新页面信息
    const pageInfo = document.getElementById('pageInfo');
    if (pageInfo) {
        pageInfo.textContent = `共 ${totalDocs} 个文档`;
    }
    
    // 更新当前页码
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

// 文档操作下拉菜单
function toggleDocDropdown(button) {
    // 关闭所有其他下拉菜单
    document.querySelectorAll('.doc-dropdown-menu.show').forEach(menu => {
        if (menu !== button.nextElementSibling) {
            menu.classList.remove('show');
        }
    });
    
    // 切换当前下拉菜单
    const dropdown = button.nextElementSibling;
    dropdown.classList.toggle('show');
    
    // 添加点击外部关闭下拉菜单的事件
    if (dropdown.classList.contains('show')) {
        setTimeout(() => {
            document.addEventListener('click', closeOnClickOutside);
        }, 0);
    }
    
    function closeOnClickOutside(e) {
        if (!dropdown.contains(e.target) && !button.contains(e.target)) {
            dropdown.classList.remove('show');
            document.removeEventListener('click', closeOnClickOutside);
        }
    }
}

// 查看文档
function viewDocument(docId) {
    const doc = documentsList.find(d => d.id == docId);
    if (doc) {
        showNotification(`查看文档: ${doc.filename}`, 'info');
        // 这里实现查看文档的逻辑
    }
}

// 下载文档
function downloadDocument(docId) {
    const doc = documentsList.find(d => d.id == docId);
    if (doc) {
        showNotification(`下载文档: ${doc.filename}`, 'info');
        // 这里实现下载文档的逻辑
    }
}

// 确认删除文档
function confirmDeleteDocument(docId, filename) {
    const confirmModal = document.getElementById('confirmActionModal');
    const confirmTitle = document.getElementById('confirmModalTitle');
    const confirmMessage = document.getElementById('confirmModalMessage');
    const confirmButton = document.getElementById('confirmActionBtn');
    
    if (confirmModal && confirmTitle && confirmMessage && confirmButton) {
        confirmTitle.textContent = '确认删除文档';
        confirmMessage.textContent = `您确定要删除文档 "${filename}" 吗？此操作不可恢复。`;
        
        // 设置确认按钮的点击事件
        confirmButton.onclick = function() {
            deleteDocument(docId);
            confirmModal.classList.remove('show');
        };
        
        // 显示模态框
        confirmModal.classList.add('show');
    }
}

// 删除文档
async function deleteDocument(docId) {
    try {
        const response = await fetch(`/knowledge/api/documents/delete/${docId}?kb_name=${encodeURIComponent(currentKbName)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('文档删除成功', 'success');
            // 重新加载文档列表
            loadDocumentsList();
        } else {
            showNotification('删除文档失败: ' + (result.message || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('删除文档失败:', error);
        showNotification('删除文档失败', 'error');
    }
}

// 重试向量化文档
function retryVectorizeDocument(docId, filename) {
    const confirmModal = document.getElementById('confirmActionModal');
    const confirmTitle = document.getElementById('confirmModalTitle');
    const confirmMessage = document.getElementById('confirmModalMessage');
    const confirmButton = document.getElementById('confirmActionBtn');
    
    if (confirmModal && confirmTitle && confirmMessage && confirmButton) {
        confirmTitle.textContent = '确认重新向量化';
        confirmMessage.textContent = `您确定要重新向量化文档 "${filename}" 吗？这将重新处理该文档并生成新的向量数据。`;
        
        // 修改确认按钮样式为主要按钮
        confirmButton.className = 'doc-btn doc-btn-primary';
        confirmButton.textContent = '确认重试';
        
        // 设置确认按钮的点击事件
        confirmButton.onclick = function() {
            executeRetryVectorize(docId);
            confirmModal.classList.remove('show');
            // 恢复按钮样式
            confirmButton.className = 'doc-btn doc-btn-danger';
            confirmButton.textContent = '确认';
        };
        
        // 显示模态框
        confirmModal.classList.add('show');
    }
}

// 执行重试向量化
async function executeRetryVectorize(docId) {
    try {
        showNotification('开始重新向量化文档...', 'info');
        
        const response = await fetch(`/knowledge/api/documents/re-vectorize/${docId}?kb_name=${encodeURIComponent(currentKbName)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('文档已添加到重新处理队列', 'success');
            // 重新加载文档列表以更新状态
            loadDocumentsList();
        } else {
            showNotification('重新向量化失败: ' + (result.message || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('重新向量化失败:', error);
        showNotification('重新向量化失败', 'error');
    }
}

// 格式化日期时间
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '未知时间';
    
    try {
        const date = new Date(dateTimeStr);
        
        if (isNaN(date.getTime())) {
            return dateTimeStr; // 如果无法解析，返回原始字符串
        }
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch (error) {
        console.error('格式化日期时间错误:', error);
        return dateTimeStr;
    }
}

// 转义HTML
function escapeHtml(text) {
    if (!text) return '';
    
    return text
        .toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// 队列状态管理
function updateProcessingQueue() {
    if (!documentsList || documentsList.length === 0) {
        hideProcessingQueue();
        return;
    }
    
    // 统计各种状态的文档数量
    const statusCounts = {
        waiting: 0,
        processing: 0,
        completed: 0,
        error: 0
    };
    
    documentsList.forEach(doc => {
        const vectorStatus = doc.vector_status || doc.status;
        if (vectorStatus) {
            const status = vectorStatus.toLowerCase();
            if (status === 'waiting' || status === 'pending') {
                statusCounts.waiting++;
            } else if (status === 'processing') {
                statusCounts.processing++;
            } else if (status === 'completed') {
                statusCounts.completed++;
            } else if (status === 'error') {
                statusCounts.error++;
            }
        } else {
            // 如果没有状态信息，根据has_vector判断
            if (doc.has_vector) {
                statusCounts.completed++;
            } else {
                statusCounts.waiting++;
            }
        }
    });
    
    // 计算待处理文档数量（等待中 + 处理中）
    const pendingCount = statusCounts.waiting + statusCounts.processing;
    
    if (pendingCount > 0) {
        showProcessingQueue(pendingCount, statusCounts);
    } else {
        hideProcessingQueue();
    }
}

function showProcessingQueue(pendingCount, statusCounts) {
    const queueElement = document.getElementById('processingQueue');
    const countElement = document.getElementById('queueCount');
    
    if (queueElement && countElement) {
        countElement.textContent = pendingCount;
        queueElement.style.display = 'inline-flex';
        
        // 更新队列元素的标题，显示详细信息
        const title = `等待中: ${statusCounts.waiting}个, 处理中: ${statusCounts.processing}个`;
        queueElement.title = title;
    }
}

function hideProcessingQueue() {
    const queueElement = document.getElementById('processingQueue');
    if (queueElement) {
        queueElement.style.display = 'none';
    }
}

// 自动状态检查
let statusCheckInterval = null;

function startStatusMonitoring() {
    // 清除之前的定时器
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // 每3秒检查一次状态
    statusCheckInterval = setInterval(async () => {
        // 只有在有待处理文档时才自动刷新
        if (hasPendingDocuments()) {
            await loadDocumentsList();
        }
    }, 3000);
}

function stopStatusMonitoring() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

function hasPendingDocuments() {
    if (!documentsList || documentsList.length === 0) {
        return false;
    }
    
    return documentsList.some(doc => {
        const vectorStatus = doc.vector_status || doc.status;
        if (vectorStatus) {
            const status = vectorStatus.toLowerCase();
            return status === 'waiting' || status === 'pending' || status === 'processing';
        } else {
            return !doc.has_vector;
        }
    });
}

// 页面卸载时停止监控
window.addEventListener('beforeunload', function() {
    stopStatusMonitoring();
});

// 分层索引状态管理
async function checkHierarchicalIndexStatus() {
    if (!currentKbName) {
        console.warn('无法检查分层索引状态：知识库名称为空');
        return;
    }
    
    try {
        // 使用实时API，不依赖缓存
        const response = await fetch(`/knowledge/api/documents/hierarchical-status-realtime?kb_name=${encodeURIComponent(currentKbName)}`);
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                updateHierarchicalIndexDisplay(result.data);
            }
        }
    } catch (error) {
        console.error('检查分层索引状态失败:', error);
    }
}

function updateHierarchicalIndexDisplay(statusData) {
    // 保存状态到全局变量，供文档列表使用
    window.hierarchicalIndexStatus = statusData;
    
    const statusElement = document.getElementById('hierarchicalStatus');
    const statusTextElement = document.getElementById('hierarchicalStatusText');
    const rebuildBtnElement = document.getElementById('rebuildHierarchicalBtn');
    
    if (!statusElement || !statusTextElement) {
        return;
    }
    
    // 重置所有状态类
    statusElement.className = 'hierarchical-status';
    
    // 根据文档数量和状态决定显示内容
    const docCount = statusData.doc_count || 0;
    const hierarchicalExists = statusData.hierarchical_exists;
    const recommendation = statusData.retriever_recommendation;
    
    let statusClass = '';
    let statusText = '';
    let tooltip = '';
    let showRebuildBtn = false;
    
    if (docCount === 0) {
        // 没有文档
        statusClass = 'status-disabled';
        statusText = '无文档';
        tooltip = '知识库中没有文档，无需分层索引';
    } else if (docCount <= 100) {
        // 文档较少，不需要分层索引
        statusClass = 'status-disabled';
        statusText = '向量检索';
        tooltip = `文档数量较少(${docCount}个)，建议使用向量检索`;
    } else if (docCount <= 300) {
        // 中等数量文档，建议关键词组合检索
        statusClass = 'status-warning';
        statusText = '关键词检索';
        tooltip = `文档数量适中(${docCount}个)，建议使用关键词组合检索`;
    } else {
        // 大量文档，需要分层索引
        if (hierarchicalExists) {
            statusClass = 'status-good';
            statusText = '分层索引已启用';
            tooltip = `文档数量较多(${docCount}个)，分层索引已建立，检索性能最佳`;
            showRebuildBtn = true;
        } else {
            statusClass = 'status-error';
            statusText = '需要分层索引';
            tooltip = `文档数量较多(${docCount}个)，建议建立分层索引以提升检索性能`;
            showRebuildBtn = true;
        }
    }
    
    // 更新UI
    statusElement.classList.add(statusClass);
    statusElement.setAttribute('data-tooltip', tooltip);
    statusTextElement.textContent = statusText;
    
    if (rebuildBtnElement) {
        rebuildBtnElement.style.display = showRebuildBtn ? 'inline-block' : 'none';
        rebuildBtnElement.onclick = () => triggerHierarchicalRebuild();
    }
    
    // 显示状态元素
    statusElement.style.display = 'inline-flex';
    
    // 重新渲染文档列表以更新分层索引列
    if (documentsList && documentsList.length > 0) {
        renderDocumentsList();
    }
}

async function triggerHierarchicalRebuild() {
    if (!currentKbName) {
        showNotification('无法重建分层索引：知识库名称为空', 'error');
        return;
    }
    
    // 确认对话框
    if (!confirm('确定要重建分层索引吗？这可能需要几分钟时间。')) {
        return;
    }
    
    const statusElement = document.getElementById('hierarchicalStatus');
    const statusTextElement = document.getElementById('hierarchicalStatusText');
    const rebuildBtnElement = document.getElementById('rebuildHierarchicalBtn');
    
    try {
        // 更新状态为构建中
        if (statusElement && statusTextElement) {
            statusElement.className = 'hierarchical-status status-building';
            statusTextElement.textContent = '正在重建索引...';
            statusElement.setAttribute('data-tooltip', '分层索引正在重建中，请耐心等待');
        }
        
        if (rebuildBtnElement) {
            rebuildBtnElement.style.display = 'none';
        }
        
        showNotification('开始重建分层索引', '这可能需要几分钟时间，请耐心等待', 'info');
        
        // 发送重建请求
        const formData = new FormData();
        formData.append('kb_name', currentKbName);
        
        const response = await fetch('/knowledge/api/documents/rebuild-hierarchical-index', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                showNotification('分层索引重建成功', '检索性能已优化', 'success');
                
                // 等待一下再检查状态
                setTimeout(() => {
                    checkHierarchicalIndexStatus();
                }, 2000);
            } else {
                showNotification('分层索引重建失败', result.message, 'error');
                // 重建失败，恢复之前的状态
                setTimeout(() => {
                    checkHierarchicalIndexStatus();
                }, 1000);
            }
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
    } catch (error) {
        console.error('重建分层索引失败:', error);
        showNotification('分层索引重建失败', error.message, 'error');
        
        // 重建失败，恢复之前的状态
        setTimeout(() => {
            checkHierarchicalIndexStatus();
        }, 1000);
    }
}

// 全局暴露函数供其他模块使用
window.checkHierarchicalIndexStatus = checkHierarchicalIndexStatus; 