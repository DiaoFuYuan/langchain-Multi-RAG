/**
 * 智能体配置页面 JavaScript
 * 负责页面交互逻辑、数据管理和用户操作处理
 */

// 全局变量
let agentConfig = {
    id: 0,
    name: '',
    description: '',
    problem_description: '',
    answer_description: '',
    category: 'other',
    template: 'simple',
    system_prompt: '',
    is_public: false,
    model_settings: {
        model: 'deepseek-r1-32b',
        temperature: 0.7,
        max_tokens: 4096,
        top_p: 0.95
    },
    tools: {
        web_search: false,
        calculator: false,
        time_tool: false,
        code_execution: false,
        file_upload: false,
        voice_input: false
    },
    knowledge_bases: [],
    variables: [],
    opening_message: '我是你的智能助手，你可以问我：\n[你的主要职责是什么？]'
};

// 提示词模板
const promptTemplates = {
    customer_service: `你是一个专业的客服助手。

请遵循以下原则：
- 始终保持礼貌和耐心
- 快速准确地回答用户问题
- 如果无法解决问题，及时转接人工客服
- 记录用户反馈并持续改进服务质量`,

    teacher: `你是一个专业的教学助手。

请遵循以下原则：
- 用简单易懂的语言解释复杂概念
- 鼓励学生思考和提问
- 提供实例和练习来加深理解
- 根据学生水平调整教学方式`,

    writer: `你是一个专业的写作助手。

请遵循以下原则：
- 帮助用户改进文章结构和表达
- 提供创意和灵感
- 检查语法和拼写错误
- 根据不同文体调整写作风格`,

    analyst: `你是一个专业的数据分析师。

请遵循以下原则：
- 客观分析数据和趋势
- 提供清晰的图表和可视化建议
- 解释分析方法和结论
- 基于数据提出可行的建议`
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initConfigPage();
    bindEvents();
    loadKnowledgeBases();
    
    // 如果有智能体数据，填充表单
    if (window.agentData) {
        populateForm(window.agentData);
    }
});

/**
 * 初始化配置页面
 */
function initConfigPage() {
    console.log('初始化智能体配置页面');
    
    // 设置侧边栏激活状态
    setTimeout(() => {
        if (window.sidebarManager) {
            window.sidebarManager.setActiveMenuByPage('agent-quick');
        }
    }, 100);
}

/**
 * 绑定事件监听器
 */
function bindEvents() {
    // 表单输入事件
    bindInputEvents();
    
    // 工具开关事件
    bindToolEvents();
    
    // 聊天输入事件
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendTestMessage();
            }
        });
    }
    
    // 点击外部关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            closeAllDropdowns();
        }
    });
}

/**
 * 绑定输入事件
 */
function bindInputEvents() {
    // 问题描述
    const problemDescription = document.getElementById('problemDescription');
    if (problemDescription) {
        problemDescription.addEventListener('input', function() {
            updateConfig('problem_description', this.value);
        });
    }
    
    // 回答描述
    const answerDescription = document.getElementById('answerDescription');
    if (answerDescription) {
        answerDescription.addEventListener('input', function() {
            updateConfig('answer_description', this.value);
        });
    }
    
    // 模型选择
    const modelSelect = document.getElementById('modelSelect');
    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            updateConfig('model_settings.model', this.value);
        });
    }
    
    // 系统提示词
    const systemPrompt = document.getElementById('systemPrompt');
    if (systemPrompt) {
        systemPrompt.addEventListener('input', function() {
            updateConfig('system_prompt', this.value);
        });
    }
}

/**
 * 绑定工具事件
 */
function bindToolEvents() {
    // 文件上传开关
    const fileUploadEnabled = document.getElementById('fileUploadEnabled');
    if (fileUploadEnabled) {
        fileUploadEnabled.addEventListener('change', function() {
            updateConfig('tools.file_upload', this.checked);
            updateToolStatus('file_upload', this.checked);
        });
    }
    
    // 语音输入开关
    const voiceInputEnabled = document.getElementById('voiceInputEnabled');
    if (voiceInputEnabled) {
        voiceInputEnabled.addEventListener('change', function() {
            updateConfig('tools.voice_input', this.checked);
        });
    }
}

/**
 * 填充表单数据
 */
