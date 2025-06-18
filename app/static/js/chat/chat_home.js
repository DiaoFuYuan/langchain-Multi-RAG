// 页面加载完成后执行初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('聊天页面加载完成');
    initialize();
    updateChatHistory();
    initializeSettings();
});

// 全局变量
let isProcessing = false;
let availableModels = [];
let selectedModel = null;
let networkSearchEnabled = localStorage.getItem('networkSearchEnabled') === 'true' || false;
    
// 初始化函数
function initialize() {
    setupSidebarResponse();
    setupInputFieldEvents();
    setupSendMessage();
    setupRefreshChat();
    loadAvailableModels();
    setupModelSelectorEvents();
    restoreNetworkSearchState();
}
    
// 设置输入框事件
function setupInputFieldEvents() {
    const userInput = document.getElementById('userInput');
    
    if (userInput) {
        // 自动调整textarea高度
        function adjustTextareaHeight() {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
        }
        
        // 监听输入事件，自动调整高度
        userInput.addEventListener('input', function() {
            adjustTextareaHeight();
            
            // 检查是否包含@网络搜索标记时，显示提示
            const networkBtn = document.querySelector('button[title="联网搜索"]');
            if (networkBtn && this.value.includes('@网络搜索') && !networkBtn.classList.contains('active')) {
                    networkBtn.style.animation = 'pulse 0.5s ease-in-out';
                    setTimeout(() => {
                        networkBtn.style.animation = '';
                    }, 500);
            }
        });
        
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // 初始调整高度
        adjustTextareaHeight();
        userInput.focus();
    }
}
    
// 设置发送消息按钮事件
function setupSendMessage() {
    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
}
    
// 设置刷新聊天按钮事件
function setupRefreshChat() {
    const refreshButton = document.querySelector('.refresh-btn');
    
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = '';
            isProcessing = false;
            
            const userInput = document.getElementById('userInput');
            if (userInput) {
                userInput.focus();
            }
        });
    }
}
    
// 设置侧边栏响应
function setupSidebarResponse() {
    const sidebar = document.querySelector('.sidebar');
    const container = document.querySelector('.chat-container');
    
    if (sidebar && container) {
        const marginLeft = sidebar.classList.contains('collapsed') ? '55px' : '205px';
        container.style.marginLeft = marginLeft;
        
        const toggleButton = sidebar.querySelector('.sidebar-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', function() {
                sidebar.classList.toggle('collapsed');
                container.style.marginLeft = sidebar.classList.contains('collapsed') ? '55px' : '205px';
            });
        }
    }
}

// 滚动聊天区域到底部
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 加载可用模型列表
async function loadAvailableModels() {
    try {
        const response = await fetch('/config/api/available-models');
        const result = await response.json();
        
        if (result.success) {
            availableModels = result.data;
            populateModelSelect();
            
            const savedModelId = localStorage.getItem('selectedModelId');
            if (savedModelId) {
                const modelSelect = document.getElementById('modelSelect');
                if (modelSelect) {
                    modelSelect.value = savedModelId;
                    updateSelectedModel();
                }
            }
                } else {
            console.error('加载模型列表失败:', result.message);
        }
    } catch (error) {
        console.error('加载模型列表时发生错误:', error);
    }
}

// 填充模型选择下拉菜单
function populateModelSelect() {
    const modelSelect = document.getElementById('modelSelect');
    if (!modelSelect) return;
    
    modelSelect.innerHTML = '<option value="">选择模型...</option>';
    
    availableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.display_name;
        modelSelect.appendChild(option);
    });
    
    // 设置事件监听器（避免重复绑定）
    if (!modelSelect.hasAttribute('data-listener-added')) {
        modelSelect.addEventListener('change', function() {
            updateSelectedModel();
            localStorage.setItem('selectedModelId', this.value);
        });
        modelSelect.setAttribute('data-listener-added', 'true');
    }
}

// 更新选择的模型
function updateSelectedModel() {
    const modelSelect = document.getElementById('modelSelect');
    if (!modelSelect) return;
    
    const selectedModelId = modelSelect.value;
    selectedModel = selectedModelId ? availableModels.find(model => model.id == selectedModelId) : null;
    if (selectedModel) {
        console.log('选择的模型:', selectedModel);
    }
}
    
// 发送消息函数
function sendMessage() {
    if (isProcessing) return;

    const userInput = document.getElementById('userInput');
    const userMessage = userInput.value.trim();
    
    if (!userMessage) return;

    // 检查是否选择了模型
    if (!selectedModel) {
        alert('请先选择一个模型');
        return;
    }

    // 检查是否启用了联网搜索
    const hasNetworkTag = userMessage.includes('@网络搜索');
    console.log('🔍 联网搜索检查:', {
        networkSearchEnabled,
        hasNetworkTag,
        shouldUseNetworkSearch: networkSearchEnabled || hasNetworkTag
    });
    
    if (networkSearchEnabled || hasNetworkTag) {
        const cleanMessage = hasNetworkTag ? userMessage.replace('@网络搜索', '').trim() : userMessage;
        console.log('🌐 启动联网搜索模式，查询:', cleanMessage);
        
        showToast('🌐 启动联网搜索', 'info');
        
        addMessageToChat('user', hasNetworkTag ? userMessage : userMessage);
        userInput.value = '';
        processNetworkSearchMessage(cleanMessage);
        return;
    }

    // 检查是否启用了RAG并配置了知识库
    const shouldUseRAG = checkRAGConfiguration();
    
        addMessageToChat('user', userMessage);
        userInput.value = '';
    
    if (shouldUseRAG) {
        showToast('🔗 启动知识库检索', 'info');
        
        processRAGMessageWithStreaming(userMessage);
    } else {
        processMessageWithStreaming(userMessage);
    }
}

// 检查RAG配置
function checkRAGConfiguration() {
    if (window.ragSidebarManager && window.ragSidebarManager.isRAGEnabled()) {
        const ragConfig = window.ragSidebarManager.getFullRAGConfig();
        if (ragConfig.hasKnowledgeBases && ragConfig.selectedKnowledgeBases.length > 0) {
            console.log('使用RAG模式，配置:', ragConfig);
            return true;
        } else {
            console.log('RAG已启用但未配置知识库，使用普通模式');
        }
    }
    console.log('RAG未启用，使用普通模式');
    return false;
}

// 获取RAG配置
function getRAGConfiguration() {
    // 获取前端通用配置参数
    const frontendSettings = getCurrentSettings();
    
    if (window.ragSidebarManager) {
        const ragConfig = window.ragSidebarManager.getFullRAGConfig();
        const knowledgeBaseIds = (ragConfig.selectedKnowledgeBases || []).map(id => String(id));
        const currentModel = selectedModel;
        
        // 融合前端配置和RAG配置：前端配置优先
        const finalTemperature = frontendSettings.temperature ? 
            parseFloat(frontendSettings.temperature) : 
            (ragConfig.temperature || 0.3);
        
        const config = {
            knowledge_base_ids: knowledgeBaseIds,
            top_k: ragConfig.topK || 15,  // 增加到15，确保杨女士等实体的所有相关块都能被检索
            threshold: ragConfig.threshold || 0.7,
            rerank: ragConfig.rerank || false,
            context_window: ragConfig.contextWindow || 150,
            keyword_threshold: ragConfig.keywordThreshold || 1,
            enable_context_enrichment: ragConfig.enableContextEnrichment || true,
            enable_ranking: ragConfig.enableRanking || true,
            temperature: finalTemperature,
            memory_window: ragConfig.memoryWindow || 5,
            retriever_type: 'hierarchical',  // 强制使用分层检索器
            selected_model: currentModel ? {
                model_id: currentModel.id,
                provider: currentModel.provider,
                model_name: currentModel.model_name,
                endpoint: currentModel.endpoint,
                display_name: currentModel.display_name
            } : null,
            // 添加前端通用配置
            frontend_settings: frontendSettings
        };
        
        console.log("🔧 RAG配置 (已融合前端设置):", config);
        console.log("🎛️ 应用的温度设置:", finalTemperature, "(来源:", frontendSettings.temperature ? "前端配置" : "RAG配置", ")");
        return config;
    }
    
    return {
        knowledge_base_ids: [],
        top_k: 15,  // 增加默认值，确保实体聚合检索效果
        threshold: 0.3,
        rerank: false,
        context_window: 150,
        keyword_threshold: 1,
        enable_context_enrichment: true,
        enable_ranking: true,
        temperature: parseFloat(frontendSettings.temperature) || 0.3,
        memory_window: 5,
        retriever_type: 'hierarchical',  // 默认使用分层检索器
        selected_model: null,
        frontend_settings: frontendSettings
    };
}

