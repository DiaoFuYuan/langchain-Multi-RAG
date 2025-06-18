/**
 * 文档上传功能模块
 */

class DocumentUploadManager {
    constructor() {
        this.currentKbName = null;
        this.isUploading = false;
        this.uploadQueue = [];
        this.completedUploads = [];
        this.failedUploads = [];
        this.queueStatusInterval = null;
        
        this.initializeElements();
        this.bindEvents();
        
        // 检查是否在正确的页面上
        if (!this.modal) {
            console.info('DocumentUploadManager: 上传模态框不存在，文档上传功能在当前页面不可用');
        }
    }

    initializeElements() {
        // 获取DOM元素
        this.modal = document.getElementById('uploadDocumentModal');
        this.fileInput = document.getElementById('uploadFileInput');
        this.uploadArea = document.getElementById('uploadArea');
        this.fileList = document.getElementById('uploadFileList');
        this.selectedFilesList = document.getElementById('selectedFilesList');
        this.uploadBtn = document.getElementById('startUploadBtn');
        this.cancelBtn = document.getElementById('cancelUploadBtn');
        this.progressContainer = document.getElementById('uploadProgressContainer');
        this.progressBar = document.getElementById('uploadProgressBar');
        this.progressText = document.getElementById('uploadProgressText');
        this.queueStatus = document.getElementById('queueStatus');
        
        // 如果队列状态元素不存在，且modal存在，创建它
        if (!this.queueStatus && this.modal) {
            this.createQueueStatusElement();
        }
    }
    
    createQueueStatusElement() {
        // 确保modal存在
        if (!this.modal) {
            console.warn('上传模态框不存在，跳过创建队列状态元素');
            return;
        }
        
        // 在上传模态框中添加队列状态显示
        const modalBody = this.modal.querySelector('.doc-modal-body');
        if (modalBody) {
            const queueStatusHtml = `
                <div id="queueStatus" class="queue-status" style="display: none;">
                    <div class="queue-info">
                        <i class="fas fa-clock"></i>
                        <span class="queue-text">处理队列状态</span>
                    </div>
                    <div class="queue-details">
                        <span id="queueCount">0</span> 个文件等待处理
                        <span id="currentProcessing" style="display: none;">
                            | 正在处理: <span id="currentFileName"></span>
                        </span>
                    </div>
                </div>
            `;
            modalBody.insertAdjacentHTML('beforeend', queueStatusHtml);
            this.queueStatus = document.getElementById('queueStatus');
        } else {
            console.warn('找不到模态框主体元素，无法创建队列状态元素');
        }
    }

