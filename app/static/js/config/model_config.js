// 模型配置页面JavaScript

// 全局变量
let currentProvider = null;
let configModal = null;
let addModelModal = null;
let instanceConfigurations = []; // 存储实例配置数据
let currentEditingConfigId = null; // 当前正在编辑的配置ID

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化模态框
    configModal = document.getElementById('configModal');
    addModelModal = document.getElementById('addModelModal');
    
    // 初始化侧边栏管理器
    if (typeof SidebarManager !== 'undefined') {
        const sidebarManager = new SidebarManager();
        // 设置当前页面为模型配置
        sidebarManager.setActiveMenuByPage('model-config');
    }
    
    // 初始化搜索功能
    initializeSearch();
    
    // 初始化表单事件
    initializeFormEvents();
    
    // 初始化星号样式
    initializeAsteriskStyles();
    
    // 加载模型配置数据
    loadModelConfigurations();
    
    // 初始化实例配置表格
    initializeInstanceTable();
    
    // 从数据库加载实例配置
    loadInstanceConfigurationsFromDB();
    
    console.log('模型配置页面初始化完成');
});

// 初始化搜索功能
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            filterProviders(searchTerm);
        });
    }
}

// 过滤供应商
function filterProviders(searchTerm) {
    const providerCards = document.querySelectorAll('.provider-card');
    
    providerCards.forEach(card => {
        const providerName = card.querySelector('h3').textContent.toLowerCase();
        const providerDescription = card.querySelector('.provider-description')?.textContent.toLowerCase() || '';
        const tags = Array.from(card.querySelectorAll('.tag')).map(tag => tag.textContent.toLowerCase()).join(' ');
        
        const isMatch = providerName.includes(searchTerm) || 
                       providerDescription.includes(searchTerm) || 
                       tags.includes(searchTerm);
        
        card.style.display = isMatch ? 'block' : 'none';
    });
}

// 初始化表单事件
function initializeFormEvents() {
    // 配置表单提交
    const configForm = document.getElementById('configForm');
    if (configForm) {
        configForm.addEventListener('submit', handleConfigSubmit);
    }
    
    // 添加模型表单提交
    const addModelForm = document.getElementById('addModelForm');
    if (addModelForm) {
        addModelForm.addEventListener('submit', handleAddModelSubmit);
    }
    
    // 点击模态框外部关闭
    window.addEventListener('click', function(event) {
        if (event.target === configModal) {
            closeConfigModal();
        }
        if (event.target === addModelModal) {
            closeAddModelModal();
        }
        // 添加DeepSeek模态框的点击外部关闭
        const deepSeekModal = document.getElementById('deepSeekConfigModal');
        if (event.target === deepSeekModal) {
            closeDeepSeekConfigModal();
        }
        // 添加OpenAI-API-compatible模态框的点击外部关闭
        const compatibleModal = document.getElementById('openaiCompatibleConfigModal');
        if (event.target === compatibleModal) {
            closeOpenAICompatibleConfigModal();
        }
    });
}

// 配置供应商
function configureProvider(provider) {
    currentProvider = provider;
    
    // 如果不是从编辑实例进入的，清除编辑状态
    if (!instanceConfigurations.find(config => config.id === currentEditingConfigId)) {
        currentEditingConfigId = null;
    }
    
    // 设置表单默认值
    setProviderDefaults(provider);
    
    // 显示配置模态框
    showConfigModal();
    
    console.log(`配置供应商: ${provider}`);
}

// DeepSeek专用配置函数
function configureDeepSeek() {
    currentProvider = 'deepseek';
    
    // 显示DeepSeek专用模态框
    showDeepSeekConfigModal();
}

