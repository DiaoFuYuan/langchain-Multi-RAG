// 通用对话RAG配置侧边页JavaScript

// RAG配置管理器
class RAGSidebarManager {
    constructor() {
        this.ragSidePanel = document.getElementById('ragSidePanel');
        this.ragSidebarToggleBtn = document.getElementById('ragSidebarToggleBtn');
        this.ragSidePanelClose = document.getElementById('ragSidePanelClose');
        this.ragToggleSwitch = document.getElementById('ragToggleSwitch');
        this.ragSelectKnowledgeBtn = document.getElementById('ragSelectKnowledgeBtn');
        this.ragClearSelectionBtn = document.getElementById('ragClearSelectionBtn');
        this.chatContainer = document.getElementById('simpleChatContainer');
        
        // RAG配置状态
        this.selectedKnowledgeBases = [];
        this.ragConfig = {
            topK: 10,
            threshold: 0.3,
            rerank: true,
            // 新增检索器参数
            contextWindow: 150,
            keywordThreshold: 1,
            enableContextEnrichment: true,
            enableRanking: true,
            // 新增生成器参数
            temperature: 0.3,
            memoryWindow: 5
        };
        
        // 从知识库API获取数据，而不是使用模拟数据
        this.knowledgeBases = [];
        this.loadKnowledgeBases();
        
        // 初始化
        this.init();
    }

    // 初始化DOM元素
    initializeElements() {
        this.ragSidePanel = document.getElementById('ragSidePanel');
        this.ragSidePanelClose = document.getElementById('ragSidePanelClose');
        this.ragSidebarToggleBtn = document.getElementById('ragSidebarToggleBtn');
        this.simpleChatContainer = document.getElementById('simpleChatContainer');
        
        // RAG开关控件
        this.ragToggleSwitch = document.getElementById('ragToggleSwitch');
        this.ragToggleText = document.getElementById('ragToggleText');
        
        // RAG配置控件
        this.ragTopKSlider = document.getElementById('ragTopKSlider');
        this.ragTopKValue = document.getElementById('ragTopKValue');
        this.ragThresholdSlider = document.getElementById('ragThresholdSlider');
        this.ragThresholdValue = document.getElementById('ragThresholdValue');
        this.ragRerankCheckbox = document.getElementById('ragRerankCheckbox');
        
        // 新增检索器参数控件
        this.ragContextWindowSlider = document.getElementById('ragContextWindowSlider');
        this.ragContextWindowValue = document.getElementById('ragContextWindowValue');
        this.ragKeywordThresholdSlider = document.getElementById('ragKeywordThresholdSlider');
        this.ragKeywordThresholdValue = document.getElementById('ragKeywordThresholdValue');
        this.ragContextEnrichmentCheckbox = document.getElementById('ragContextEnrichmentCheckbox');
        this.ragRankingCheckbox = document.getElementById('ragRankingCheckbox');
        
        // 新增生成器参数控件
        this.ragTemperatureSlider = document.getElementById('ragTemperatureSlider');
        this.ragTemperatureValue = document.getElementById('ragTemperatureValue');
        this.ragMemoryWindowSlider = document.getElementById('ragMemoryWindowSlider');
        this.ragMemoryWindowValue = document.getElementById('ragMemoryWindowValue');
        
        // 知识库管理控件
        this.ragSelectKnowledgeBtn = document.getElementById('ragSelectKnowledgeBtn');
        this.ragClearSelectionBtn = document.getElementById('ragClearSelectionBtn');
        this.ragSelectedKnowledgeList = document.getElementById('ragSelectedKnowledgeList');
        this.ragKbSelectedCount = document.getElementById('ragKbSelectedCount');
        
        // 状态显示控件
        this.ragStatusIndicator = document.getElementById('ragStatusIndicator');
        this.ragKbCount = document.getElementById('ragKbCount');
        this.ragVectorDim = document.getElementById('ragVectorDim');
    }