// 添加消息到聊天区域
function addMessageToChat(sender, text, timestamp = new Date()) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `simple-message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = `<i class="fas fa-${sender === 'user' ? 'user' : 'robot'}"></i>`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const isMarkdown = sender === 'bot' && 
        (text.includes('```') || text.includes('#') || 
         text.includes('- ') || text.includes('|') || 
         text.includes('> ') || text.includes('*') ||
         text.includes('**') || text.includes('1.'));
         
    if (isMarkdown || sender === 'bot') {
        contentDiv.className = 'message-content has-markdown';
        const markdownDiv = document.createElement('div');
        markdownDiv.className = 'markdown-content';
        markdownDiv.innerHTML = sender === 'bot' ? simpleFrontendMarkdown(text) : `<p>${convertUrlsToLinks(text)}</p>`;
        contentDiv.appendChild(markdownDiv);
        
        // 应用markdown增强功能
        if (window.markdownEnhancer) {
            window.markdownEnhancer.enhance(markdownDiv);
        }
    } else {
        contentDiv.innerHTML = `<p>${convertUrlsToLinks(text)}</p>`;
    }
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// 将文本中的URL转换为可点击的链接
function convertUrlsToLinks(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, function(url) {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });
}

// 生成信息样式
function getInfoStyle(type, text, icon, color) {
    return `<div class="${type}-info" style="display: flex; align-items: center; color: #666; font-size: 14px; margin: 0; padding: 6px 12px; background:rgb(246, 246, 246); border-radius: 6px; margin-bottom: 8px; border-left: 3px solid ${color};border-right: 3px solid ${color};">
        <i class="fas fa-${icon}" style="margin-right: 6px; color: ${color};"></i> 
        <span>${text}</span>
    </div>`;
}

// 生成紧凑的搜索信息样式
function getCompactSearchInfo() {
    return getInfoStyle('search', '基于联网搜索结果回答', 'globe', '#007bff');
}

// 生成紧凑的知识库信息样式
function getCompactKnowledgeInfo() {
    return getInfoStyle('knowledge', '基于知识库回答', 'chain', '#28a745');
}

// 创建机器人消息容器
function createBotMessageContainer() {
    const botMessageDiv = document.createElement('div');
    botMessageDiv.className = 'simple-message bot-message';
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content has-markdown';
    
    const markdownDiv = document.createElement('div');
    markdownDiv.className = 'markdown-content';
    
    contentDiv.appendChild(markdownDiv);
    botMessageDiv.appendChild(avatarDiv);
    botMessageDiv.appendChild(contentDiv);
    
    return { botMessageDiv, markdownDiv };
}

// 创建联网搜索进度显示元素
function createNetworkSearchProgress() {
    const progressContainer = document.createElement('div');
    progressContainer.className = 'network-search-progress';
    
    const indicator = document.createElement('div');
    indicator.className = 'progress-indicator';
    
    const text = document.createElement('span');
    text.className = 'progress-text';
    
    progressContainer.appendChild(indicator);
    progressContainer.appendChild(text);
    
    return progressContainer;
}

// 更新联网搜索进度状态
function updateNetworkSearchProgress(progressElement, status, text) {
    if (!progressElement) return;
    
    // 移除所有状态类
    progressElement.classList.remove('searching', 'found', 'generating');
    
    // 添加新的状态类
    progressElement.classList.add(status);
    
    // 更新文字
    const textElement = progressElement.querySelector('.progress-text');
    if (textElement) {
        textElement.textContent = text;
    }
}

// 统一的渲染函数
function renderMarkdownContent(element, text, infoHeader = '') {
    const content = infoHeader + simpleFrontendMarkdown(text);
    element.innerHTML = content;
    
    if (window.markdownEnhancer) {
        window.markdownEnhancer.enhance(element);
    }
    scrollToBottom();
}

// 防抖渲染函数
function createDebouncedRenderer(element, infoHeader = '') {
    let renderTimeout = null;
    let lastRenderTime = 0;
    const RENDER_INTERVAL = 100;
    
    return function(text) {
        const now = Date.now();
        
        if (renderTimeout) {
            clearTimeout(renderTimeout);
        }
        
        if (now - lastRenderTime < RENDER_INTERVAL) {
            renderTimeout = setTimeout(() => {
                renderMarkdownContent(element, text, infoHeader);
                lastRenderTime = Date.now();
            }, RENDER_INTERVAL - (now - lastRenderTime));
        } else {
            renderMarkdownContent(element, text, infoHeader);
            lastRenderTime = now;
        }
    };
}

// 处理联网搜索消息
async function processNetworkSearchMessage(userMessage) {
    console.log('🚀 开始处理联网搜索消息:', userMessage);
    isProcessing = true;
    
    const chatMessages = document.getElementById('chatMessages');
    const { botMessageDiv, markdownDiv } = createBotMessageContainer();
    
    // 添加联网搜索特殊样式
    botMessageDiv.classList.add('network-search');
    
    // 创建纯光标显示容器
    const cursorContainer = document.createElement('div');
    cursorContainer.className = 'network-search-cursor-container';
    const cursorElement = document.createElement('span');
    cursorElement.className = 'cursor-blink';
    cursorContainer.appendChild(cursorElement);
    
    // 创建进度显示元素
    const progressElement = createNetworkSearchProgress();
    
    // 初始显示光标和"正在查询中"状态
    markdownDiv.innerHTML = '';
    markdownDiv.appendChild(cursorContainer);
    botMessageDiv.appendChild(progressElement);
    
    chatMessages.appendChild(botMessageDiv);
    scrollToBottom();
    
    // 更新进度状态为"正在查询中"
    updateNetworkSearchProgress(progressElement, 'searching', '正在查询中');
    
    try {
        // 获取前端配置的参数
        const currentSettings = getCurrentSettings();
        console.log('🔧 联网搜索使用的配置参数:', {
            model: selectedModel,
            settings: currentSettings
        });
        
        // 1. 先进行联网搜索
        const searchResponse = await fetch('/network/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: userMessage,
                llm_config: selectedModel,
                settings: currentSettings
            })
        });
        
        if (!searchResponse.ok) {
            throw new Error(`搜索请求失败: ${searchResponse.status}`);
        }
        
        const searchData = await searchResponse.json();
        console.log('🔍 搜索API响应:', searchData);
        
        if (!searchData.success) {
            throw new Error(searchData.error || '搜索失败');
        }
        
        // 2. 更新状态为"已搜索到结果"
        updateNetworkSearchProgress(progressElement, 'found', '已搜索到结果');
        
        const enhancedPrompt = searchData.enhanced_prompt;
        console.log('🤖 AI分析阶段使用的增强提示词长度:', enhancedPrompt.length);
        console.log('🔧 AI分析阶段应用的配置参数:', currentSettings);
        
        // 3. 发送增强的提示词给AI模型进行流式对话
        const response = await fetch('/chat/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: enhancedPrompt,
                model_config: selectedModel,
                settings: currentSettings
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // 4. 处理流式响应，当开始生成内容时显示"正在生成中"状态
        await processNetworkSearchStreamResponse(response, markdownDiv, progressElement, getCompactSearchInfo());
        
    } catch (error) {
        console.error('联网搜索处理失败:', error);
        
        // 移除进度显示，显示错误信息
        if (progressElement.parentNode) {
            progressElement.parentNode.removeChild(progressElement);
        }
        
        markdownDiv.innerHTML = `
            <div class="error-message" style="display: flex; align-items: center; color: #d73527; font-size: 14px; padding: 8px 12px; margin: 8px 0; background: #fff2f0; border-radius: 6px; border-left: 3px solid #d73527;">
                <i class="fas fa-exclamation-triangle" style="margin-right: 8px;"></i>
                <span style="font-weight: 500;">联网搜索失败: ${error.message}</span>
                <br><span style="font-size: 13px; color: #999; margin-top: 4px; display: inline-block;">请检查网络连接或稍后重试</span>
            </div>
        `;
        isProcessing = false;
    }
}