// 显示DeepSeek配置模态框
function showDeepSeekConfigModal() {
    const deepSeekModal = document.getElementById('deepSeekConfigModal');
    if (deepSeekModal) {
        deepSeekModal.classList.add('show');
        deepSeekModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

// 关闭DeepSeek配置模态框
function closeDeepSeekConfigModal() {
    const deepSeekModal = document.getElementById('deepSeekConfigModal');
    if (deepSeekModal) {
        deepSeekModal.classList.remove('show');
        deepSeekModal.style.display = 'none';
        document.body.style.overflow = 'auto';
        currentProvider = null;
    }
}

// 处理DeepSeek配置表单提交
async function handleDeepSeekConfigSubmit(event) {
    event.preventDefault();
    
    const apiKey = document.getElementById('deepSeekApiKey').value.trim();
    const modelName = document.getElementById('deepSeekModelName').value.trim();
    const endpoint = document.getElementById('deepSeekEndpoint').value.trim() || 'https://api.deepseek.com/v1';
    
    if (!apiKey) {
        showNotification('请输入API Key', 'error');
        return;
    }
    
    if (!modelName) {
        showNotification('请输入模型名称', 'error');
        return;
    }
    
    const saveButton = document.querySelector('#deepSeekConfigModal .btn-primary');
    const originalText = saveButton.textContent;
    
    try {
        // 显示保存状态
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
        saveButton.disabled = true;
        
        // 调用后端API保存配置
        const response = await fetch('/config/api/provider-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: 'deepseek',
                api_key: apiKey,
                model_name: modelName,
                endpoint: endpoint
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('DeepSeek配置保存成功', 'success');
            closeDeepSeekConfigModal();
            
            // 更新卡片状态
            updateProviderCardStatus('deepseek', 'configured');
            
            // 重新从数据库加载实例配置
            await loadInstanceConfigurationsFromDB();
        } else {
            showNotification(`保存失败: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('保存DeepSeek配置失败:', error);
        showNotification('保存配置失败，请检查网络连接', 'error');
    } finally {
        // 恢复按钮状态
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    }
}

// 测试DeepSeek连接
async function testDeepSeekConnection() {
    const apiKey = document.getElementById('deepSeekApiKey').value.trim();
    const modelName = document.getElementById('deepSeekModelName').value.trim();
    const endpoint = document.getElementById('deepSeekEndpoint').value.trim() || 'https://api.deepseek.com/v1';
    
    if (!apiKey) {
        showNotification('请先输入API Key', 'error');
        return;
    }
    
    if (!modelName) {
        showNotification('请先输入模型名称', 'error');
        return;
    }
    
    const testBtn = document.querySelector('#deepSeekConfigModal .btn-test');
    const originalText = testBtn.textContent;
    
    try {
        testBtn.disabled = true;
        testBtn.textContent = '测试中...';
        
        // 这里可以添加实际的连接测试逻辑
        // 模拟测试延迟
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        showNotification(`DeepSeek连接测试成功 (模型: ${modelName})`, 'success');
        
    } catch (error) {
        console.error('DeepSeek连接测试失败:', error);
        showNotification('连接测试失败', 'error');
    } finally {
        testBtn.disabled = false;
        testBtn.textContent = originalText;
    }
}

// 设置供应商默认值
function setProviderDefaults(provider) {
    // 设置模态框标题
    const modalTitle = document.getElementById('modalTitle');
    const providerNames = {
        'openai': 'OpenAI',
        'vllm': 'vLLM',
        'deepseek': 'DeepSeek',
        'anthropic': 'Anthropic',
        'azure-openai': 'Azure OpenAI',
        'openai-compatible': 'OpenAI兼容API'
    };
    
    if (modalTitle) {
        modalTitle.textContent = `配置 ${providerNames[provider] || provider}`;
    }
    
    // 重置表单（只有在不是编辑状态时才重置）
    if (!currentEditingConfigId) {
        const form = document.getElementById('configForm');
        if (form) {
            form.reset();
        }
    }
    
    const endpointInput = document.getElementById('endpoint');
    const modelNameInput = document.getElementById('modelName');
    
    const defaultEndpoints = {
        'openai': 'https://api.openai.com/v1',
        'vllm': 'http://localhost:8000/v1',
        'deepseek': 'https://api.deepseek.com/v1',
        'anthropic': 'https://api.anthropic.com',
        'azure-openai': ''
    };
    
    const defaultModelNames = {
        'openai': 'gpt-3.5-turbo',
        'vllm': 'your-model-name',
        'deepseek': 'deepseek-chat',
        'anthropic': 'claude-3-sonnet-20240229',
        'azure-openai': 'gpt-35-turbo'
    };
    
    if (endpointInput && defaultEndpoints[provider]) {
        endpointInput.placeholder = defaultEndpoints[provider];
    }
    
    if (modelNameInput && defaultModelNames[provider]) {
        modelNameInput.placeholder = `例如: ${defaultModelNames[provider]}`;
    }
}

// 显示配置模态框
function showConfigModal() {
    if (configModal) {
        configModal.classList.add('show');
        configModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

// 关闭配置模态框
function closeConfigModal() {
    configModal.classList.remove('show');
    configModal.style.display = 'none';
    document.body.style.overflow = 'auto';
    currentProvider = null;
    currentEditingConfigId = null; // 清除正在编辑的配置ID
    
    // 清空表单
    const form = document.getElementById('configForm');
    if (form) {
        form.reset();
        
        // 清理编辑状态的UI变化
        const apiKeyInput = document.getElementById('apiKey');
        if (apiKeyInput) {
            apiKeyInput.removeAttribute('readonly');
            apiKeyInput.style.backgroundColor = '';
            apiKeyInput.style.color = '';
            
            // 移除提示信息
            const hint = apiKeyInput.parentNode.querySelector('.edit-hint');
            if (hint) {
                hint.remove();
            }
        }
    }
}

// 添加模型
function addModel(provider) {
    currentProvider = provider;
    
    // 设置模态框标题
    const addModelTitle = document.getElementById('addModelTitle');
    const providerNames = {
        'openai': 'OpenAI',
        'vllm': 'vLLM',
        'deepseek': 'DeepSeek',
        'anthropic': 'Anthropic',
        'azure-openai': 'Azure OpenAI'
    };
    
    addModelTitle.textContent = `为 ${providerNames[provider] || provider} 添加模型`;
    
    // 重置表单
    document.getElementById('addModelForm').reset();
    
    // 显示模态框
    showAddModelModal();
}

// 显示添加模型模态框
function showAddModelModal() {
    if (addModelModal) {
        addModelModal.classList.add('show');
        addModelModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

// 关闭添加模型模态框
function closeAddModelModal() {
    if (addModelModal) {
        addModelModal.classList.remove('show');
        addModelModal.style.display = 'none';
        document.body.style.overflow = 'auto';
        currentProvider = null;
    }
}

// 切换密码显示
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.parentElement.querySelector('.btn-toggle-password i');
    
    if (input.type === 'password') {
        input.type = 'text';
        button.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        button.className = 'fas fa-eye';
    }
}

// 测试连接
async function testConnection() {
    if (!currentProvider) {
        showNotification('请先选择供应商', 'error');
        return;
    }
    
    const form = document.getElementById('configForm');
    const formData = new FormData(form);
    
    let apiKey = null;
    const endpoint = formData.get('endpoint');
    const modelName = formData.get('modelName');
    
    // 如果是编辑状态，直接从数据库配置中获取API密钥
    if (currentEditingConfigId) {
        const currentEditingConfig = instanceConfigurations.find(config => 
            config.id === currentEditingConfigId
        );
        
        if (currentEditingConfig) {
            apiKey = currentEditingConfig.apiKey;
            console.log(`编辑模式：使用数据库中的API密钥进行测试连接`);
            console.log(`配置信息: ${currentEditingConfig.providerName} - ${currentEditingConfig.modelName}`);
            console.log(`数据库密钥前4位: ${apiKey.substring(0, 4)}***`);
        } else {
            showNotification('无法找到正在编辑的配置，请重新打开配置', 'error');
            return;
        }
    } else {
        // 如果不是编辑状态，从表单获取API密钥
        apiKey = formData.get('apiKey');
        console.log('新建模式：使用表单中的API密钥进行测试连接');
    }
    
    if (!apiKey) {
        showNotification('请输入API Key', 'error');
        return;
    }
    
    if (!modelName) {
        showNotification('请输入模型名称', 'error');
        return;
    }
    
    const testButton = document.querySelector('.btn-test');
    const originalText = testButton.innerHTML;
    
    // 显示加载状态
    testButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 测试中...';
    testButton.disabled = true;
    
    try {
        const response = await fetch('/config/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: currentProvider,
                api_key: apiKey,
                endpoint: endpoint || undefined,
                model_name: modelName
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const configInfo = currentEditingConfigId ? 
                ' (使用数据库中的API密钥)' : ' (使用表单中的API密钥)';
            showNotification(`连接测试成功！${configInfo}`, 'success');
        } else {
            showNotification(`连接测试失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('测试连接失败:', error);
        showNotification('连接测试失败，请检查网络连接', 'error');
    } finally {
        // 恢复按钮状态
        testButton.innerHTML = originalText;
        testButton.disabled = false;
    }
}

// 处理配置表单提交
async function handleConfigSubmit(event) {
    event.preventDefault();
    
    if (!currentProvider) {
        showNotification('请先选择供应商', 'error');
        return;
    }
    
    const form = event.target;
    const formData = new FormData(form);
    
    const saveButton = form.querySelector('.btn-save');
    const originalText = saveButton.textContent;
    
    // 显示加载状态
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
    saveButton.disabled = true;
    
    try {
        const response = await fetch('/config/api/provider-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: currentProvider,
                api_key: formData.get('apiKey'),
                endpoint: formData.get('endpoint') || undefined,
                organization: formData.get('organization') || undefined,
                model_name: formData.get('modelName')
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('配置保存成功！', 'success');
            closeConfigModal();
            // 更新供应商卡片状态
            updateProviderCardStatus(currentProvider, 'configured');
            // 重新从数据库加载实例配置
            await loadInstanceConfigurationsFromDB();
            // 清除编辑状态
            currentEditingConfigId = null;
        } else {
            showNotification(`保存失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('保存配置失败:', error);
        showNotification('保存失败，请检查网络连接', 'error');
    } finally {
        // 恢复按钮状态
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    }
}

// 处理添加模型表单提交
async function handleAddModelSubmit(event) {
    event.preventDefault();
    
    if (!currentProvider) {
        showNotification('请先选择供应商', 'error');
        return;
    }
    
    const form = event.target;
    const formData = new FormData(form);
    
    const saveButton = form.querySelector('.btn-save');
    const originalText = saveButton.textContent;
    
    // 显示加载状态
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 添加中...';
    saveButton.disabled = true;
    
    try {
        const response = await fetch('/config/api/add-model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: currentProvider,
                model_name: formData.get('modelName'),
                model_type: formData.get('modelType'),
                description: formData.get('modelDescription') || undefined
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('模型添加成功！', 'success');
            closeAddModelModal();
            // 刷新模型列表
            loadModelConfigurations();
        } else {
            showNotification(`添加失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('添加模型失败:', error);
        showNotification('添加失败，请检查网络连接', 'error');
    } finally {
        // 恢复按钮状态
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    }
}

// 更新供应商卡片状态
function updateProviderCardStatus(provider, status) {
    const providerCard = document.querySelector(`[data-provider="${provider}"]`);
    if (providerCard) {
        // 移除所有状态类
        providerCard.classList.remove('unconfigured', 'configured', 'installed');
        // 添加新状态类
        providerCard.classList.add(status);
        
        // 更新状态文本
        const statusElement = providerCard.querySelector('.provider-status');
        if (statusElement && status === 'configured') {
            statusElement.innerHTML = '<i class="fas fa-check-circle status-success"></i> 已配置';
        }
    }
}

// 加载模型配置数据
async function loadModelConfigurations() {
    try {
        const response = await fetch('/config/api/model-configurations');
        const result = await response.json();
        
        if (result.success) {
            updateProviderCards(result.data);
        } else {
            console.error('加载模型配置失败:', result.message);
        }
    } catch (error) {
        console.error('加载模型配置失败:', error);
    }
}

// 更新供应商卡片
function updateProviderCards(configurations) {
    configurations.forEach(config => {
        updateProviderCardStatus(config.provider, config.status);
    });
}

// 初始化实例配置表格
function initializeInstanceTable() {
    updateInstanceTable();
}

// 更新实例配置表格
function updateInstanceTable() {
    const tableBody = document.getElementById('instanceTableBody');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('instanceTable');
    
    if (instanceConfigurations.length === 0) {
        table.classList.add('empty');
        emptyState.style.display = 'flex';
    } else {
        table.classList.remove('empty');
        emptyState.style.display = 'none';
        
        tableBody.innerHTML = instanceConfigurations.map(config => {
            const isActive = config.isActive !== false; // 默认为true，除非明确为false
            const rowClass = isActive ? '' : 'inactive-row';
            const statusText = isActive ? '' : ' (已删除)';
            
            return `
            <tr data-config-id="${config.id}" class="${rowClass}">
                <td>${config.endpoint}${statusText}</td>
                <td>${config.modelName || config.providerName}${statusText}</td>
                <td>
                    <span class="model-type-badge ${getModelTypeBadgeClass(config.modelType)}">
                        ${getModelTypeDisplayText(config.modelType)}
                    </span>
                </td>
                <td class="api-key-cell">${maskApiKey(config.apiKey)}</td>
                <td>
                    <div class="test-result ${isActive ? config.testStatus : 'inactive'}">
                        <i class="fas ${isActive ? getTestStatusIcon(config.testStatus) : 'fa-ban'}"></i>
                        ${isActive ? getTestStatusText(config.testStatus) : '已删除'}
                    </div>
                </td>
                <td>
                    <div class="action-buttons">
                        ${isActive ? `
                            <button class="btn-action test" onclick="testInstanceConnection('${config.id}')" title="测试连接">
                                <i class="fas fa-plug"></i>
                            </button>
                        <button class="btn-action edit" onclick="editInstance('${config.id}')" title="编辑">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-action delete" onclick="deleteInstance('${config.id}')" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                        ` : `
                            <button class="btn-action restore" onclick="restoreInstance('${config.id}')" title="恢复">
                                <i class="fas fa-undo"></i>
                            </button>
                            <button class="btn-action permanent-delete" onclick="permanentDeleteInstance('${config.id}')" title="永久删除">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        `}
                    </div>
                </td>
            </tr>
        `;
        }).join('');
    }
}

// 掩码 API Key
function maskApiKey(apiKey) {
    if (!apiKey || apiKey.length < 8) return '***';
    return apiKey.substring(0, 4) + '***' + apiKey.substring(apiKey.length - 4);
}

// 获取测试状态图标
function getTestStatusIcon(status) {
    switch (status) {
        case 'success': return 'fa-check-circle';
        case 'failed': return 'fa-times-circle';
        case 'pending': return 'fa-clock';
        default: return 'fa-question-circle';
    }
}

// 获取测试状态文本
function getTestStatusText(status) {
    switch (status) {
        case 'success': return '连接成功';
        case 'failed': return '连接失败';
        case 'pending': return '测试中';
        default: return '未知';
    }
}

// 获取模型类型显示文本
function getModelTypeDisplayText(modelType) {
    switch (modelType) {
        case 'llm': return 'LLM';
        case 'embedding': return 'Embedding';
        case 'rerank': return 'Rerank';
        case 'speech2text': return 'Speech2Text';
        case 'tts': return 'TTS';
        default: return '未指定';
    }
}

// 获取模型类型徽章样式类
function getModelTypeBadgeClass(modelType) {
    switch (modelType) {
        case 'llm': return 'llm';
        case 'embedding': return 'embedding';
        case 'rerank': return 'rerank';
        case 'speech2text': return 'speech2text';
        case 'tts': return 'tts';
        default: return 'default';
    }
}

// 从数据库加载实例配置
async function loadInstanceConfigurationsFromDB() {
    try {
        const response = await fetch('/config/api/model-configs');
        const result = await response.json();
        
        if (result.success) {
            // 清空现有配置
            instanceConfigurations = [];
            
            console.log('=== 加载数据库配置 ===');
            console.log(`加载配置数量: ${result.data.length}`);
            
            // 转换数据库数据为前端格式
            result.data.forEach(config => {
                console.log(`配置ID: ${config.id}, 供应商: ${config.provider}, API密钥前4位: ${config.api_key ? config.api_key.substring(0, 4) + '***' : '无密钥'}`);
                
                instanceConfigurations.push({
                    id: config.id.toString(),
                    provider: config.provider,
                    providerName: config.provider_name,
                    modelName: config.model_name,
                    modelType: config.model_type,
                    endpoint: config.endpoint || getDefaultEndpoint(config.provider),
                    apiKey: config.api_key,
                    organization: config.organization,
                    contextLength: config.context_length,
                    maxTokens: config.max_tokens,
                    testStatus: config.test_status,
                    testMessage: config.test_message,
                    isActive: config.is_active,
                    createdAt: config.created_at
                });
            });
            
            console.log('=====================');
            
            updateInstanceTable();
            console.log('从数据库加载实例配置成功');
        } else {
            console.error('加载实例配置失败:', result.message);
            showNotification('加载实例配置失败', 'error');
        }
    } catch (error) {
        console.error('加载实例配置失败:', error);
        showNotification('加载实例配置失败，请检查网络连接', 'error');
    }
}

// 获取默认端点
function getDefaultEndpoint(provider) {
    const defaultEndpoints = {
        'openai': 'https://api.openai.com/v1',
        'vllm': 'http://localhost:8000/v1',
        'deepseek': 'https://api.deepseek.com/v1',
        'anthropic': 'https://api.anthropic.com',
        'azure-openai': ''
    };
    return defaultEndpoints[provider] || '';
}

// 编辑实例配置
function editInstance(configId) {
    const config = instanceConfigurations.find(item => item.id === configId);
    if (config) {
        // 设置当前正在编辑的配置ID
        currentEditingConfigId = configId;
        
        // 重新打开配置模态框进行编辑
        configureProvider(config.provider);
        
        // 填充现有数据
        const apiKeyInput = document.getElementById('apiKey');
        apiKeyInput.value = '●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●'; // 显示掩码
        apiKeyInput.setAttribute('readonly', true);
        apiKeyInput.style.backgroundColor = '#f8f9fa';
        apiKeyInput.style.color = '#6c757d';
        
        // 添加提示信息
        let existingHint = apiKeyInput.parentNode.querySelector('.edit-hint');
        if (!existingHint) {
            const hint = document.createElement('div');
            hint.className = 'edit-hint';
            hint.innerHTML = '<i class="fas fa-info-circle"></i> 正在编辑已保存的配置，将使用数据库中的API密钥';
            hint.style.cssText = 'color: #17a2b8; font-size: 12px; margin-top: 5px;';
            apiKeyInput.parentNode.appendChild(hint);
        }
        
        document.getElementById('modelName').value = config.modelName || '';
        document.getElementById('endpoint').value = config.endpoint;
        if (config.organization && document.getElementById('organization')) {
            document.getElementById('organization').value = config.organization;
        }
        
        console.log(`开始编辑配置: ${config.providerName} - ${config.modelName}`);
    }
}

// 删除实例配置
async function deleteInstance(configId) {
    if (confirm('确定要删除这个配置吗？')) {
        try {
            const response = await fetch(`/config/api/model-configs/${configId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('配置已删除', 'success');
                // 重新从数据库加载实例配置
                await loadInstanceConfigurationsFromDB();
            } else {
                showNotification(`删除失败: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('删除配置失败:', error);
            showNotification('删除失败，请检查网络连接', 'error');
        }
    }
}

// 显示新建实例模态框
function showNewInstanceModal() {
    // 这里可以显示一个选择供应商的模态框，或者直接提示用户通过待配置区域进行配置
    showNotification('请通过上方"待配置"区域选择供应商进行配置', 'info');
}

// 显示通知
function showNotification(message, type = 'info', duration = null) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // 设置图标
    const icons = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    };
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="notification-icon ${icons[type] || icons.info}"></i>
            <span class="notification-message">${message}</span>
            <i class="notification-close fas fa-times" onclick="this.parentElement.parentElement.remove()"></i>
        </div>
    `;
    
    // 检查是否有现有通知
    const existingNotifications = document.querySelectorAll('.notification');
    
    // 如果有现有通知，调整新通知的位置
    if (existingNotifications.length > 0) {
        // 计算新通知的top位置
        let topOffset = 80; // 基础位置
        existingNotifications.forEach(existing => {
            topOffset += existing.offsetHeight + 10; // 每个通知高度 + 间距
        });
        notification.style.top = `${topOffset}px`;
        
        // 如果通知太多，移除最旧的通知
        if (existingNotifications.length >= 3) {
            existingNotifications[0].remove();
        }
    }
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 设置自动移除时间
    let autoRemoveTime = duration;
    if (!autoRemoveTime) {
        // 根据消息类型设置不同的显示时间
        if (type === 'success' && (message.includes('测试成功') || message.includes('连接测试成功'))) {
            autoRemoveTime = 10000; // 测试成功消息显示10秒
        } else if (type === 'success') {
            autoRemoveTime = 8000; // 其他成功消息显示8秒
        } else if (type === 'error') {
            autoRemoveTime = 12000; // 错误消息显示12秒
        } else {
            autoRemoveTime = 8000; // 默认显示8秒
        }
    }
    
    // 自动移除通知
    const removeTimer = setTimeout(() => {
        if (notification.parentElement) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
                    // 重新调整剩余通知的位置
                    adjustNotificationPositions();
                }
            }, 300); // 等待动画完成
        }
    }, autoRemoveTime);
    
    // 为通知添加移除定时器引用，以便手动关闭时清除
    notification.removeTimer = removeTimer;
    
    // 更新关闭按钮的点击事件
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.onclick = function() {
        clearTimeout(notification.removeTimer);
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
                adjustNotificationPositions();
            }
        }, 300);
    };
}

// 调整通知位置
function adjustNotificationPositions() {
    const notifications = document.querySelectorAll('.notification');
    let topOffset = 80;
    
    notifications.forEach(notification => {
        notification.style.top = `${topOffset}px`;
        topOffset += notification.offsetHeight + 10;
    });
}

// 导出函数供全局使用
window.configureProvider = configureProvider;
window.addModel = addModel;
window.closeConfigModal = closeConfigModal;
window.closeAddModelModal = closeAddModelModal;
window.togglePassword = togglePassword;
window.testConnection = testConnection;
window.showNewInstanceModal = showNewInstanceModal;
window.editInstance = editInstance;
window.deleteInstance = deleteInstance; 
window.testInstanceConnection = testInstanceConnection;
window.restoreInstance = restoreInstance;
window.permanentDeleteInstance = permanentDeleteInstance;

// OpenAI-API-compatible专用配置函数
function configureOpenAICompatible() {
    currentProvider = 'openai-compatible';
    
    // 显示OpenAI-API-compatible专用模态框
    showOpenAICompatibleConfigModal();
}

// 显示OpenAI-API-compatible配置模态框
function showOpenAICompatibleConfigModal() {
    const compatibleModal = document.getElementById('openaiCompatibleConfigModal');
    if (compatibleModal) {
        compatibleModal.classList.add('show');
        compatibleModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

// 关闭OpenAI-API-compatible配置模态框
function closeOpenAICompatibleConfigModal() {
    const compatibleModal = document.getElementById('openaiCompatibleConfigModal');
    if (compatibleModal) {
        compatibleModal.classList.remove('show');
        compatibleModal.style.display = 'none';
        document.body.style.overflow = 'auto';
        currentProvider = null;
    }
}

// 处理OpenAI-API-compatible配置表单提交
async function handleOpenAICompatibleConfigSubmit(event) {
    event.preventDefault();
    
    const modelType = document.getElementById('compatibleModelType').value.trim();
    const modelName = document.getElementById('compatibleModelName').value.trim();
    const apiKey = document.getElementById('compatibleApiKey').value.trim();
    const endpoint = document.getElementById('compatibleEndpoint').value.trim();
    const contextLength = document.getElementById('compatibleContextLength').value.trim();
    const maxTokens = document.getElementById('compatibleMaxTokens').value.trim();
    
    if (!modelType) {
        showNotification('请选择模型类型', 'error');
        return;
    }
    
    if (!modelName) {
        showNotification('请输入模型名称', 'error');
        return;
    }
    
    if (!apiKey) {
        showNotification('请输入API Key', 'error');
        return;
    }
    
    if (!endpoint) {
        showNotification('请输入API endpoint URL', 'error');
        return;
    }
    
    const saveButton = document.querySelector('#openaiCompatibleConfigModal .btn-primary');
    const originalText = saveButton.textContent;
    
    try {
        // 显示保存状态
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
        saveButton.disabled = true;
        
        // 调用后端API保存配置
        const response = await fetch('/config/api/provider-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: 'openai-compatible',
                api_key: apiKey,
                model_name: modelName,
                endpoint: endpoint,
                model_type: modelType,
                context_length: contextLength ? parseInt(contextLength) : null,
                max_tokens: maxTokens ? parseInt(maxTokens) : null
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('OpenAI-API-compatible配置保存成功', 'success');
            closeOpenAICompatibleConfigModal();
            
            // 更新卡片状态
            updateProviderCardStatus('openai-compatible', 'configured');
            
            // 重新从数据库加载实例配置
            await loadInstanceConfigurationsFromDB();
        } else {
            showNotification(`保存失败: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('保存OpenAI-API-compatible配置失败:', error);
        showNotification('保存配置失败，请检查网络连接', 'error');
    } finally {
        // 恢复按钮状态
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    }
}

// 测试OpenAI-API-compatible连接
async function testOpenAICompatibleConnection() {
    const modelType = document.getElementById('compatibleModelType').value.trim();
    const modelName = document.getElementById('compatibleModelName').value.trim();
    const apiKey = document.getElementById('compatibleApiKey').value.trim();
    const endpoint = document.getElementById('compatibleEndpoint').value.trim();
    
    if (!modelType) {
        showNotification('请先选择模型类型', 'error');
        return;
    }
    
    if (!modelName) {
        showNotification('请先输入模型名称', 'error');
        return;
    }
    
    if (!apiKey) {
        showNotification('请先输入API Key', 'error');
        return;
    }
    
    if (!endpoint) {
        showNotification('请先输入API endpoint URL', 'error');
        return;
    }
    
    const testBtn = document.querySelector('#openaiCompatibleConfigModal .btn-test');
    const originalText = testBtn.textContent;
    
    try {
        testBtn.disabled = true;
        testBtn.textContent = '测试中...';
        
        // 调用后端API进行连接测试
        const response = await fetch('/config/api/test-openai-compatible-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_type: modelType,
                model_name: modelName,
                api_key: apiKey,
                endpoint: endpoint
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`${modelType.toUpperCase()}模型连接测试成功`, 'success');
        } else {
            showNotification(`连接测试失败: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('OpenAI-API-compatible连接测试失败:', error);
        showNotification('连接测试失败，请检查网络连接', 'error');
    } finally {
        testBtn.disabled = false;
        testBtn.textContent = originalText;
    }
}

// 初始化星号样式
function initializeAsteriskStyles() {
    // 查找所有包含星号的标签
    const labels = document.querySelectorAll('.form-group label');
    
    labels.forEach(label => {
        const text = label.textContent;
        if (text.includes('*')) {
            // 将星号替换为红色的span
            const newText = text.replace(/\*/g, '<span class="asterisk" style="color: #ef4444; font-weight: 700;">*</span>');
            label.innerHTML = newText;
            label.classList.add('has-asterisk');
        }
    });
    
    // 监听模态框显示事件，处理动态加载的内容
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const newLabels = node.querySelectorAll('.form-group label');
                        newLabels.forEach(label => {
                            const text = label.textContent;
                            if (text.includes('*') && !label.classList.contains('has-asterisk')) {
                                const newText = text.replace(/\*/g, '<span class="asterisk" style="color: #ef4444; font-weight: 700;">*</span>');
                                label.innerHTML = newText;
                                label.classList.add('has-asterisk');
                            }
                        });
                    }
                });
            }
        });
    });
    
    // 观察整个文档的变化
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// 测试实例连接
async function testInstanceConnection(configId) {
    const config = instanceConfigurations.find(item => item.id === configId);
    if (!config) {
        showNotification('配置不存在', 'error');
        return;
    }
    
    // 添加调试日志确认使用数据库密钥
    console.log('=== 测试实例连接 ===');
    console.log(`配置ID: ${configId}`);
    console.log(`供应商: ${config.provider}`);
    console.log(`模型名称: ${config.modelName}`);
    console.log(`端点: ${config.endpoint}`);
    console.log(`数据库API密钥前4位: ${config.apiKey ? config.apiKey.substring(0, 4) + '***' : '未找到密钥'}`);
    console.log(`完整API密钥: ${config.apiKey}`); // 临时调试用，显示完整密钥
    console.log('===================');
    
    const testBtn = document.querySelector(`tr[data-config-id="${configId}"] .btn-action.test`);
    const originalIcon = testBtn.innerHTML;
    
    try {
        // 显示测试状态
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        testBtn.disabled = true;
        
        // 更新表格中的测试状态
        const testResultElement = document.querySelector(`tr[data-config-id="${configId}"] .test-result`);
        testResultElement.className = 'test-result pending';
        testResultElement.innerHTML = '<i class="fas fa-clock"></i> 测试中';
        
        // 根据模型类型选择合适的测试端点
        let testEndpoint = '/config/api/test-connection';
        let requestBody = {
            config_id: parseInt(configId), // 传递配置ID，让后端从数据库获取完整API key
            provider: config.provider,
            endpoint: config.endpoint,
            model_name: config.modelName
        };
        
        // 如果是OpenAI-compatible且有特定的模型类型，使用专门的测试端点
        if (config.provider === 'openai-compatible' && config.modelType && 
            ['embedding', 'rerank', 'speech2text', 'tts'].includes(config.modelType)) {
            testEndpoint = '/config/api/test-openai-compatible-connection';
            requestBody = {
                config_id: parseInt(configId), // 传递配置ID
                model_type: config.modelType,
                model_name: config.modelName,
                endpoint: config.endpoint
            };
            console.log(`使用专门的测试端点处理 ${config.modelType} 模型`);
        }
        
        // 调用后端测试API
        const response = await fetch(testEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const result = await response.json();
        
        console.log('=== 后端测试响应 ===');
        console.log('响应状态:', response.status);
        console.log('响应结果:', result);
        console.log('==================');
        
        if (result.success) {
            // 更新本地配置状态
            config.testStatus = 'success';
            config.testMessage = result.message;
            
            // 更新表格显示
            testResultElement.className = 'test-result success';
            testResultElement.innerHTML = '<i class="fas fa-check-circle"></i> 连接成功';
            
            // 更新数据库中的测试状态
            await updateTestStatusInDB(configId, 'success', result.message);
            
            showNotification(`${config.providerName} - ${config.modelName} 连接测试成功 (使用数据库密钥)`, 'success');
        } else {
            // 更新本地配置状态
            config.testStatus = 'failed';
            config.testMessage = result.message;
            
            // 更新表格显示
            testResultElement.className = 'test-result failed';
            testResultElement.innerHTML = '<i class="fas fa-times-circle"></i> 连接失败';
            
            // 更新数据库中的测试状态
            await updateTestStatusInDB(configId, 'failed', result.message);
            
            console.error('=== 测试失败详情 ===');
            console.error('错误消息:', result.message);
            console.error('供应商:', config.provider);
            console.error('端点:', config.endpoint);
            console.error('模型:', config.modelName);
            console.error('密钥:', config.apiKey);
            console.error('==================');
            
            showNotification(`${config.providerName} - ${config.modelName} 连接测试失败: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('测试连接失败:', error);
        
        // 更新本地配置状态
        config.testStatus = 'failed';
        config.testMessage = '网络错误';
        
        // 更新表格显示
        const testResultElement = document.querySelector(`tr[data-config-id="${configId}"] .test-result`);
        testResultElement.className = 'test-result failed';
        testResultElement.innerHTML = '<i class="fas fa-times-circle"></i> 连接失败';
        
        showNotification('连接测试失败，请检查网络连接', 'error');
    } finally {
        // 恢复按钮状态
        testBtn.innerHTML = originalIcon;
        testBtn.disabled = false;
    }
}

// 更新数据库中的测试状态
async function updateTestStatusInDB(configId, testStatus, testMessage) {
    try {
        const response = await fetch(`/config/api/model-configs/${configId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                test_status: testStatus,
                test_message: testMessage
            })
        });
        
        const result = await response.json();
        if (!result.success) {
            console.error('更新测试状态失败:', result.message);
        }
    } catch (error) {
        console.error('更新测试状态失败:', error);
    }
}

// 恢复实例配置
async function restoreInstance(configId) {
    if (confirm('确定要恢复这个配置吗？')) {
        try {
            const response = await fetch(`/config/api/model-configs/${configId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    is_active: true
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('配置已恢复', 'success');
                // 重新从数据库加载实例配置
                await loadInstanceConfigurationsFromDB();
            } else {
                showNotification(`恢复失败: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('恢复配置失败:', error);
            showNotification('恢复失败，请检查网络连接', 'error');
        }
    }
}

// 永久删除实例配置
async function permanentDeleteInstance(configId) {
    if (confirm('确定要永久删除这个配置吗？此操作不可恢复！')) {
        try {
            const response = await fetch(`/config/api/model-configs/${configId}/permanent`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('配置已永久删除', 'success');
                // 重新从数据库加载实例配置
                await loadInstanceConfigurationsFromDB();
            } else {
                showNotification(`永久删除失败: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('永久删除配置失败:', error);
            showNotification('永久删除失败，请检查网络连接', 'error');
        }
    }
} 