    bindEvents() {
        // 文件选择事件
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                this.handleFileSelection(e.target.files);
            });
        }

        // 上传区域点击事件
        if (this.uploadArea) {
            this.uploadArea.addEventListener('click', () => {
                if (this.fileInput) {
                    this.fileInput.click();
                }
            });
        }

        // 拖拽上传
        if (this.uploadArea) {
            this.uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.uploadArea.classList.add('drag-over');
            });

            this.uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                this.uploadArea.classList.remove('drag-over');
            });

            this.uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                this.uploadArea.classList.remove('drag-over');
                this.handleFileSelection(e.dataTransfer.files);
            });
        }

        // 上传按钮
        if (this.uploadBtn) {
            this.uploadBtn.addEventListener('click', () => {
                this.startUpload();
            });
        }

        // 取消按钮
        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', () => {
                this.closeUploadModal();
            });
        }
    }

    openUploadModal(kbName) {
        console.log('openUploadModal 被调用，kbName:', kbName);
        console.log('this.modal:', this.modal);
        
        this.currentKbName = kbName;
        this.resetUploadState();
        
        if (this.modal) {
            console.log('显示模态框');
            this.modal.classList.add('show');
            // 开始监控队列状态
            this.startQueueStatusMonitoring();
        } else {
            console.error('模态框元素不存在，无法显示');
        }
    }

    closeUploadModal() {
        if (this.modal) {
            this.modal.classList.remove('show');
            this.resetUploadState();
            // 停止监控队列状态
            this.stopQueueStatusMonitoring();
        }
    }

    resetUploadState() {
        this.uploadQueue = [];
        this.completedUploads = [];
        this.failedUploads = [];
        this.isUploading = false;
        
        if (this.fileInput) this.fileInput.value = '';
        if (this.selectedFilesList) this.selectedFilesList.style.display = 'none';
        if (this.fileList) this.fileList.innerHTML = '';
        if (this.uploadBtn) {
            this.uploadBtn.disabled = true;
            this.uploadBtn.textContent = '开始上传';
        }
        if (this.progressContainer) this.progressContainer.style.display = 'none';
        if (this.queueStatus) this.queueStatus.style.display = 'none';
    }

    handleFileSelection(files) {
        const fileArray = Array.from(files);
        
        // 验证文件
        const validFiles = fileArray.filter(file => this.validateFile(file));
        
        // 添加到上传队列
        validFiles.forEach(file => {
            if (!this.uploadQueue.find(f => f.name === file.name && f.size === file.size)) {
                this.uploadQueue.push(file);
            }
        });

        this.updateFileList();
        this.updateUploadButton();
    }

    validateFile(file) {
        // 文件大小限制 (1GB)
        const maxSize = 1024 * 1024 * 1024;
        if (file.size > maxSize) {
            showNotification(`文件 "${file.name}" 超过1GB大小限制`, 'error');
            return false;
        }

        // 文件类型限制
        const allowedTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/csv'
        ];

        const allowedExtensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'];
        const fileExtension = file.name.split('.').pop().toLowerCase();

        if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
            showNotification(`不支持的文件类型: "${file.name}"`, 'error');
            return false;
        }

        return true;
    }

    updateFileList() {
        if (!this.fileList || !this.selectedFilesList) return;

        if (this.uploadQueue.length === 0) {
            this.selectedFilesList.style.display = 'none';
            return;
        }

        // 显示已选择文件区域
        this.selectedFilesList.style.display = 'block';

        const html = this.uploadQueue.map((file, index) => `
            <div class="upload-file-item" data-index="${index}">
                <div class="file-info">
                    <i class="fas ${this.getFileIcon(file)}"></i>
                    <div class="file-details">
                        <div class="file-name">${this.escapeHtml(file.name)}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button class="remove-file-btn" onclick="uploadManager.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');

        this.fileList.innerHTML = html;
    }

    removeFile(index) {
        this.uploadQueue.splice(index, 1);
        this.updateFileList();
        this.updateUploadButton();
    }

    updateUploadButton() {
        if (this.uploadBtn) {
            this.uploadBtn.disabled = this.uploadQueue.length === 0 || this.isUploading;
        }
    }

    async startUpload() {
        if (this.isUploading || this.uploadQueue.length === 0) return;

        this.isUploading = true;
        this.completedUploads = [];
        this.failedUploads = [];

        // 显示进度条
        if (this.progressContainer) {
            this.progressContainer.style.display = 'block';
        }

        // 更新按钮状态
        if (this.uploadBtn) {
            this.uploadBtn.disabled = true;
            this.uploadBtn.textContent = '上传中...';
        }

        const total = this.uploadQueue.length;
        let completed = 0;

        // 逐个上传文件
        for (let i = 0; i < this.uploadQueue.length; i++) {
            const file = this.uploadQueue[i];
            
            try {
                this.updateProgress(completed, total, `正在上传: ${file.name}`);
                
                const result = await this.uploadSingleFile(file);
                this.completedUploads.push({
                    file: file,
                    result: result
                });
                
                completed++;
                this.updateProgress(completed, total, `已完成: ${file.name}`);
                
            } catch (error) {
                this.failedUploads.push({
                    file: file,
                    error: error.message
                });
                
                completed++;
                this.updateProgress(completed, total, `失败: ${file.name}`);
            }
        }

        // 上传完成
        this.isUploading = false;
        
        // 显示完成通知
        if (completed === total) {
            showNotification('上传完成', `成功上传 ${completed} 个文件，正在初始化...`, 'success');
            
            // 立即刷新文档列表以显示新文档的状态
            if (window.loadDocumentsList) {
                loadDocumentsList();
            }
            
            // 等待文件初始化完成后再关闭模态框
            this.updateProgress(completed, total, '等待文件初始化完成...');
            await this.waitForFilesInitialization();
            
            // 关闭模态框
            setTimeout(() => {
                this.closeUploadModal();
                // 再次刷新确保状态同步
                if (window.loadDocumentsList) {
                    loadDocumentsList();
                }
                // 确保状态监控正在运行
                if (window.startStatusMonitoring) {
                    startStatusMonitoring();
                }
                showNotification('初始化完成', '所有文件已成功添加到知识库，正在检查分层索引...', 'success');
                
                // 检查并更新分层索引状态
                if (window.checkHierarchicalIndexStatus) {
                    setTimeout(() => {
                        window.checkHierarchicalIndexStatus();
                    }, 2000);
                }
            }, 500);
        } else {
            showNotification('上传完成', `成功上传 ${completed}/${total} 个文件`, 'warning');
            // 即使部分失败，也要刷新列表
            if (window.loadDocumentsList) {
                loadDocumentsList();
            }
            
            // 等待一段时间后关闭模态框
            setTimeout(() => {
                this.closeUploadModal();
            }, 2000);
        }
    }

    async uploadSingleFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('kb_name', this.currentKbName);

        const response = await fetch('/knowledge/api/documents/upload-with-vectorization', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '上传失败');
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || '上传失败');
        }

        return result;
    }

    updateProgress(completed, total, message) {
        const percentage = Math.round((completed / total) * 100);
        
        if (this.progressBar) {
            this.progressBar.style.width = `${percentage}%`;
        }
        
        if (this.progressText) {
            this.progressText.textContent = `${message} (${completed}/${total})`;
        }
    }

    // 队列状态监控
    startQueueStatusMonitoring() {
        // 立即获取一次状态
        this.updateQueueStatus();
        
        // 每2秒更新一次队列状态
        this.queueStatusInterval = setInterval(() => {
            this.updateQueueStatus();
        }, 2000);
    }

    stopQueueStatusMonitoring() {
        if (this.queueStatusInterval) {
            clearInterval(this.queueStatusInterval);
            this.queueStatusInterval = null;
        }
    }

    async updateQueueStatus() {
        try {
            const response = await fetch('/knowledge/api/documents/processing-status');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.displayQueueStatus(result.data);
                }
            }
        } catch (error) {
            console.error('获取队列状态失败:', error);
        }
    }

    displayQueueStatus(status) {
        if (!this.queueStatus) return;

        const queueCount = status.queue_size || 0;
        const currentTask = status.current_task;
        
        if (queueCount > 0 || currentTask) {
            this.queueStatus.style.display = 'block';
            
            const queueCountElement = document.getElementById('queueCount');
            const currentProcessingElement = document.getElementById('currentProcessing');
            const currentFileNameElement = document.getElementById('currentFileName');
            
            if (queueCountElement) {
                queueCountElement.textContent = queueCount;
            }
            
            if (currentTask && currentProcessingElement && currentFileNameElement) {
                currentProcessingElement.style.display = 'inline';
                currentFileNameElement.textContent = currentTask.filename || '未知文件';
            } else if (currentProcessingElement) {
                currentProcessingElement.style.display = 'none';
            }
        } else {
            this.queueStatus.style.display = 'none';
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getFileIcon(file) {
        const fileName = file.name.toLowerCase();
        const fileType = file.type.toLowerCase();
        
        if (fileType.includes('pdf') || fileName.endsWith('.pdf')) {
            return 'fa-file-pdf';
        } else if (fileType.includes('word') || fileName.endsWith('.doc') || fileName.endsWith('.docx')) {
            return 'fa-file-word';
        } else if (fileType.includes('excel') || fileName.endsWith('.xls') || fileName.endsWith('.xlsx')) {
            return 'fa-file-excel';
        } else if (fileType.includes('text') || fileName.endsWith('.txt')) {
            return 'fa-file-alt';
        } else if (fileName.endsWith('.csv')) {
            return 'fa-file-csv';
        } else {
            return 'fa-file';
        }
    }

    // 新增方法：等待文件初始化完成
    async waitForFilesInitialization() {
        const maxWaitTime = 10000; // 最大等待10秒
        const checkInterval = 1000; // 每秒检查一次
        let waitedTime = 0;
        
        while (waitedTime < maxWaitTime) {
            try {
                // 检查所有上传的文件是否都已在元数据中
                const response = await fetch(`/knowledge/api/documents?kb_name=${encodeURIComponent(this.currentKbName)}&page=1&limit=100`);
                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        const documents = result.data || [];
                        const uploadedFileNames = this.completedUploads.map(upload => upload.file.name);
                        
                        // 检查是否所有上传的文件都在文档列表中
                        const allFilesFound = uploadedFileNames.every(fileName => 
                            documents.some(doc => doc.filename === fileName)
                        );
                        
                        if (allFilesFound) {
                            this.updateProgress(this.completedUploads.length, this.uploadQueue.length, '所有文件初始化完成');
                            return; // 所有文件都已初始化完成
                        }
                    }
                }
            } catch (error) {
                console.error('检查文件初始化状态失败:', error);
            }
            
            // 等待一段时间后再次检查
            await new Promise(resolve => setTimeout(resolve, checkInterval));
            waitedTime += checkInterval;
            
            // 更新进度显示
            const remainingTime = Math.max(0, (maxWaitTime - waitedTime) / 1000);
            this.updateProgress(this.completedUploads.length, this.uploadQueue.length, 
                `等待文件初始化... (${remainingTime.toFixed(0)}秒)`);
        }
        
        // 超时后仍然继续，但给出警告
        console.warn('文件初始化等待超时，可能存在同步问题');
        this.updateProgress(this.completedUploads.length, this.uploadQueue.length, '初始化超时，请手动刷新页面');
    }
}

// 创建全局实例
const uploadManager = new DocumentUploadManager();

// 导出给其他模块使用
window.uploadManager = uploadManager;