// 处理消息并使用流式输出
function processMessageWithStreaming(userMessage) {
    isProcessing = true;
    
    const chatMessages = document.getElementById('chatMessages');
    const { botMessageDiv, markdownDiv } = createBotMessageContainer();
    
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';
    botMessageDiv.querySelector('.message-content').appendChild(typingIndicator);
    
    chatMessages.appendChild(botMessageDiv);
    scrollToBottom();
    
    fetch('/chat/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: userMessage,
            model_config: selectedModel,
            settings: getCurrentSettings()
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return processStreamResponse(response, markdownDiv, '', typingIndicator);
    })
    .catch(error => {
        console.error('流式处理错误:', error);
        const contentDiv = botMessageDiv.querySelector('.message-content');
        if (contentDiv.querySelector('.typing-indicator')) {
            contentDiv.innerHTML = `<p>网络请求失败: ${error.message}</p>`;
        }
        isProcessing = false;
    });
}

// 处理RAG消息并使用流式输出
function processRAGMessageWithStreaming(userMessage) {
    isProcessing = true;
    
    const chatMessages = document.getElementById('chatMessages');
    const { botMessageDiv, markdownDiv } = createBotMessageContainer();
    botMessageDiv.classList.add('rag-chat');
    
    // 添加知识库检索特殊样式
    botMessageDiv.classList.add('rag-search');
    
    // 创建纯光标显示容器
    const cursorContainer = document.createElement('div');
    cursorContainer.className = 'network-search-cursor-container';
    const cursorElement = document.createElement('span');
    cursorElement.className = 'cursor-blink';
    cursorContainer.appendChild(cursorElement);
    
    // 创建进度显示元素
    const progressElement = createNetworkSearchProgress();
    
    // 初始显示光标和"正在检索中"状态
    markdownDiv.innerHTML = '';
    markdownDiv.appendChild(cursorContainer);
    botMessageDiv.appendChild(progressElement);
    
    chatMessages.appendChild(botMessageDiv);
    scrollToBottom();
    
    // 更新进度状态为"正在检索中"
    updateNetworkSearchProgress(progressElement, 'searching', '开始检索知识库');
    
    // 获取RAG配置
    const ragConfig = getRAGConfiguration();
    
    const requestBody = {
        message: userMessage,
        knowledge_base_ids: ragConfig.knowledge_base_ids || [],
        knowledge_bases: ragConfig.knowledge_base_ids || [],
        history: [],
        session_id: null,
        top_k: ragConfig.top_k || 15,  // 增加到15，确保杨女士等实体的所有相关块都能被检索
        threshold: ragConfig.threshold || 0.7,
        rerank: ragConfig.rerank || false,
        context_window: ragConfig.context_window || 150,
        keyword_threshold: ragConfig.keyword_threshold || 1,
        enable_context_enrichment: ragConfig.enable_context_enrichment || true,
        enable_ranking: ragConfig.enable_ranking || true,
        temperature: ragConfig.temperature || 0.3,
        memory_window: ragConfig.memory_window || 5,
        selected_model: ragConfig.selected_model,
        retriever_type: 'hierarchical'  // 强制使用分层检索器
    };
    
    console.log('发送RAG请求:', requestBody);
    
    fetch('/rag/api/chat-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return processRAGStreamResponseWithProgress(response, markdownDiv, progressElement, getCompactKnowledgeInfo());
    })
    .catch(error => {
        console.error('RAG聊天请求失败:', error);
        
        // 移除进度显示，显示错误信息
        if (progressElement.parentNode) {
            progressElement.parentNode.removeChild(progressElement);
        }
        
        markdownDiv.innerHTML = `<p>RAG请求失败: ${error.message}</p>`;
        isProcessing = false;
    });
}

// 联网搜索专用的流式响应处理器
async function processNetworkSearchStreamResponse(response, markdownDiv, progressElement, infoHeader = '') {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const debouncedRenderer = createDebouncedRenderer(markdownDiv, infoHeader);
    let accumulatedText = '';
    let firstChunkReceived = false;
    let generatingStarted = false;
    
    function processStream({ done, value }) {
        if (done) {
            if (accumulatedText) {
                renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
            }
            // 流式响应结束，移除进度显示
            if (progressElement && progressElement.parentNode) {
                progressElement.parentNode.removeChild(progressElement);
            }
            isProcessing = false;
            return;
        }
        
        try {
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n').filter(line => line.trim());
            
            for (const line of lines) {
                if (!line.trim()) continue;
                
                try {
                    // 处理SSE格式
                    let jsonStr = line;
                    if (line.startsWith('data: ')) {
                        jsonStr = line.slice(6);
                        if (jsonStr === '[DONE]') {
                            if (accumulatedText) {
                                renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
                            }
                            // 流式响应结束，移除进度显示
                            if (progressElement && progressElement.parentNode) {
                                progressElement.parentNode.removeChild(progressElement);
                            }
                            isProcessing = false;
                            return;
                        }
                    }
                    
                    const data = JSON.parse(jsonStr);
                    
                    if (data.content) {
                        if (!generatingStarted) {
                            // 收到第一个内容块时，更新进度为"正在生成中"
                            updateNetworkSearchProgress(progressElement, 'generating', '正在生成中');
                            generatingStarted = true;
                        }
                        
                        if (!firstChunkReceived) {
                            // 第一次收到内容时，替换光标为实际内容
                            markdownDiv.innerHTML = '';
                            if (infoHeader) {
                                markdownDiv.innerHTML = infoHeader;
                            }
                            firstChunkReceived = true;
                        }
                        
                        accumulatedText += data.content;
                        debouncedRenderer(accumulatedText);
                    } else if (data.status === 'chunk' && data.content) {
                        if (!generatingStarted) {
                            // 收到第一个内容块时，更新进度为"正在生成中"
                            updateNetworkSearchProgress(progressElement, 'generating', '正在生成中');
                            generatingStarted = true;
                        }
                        
                        if (!firstChunkReceived) {
                            markdownDiv.innerHTML = '';
                            if (infoHeader) {
                                markdownDiv.innerHTML = infoHeader;
                            }
                            firstChunkReceived = true;
                        }
                        
                        accumulatedText += data.content;
                        debouncedRenderer(accumulatedText);
                    } else if (data.status === 'done' || data.status === 'error') {
                        if (data.status === 'error' && !firstChunkReceived) {
                            markdownDiv.innerHTML = `<p>错误: ${data.error}</p>`;
                        } else if (accumulatedText) {
                            renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
                        }
                        // 流式响应结束，移除进度显示
                        if (progressElement && progressElement.parentNode) {
                            progressElement.parentNode.removeChild(progressElement);
                        }
                        isProcessing = false;
                        return;
                    }
                } catch (e) {
                    console.error('解析JSON失败:', e, '原始数据:', line);
                }
            }
        } catch (e) {
            console.error('处理流数据块时出错:', e);
        }
        
        return reader.read().then(processStream);
    }
    
    return reader.read().then(processStream);
}

