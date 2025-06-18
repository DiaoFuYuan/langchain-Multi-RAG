// Markdown交互功能模块

// 初始化markdown功能
function initializeMarkdownFeatures() {
    document.addEventListener('click', handleMarkdownClicks);
    document.addEventListener('change', handleTaskListChanges);
}

// 处理markdown中的点击事件
function handleMarkdownClicks(event) {
    // 代码复制功能
    if (event.target.closest('.simple-code-header')) {
        const codeHeader = event.target.closest('.simple-code-header');
        const codeBlock = codeHeader.nextElementSibling;
        if (codeBlock && codeBlock.tagName === 'PRE') {
            const code = codeBlock.querySelector('code');
            if (code) {
                copyCodeToClipboard(code.textContent, codeHeader);
            }
        }
    }
}

// 处理任务列表变化
function handleTaskListChanges(event) {
    if (event.target.type === 'checkbox' && event.target.closest('.task-list')) {
        const listItem = event.target.closest('li');
        const textSpan = listItem.querySelector('span');
        if (textSpan) {
            if (event.target.checked) {
                textSpan.style.textDecoration = 'line-through';
                textSpan.style.color = '#718096';
            } else {
                textSpan.style.textDecoration = 'none';
                textSpan.style.color = '';
            }
        }
    }
}

// 复制代码到剪贴板
async function copyCodeToClipboard(code, headerElement) {
    try {
        await navigator.clipboard.writeText(code);
        
        // 显示复制成功提示
        const originalAfter = window.getComputedStyle(headerElement, '::after').content;
        headerElement.style.setProperty('--copy-indicator', '"✅"');
        headerElement.classList.add('code-copied');
        
        // 2秒后恢复原状
        setTimeout(() => {
            headerElement.style.removeProperty('--copy-indicator');
            headerElement.classList.remove('code-copied');
        }, 2000);
        
        // 显示toast提示
        if (typeof showToast === 'function') {
            showToast('代码已复制到剪贴板', 'success');
        }
    } catch (err) {
        console.error('复制失败:', err);
        if (typeof showToast === 'function') {
            showToast('复制失败，请手动选择复制', 'error');
        }
        
        // 降级方案：选中文本
        selectText(headerElement.nextElementSibling.querySelector('code'));
    }
}

// 选中文本（降级方案）
function selectText(element) {
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
}

// 增强markdown渲染功能
function enhanceMarkdownContent(container) {
    if (!container) return;
    
    // 处理表格的响应式
    enhanceTableResponsiveness(container);
    
    // 处理任务列表
    enhanceTaskLists(container);
    
    // 添加代码语言标识
    enhanceCodeBlocks(container);
    
    // 处理外部链接
    enhanceExternalLinks(container);
}

// 增强表格响应式
function enhanceTableResponsiveness(container) {
    const tables = container.querySelectorAll('table');
    tables.forEach(table => {
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

// 增强任务列表
function enhanceTaskLists(container) {
    const taskListItems = container.querySelectorAll('li');
    taskListItems.forEach(item => {
        const text = item.textContent.trim();
        
        // 检查是否是任务列表项
        if (text.startsWith('[ ]') || text.startsWith('[x]') || text.startsWith('[X]')) {
            const isChecked = text.startsWith('[x]') || text.startsWith('[X]');
            const taskText = text.substring(3).trim();
            
            // 转换为真正的复选框
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = isChecked;
            
            const textSpan = document.createElement('span');
            textSpan.textContent = taskText;
            
            // 设置样式
            if (isChecked) {
                textSpan.style.textDecoration = 'line-through';
                textSpan.style.color = '#718096';
            }
            
            // 更新列表项
            item.innerHTML = '';
            item.appendChild(checkbox);
            item.appendChild(textSpan);
            
            // 添加任务列表类
            const ul = item.closest('ul');
            if (ul) {
                ul.classList.add('task-list');
            }
        }
    });
}

// 增强代码块
function enhanceCodeBlocks(container) {
    const codeBlocks = container.querySelectorAll('.simple-code-block');
    codeBlocks.forEach(block => {
        const header = block.querySelector('.simple-code-header');
        const langSpan = header?.querySelector('.simple-code-language');
        
        if (langSpan && header) {
            // 添加复制按钮提示
            header.setAttribute('title', '点击复制代码');
            header.style.cursor = 'pointer';
            
            // 根据语言添加图标
            const language = langSpan.textContent.toLowerCase();
            const icon = getLanguageIcon(language);
            if (icon) {
                langSpan.innerHTML = `${icon} ${langSpan.textContent}`;
            }
        }
    });
}

// 获取编程语言图标
function getLanguageIcon(language) {
    const icons = {
        'javascript': '🟨',
        'js': '🟨',
        'typescript': '🔷',
        'ts': '🔷',
        'python': '🐍',
        'py': '🐍',
        'java': '☕',
        'html': '🌐',
        'css': '🎨',
        'json': '📋',
        'xml': '📄',
        'sql': '🗄️',
        'bash': '💻',
        'shell': '💻',
        'markdown': '📝',
        'md': '📝',
        'yaml': '⚙️',
        'yml': '⚙️',
        'php': '🐘',
        'cpp': '⚡',
        'c++': '⚡',
        'c': '🔧',
        'go': '🐹',
        'rust': '🦀',
        'ruby': '💎',
        'swift': '🐦',
        'kotlin': '💜',
        'dart': '🎯',
        'r': '📊',
        'matlab': '🔢',
        'scala': '🏗️',
        'perl': '🐪',
        'lua': '🌙'
    };
    
    return icons[language] || '📝';
}

// 增强外部链接
function enhanceExternalLinks(container) {
    const links = container.querySelectorAll('a[href^="http"]');
    links.forEach(link => {
        // 添加外部链接图标
        if (!link.querySelector('.external-link-icon')) {
            const icon = document.createElement('span');
            icon.className = 'external-link-icon';
            icon.innerHTML = ' 🔗';
            icon.style.fontSize = '0.8em';
            icon.style.opacity = '0.6';
            link.appendChild(icon);
        }
        
        // 确保在新标签页打开
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
    });
}

// 创建信息框快捷函数
function createInfoBox(content, type = 'info') {
    const box = document.createElement('div');
    box.className = `${type}-box`;
    
    const p = document.createElement('p');
    p.innerHTML = content;
    box.appendChild(p);
    
    return box;
}

// 数学公式渲染（如果需要）
function renderMathFormulas(container) {
    // 这里可以集成MathJax或KaTeX
    const mathElements = container.querySelectorAll('.math');
    mathElements.forEach(element => {
        // 简单的上下标处理
        let text = element.textContent;
        text = text.replace(/\^(\d+)/g, '<sup>$1</sup>');
        text = text.replace(/_(\d+)/g, '<sub>$1</sub>');
        element.innerHTML = text;
    });
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeMarkdownFeatures();
});

// 导出功能供其他模块使用
window.markdownEnhancer = {
    enhance: enhanceMarkdownContent,
    createInfoBox: createInfoBox,
    renderMath: renderMathFormulas
}; 