    // 设置事件监听器
    setupEventListeners() {
        // 侧边栏切换
        if (this.ragSidebarToggleBtn) {
            this.ragSidebarToggleBtn.addEventListener('click', () => this.toggleSidePanel());
        }
        
        if (this.ragSidePanelClose) {
            this.ragSidePanelClose.addEventListener('click', () => this.closeSidePanel());
        }

        // RAG开关监听器
        this.setupRAGToggleListener();
        
        // RAG配置控件
        this.setupRAGConfigListeners();
        
        // 知识库管理
        this.setupKnowledgeManagementListeners();
    }

    // 设置RAG开关监听器
    setupRAGToggleListener() {
        if (this.ragToggleSwitch) {
            this.ragToggleSwitch.addEventListener('change', (e) => {
                this.ragConfig.enabled = e.target.checked;
                this.updateRAGToggleText();
                this.updateInputPlaceholder();
                this.onRAGConfigChange();
                
                // 如果启用RAG但没有选择知识库，提示用户
                if (this.ragConfig.enabled && this.selectedKnowledgeBases.length === 0) {
                    this.showRAGConfigTip();
                }
            });
        }
    }

    // 更新输入框placeholder文本
    updateInputPlaceholder() {
        const userInput = document.getElementById('userInput');
        if (userInput) {
            if (this.ragConfig.enabled) {
                userInput.placeholder = '配置你的知识库，优先使用知识库回答你的问题';
            } else {
                userInput.placeholder = '随时输入你的问题，可使用联网搜索获取最新信息';
            }
        }
    }

    // 更新RAG开关文本
    updateRAGToggleText() {
        if (this.ragToggleText) {
            const textSpan = this.ragToggleText.querySelector('span');
            if (textSpan) {
                textSpan.textContent = this.ragConfig.enabled ? '知识库问答已启用' : '启用知识库问答';
            }
        }
    }

    // 显示RAG配置提示
    showRAGConfigTip() {
        // 创建提示消息
        const tip = document.createElement('div');
        tip.className = 'rag-config-tip';
        tip.innerHTML = `
            <div class="rag-tip-content">
                <i class="fas fa-info-circle"></i>
                <span>已启用知识库问答，建议配置知识库以获得更好的回答效果</span>
                <button class="rag-tip-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // 添加提示样式
        const style = document.createElement('style');
        style.textContent = `
            .rag-config-tip {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10001;
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 12px 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                animation: slideInRight 0.3s ease;
                max-width: 350px;
            }
            .rag-tip-content {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 13px;
                color: #856404;
            }
            .rag-tip-content i:first-child {
                color: #f39c12;
                font-size: 16px;
            }
            .rag-tip-close {
                background: none;
                border: none;
                color: #856404;
                cursor: pointer;
                padding: 2px;
                border-radius: 2px;
                margin-left: auto;
            }
            .rag-tip-close:hover {
                background: rgba(133, 100, 4, 0.1);
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(tip);
        
        // 3秒后自动移除提示
        setTimeout(() => {
            if (tip.parentElement) {
                tip.remove();
                style.remove();
            }
        }, 3000);
    }

    // 设置RAG配置监听器
    setupRAGConfigListeners() {
        // Top-K滑块
        if (this.ragTopKSlider && this.ragTopKValue) {
            this.ragTopKSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                this.ragTopKValue.textContent = value;
                this.ragConfig.topK = value;
                this.onRAGConfigChange();
            });
        }