// 统一的流式响应处理器
async function processStreamResponse(response, markdownDiv, infoHeader = '', typingIndicator = null) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
    const debouncedRenderer = createDebouncedRenderer(markdownDiv, infoHeader);
        let accumulatedText = '';
        let firstChunkReceived = false;
        
    function processStream({ done, value }) {
            if (done) {
                if (accumulatedText) {
                renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
                }
                isProcessing = false;
                return;
            }
            
            try {
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n').filter(line => line.trim());
                
                for (const line of lines) {
                if (!line.trim()) continue;
                
                try {
                    // 处理SSE格式
                    let jsonStr = line;
                    if (line.startsWith('data: ')) {
                        jsonStr = line.slice(6);
                        if (jsonStr === '[DONE]') {
                            renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
                            isProcessing = false;
                            return;
                        }
                    }
                    
                    const data = JSON.parse(jsonStr);
                    
                    if (data.content) {
                            if (!firstChunkReceived) {
                                firstChunkReceived = true;
                            if (typingIndicator && typingIndicator.parentNode) {
                                typingIndicator.parentNode.removeChild(typingIndicator);
                            }
                            if (infoHeader) {
                                markdownDiv.innerHTML = infoHeader;
                            }
                        }
                        
                        accumulatedText += data.content;
                        debouncedRenderer(accumulatedText);
                    } else if (data.status === 'chunk' && data.content) {
                            if (!firstChunkReceived) {
                                firstChunkReceived = true;
                            if (typingIndicator && typingIndicator.parentNode) {
                                typingIndicator.parentNode.removeChild(typingIndicator);
                            }
                            }
                            
                            accumulatedText += data.content;
                        debouncedRenderer(accumulatedText);
                    } else if (data.status === 'done' || data.status === 'error') {
                        if (data.status === 'error' && !firstChunkReceived) {
                            const contentDiv = markdownDiv.parentNode;
                                if (contentDiv.querySelector('.typing-indicator')) {
                                contentDiv.innerHTML = `<p>错误: ${data.error}</p>`;
                            }
                        } else if (accumulatedText) {
                            renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
                            }
                            isProcessing = false;
                        return;
                        }
                    } catch (e) {
                    console.error('解析JSON失败:', e, '原始数据:', line);
                    }
                }
            } catch (e) {
            console.error('处理流数据块时出错:', e);
        }
        
        return reader.read().then(processStream);
    }
    
    return reader.read().then(processStream);
}

// RAG流式响应处理器（带进度显示）
async function processRAGStreamResponseWithProgress(response, markdownDiv, progressElement, infoHeader = '') {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const debouncedRenderer = createDebouncedRenderer(markdownDiv, infoHeader);
    let accumulatedText = '';
    let firstChunkReceived = false;
    let knowledgeRetrieved = false;
    let generatingStarted = false;
    
    function processRAGStream({ done, value }) {
        if (done) {
            if (accumulatedText) {
                renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
            }
            // 流式响应结束，移除进度显示
            if (progressElement && progressElement.parentNode) {
                progressElement.parentNode.removeChild(progressElement);
            }
            isProcessing = false;
            return;
        }
        
        try {
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n').filter(line => line.trim());
            
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    const jsonStr = line.substring(6);
                    const data = JSON.parse(jsonStr);
                    
                    if (data.type === 'start') {
                        if (!knowledgeRetrieved) {
                            // 延迟1秒后更新状态为"正在检索中"
                            setTimeout(() => {
                                if (progressElement && progressElement.parentNode) {
                                    updateNetworkSearchProgress(progressElement, 'found', '正在检索中');
                                }
                            }, 1000);
                            knowledgeRetrieved = true;
                        }
                        
                        if (!firstChunkReceived) {
                            firstChunkReceived = true;
                        }
                    } else if (data.type === 'message' && data.content) {
                        if (!generatingStarted) {
                            // 收到第一个内容块时，更新进度为"正在生成回答"
                            updateNetworkSearchProgress(progressElement, 'generating', '正在生成回答');
                            generatingStarted = true;
                        }
                        
                        if (!firstChunkReceived) {
                            // 第一次收到内容时，替换光标为实际内容
                            markdownDiv.innerHTML = '';
                            if (infoHeader) {
                                markdownDiv.innerHTML = infoHeader;
                            }
                            firstChunkReceived = true;
                        }
                        
                        accumulatedText += data.content;
                        debouncedRenderer(accumulatedText);
                    } else if (data.type === 'done') {
                        if (!firstChunkReceived) {
                            markdownDiv.innerHTML = '<p>没有接收到RAG回复</p>';
                        } else if (accumulatedText) {
                            renderMarkdownContent(markdownDiv, accumulatedText, infoHeader);
                        }
                        // 流式响应结束，移除进度显示
                        if (progressElement && progressElement.parentNode) {
                            progressElement.parentNode.removeChild(progressElement);
                        }
                        isProcessing = false;
                    } else if (data.type === 'error') {
                        markdownDiv.innerHTML = `<p>RAG错误: ${data.message}</p>`;
                        // 流式响应结束，移除进度显示
                        if (progressElement && progressElement.parentNode) {
                            progressElement.parentNode.removeChild(progressElement);
                        }
                        isProcessing = false;
                    }
                } catch (e) {
                    console.error('解析RAG JSON行时出错:', e, '原始数据:', line);
                }
            }
        } catch (e) {
            console.error('处理RAG流数据块时出错:', e);
        }
        
        return reader.read().then(processRAGStream);
    }
    
    return reader.read().then(processRAGStream);
}

// RAG流式响应处理器（原版，保持兼容性）
async function processRAGStreamResponse(response, markdownDiv, typingIndicator) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const debouncedRenderer = createDebouncedRenderer(markdownDiv, getCompactKnowledgeInfo());
    let accumulatedText = '';
    let firstChunkReceived = false;
    
    function processRAGStream({ done, value }) {
        if (done) {
            if (accumulatedText) {
                renderMarkdownContent(markdownDiv, accumulatedText, getCompactKnowledgeInfo());
            }
            isProcessing = false;
            return;
        }
        
        try {
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n').filter(line => line.trim());
            
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    const jsonStr = line.substring(6);
                    const data = JSON.parse(jsonStr);
                    
                    if (data.type === 'start') {
                        if (typingIndicator && typingIndicator.parentNode) {
                            typingIndicator.parentNode.removeChild(typingIndicator);
                        }
                        
                        if (!firstChunkReceived) {
                            firstChunkReceived = true;
                        }
                        
                        // 添加闪烁光标特效
                        const cursorIndicator = document.createElement('div');
                        cursorIndicator.className = 'rag-cursor-indicator';
                        cursorIndicator.innerHTML = '<span class="typing-cursor">|</span>';
                        markdownDiv.appendChild(cursorIndicator);
                    } else if (data.type === 'message' && data.content) {
                        if (!firstChunkReceived) {
                            firstChunkReceived = true;
                            if (typingIndicator && typingIndicator.parentNode) {
                                typingIndicator.parentNode.removeChild(typingIndicator);
                            }
                            markdownDiv.innerHTML = getCompactKnowledgeInfo();
                        }
                        
                        // 移除闪烁光标特效
                        const cursorIndicator = markdownDiv.querySelector('.rag-cursor-indicator');
                        if (cursorIndicator) {
                            cursorIndicator.remove();
                        }
                        
                        accumulatedText += data.content;
                        debouncedRenderer(accumulatedText);
                    } else if (data.type === 'done') {
                        if (!firstChunkReceived && typingIndicator && typingIndicator.parentNode) {
                            const contentDiv = typingIndicator.parentNode;
                            contentDiv.innerHTML = '<p>没有接收到RAG回复</p>';
                        } else if (accumulatedText) {
                            renderMarkdownContent(markdownDiv, accumulatedText, getCompactKnowledgeInfo());
                        }
                        isProcessing = false;
                    } else if (data.type === 'error') {
                        if (typingIndicator && typingIndicator.parentNode) {
                            const contentDiv = typingIndicator.parentNode;
                            contentDiv.innerHTML = `<p>RAG错误: ${data.message}</p>`;
                        }
                        isProcessing = false;
                    }
                } catch (e) {
                    console.error('解析RAG JSON行时出错:', e, '原始数据:', line);
                }
            }
        } catch (e) {
            console.error('处理RAG流数据块时出错:', e);
        }
        
        return reader.read().then(processRAGStream);
    }
    
    return reader.read().then(processRAGStream);
}