function populateForm(agentData) {
    agentConfig.id = agentData.id;
    agentConfig.name = agentData.name;
    agentConfig.description = agentData.description;
    agentConfig.problem_description = agentData.problem_description || '';
    agentConfig.answer_description = agentData.answer_description || '';
    agentConfig.category = agentData.category;
    agentConfig.template = agentData.template;
    agentConfig.system_prompt = agentData.system_prompt;
    agentConfig.is_public = agentData.is_public;
    
    // 填充表单字段
    const problemDescription = document.getElementById('problemDescription');
    if (problemDescription) {
        problemDescription.value = agentConfig.problem_description;
    }
    
    const answerDescription = document.getElementById('answerDescription');
    if (answerDescription) {
        answerDescription.value = agentConfig.answer_description;
    }
    
    const systemPrompt = document.getElementById('systemPrompt');
    if (systemPrompt) {
        systemPrompt.value = agentConfig.system_prompt;
    }
    
    const modelSelect = document.getElementById('modelSelect');
    if (modelSelect) {
        modelSelect.value = agentConfig.model_settings.model;
    }
}

/**
 * 更新配置
 */
function updateConfig(path, value) {
    const keys = path.split('.');
    let obj = agentConfig;
    
    for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) {
            obj[keys[i]] = {};
        }
        obj = obj[keys[i]];
    }
    
    obj[keys[keys.length - 1]] = value;
    console.log('配置已更新:', path, '=', value);
}

/**
 * 更新工具状态显示
 */
function updateToolStatus(toolName, enabled) {
    // 这里可以更新工具状态的显示
    console.log(`工具 ${toolName} ${enabled ? '已启用' : '已禁用'}`);
}

/**
 * 加载知识库列表
 */
async function loadKnowledgeBases() {
    try {
        const response = await fetch('/knowledge/api/knowledge-bases');
        if (response.ok) {
            const data = await response.json();
            renderKnowledgeBases(data.knowledge_bases || []);
        }
    } catch (error) {
        console.error('加载知识库失败:', error);
    }
}

/**
 * 渲染知识库列表
 */
function renderKnowledgeBases(knowledgeBases) {
    const knowledgeList = document.getElementById('knowledgeList');
    if (!knowledgeList) return;
    
    if (knowledgeBases.length === 0) {
        knowledgeList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-plus-circle"></i>
                <span>暂无关联知识库</span>
            </div>
        `;
        return;
    }
    
    knowledgeList.innerHTML = knowledgeBases.map(kb => `
        <div class="knowledge-item">
            <input type="checkbox" id="kb_${kb.id}" onchange="toggleKnowledgeBase(${kb.id}, this.checked)">
            <label for="kb_${kb.id}">${kb.name}</label>
        </div>
    `).join('');
}

/**
 * 切换知识库选择
 */
function toggleKnowledgeBase(kbId, selected) {
    if (selected) {
        if (!agentConfig.knowledge_bases.includes(kbId)) {
            agentConfig.knowledge_bases.push(kbId);
        }
    } else {
        agentConfig.knowledge_bases = agentConfig.knowledge_bases.filter(id => id !== kbId);
    }
    console.log('知识库选择已更新:', agentConfig.knowledge_bases);
}

/**
 * 保存智能体配置
 */
async function saveAgent() {
    try {
        // 验证必填字段
        if (!agentConfig.name || agentConfig.name.trim() === '') {
            showError('请输入智能体名称');
            return;
        }
        
        if (!agentConfig.system_prompt || agentConfig.system_prompt.trim() === '') {
            showError('请输入系统提示词');
            return;
        }
        
        const response = await fetch(`/agent/api/agents/${agentConfig.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(agentConfig)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '保存失败');
        }
        
        const result = await response.json();
        showSuccess('智能体配置保存成功！');
        
        // 更新页面标题
        document.title = `${result.name} - 智能体配置`;
        
    } catch (error) {
        console.error('保存智能体配置失败:', error);
        showError('保存失败: ' + error.message);
    }
}

/**
 * 重置智能体配置
 */
function resetAgent() {
    if (confirm('确定要重置所有配置吗？此操作不可撤销。')) {
        location.reload();
    }
}

/**
 * 调试智能体
 */
function debugAgent() {
    showInfo('调试功能正在开发中...');
}

/**
 * 切换发布下拉菜单
 */