        // 阈值滑块
        if (this.ragThresholdSlider && this.ragThresholdValue) {
            this.ragThresholdSlider.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                this.ragThresholdValue.textContent = value;
                this.ragConfig.threshold = value;
                this.onRAGConfigChange();
            });
        }

        // 重排序复选框
        if (this.ragRerankCheckbox) {
            this.ragRerankCheckbox.addEventListener('change', (e) => {
                this.ragConfig.rerank = e.target.checked;
                this.onRAGConfigChange();
            });
        }

        // 新增检索器参数监听器
        // 上下文窗口滑块
        if (this.ragContextWindowSlider && this.ragContextWindowValue) {
            this.ragContextWindowSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                this.ragContextWindowValue.textContent = value;
                this.ragConfig.contextWindow = value;
                this.onRAGConfigChange();
            });
        }

        // 关键词匹配阈值滑块
        if (this.ragKeywordThresholdSlider && this.ragKeywordThresholdValue) {
            this.ragKeywordThresholdSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                this.ragKeywordThresholdValue.textContent = value;
                this.ragConfig.keywordThreshold = value;
                this.onRAGConfigChange();
            });
        }

        // 上下文增强复选框
        if (this.ragContextEnrichmentCheckbox) {
            this.ragContextEnrichmentCheckbox.addEventListener('change', (e) => {
                this.ragConfig.enableContextEnrichment = e.target.checked;
                this.onRAGConfigChange();
            });
        }

        // 相关性排序复选框
        if (this.ragRankingCheckbox) {
            this.ragRankingCheckbox.addEventListener('change', (e) => {
                this.ragConfig.enableRanking = e.target.checked;
                this.onRAGConfigChange();
            });
        }

        // 新增生成器参数监听器
        // 生成温度滑块
        if (this.ragTemperatureSlider && this.ragTemperatureValue) {
            this.ragTemperatureSlider.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                this.ragTemperatureValue.textContent = value;
                this.ragConfig.temperature = value;
                this.onRAGConfigChange();
            });
        }

        // 记忆窗口滑块
        if (this.ragMemoryWindowSlider && this.ragMemoryWindowValue) {
            this.ragMemoryWindowSlider.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                this.ragMemoryWindowValue.textContent = value;
                this.ragConfig.memoryWindow = value;
                this.onRAGConfigChange();
            });
        }
    }

    // 设置知识库管理监听器
    setupKnowledgeManagementListeners() {
        // 选择知识库按钮
        if (this.ragSelectKnowledgeBtn) {
            this.ragSelectKnowledgeBtn.addEventListener('click', () => {
                this.openKnowledgeSelector();
            });
        }
        
        // 清空选择按钮
        if (this.ragClearSelectionBtn) {
            this.ragClearSelectionBtn.addEventListener('click', () => {
                this.clearKnowledgeSelection();
            });
        }
    }

    // 切换侧边面板
    toggleSidePanel() {
        if (this.isExpanded) {
            this.closeSidePanel();
        } else {
            this.openSidePanel();
        }
    }

    // 打开侧边面板
    openSidePanel() {
        if (this.simpleChatContainer) {
            this.simpleChatContainer.classList.add('rag-expanded');
        }
        
        if (this.ragSidebarToggleBtn) {
            this.ragSidebarToggleBtn.setAttribute('title', '收起RAG配置');
        }
        
        this.isExpanded = true;
        console.log('RAG配置面板已展开');
    }

    // 关闭侧边面板
    closeSidePanel() {
        if (this.simpleChatContainer) {
            this.simpleChatContainer.classList.remove('rag-expanded');
        }
        
        if (this.ragSidebarToggleBtn) {
            this.ragSidebarToggleBtn.setAttribute('title', '展开RAG配置');
        }
        
        this.isExpanded = false;
        console.log('RAG配置面板已收起');
    }

    // RAG配置变化回调
    onRAGConfigChange() {
        console.log('RAG配置已更新:', this.ragConfig);
        // 这里可以添加配置保存逻辑
        this.saveRAGConfig();
    }

    // 保存RAG配置
    async saveRAGConfig() {
        try {
            // 暂时使用本地存储代替API调用
            const config = {
                ...this.ragConfig,
                selectedKnowledgeBases: this.selectedKnowledgeBases
            };
            
            localStorage.setItem('ragConfig', JSON.stringify(config));
            console.log('RAG配置已保存到本地存储:', config);
            
            // 注释掉API调用直到后端实现
            /*
            const response = await fetch('/api/rag/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.ragConfig)
            });
            
            if (response.ok) {
                console.log('RAG配置保存成功');
            }
            */
        } catch (error) {
            console.error('保存RAG配置失败:', error);
        }
    }

    // 加载RAG配置
    loadRAGConfig() {
        try {
            const saved = localStorage.getItem('ragConfig');
            if (saved) {
                const config = JSON.parse(saved);
                this.setRAGConfig(config);
                console.log('已加载保存的RAG配置:', config);
            }
        } catch (error) {
            console.error('加载RAG配置失败:', error);
        }
    }

    // 异步加载知识库数据
    async loadKnowledgeBases() {
        try {
            const response = await fetch('/knowledge/api/knowledge_bases');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data && data.data.knowledge_bases) {
                    this.knowledgeBases = data.data.knowledge_bases || [];
                } else {
                    console.warn('知识库数据格式异常，使用模拟数据');
                    this.knowledgeBases = this.getSimulatedKnowledgeBases();
                }
            } else {
                console.warn('无法加载知识库数据，使用模拟数据');
                this.knowledgeBases = this.getSimulatedKnowledgeBases();
            }
        } catch (error) {
            console.warn('加载知识库数据失败，使用模拟数据:', error);
            this.knowledgeBases = this.getSimulatedKnowledgeBases();
        }
        
        // 更新UI
        this.updateSelectedKnowledgeBases();
        this.updateKnowledgeBaseCount();
    }

    // 获取模拟知识库数据
    getSimulatedKnowledgeBases() {
        return [
            {
                id: 1,
                name: "技术文档库",
                description: "包含各种技术文档和API参考",
                document_count: 150
            },
            {
                id: 2,
                name: "产品手册库",
                description: "产品使用手册和说明文档",
                document_count: 89
            },
            {
                id: 3,
                name: "FAQ知识库",
                description: "常见问题解答集合",
                document_count: 234
            }
        ];
    }

    // 打开知识库选择器
    openKnowledgeSelector() {
        // 如果知识库数据为空，提示用户先创建知识库
        if (this.knowledgeBases.length === 0) {
            this.showKnowledgeManagementOptions();
        } else {
            this.showSimpleKnowledgeSelector();
        }
    }

    // 显示知识库管理选项
    showKnowledgeManagementOptions() {
        const modal = document.createElement('div');
        modal.className = 'rag-knowledge-modal';
        modal.innerHTML = `
            <div class="rag-modal-overlay">
                <div class="rag-modal-content">
                    <div class="rag-modal-header">
                        <h3><i class="fas fa-database"></i> 知识库管理</h3>
                        <button class="rag-modal-close">&times;</button>
                    </div>
                    <div class="rag-modal-body">
                        <div class="empty-knowledge-state">
                            <div class="empty-icon">
                                <i class="fas fa-database"></i>
                            </div>
                            <div class="empty-message">
                                <h4>暂无可用知识库</h4>
                                <p>请先创建知识库，然后返回此处选择使用</p>
                            </div>
                            <div class="knowledge-actions">
                                <button class="kb-action-btn primary" onclick="window.open('/knowledge/knowledge_base', '_blank')">
                                    <i class="fas fa-plus"></i> 创建知识库
                                </button>
                                <button class="kb-action-btn" onclick="ragSidebarManager.refreshKnowledgeBases()">
                                    <i class="fas fa-sync-alt"></i> 刷新列表
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="rag-modal-footer">
                        <button class="rag-modal-btn rag-modal-btn-cancel">关闭</button>
                    </div>
                </div>
            </div>
        `;

        // 添加样式
        this.addModalStyles(modal);
        
        // 事件监听
        this.setupModalEvents(modal);
        
        // 显示模态框
        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // 刷新知识库列表
    async refreshKnowledgeBases() {
        try {
            await this.loadKnowledgeBases();
            this.showMessage('知识库列表已刷新', 'success');
            
            // 关闭当前模态框
            const modal = document.querySelector('.rag-knowledge-modal');
            if (modal) {
                modal.remove();
            }
            
            // 如果现在有知识库了，重新打开选择器
            if (this.knowledgeBases.length > 0) {
                setTimeout(() => this.showSimpleKnowledgeSelector(), 300);
            }
        } catch (error) {
            this.showMessage('刷新失败: ' + error.message, 'error');
        }
    }

    // 显示消息提示
    showMessage(message, type = 'info') {
        // 创建提示元素
        const toast = document.createElement('div');
        toast.className = `rag-toast rag-toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // 添加到页面
        document.body.appendChild(toast);
        
        // 显示动画
        setTimeout(() => toast.classList.add('show'), 10);
        
        // 自动隐藏
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // 显示知识库选择模态框
    showSimpleKnowledgeSelector() {
        const modal = document.createElement('div');
        modal.className = 'rag-knowledge-modal';
        modal.innerHTML = `
            <div class="rag-modal-overlay">
                <div class="rag-modal-content">
                    <div class="rag-modal-header">
                        <h3>选择知识库</h3>
                        <button class="rag-modal-close">&times;</button>
                    </div>
                    <div class="rag-modal-body">
                        <div class="rag-kb-list">
                            ${this.knowledgeBases.map(kb => `
                                <div class="rag-kb-option" data-kb-id="${kb.id}">
                                    <input type="checkbox" id="kb-${kb.id}" ${this.selectedKnowledgeBases.includes(kb.id) ? 'checked' : ''}>
                                    <label for="kb-${kb.id}">
                                        <div class="rag-kb-option-name">${kb.name}</div>
                                        <div class="rag-kb-option-desc">${kb.description}</div>
                                        <div class="rag-kb-option-count">${kb.document_count || 0} 个文档</div>
                                    </label>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="rag-modal-footer">
                        <button class="rag-modal-btn rag-modal-btn-cancel">取消</button>
                        <button class="rag-modal-btn rag-modal-btn-confirm">确认</button>
                    </div>
                </div>
            </div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .rag-knowledge-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 10000;
            }
            .rag-modal-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .rag-modal-content {
                background: white;
                border-radius: 8px;
                width: 90%;
                max-width: 500px;
                max-height: 80vh;
                display: flex;
                flex-direction: column;
            }
            .rag-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px;
                border-bottom: 1px solid #eee;
            }
            .rag-modal-close {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
            }
            .rag-modal-body {
                flex: 1;
                padding: 16px;
                overflow-y: auto;
            }
            .rag-kb-option {
                display: flex;
                align-items: flex-start;
                gap: 8px;
                padding: 12px;
                border: 1px solid #eee;
                border-radius: 6px;
                margin-bottom: 8px;
                cursor: pointer;
            }
            .rag-kb-option:hover {
                background: #f8f9fa;
            }
            .rag-kb-option label {
                flex: 1;
                cursor: pointer;
            }
            .rag-kb-option-name {
                font-weight: 600;
                margin-bottom: 4px;
            }
            .rag-kb-option-desc {
                font-size: 12px;
                color: #666;
                margin-bottom: 4px;
            }
            .rag-kb-option-count {
                font-size: 11px;
                color: #999;
            }
            .rag-modal-footer {
                display: flex;
                justify-content: flex-end;
                gap: 8px;
                padding: 16px;
                border-top: 1px solid #eee;
            }
            .rag-modal-btn {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .rag-modal-btn-cancel {
                background: #f5f5f5;
                color: #666;
            }
            .rag-modal-btn-confirm {
                background: #667eea;
                color: white;
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(modal);

        // 事件处理
        const closeModal = () => {
            document.body.removeChild(modal);
            document.head.removeChild(style);
        };

        modal.querySelector('.rag-modal-close').addEventListener('click', closeModal);
        modal.querySelector('.rag-modal-btn-cancel').addEventListener('click', closeModal);
        modal.querySelector('.rag-modal-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) closeModal();
        });

        modal.querySelector('.rag-modal-btn-confirm').addEventListener('click', () => {
            const selectedIds = [];
            modal.querySelectorAll('.rag-kb-option input:checked').forEach(checkbox => {
                const kbId = parseInt(checkbox.closest('.rag-kb-option').dataset.kbId);
                selectedIds.push(kbId);
            });
            
            this.selectedKnowledgeBases = selectedIds;
            this.updateSelectedKnowledgeBases();
            this.updateSelectedCount();
            closeModal();
        });
    }

    // 清除选中的知识库
    clearKnowledgeSelection() {
        this.selectedKnowledgeBases = [];
        this.updateSelectedKnowledgeBases();
        this.updateSelectedCount();
    }

    // 更新已选择知识库显示
    updateSelectedKnowledgeBases() {
        const selectedList = document.getElementById('ragSelectedKnowledgeList');
        
        if (!selectedList) return;
        
        if (this.selectedKnowledgeBases.length === 0) {
            // 显示空状态
            selectedList.innerHTML = `
                <div class="rag-empty-selection-state">
                    <i class="fas fa-inbox"></i>
                    <span>暂未选择任何知识库</span>
                    <p>点击上方"选择知识库"按钮开始选择</p>
                </div>
            `;
        } else {
            // 显示已选择的知识库
            const selectedKBs = this.knowledgeBases.filter(kb => 
                this.selectedKnowledgeBases.includes(kb.id)
            );
            
            selectedList.innerHTML = selectedKBs.map(kb => `
                <div class="rag-kb-item" data-kb-id="${kb.id}">
                    <span class="rag-kb-item-name">${kb.name}</span>
                    <button class="rag-kb-item-remove" onclick="ragSidebarManager.removeKnowledgeBase(${kb.id})" title="移除知识库">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `).join('');
        }
        
        this.updateSelectedCount();
    }

    // 移除知识库
    removeKnowledgeBase(kbId) {
        // 确保kbId是数字类型
        const id = parseInt(kbId);
        this.selectedKnowledgeBases = this.selectedKnowledgeBases.filter(selectedId => selectedId !== id);
        this.updateSelectedKnowledgeBases();
        this.saveRAGConfig();
        
        console.log('移除知识库:', id, '剩余:', this.selectedKnowledgeBases);
    }

    // 更新选中数量
    updateSelectedCount() {
        if (this.ragKbSelectedCount) {
            const count = this.selectedKnowledgeBases.length;
            this.ragKbSelectedCount.textContent = `已选择 ${count} 个知识库`;
            
            // 根据选择状态添加或移除CSS类
            if (count > 0) {
                this.ragKbSelectedCount.classList.add('has-selection');
            } else {
                this.ragKbSelectedCount.classList.remove('has-selection');
            }
        }
    }

    // 更新知识库数量
    updateKnowledgeBaseCount() {
        if (this.ragKbCount) {
            this.ragKbCount.textContent = this.knowledgeBases.length;
        }
    }

    // 更新RAG状态
    updateRAGStatus(status, text) {
        if (this.ragStatusIndicator) {
            this.ragStatusIndicator.className = `rag-status-indicator ${status}`;
            this.ragStatusIndicator.textContent = text;
        }
    }

    // 获取当前RAG配置
    getRAGConfig() {
        return {
            ...this.ragConfig,
            selectedKnowledgeBases: this.selectedKnowledgeBases
        };
    }

    // 设置RAG配置
    setRAGConfig(config) {
        if (config.enabled !== undefined) {
            this.ragConfig.enabled = config.enabled;
            if (this.ragToggleSwitch) this.ragToggleSwitch.checked = config.enabled;
            this.updateRAGToggleText();
        }
        
        if (config.topK !== undefined) {
            this.ragConfig.topK = config.topK;
            if (this.ragTopKSlider) this.ragTopKSlider.value = config.topK;
            if (this.ragTopKValue) this.ragTopKValue.textContent = config.topK;
        }
        
        if (config.threshold !== undefined) {
            this.ragConfig.threshold = config.threshold;
            if (this.ragThresholdSlider) this.ragThresholdSlider.value = config.threshold;
            if (this.ragThresholdValue) this.ragThresholdValue.textContent = config.threshold;
        }
        
        if (config.rerank !== undefined) {
            this.ragConfig.rerank = config.rerank;
            if (this.ragRerankCheckbox) this.ragRerankCheckbox.checked = config.rerank;
        }

        // 新增检索器参数设置
        if (config.contextWindow !== undefined) {
            this.ragConfig.contextWindow = config.contextWindow;
            if (this.ragContextWindowSlider) this.ragContextWindowSlider.value = config.contextWindow;
            if (this.ragContextWindowValue) this.ragContextWindowValue.textContent = config.contextWindow;
        }

        if (config.keywordThreshold !== undefined) {
            this.ragConfig.keywordThreshold = config.keywordThreshold;
            if (this.ragKeywordThresholdSlider) this.ragKeywordThresholdSlider.value = config.keywordThreshold;
            if (this.ragKeywordThresholdValue) this.ragKeywordThresholdValue.textContent = config.keywordThreshold;
        }

        if (config.enableContextEnrichment !== undefined) {
            this.ragConfig.enableContextEnrichment = config.enableContextEnrichment;
            if (this.ragContextEnrichmentCheckbox) this.ragContextEnrichmentCheckbox.checked = config.enableContextEnrichment;
        }

        if (config.enableRanking !== undefined) {
            this.ragConfig.enableRanking = config.enableRanking;
            if (this.ragRankingCheckbox) this.ragRankingCheckbox.checked = config.enableRanking;
        }

        // 新增生成器参数设置
        if (config.temperature !== undefined) {
            this.ragConfig.temperature = config.temperature;
            if (this.ragTemperatureSlider) this.ragTemperatureSlider.value = config.temperature;
            if (this.ragTemperatureValue) this.ragTemperatureValue.textContent = config.temperature;
        }

        if (config.memoryWindow !== undefined) {
            this.ragConfig.memoryWindow = config.memoryWindow;
            if (this.ragMemoryWindowSlider) this.ragMemoryWindowSlider.value = config.memoryWindow;
            if (this.ragMemoryWindowValue) this.ragMemoryWindowValue.textContent = config.memoryWindow;
        }
        
        if (config.selectedKnowledgeBases && Array.isArray(config.selectedKnowledgeBases)) {
            this.selectedKnowledgeBases = [...config.selectedKnowledgeBases];
            this.updateSelectedKnowledgeBases();
            this.updateSelectedCount();
        }
        
        // 更新输入框placeholder
        this.updateInputPlaceholder();
    }

    // 获取RAG是否启用
    isRAGEnabled() {
        return this.ragConfig.enabled;
    }

    // 获取完整的RAG配置（包括启用状态）
    getFullRAGConfig() {
        return {
            ...this.ragConfig,
            selectedKnowledgeBases: this.selectedKnowledgeBases,
            hasKnowledgeBases: this.selectedKnowledgeBases.length > 0
        };
    }

    // 初始化方法
    init() {
        this.initializeElements();
        this.setupEventListeners();
        this.loadRAGConfig(); // 加载保存的配置
        this.updateRAGToggleText();
        this.updateInputPlaceholder(); // 初始化placeholder
        this.updateSelectedCount();
        this.updateSelectedKnowledgeBases();
    }
}

// 全局RAG侧边栏管理器实例
let ragSidebarManager;

// 初始化RAG侧边栏管理器
document.addEventListener('DOMContentLoaded', function() {
    ragSidebarManager = new RAGSidebarManager();
    
    // 将管理器实例暴露到全局作用域，方便其他脚本调用
    window.ragSidebarManager = ragSidebarManager;
});

// 全局函数：保存RAG设置
function saveRAGSettings() {
    if (window.ragSidebarManager) {
        try {
            // 保存当前RAG配置
            ragSidebarManager.saveRAGConfig();
            
            // 显示保存成功提示
            showRAGNotification('保存成功', 'RAG配置已保存', 'success');
            
        } catch (error) {
            console.error('保存RAG设置失败:', error);
            showRAGNotification('保存失败', '无法保存RAG配置，请重试', 'error');
        }
    }
}

// 全局函数：取消RAG设置
function cancelRAGSettings() {
    if (window.ragSidebarManager) {
        try {
            // 重置为默认配置
            const defaultConfig = {
                topK: 5,
                threshold: 0.7,
                rerank: true,
                enabled: false,
                // 检索器参数默认值
                contextWindow: 150,
                keywordThreshold: 1,
                enableContextEnrichment: true,
                enableRanking: true,
                // 生成器参数默认值
                temperature: 0.3,
                memoryWindow: 5
            };
            
            ragSidebarManager.setRAGConfig(defaultConfig);
            
            // 清空选择的知识库
            ragSidebarManager.clearKnowledgeSelection();
            
            // 显示取消提示
            showRAGNotification('已取消', 'RAG配置已重置为默认设置', 'info');
            
        } catch (error) {
            console.error('取消RAG设置失败:', error);
            showRAGNotification('操作失败', '无法重置RAG配置，请重试', 'error');
        }
    }
}

// 显示RAG通知消息
function showRAGNotification(title, message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `rag-notification rag-notification-${type}`;
    
    let iconClass;
    switch (type) {
        case 'success':
            iconClass = 'fas fa-check-circle';
            break;
        case 'error':
            iconClass = 'fas fa-exclamation-circle';
            break;
        case 'info':
        default:
            iconClass = 'fas fa-info-circle';
            break;
    }
    
    notification.innerHTML = `
        <div class="rag-notification-content">
            <div class="rag-notification-icon">
                <i class="${iconClass}"></i>
            </div>
            <div class="rag-notification-text">
                <div class="rag-notification-title">${title}</div>
                <div class="rag-notification-message">${message}</div>
            </div>
            <button class="rag-notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // 添加通知样式
    const style = document.createElement('style');
    style.id = 'rag-notification-styles';
    if (!document.getElementById('rag-notification-styles')) {
        style.textContent = `
            .rag-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10001;
                border-radius: 8px;
                padding: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                animation: slideInRight 0.3s ease;
                max-width: 400px;
                min-width: 300px;
            }
            .rag-notification-success {
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                border: 1px solid #c3e6cb;
            }
            .rag-notification-error {
                background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
                border: 1px solid #f5c6cb;
            }
            .rag-notification-info {
                background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
                border: 1px solid #bee5eb;
            }
            .rag-notification-content {
                display: flex;
                align-items: flex-start;
                gap: 12px;
            }
            .rag-notification-icon {
                flex-shrink: 0;
                font-size: 20px;
                margin-top: 2px;
            }
            .rag-notification-success .rag-notification-icon {
                color: #155724;
            }
            .rag-notification-error .rag-notification-icon {
                color: #721c24;
            }
            .rag-notification-info .rag-notification-icon {
                color: #0c5460;
            }
            .rag-notification-text {
                flex: 1;
            }
            .rag-notification-title {
                font-weight: 600;
                font-size: 14px;
                margin-bottom: 4px;
            }
            .rag-notification-success .rag-notification-title {
                color: #155724;
            }
            .rag-notification-error .rag-notification-title {
                color: #721c24;
            }
            .rag-notification-info .rag-notification-title {
                color: #0c5460;
            }
            .rag-notification-message {
                font-size: 13px;
                line-height: 1.4;
            }
            .rag-notification-success .rag-notification-message {
                color: #155724;
            }
            .rag-notification-error .rag-notification-message {
                color: #721c24;
            }
            .rag-notification-info .rag-notification-message {
                color: #0c5460;
            }
            .rag-notification-close {
                background: none;
                border: none;
                cursor: pointer;
                padding: 2px;
                border-radius: 2px;
                font-size: 14px;
                flex-shrink: 0;
            }
            .rag-notification-success .rag-notification-close {
                color: #155724;
            }
            .rag-notification-error .rag-notification-close {
                color: #721c24;
            }
            .rag-notification-info .rag-notification-close {
                color: #0c5460;
            }
            .rag-notification-close:hover {
                opacity: 0.7;
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除通知
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
} 