// 新增的功能函数

// 恢复联网搜索按钮状态
function restoreNetworkSearchState() {
    const userInput = document.getElementById('userInput');
    const networkBtn = document.querySelector('button[title="联网搜索"]');
    
    if (userInput && networkBtn && networkSearchEnabled) {
        // 恢复按钮激活状态
        networkBtn.classList.add('active');
        userInput.placeholder = '联网搜索模式已启用，输入问题进行搜索...';
        console.log('🔄 已恢复联网搜索模式状态');
    }
}

function toggleNetwork() {
    console.log('联网搜索功能');
    const userInput = document.getElementById('userInput');
    const networkBtn = document.querySelector('button[title="联网搜索"]');
    
    if (userInput && networkBtn) {
        networkSearchEnabled = !networkSearchEnabled;
        
        // 保存状态到localStorage，页面刷新后保持状态
        localStorage.setItem('networkSearchEnabled', networkSearchEnabled.toString());
        
        if (networkSearchEnabled) {
            // 启用联网搜索
            networkBtn.classList.add('active');
            userInput.placeholder = '联网搜索模式已启用，输入问题进行搜索...';
            
            showToast('联网搜索模式已启用', 'success');
        } else {
            // 关闭联网搜索
            networkBtn.classList.remove('active');
            userInput.placeholder = '随时输入你的问题，可使用联网搜索获取最新信息';
            showToast('联网搜索模式已关闭', 'info');
        }
        
        // 自动调整输入框高度
        userInput.style.height = 'auto';
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
        
        // 聚焦输入框
        userInput.focus();
    }
}

// 附件功能
function toggleAttachment() {
    console.log('附件功能');
    // 创建文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.accept = '.txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif';
    
    fileInput.onchange = function(event) {
        const files = event.target.files;
        if (files.length > 0) {
            const fileNames = Array.from(files).map(file => file.name).join(', ');
            showToast(`已选择文件: ${fileNames}`, 'success');
            // 这里可以添加文件上传的实现
        }
    };
    
    fileInput.click();
}

// 删除toggleGitHub函数，添加模型选择器功能
function toggleModelSelector() {
    const dropdown = document.getElementById('modelConfigDropdown');
    const settingsBtn = document.querySelector('button[title="模型设置"]');
    
    if (dropdown.classList.contains('show')) {
        // 关闭下拉框
        dropdown.classList.remove('show');
        settingsBtn.classList.remove('active');
                } else {
        // 打开下拉框
        dropdown.classList.add('show');
        settingsBtn.classList.add('active');
        loadModelOptions();
    }
}

// 关闭模型选择器
function closeModelSelector() {
    const dropdown = document.getElementById('modelConfigDropdown');
    const settingsBtn = document.querySelector('button[title="模型设置"]');
    
    dropdown.classList.remove('show');
    settingsBtn.classList.remove('active');
}

// 加载模型选项
function loadModelOptions() {
    const modelOptionsContainer = document.getElementById('modelOptions');
    
    // 显示加载状态
    modelOptionsContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">加载中...</div>';
    
    // 获取可用模型列表
    fetch('/config/api/available-models')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data) {
                renderModelOptions(data.data);
            } else {
                modelOptionsContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336; font-size: 12px;">加载失败</div>';
            }
        })
        .catch(error => {
            console.error('Error loading models:', error);
            modelOptionsContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336; font-size: 12px;">网络错误</div>';
        });
}

// 渲染模型选项
function renderModelOptions(models) {
    const modelOptionsContainer = document.getElementById('modelOptions');
    const currentModel = document.getElementById('modelSelect').value;
    
    let html = '';
    models.forEach(model => {
        const isSelected = model.id == currentModel;
        const icon = getModelIcon(model.provider);
        const description = getModelDescription(model.provider);
        
        html += `
            <div class="model-option ${isSelected ? 'selected' : ''}" onclick="selectModelOption('${model.id}', '${model.display_name}')">
                <div class="model-option-icon">
                    <i class="${icon}"></i>
                </div>
                <div class="model-option-info">
                    <div class="model-option-name">${model.display_name}</div>
                    <div class="model-option-description">${description}</div>
                </div>
            </div>
        `;
    });
    
    modelOptionsContainer.innerHTML = html;
}

// 获取模型图标
function getModelIcon(provider) {
    const iconMap = {
        'openai': 'fas fa-brain',
        'deepseek': 'fas fa-robot',
        'anthropic': 'fas fa-comments',
        'vllm': 'fas fa-server',
        'claude': 'fas fa-comments',
        'gemini': 'fas fa-gem',
        'llama': 'fas fa-fire',
        'qwen': 'fas fa-star',
        'chatglm': 'fas fa-lightbulb',
        'baichuan': 'fas fa-mountain',
        'yi': 'fas fa-yin-yang'
    };
    
    return iconMap[provider] || 'fas fa-cog';
}

// 获取模型描述
function getModelDescription(provider) {
    const descriptionMap = {
        'openai': 'OpenAI的GPT系列模型',
        'deepseek': 'DeepSeek的高性能模型',
        'anthropic': 'Anthropic的Claude系列模型',
        'vllm': '本地部署的开源模型',
        'claude': 'Anthropic的AI助手',
        'gemini': 'Google的多模态AI模型',
        'llama': 'Meta开源的大语言模型',
        'qwen': '阿里巴巴的通义千问模型',
        'chatglm': '智谱AI的对话模型',
        'baichuan': '百川智能的中文优化模型',
        'yi': '零一万物的高性能模型'
    };
    
    return descriptionMap[provider] || '智能AI助手，为您提供优质服务';
}

// 选择模型选项
function selectModelOption(modelId, modelName) {
    // 更新模型选择器
                const modelSelect = document.getElementById('modelSelect');
    modelSelect.value = modelId;
    
    // 更新选中的模型
                    updateSelectedModel();
    
    // 保存到本地存储
    localStorage.setItem('selectedModelId', modelId);
    
    // 更新UI中的选中状态
    document.querySelectorAll('.model-option').forEach(item => {
        item.classList.remove('selected');
    });
    event.target.closest('.model-option').classList.add('selected');
    
    // 显示成功提示
    showToast(`已切换到 ${modelName}`, 'success');
    
    // 关闭下拉框
    setTimeout(() => {
        closeModelSelector();
    }, 300);
}

// 设置模型选择器事件监听
function setupModelSelectorEvents() {
    // 点击页面其他地方关闭下拉框
    document.addEventListener('click', function(e) {
        const dropdown = document.getElementById('modelConfigDropdown');
        const settingsBtn = document.getElementById('modelSettingsBtn');
        
        if (dropdown && settingsBtn && 
            !dropdown.contains(e.target) && 
            !settingsBtn.contains(e.target) &&
            dropdown.classList.contains('show')) {
            closeModelSelector();
        }
    });
    
    // ESC键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const dropdown = document.getElementById('modelConfigDropdown');
            if (dropdown && dropdown.classList.contains('show')) {
                closeModelSelector();
            }
        }
    });
}