function togglePublishDropdown() {
    const dropdown = document.getElementById('publishDropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

/**
 * 关闭所有下拉菜单
 */
function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

/**
 * 发布智能体
 */
async function publishAgent(type) {
    try {
        const isPublic = type === 'public';
        
        const response = await fetch(`/agent/api/agents/${agentConfig.id}/publish`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_public: isPublic })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '发布失败');
        }
        
        const result = await response.json();
        showSuccess(`智能体已${isPublic ? '公开' : '私有'}发布！`);
        
        // 更新状态显示
        updatePublishStatus(isPublic);
        
    } catch (error) {
        console.error('发布智能体失败:', error);
        showError('发布失败: ' + error.message);
    }
    
    closeAllDropdowns();
}

/**
 * 更新发布状态显示
 */
function updatePublishStatus(isPublic) {
    const statusBadge = document.querySelector('.status-badge');
    if (statusBadge) {
        if (isPublic) {
            statusBadge.className = 'status-badge published';
            statusBadge.innerHTML = '<i class="fas fa-circle"></i> 已发布';
        } else {
            statusBadge.className = 'status-badge unpublished';
            statusBadge.innerHTML = '<i class="fas fa-circle"></i> 未发布';
        }
    }
}

/**
 * 选择知识库
 */
function selectKnowledge() {
    showInfo('知识库选择功能正在开发中...');
}

/**
 * 编辑知识库参数
 */
function editKnowledge() {
    showInfo('知识库参数编辑功能正在开发中...');
}

/**
 * 选择插件
 */
function selectPlugins() {
    showInfo('插件选择功能正在开发中...');
}

/**
 * 添加变量
 */
function addVariable() {
    showInfo('变量添加功能正在开发中...');
}

/**
 * 编辑开场白
 */
function editOpeningMessage() {
    const newMessage = prompt('请输入新的开场白:', agentConfig.opening_message);
    if (newMessage !== null) {
        agentConfig.opening_message = newMessage;
        updateOpeningMessageDisplay();
        showSuccess('开场白已更新');
    }
}

/**
 * 更新开场白显示
 */
function updateOpeningMessageDisplay() {
    const openingMessage = document.getElementById('openingMessage');
    if (openingMessage) {
        openingMessage.innerHTML = `<p>${agentConfig.opening_message.replace(/\n/g, '<br>')}</p>`;
    }
}

/**
 * 清空预览
 */
function clearPreview() {
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        chatContainer.innerHTML = `
            <div class="chat-message bot-message">
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <p>我是你的智能助手，你可以问我：</p>
                    <div class="suggested-questions">
                        <button class="suggestion-btn" onclick="sendSuggestion('你的主要职责是什么？')">你的主要职责是什么？</button>
                    </div>
                </div>
            </div>
        `;
    }
}

/**
 * 发送测试消息
 */
function sendTestMessage() {
    const chatInput = document.getElementById('chatInput');
    if (!chatInput || !chatInput.value.trim()) return;
    
    const message = chatInput.value.trim();
    chatInput.value = '';
    
    addChatMessage(message, 'user');
    
    // 模拟AI回复
    setTimeout(() => {
        const response = generateMockResponse(message);
        addChatMessage(response, 'bot');
    }, 1000);
}

/**
 * 发送建议问题
 */
function sendSuggestion(question) {
    addChatMessage(question, 'user');
    
    // 模拟AI回复
    setTimeout(() => {
        const response = generateMockResponse(question);
        addChatMessage(response, 'bot');
    }, 1000);
}

/**
 * 添加聊天消息
 */
function addChatMessage(content, type) {
    const chatContainer = document.getElementById('chatContainer');
    if (!chatContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    const avatar = type === 'user' ? 
        '<div class="message-avatar" style="background: #10b981;"><i class="fas fa-user"></i></div>' :
        '<div class="message-avatar"><i class="fas fa-robot"></i></div>';
    
    messageDiv.innerHTML = `
        ${avatar}
        <div class="message-content">
            <p>${content}</p>
        </div>
    `;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * 生成模拟回复
 */
function generateMockResponse(message) {
    const responses = [
        '这是一个很好的问题！让我来为您详细解答...',
        '根据您的问题，我建议您可以考虑以下几个方面...',
        '感谢您的提问，这个问题涉及到多个层面...',
        '我理解您的需求，让我为您提供一些实用的建议...'
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
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
        success: '#10b981',
        error: '#ef4444',
        info: '#3b82f6'
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

console.log('智能体配置脚本加载完成'); 