// 通用提示函数
function showToast(message, type = 'info') {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // 添加样式
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '6px',
        color: 'white',
        fontSize: '14px',
        zIndex: '10000',
        opacity: '0',
        transform: 'translateY(-20px)',
        transition: 'all 0.3s ease'
    });
    
    // 根据类型设置背景色
    switch (type) {
        case 'success':
            toast.style.backgroundColor = '#4CAF50';
            break;
        case 'error':
            toast.style.backgroundColor = '#f44336';
            break;
        case 'warning':
            toast.style.backgroundColor = '#ff9800';
            break;
        default:
            toast.style.backgroundColor = '#2196F3';
    }
    
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);
    
    // 自动隐藏
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// 切换侧边面板显示/隐藏
function toggleSidePanel() {
    const container = document.querySelector('.simple-chat-container');
    const expandBtn = document.querySelector('.sidebar-toggle-btn');
    
    if (container && expandBtn) {
        container.classList.toggle('expanded');
        
        // 更新按钮图标和标题
        const icon = expandBtn.querySelector('i');
        if (container.classList.contains('expanded')) {
            icon.className = 'fas fa-chevron-right';
            expandBtn.title = '收缩侧边页';
        } else {
            icon.className = 'fas fa-chevron-left';
            expandBtn.title = '展开侧边页';
        }
    }
}

// 关闭侧边面板
function closeSidePanel() {
    const container = document.querySelector('.simple-chat-container');
    const expandBtn = document.querySelector('.sidebar-toggle-btn');
    
    if (container && expandBtn) {
        container.classList.remove('expanded');
        
        // 更新按钮图标和标题
        const icon = expandBtn.querySelector('i');
        if (icon) {
            icon.className = 'fas fa-chevron-left';
            expandBtn.title = '展开侧边页';
        }
    }
}

// 侧边面板快捷操作功能
function exportChat() {
    const messages = document.querySelectorAll('.simple-message');
    let chatContent = '';
    
    messages.forEach(message => {
        const content = message.querySelector('.message-content');
        if (content) {
            const isUser = message.classList.contains('user-message');
            const prefix = isUser ? '用户: ' : 'AI: ';
            chatContent += prefix + content.textContent.trim() + '\n\n';
        }
    });
    
    if (chatContent.trim() === '') {
        showToast('暂无对话内容可导出', 'warning');
        return;
    }
    
    // 创建下载链接
    const blob = new Blob([chatContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_export_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('对话已导出', 'success');
}

function shareChat() {
    const messages = document.querySelectorAll('.simple-message');
    let chatContent = '';
    
    messages.forEach(message => {
        const content = message.querySelector('.message-content');
        if (content) {
            const isUser = message.classList.contains('user-message');
            const prefix = isUser ? '用户: ' : 'AI: ';
            chatContent += prefix + content.textContent.trim() + '\n\n';
        }
    });
    
    if (chatContent.trim() === '') {
        showToast('暂无对话内容可分享', 'warning');
        return;
    }
    
    // 使用Web Share API（如果支持）
    if (navigator.share) {
        navigator.share({
            title: 'AI对话分享',
            text: chatContent,
        }).then(() => {
            showToast('分享成功', 'success');
        }).catch(() => {
            // 如果分享失败，复制到剪贴板
            copyToClipboard(chatContent);
        });
    } else {
        // 复制到剪贴板
        copyToClipboard(chatContent);
    }
}

function bookmarkChat() {
    const messages = document.querySelectorAll('.simple-message');
    if (messages.length === 0) {
        showToast('暂无对话内容可收藏', 'warning');
        return;
    }
    
    // 获取第一条用户消息作为标题
    let title = '未命名对话';
    for (let message of messages) {
        if (message.classList.contains('user-message')) {
            const content = message.querySelector('.message-content');
            if (content) {
                title = content.textContent.trim().substring(0, 30) + '...';
                break;
            }
        }
    }
    
    // 保存到本地存储
    const bookmarks = JSON.parse(localStorage.getItem('chatBookmarks') || '[]');
    const bookmark = {
        id: Date.now(),
        title: title,
        timestamp: new Date().toISOString(),
        messageCount: messages.length
    };
    
    bookmarks.unshift(bookmark);
    // 最多保存20个收藏
    if (bookmarks.length > 20) {
        bookmarks.splice(20);
    }
    
    localStorage.setItem('chatBookmarks', JSON.stringify(bookmarks));
    showToast('对话已收藏', 'success');
    
    // 更新聊天历史显示
    updateChatHistory();
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('内容已复制到剪贴板', 'success');
        }).catch(() => {
            showToast('复制失败', 'error');
        });
    } else {
        // 兼容旧浏览器
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showToast('内容已复制到剪贴板', 'success');
        } catch (err) {
            showToast('复制失败', 'error');
        }
        document.body.removeChild(textArea);
    }
}

function updateChatHistory() {
    const historyList = document.querySelector('.chat-history-list');
    if (!historyList) return;
    
    const bookmarks = JSON.parse(localStorage.getItem('chatBookmarks') || '[]');
    
    historyList.innerHTML = '';
    
    if (bookmarks.length === 0) {
        historyList.innerHTML = '<div class="history-item"><i class="fas fa-info-circle"></i><span>暂无聊天历史</span></div>';
        return;
    }
    
    bookmarks.slice(0, 10).forEach(bookmark => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <i class="fas fa-comment"></i>
            <span title="${bookmark.title}">${bookmark.title}</span>
        `;
        item.onclick = () => {
            showToast('历史对话功能开发中', 'info');
        };
        historyList.appendChild(item);
    });
}

// 设置选项功能
function initializeSettings() {
    // 获取设置元素
    const temperatureSlider = document.getElementById('temperatureSlider');
    const temperatureValue = document.getElementById('temperatureValue');
    const promptTextarea = document.getElementById('promptTextarea');
    
    // 从localStorage加载设置
    const savedTemperature = localStorage.getItem('aiTemperature') || '0.7';
    const savedPrompt = localStorage.getItem('systemPrompt') || '';
    
    // 应用温度设置（仅显示，不自动保存）
    if (temperatureSlider && temperatureValue) {
        temperatureSlider.value = savedTemperature;
        temperatureValue.textContent = savedTemperature;
        
        // 只更新显示值，不自动保存
        temperatureSlider.addEventListener('input', function() {
            const value = this.value;
            temperatureValue.textContent = value;
        });
    }
    
    // 应用提示词设置（仅显示，不自动保存）
    if (promptTextarea) {
        promptTextarea.value = savedPrompt;
        // 移除自动保存的事件监听器
    }
    
    // 模型选择已经在loadAvailableModels中处理
}

// 保存设置
function saveSettings() {
    try {
        // 获取当前设置值
        const temperatureSlider = document.getElementById('temperatureSlider');
        const promptTextarea = document.getElementById('promptTextarea');
        const modelSelect = document.getElementById('modelSelect');
        
        // 保存温度设置
        if (temperatureSlider) {
            const temperature = temperatureSlider.value;
            localStorage.setItem('aiTemperature', temperature);
        }
        
        // 保存提示词设置
        if (promptTextarea) {
            const prompt = promptTextarea.value.trim();
            localStorage.setItem('systemPrompt', prompt);
        }
        
        // 保存模型选择
        if (modelSelect && modelSelect.value) {
            localStorage.setItem('selectedModelId', modelSelect.value);
            updateSelectedModel(); // 更新当前选择的模型
        }
        
        // 显示成功提示
        showToast('设置已保存并应用', 'success');
        
        // 可选：关闭侧边面板
        // closeSidePanel();
        
    } catch (error) {
        console.error('保存设置时出错:', error);
        showToast('保存设置失败', 'error');
    }
}

// 取消设置（恢复到上次保存的状态）
function cancelSettings() {
    try {
        // 从localStorage重新加载设置
        const savedTemperature = localStorage.getItem('aiTemperature') || '0.7';
        const savedPrompt = localStorage.getItem('systemPrompt') || '';
        const savedModelId = localStorage.getItem('selectedModelId') || '';
        
        // 恢复温度设置
        const temperatureSlider = document.getElementById('temperatureSlider');
        const temperatureValue = document.getElementById('temperatureValue');
        if (temperatureSlider && temperatureValue) {
            temperatureSlider.value = savedTemperature;
            temperatureValue.textContent = savedTemperature;
        }
        
        // 恢复提示词设置
        const promptTextarea = document.getElementById('promptTextarea');
        if (promptTextarea) {
            promptTextarea.value = savedPrompt;
        }
        
        // 恢复模型选择
        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            modelSelect.value = savedModelId;
            updateSelectedModel();
        }
        
        // 显示取消提示
        showToast('已恢复到上次保存的设置', 'info');
        
    } catch (error) {
        console.error('恢复设置时出错:', error);
        showToast('恢复设置失败', 'error');
    }
}

function getCurrentSettings() {
    return {
        temperature: localStorage.getItem('aiTemperature') || '0.7',
        prompt: localStorage.getItem('systemPrompt') || '',
        modelId: localStorage.getItem('selectedModelId') || ''
    };
}

// 简化的markdown处理函数
function simpleFrontendMarkdown(text) {
    text = String(text || '');
    
    // 处理参考来源
    text = text.replace(/📚 参考来源:\s*([\s\S]*?)(?=\n\n|$)/g, function(match, sources) {
        const fileNames = sources.split('\n')
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('📚'))
            .map(line => line.replace(/^\d+\.\s*/, '').trim())
            .filter(fileName => fileName);
        
        if (fileNames.length > 0) {
            const listItems = fileNames.map(fileName => {
                const fileExtension = fileName.split('.').pop().toLowerCase();
                return `<li data-file-type="${fileExtension}" data-file-name="${fileName}" style="margin: 8px 0;">
                    <div class="rag-source-file-header">
                        <span class="rag-source-filename">${fileName}</span>
                    </div>
                </li>`;
            }).join('');
            
            return `<ul class="rag-sources-list" data-source-count="${fileNames.length}" style="margin: 24px 0 8px 0; padding-left: 24px; line-height: 1.6;">${listItems}</ul>`;
        }
        return '';
    });
    
    // 处理代码块
    text = text
        .replace(/```thinking\n([\s\S]*?)```/g, '<div class="thinking-text">$1</div>')
        .replace(/```thinking\n([\s\S]*)$/g, '<div class="thinking-text">$1</div>')
        .replace(/```(\w+)?\n([\s\S]*?)```/g, function(match, lang, code) {
            const language = lang || '文本';
            return `<div class="simple-code-block" style="margin: 16px 0; border: 1px solid #e9ecef;">
                <div class="simple-code-header" style="background: #f8f9fa; color: #6c757d; padding: 8px 12px; font-size: 12px; border-bottom: 1px solid #e9ecef;">
                    <span class="simple-code-language">${language}</span>
                </div>
                <pre style="margin: 0; padding: 12px; background: #fff; color: #333; overflow-x: auto; line-height: 1.4; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px;"><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>
            </div>`;
        })
        .replace(/```(\w+)?\n([\s\S]*)$/g, function(match, lang, code) {
            const language = lang || '文本';
            return `<div class="simple-code-block" style="margin: 16px 0; border: 1px solid #e9ecef;">
                <div class="simple-code-header" style="background: #f8f9fa; color: #6c757d; padding: 8px 12px; font-size: 12px; border-bottom: 1px solid #e9ecef;">
                    <span class="simple-code-language">${language}</span>
                </div>
                <pre style="margin: 0; padding: 12px; background: #fff; color: #333; overflow-x: auto; line-height: 1.4; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px;"><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>
            </div>`;
        })
        .replace(/`([^`]+)`/g, '<code style="background: #f8f9fa; color: #e83e8c; padding: 2px 4px; font-family: \'Consolas\', \'Monaco\', \'Courier New\', monospace; font-size: 0.9em;">$1</code>');

    // 处理列表和段落
    const lines = text.split('\n');
    const processedLines = [];
    let inOrderedList = false;
    let inUnorderedList = false;
    let currentListItems = [];
    let ulItems = [];
    let currentListStart = 1;
    let pendingContent = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line === '') {
            // 如果有待处理的内容且在列表中，将其添加到当前列表项
            if (pendingContent.length > 0 && (inOrderedList || inUnorderedList)) {
                const contentText = pendingContent.join('<br>');
                const styledContent = `<div style="margin-top: 12px; margin-bottom: 4px;">${contentText}</div>`;
                if (inOrderedList && currentListItems.length > 0) {
                    const lastIndex = currentListItems.length - 1;
                    currentListItems[lastIndex] += styledContent;
                } else if (inUnorderedList && ulItems.length > 0) {
                    const lastIndex = ulItems.length - 1;
                    ulItems[lastIndex] += styledContent;
                }
                pendingContent = [];
            } else if (inOrderedList) {
                processedLines.push(renderOrderedList(currentListItems, currentListStart));
                inOrderedList = false;
                currentListItems = [];
            } else if (inUnorderedList) {
                processedLines.push(renderUnorderedList(ulItems));
                inUnorderedList = false;
                ulItems = [];
            }
            processedLines.push('');
            continue;
        }
        
        const olMatch = line.match(/^(\d+)\.[ \t]+(.+)$/);
        const ulMatch = line.match(/^[-*+][ \t]+(.+)$/);
        
        if (olMatch) {
            // 处理之前的待处理内容
            if (pendingContent.length > 0) {
                if (inUnorderedList) {
                    processedLines.push(renderUnorderedList(ulItems));
                    inUnorderedList = false;
                    ulItems = [];
                }
                if (!inOrderedList) {
                    processedLines.push(...pendingContent);
                }
                pendingContent = [];
            }
            
            if (inUnorderedList) {
                processedLines.push(renderUnorderedList(ulItems));
                inUnorderedList = false;
                ulItems = [];
            }
            
            const num = parseInt(olMatch[1]);
            const content = olMatch[2];
            
            if (!inOrderedList) {
                inOrderedList = true;
                currentListStart = num;
                currentListItems = [];
            }
            
            currentListItems.push(content);
        } else if (ulMatch) {
            // 处理之前的待处理内容
            if (pendingContent.length > 0) {
                if (inOrderedList) {
                    processedLines.push(renderOrderedList(currentListItems, currentListStart));
                    inOrderedList = false;
                    currentListItems = [];
                }
                if (!inUnorderedList) {
                    processedLines.push(...pendingContent);
                }
                pendingContent = [];
            }
            
            if (inOrderedList) {
                processedLines.push(renderOrderedList(currentListItems, currentListStart));
                inOrderedList = false;
                currentListItems = [];
            }
            
            const content = ulMatch[1];
            if (!inUnorderedList) {
                inUnorderedList = true;
                ulItems = [];
            }
            
            ulItems.push(content);
        } else {
            // 检查是否是列表后的相关内容（缩进或短行）
            const isListContinuation = (inOrderedList || inUnorderedList) && 
                (line.startsWith('   ') || line.startsWith('\t') || 
                 (line.length < 100 && !line.match(/^[#>*_\-=]/) && !line.includes(':')));
            
            if (isListContinuation) {
                pendingContent.push(line);
            } else {
                // 结束当前列表
                if (pendingContent.length > 0) {
                    const contentText = pendingContent.join('<br>');
                    const styledContent = `<div style="margin-top: 12px; margin-bottom: 4px;">${contentText}</div>`;
                    if (inOrderedList && currentListItems.length > 0) {
                        const lastIndex = currentListItems.length - 1;
                        currentListItems[lastIndex] += styledContent;
                    } else if (inUnorderedList && ulItems.length > 0) {
                        const lastIndex = ulItems.length - 1;
                        ulItems[lastIndex] += styledContent;
                    }
                    pendingContent = [];
                }
                
                if (inOrderedList) {
                    processedLines.push(renderOrderedList(currentListItems, currentListStart));
                    inOrderedList = false;
                    currentListItems = [];
                } else if (inUnorderedList) {
                    processedLines.push(renderUnorderedList(ulItems));
                    inUnorderedList = false;
                    ulItems = [];
                }
                
                processedLines.push(line);
            }
        }
    }
    
    // 处理剩余的待处理内容
    if (pendingContent.length > 0) {
        const contentText = pendingContent.join('<br>');
        const styledContent = `<div style="margin-top: 12px; margin-bottom: 4px;">${contentText}</div>`;
        if (inOrderedList && currentListItems.length > 0) {
            const lastIndex = currentListItems.length - 1;
            currentListItems[lastIndex] += styledContent;
        } else if (inUnorderedList && ulItems.length > 0) {
            const lastIndex = ulItems.length - 1;
            ulItems[lastIndex] += styledContent;
        }
    }
    
    if (inOrderedList) {
        processedLines.push(renderOrderedList(currentListItems, currentListStart));
    } else if (inUnorderedList) {
        processedLines.push(renderUnorderedList(ulItems));
    }
    
    text = processedLines.join('\n');
    
    // 处理其他markdown格式
    text = text
        // 特殊标题样式
        .replace(/\*\*💭 回答：\*\*/g, '<div class="answer-header" style="margin: 20px 0 16px 0; padding: 8px 12px; background: #f8f9fa; border-left: 4px solid #007bff; font-weight: 600; color: #495057;">💭 回答</div>')
        .replace(/\*\*🤔 思考过程：\*\*/g, '<div class="thinking-section-header" style="margin: 20px 0 16px 0; padding: 8px 12px; background: #f8f9fa; border-left: 4px solid #6c757d; font-weight: 600; color: #495057;">🤔 思考过程</div>')
        
        // 强调文本
        .replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/__([^_]+)__/g, '<strong>$1</strong>')
        .replace(/_([^_]+)_/g, '<em>$1</em>')
        
        // 标题层级（简化样式）
        .replace(/^# (.+)$/gm, '<h1 style="margin: 24px 0 16px 0; font-size: 24px; font-weight: 600; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 8px;">$1</h1>')
        .replace(/^## (.+)$/gm, '<h2 style="margin: 20px 0 12px 0; font-size: 20px; font-weight: 600; color: #333;">$1</h2>')
        .replace(/^### (.+)$/gm, '<h3 style="margin: 16px 0 8px 0; font-size: 18px; font-weight: 600; color: #333;">$1</h3>')
        .replace(/^#### (.+)$/gm, '<h4 style="margin: 14px 0 6px 0; font-size: 16px; font-weight: 600; color: #333;">$1</h4>')
        .replace(/^##### (.+)$/gm, '<h5 style="margin: 12px 0 4px 0; font-size: 14px; font-weight: 600; color: #333;">$1</h5>')
        .replace(/^###### (.+)$/gm, '<h6 style="margin: 10px 0 2px 0; font-size: 13px; font-weight: 600; color: #333;">$1</h6>')
        
        // 中文编号标题
        .replace(/^([一二三四五六七八九十百千万]+)、\s*(.+)$/gm, '<h2 style="margin: 20px 0 12px 0; font-size: 20px; font-weight: 600; color: #333;">$1、$2</h2>')
        .replace(/^(\d+)、\s*(.+)$/gm, function(match, num, content) {
            if (parseInt(num) <= 10 && content.length <= 30) {
                return `<h3 style="margin: 16px 0 8px 0; font-size: 18px; font-weight: 600; color: #333;">${num}、${content}</h3>`;
            }
            return match;
        })
        .replace(/^\((\d+)\)\s*(.+)$/gm, function(match, num, content) {
            if (parseInt(num) <= 10 && content.length <= 30) {
                return `<h4 style="margin: 14px 0 6px 0; font-size: 16px; font-weight: 600; color: #333;">(${num}) ${content}</h4>`;
            }
            return match;
        })
        
        // 引用块（简化样式）
        .replace(/^> (.+)$/gm, '<blockquote style="margin: 16px 0; padding: 12px 16px; background: #f8f9fa; border-left: 3px solid #dee2e6; color: #6c757d;"><p style="margin: 0;">$1</p></blockquote>')
        
        // 多行引用块
        .replace(/^> (.+(?:\n> .+)*)/gm, function(match) {
            const lines = match.split('\n').map(line => line.replace(/^> /, '')).join('<br>');
            return `<blockquote style="margin: 16px 0; padding: 12px 16px; background: #f8f9fa; border-left: 3px solid #dee2e6; color: #6c757d;"><p style="margin: 0;">${lines}</p></blockquote>`;
        })
        
        // 链接和图片
        .replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1" style="max-width: 100%; height: auto; margin: 12px 0;">')
        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #007bff; text-decoration: underline;">$1</a>')
        
        // 分隔线
        .replace(/^---$/gm, '<hr style="margin: 20px 0; border: none; border-top: 1px solid #dee2e6;">')
        .replace(/^___$/gm, '<hr style="margin: 20px 0; border: none; border-top: 1px solid #dee2e6;">')
        .replace(/^\*\*\*$/gm, '<hr style="margin: 20px 0; border: none; border-top: 1px solid #dee2e6;">')
        
        // 文本装饰
        .replace(/~~([^~]+)~~/g, '<del>$1</del>')
        .replace(/==([^=]+)==/g, '<mark style="background: #fff3cd; padding: 1px 2px;">$1</mark>')
        
        // 键盘按键
        .replace(/\+([A-Za-z0-9]+)\+/g, '<kbd style="background: #e9ecef; border: 1px solid #adb5bd; border-radius: 2px; color: #495057; font-size: 0.9em; padding: 1px 4px;">$1</kbd>');

    // 处理段落
    const paragraphs = text.split('\n\n');
    return paragraphs.map(p => {
        if (!p.trim()) return '';
        
        // 检查是否是特殊元素（标题、列表、代码块等）
        if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || 
            p.startsWith('<blockquote') || p.startsWith('<div') || p.startsWith('<pre') ||
            p.startsWith('<hr') || p.startsWith('<img') || p.includes('<ol') || 
            p.includes('<ul') || p.includes('</ol>') || p.includes('</ul>') ||
            p.startsWith('<kbd') || p.includes('<mark')) {
            return p;
        }
        
        // 处理普通段落
        const processedParagraph = p.replace(/\n/g, '<br>');
        return `<p style="margin: 12px 0; line-height: 1.6;">${processedParagraph}</p>`;
    }).filter(p => p.trim() !== '').join('');
}

// 渲染有序列表的辅助函数
function renderOrderedList(items, start) {
    if (items.length === 0) return '';
    
    let html = `<ol start="${start}" style="margin: 24px 0 8px 0; padding-left: 24px; line-height: 1.6;">`;
    
    for (const item of items) {
        const specialMatch = item.match(/^([^：:]+)(：|:)(.*)$/);
        if (specialMatch) {
            const title = specialMatch[1].trim();
            const separator = specialMatch[2];
            const rest = specialMatch[3] || '';
            html += `<li style="margin: 8px 0;"><strong>${title}</strong>${separator}${rest}</li>`;
        } else {
            html += `<li style="margin: 8px 0;">${item}</li>`;
        }
    }
    
    html += '</ol>';
    return html;
}

// 渲染无序列表的辅助函数
function renderUnorderedList(items) {
    if (items.length === 0) return '';
    
    let html = `<ul style="margin: 24px 0 8px 0; padding-left: 24px; line-height: 1.6;">`;
    
    for (const item of items) {
        const specialMatch = item.match(/^([^：:]+)(：|:)(.*)$/);
        if (specialMatch) {
            const title = specialMatch[1].trim();
            const separator = specialMatch[2];
            const rest = specialMatch[3] || '';
            html += `<li style="margin: 8px 0;"><strong>${title}</strong>${separator}${rest}</li>`;
        } else {
            html += `<li style="margin: 8px 0;">${item}</li>`;
        }
    }
    
    html += '</ul>';
    return html;
} 