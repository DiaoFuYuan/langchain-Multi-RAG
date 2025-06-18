// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
    // 侧边栏折叠/展开功能
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    // 从本地存储加载侧边栏状态
    function loadSidebarState() {
        if (sidebar) {
            const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            
            if (isCollapsed) {
                sidebar.classList.add('collapsed');
                if (mainContent) {
                    mainContent.style.marginLeft = '50px';
                }
                if (sidebarToggle && sidebarToggle.querySelector('i')) {
                    sidebarToggle.querySelector('i').className = 'fas fa-angle-double-right';
                }
            }
            
            // 在所有情况下都初始化子菜单状态
            loadSubmenuState();
        }
    }
    
    // 初始加载侧边栏状态
    loadSidebarState();
    
    // 如果侧边栏未收缩，则初始化子菜单状态
    if (sidebar && !sidebar.classList.contains('collapsed')) {
        loadSubmenuState();
    }
    
    if (sidebarToggle && sidebar && mainContent) {
        sidebarToggle.addEventListener('click', function() {
            const isCollapsed = sidebar.classList.toggle('collapsed');
            
            // 保存到本地存储
            localStorage.setItem('sidebarCollapsed', isCollapsed);
            
            // 更新图标
            const toggleIcon = sidebarToggle.querySelector('i');
            if (toggleIcon) {
                if (isCollapsed) {
                    toggleIcon.className = 'fas fa-angle-double-right';
                } else {
                    toggleIcon.className = 'fas fa-angle-double-left';
                }
            }
            
            // 调整主内容区域
            if (isCollapsed) {
                mainContent.style.marginLeft = '50px';
                
                // 移除直接操作display属性的代码，改为通过CSS类控制
                // CSS会通过.sidebar.collapsed选择器自动处理子菜单项的显示
            } else {
                mainContent.style.marginLeft = '200px';
                
                // 关键修复：重新初始化子菜单状态，而不是通过display属性控制
                // 延迟一帧执行以确保侧边栏展开后状态稳定
                requestAnimationFrame(() => {
                    loadSubmenuState();
                });
            }
        });
    }
    
    // 子菜单展开/折叠功能
    const expandableItems = document.querySelectorAll('.sidebar-item .expand-icon');
    expandableItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.stopPropagation(); // 阻止事件冒泡
            
            const parentItem = this.parentElement;
            const parentText = parentItem.querySelector('span').textContent;
            const isExpanded = this.classList.contains('rotated');
            
            // 切换图标旋转状态 - 立即执行，减少延迟感
            this.classList.toggle('rotated');
            
            // 获取相应的子菜单容器
            let submenuContainer = null;
            let subItems = [];
            
            if (parentItem.classList.contains('explore-item')) {
                submenuContainer = document.getElementById('explore-submenu');
            } else if (parentItem.classList.contains('create-item')) {
                submenuContainer = document.getElementById('create-submenu');
                subItems = document.querySelectorAll('.sidebar-item.create-sub-item');
            } else if (parentItem.classList.contains('config-item')) {
                submenuContainer = document.getElementById('config-submenu');
                subItems = document.querySelectorAll('.sidebar-item.config-sub-item');
            } else if (parentItem.classList.contains('dialog-item')) {
                submenuContainer = document.getElementById('dialog-submenu');
                subItems = document.querySelectorAll('.sidebar-item.dialog-sub-item');
            }
            
            // 如果找到子菜单容器
            if (submenuContainer) {
                // 使用requestAnimationFrame确保DOM更新和CSS过渡效果顺畅结合
                requestAnimationFrame(() => {
                    const isNowExpanded = submenuContainer.classList.toggle('expanded');
                    
                    // 更新子菜单项的可见性
                    if (subItems.length > 0) {
                        subItems.forEach(subItem => {
                            if (isNowExpanded) {
                                subItem.classList.add('visible');
                            } else {
                                subItem.classList.remove('visible');
                            }
                        });
                    }
                    
                    // 保存状态到本地存储
                    localStorage.setItem(parentText + 'expanded', isNowExpanded);
                });
            }
        });
    });
    
    // 点击整个菜单项也触发展开/收缩，但不会触发菜单选中事件
    document.querySelectorAll('.sidebar-item').forEach(item => {
        // 只处理主菜单项（带有expand-icon的项）
        const expandIcon = item.querySelector('.expand-icon');
        if (expandIcon) {
            item.addEventListener('click', function(event) {
                // 如果点击的是展开图标本身，则不处理
                if (event.target === expandIcon || event.target.closest('.expand-icon')) {
                    return;
                }
                
                // 模拟点击展开图标
                expandIcon.click();
            });
        }
    });
    
    // 页面加载时初始化
    function initialize() {
        // 加载侧边栏状态
        loadSidebarState();
        
        // 加载子菜单状态
        loadSubmenuState();
        
        // 设置子菜单项点击事件
        setupSubmenuItemClickEvents();
        
        // 设置分类标签点击事件
        setupCategoryTabsEvents();
        
        // 加载用户信息
        loadUserInfo();
        
        // 更新顶部导航栏
        updateTopNavigation();
    }
    
    // 更新顶部导航栏的导航路径
    function updateTopNavigation() {
        // 获取当前激活的菜单项
        const activeItem = document.querySelector('.sidebar-item.active');
        if (!activeItem) return;
        
        // 获取菜单项文本
        const itemText = activeItem.querySelector('span')?.textContent.trim();
        
        // 如果找不到菜单文本，则返回
        if (!itemText) return;
        
        // 获取父菜单项
        let parentText = '';
        let parentMenuId = '';
        
        if (activeItem.classList.contains('store-item')) {
            parentText = '探索';
        } else if (activeItem.classList.contains('dialog-sub-item')) {
            parentText = '对话';
        } else if (activeItem.classList.contains('create-sub-item')) {
            parentText = '创作';
        } else if (activeItem.classList.contains('config-sub-item')) {
            parentText = '配置管理';
        }
        
        // 更新导航链接
        updateNavigationLinks(parentText, itemText);
    }
    
    // 更新顶部导航链接
    function updateNavigationLinks(parentText, subItemText) {
        const navLinks = document.querySelector('.nav-links');
        if (!navLinks) return;
        
        // 清空现有导航链接
        navLinks.innerHTML = '';
        
        // 如果有父菜单和子菜单，则显示"父菜单 / 子菜单"格式
        if (parentText && subItemText) {
            let href = '#';
            
            // 确定链接URL
            if (subItemText === '智能体商店') {
                href = '/dashboard/home';
            } else if (subItemText === '通用对话') {
                href = '/chat/home';
            } else if (subItemText === '知识库') {
                href = '/knowledge/knowledge_base';
            } else if (subItemText === '模型配置') {
                href = '#'; // 添加对应URL
            } else if (subItemText === '工作流模板') {
                href = '#'; // 添加对应URL
            } else if (subItemText === '运营面板') {
                href = '#'; // 添加对应URL
            } else if (subItemText === '快捷智能体') {
                href = '#'; // 添加对应URL
            } else if (subItemText === '工作流智能体') {
                href = '#'; // 添加对应URL
            } else if (subItemText === '插件') {
                href = '#'; // 添加对应URL
            } else if (subItemText === '数据库') {
                href = '#'; // 添加对应URL
            }
            
            const navLink = document.createElement('a');
            navLink.href = href;
            navLink.className = 'nav-link';
            navLink.textContent = `${parentText} / ${subItemText}`;
            navLinks.appendChild(navLink);
        } else if (subItemText) {
            // 只有子菜单情况，目前代码结构中不会出现
            const navLink = document.createElement('a');
            navLink.href = '#';
            navLink.className = 'nav-link';
            navLink.textContent = subItemText;
            navLinks.appendChild(navLink);
        }
    }
    
    // 设置子菜单项点击事件
    function setupSubmenuItemClickEvents() {
        // 获取所有子菜单项
        const submenuItems = document.querySelectorAll('.sidebar-item.create-sub-item, .sidebar-item.config-sub-item, .sidebar-item.dialog-sub-item, .sidebar-item.store-item');
        
        submenuItems.forEach(item => {
            item.addEventListener('click', function(event) {
                event.stopPropagation(); // 阻止事件冒泡
                
                // 移除所有子菜单项的active类
                const allMenuItems = document.querySelectorAll('.sidebar-item');
                allMenuItems.forEach(menuItem => {
                    menuItem.classList.remove('active');
                });
                
                // 为当前点击的子菜单项添加active类
                this.classList.add('active');
                
                // 保存当前激活的菜单项到本地存储
                const itemText = this.querySelector('span').textContent.trim();
                localStorage.setItem('activeMenuItem', itemText);
                
                console.log('选中子菜单项:', itemText);
                
                // 获取父菜单文本
                let parentText = '';
                if (this.classList.contains('store-item')) {
                    parentText = '探索';
                } else if (this.classList.contains('dialog-sub-item')) {
                    parentText = '对话';
                } else if (this.classList.contains('create-sub-item')) {
                    parentText = '创作';
                } else if (this.classList.contains('config-sub-item')) {
                    parentText = '配置管理';
                }
                
                // 更新顶部导航栏
                updateNavigationLinks(parentText, itemText);
                
                // 添加页面跳转逻辑
                if (itemText === '通用对话') {
                    window.location.href = '/chat/home';
                } else if (itemText === '智能体商店') {
                    window.location.href = '/dashboard/home';
                } else if (itemText === '知识库') {
                    // 跳转到知识库页面，并设置标记以便页面加载时触发数据刷新
                    localStorage.setItem('refreshKnowledgeBase', 'true');
                    window.location.href = '/knowledge/knowledge_base';
                }
                // 其他菜单项的跳转逻辑可以在这里添加
            });
        });
    }
    
    // 设置分类标签点击事件
    function setupCategoryTabsEvents() {
        // 分类标签点击事件
        const tabItems = document.querySelectorAll('.category-tabs .tab-item');
        tabItems.forEach(tab => {
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 移除所有活动状态
                tabItems.forEach(t => t.classList.remove('active'));
                
                // 设置当前选中状态
                this.classList.add('active');
                
                // 这里可以添加加载对应分类内容的逻辑
                // 例如: loadCategoryContent(this.getAttribute('data-category'));
            });
        });
    }
    
    // 从本地存储加载激活的菜单项状态
    function loadActiveMenuItemState() {
        const activeItemText = localStorage.getItem('activeMenuItem');
        
        // 获取通用对话菜单项
        const genericDialogItem = Array.from(document.querySelectorAll('.sidebar-item.dialog-sub-item')).find(item => 
            item.querySelector('span').textContent.trim() === '通用对话'
        );
        
        if (activeItemText) {
            // 尝试查找匹配的菜单项（所有类型的菜单项）
            const allMenuItems = document.querySelectorAll('.sidebar-item');
            
            // 查找文本内容匹配的菜单项
            const matchedItem = Array.from(allMenuItems).find(item => {
                const itemText = item.querySelector('span')?.textContent.trim();
                return itemText === activeItemText;
            });
            
            // 如果找到匹配的菜单项，设置其active状态
            if (matchedItem) {
                // 移除所有菜单项的active类
                allMenuItems.forEach(item => item.classList.remove('active'));
                
                // 为匹配的菜单项添加active类
                matchedItem.classList.add('active');
            } else if (genericDialogItem) {
                // 如果没有找到匹配项，默认激活"通用对话"菜单
                allMenuItems.forEach(item => item.classList.remove('active'));
                genericDialogItem.classList.add('active');
            }
        } else if (genericDialogItem) {
            // 如果本地存储中没有记录，默认激活"通用对话"菜单
            const allMenuItems = document.querySelectorAll('.sidebar-item');
            allMenuItems.forEach(item => item.classList.remove('active'));
            genericDialogItem.classList.add('active');
            
            // 保存到本地存储
            localStorage.setItem('activeMenuItem', '通用对话');
        }
    }
    
    // 页面加载时根据本地存储设置子菜单初始状态
    function loadSubmenuState() {
        const sidebarIsCollapsed = sidebar.classList.contains('collapsed');
        
        // 获取各个菜单项
        const exploreItem = document.querySelector('.sidebar-item.explore-item');
        const createItem = document.querySelector('.sidebar-item.create-item');
        const configItem = document.querySelector('.sidebar-item.config-item');
        const dialogItem = document.querySelector('.sidebar-item.dialog-item');
        
        // 获取相应的子菜单项
        const createSubItems = document.querySelectorAll('.sidebar-item.create-sub-item');
        const configSubItems = document.querySelectorAll('.sidebar-item.config-sub-item');
        const dialogSubItems = document.querySelectorAll('.sidebar-item.dialog-sub-item');
        
        // 获取子菜单容器
        const exploreSubmenu = document.getElementById('explore-submenu');
        const createSubmenu = document.getElementById('create-submenu');
        const configSubmenu = document.getElementById('config-submenu');
        const dialogSubmenu = document.getElementById('dialog-submenu');
        
        // 加载"探索"子菜单状态
        if (exploreItem && exploreSubmenu) {
            const isExpanded = localStorage.getItem('探索expanded') === 'true';
            const icon = exploreItem.querySelector('.expand-icon');
            
            if (isExpanded) {
                icon.classList.add('rotated');
                exploreSubmenu.classList.add('expanded');
            }
        }
        
        // 加载"创作"子菜单状态
        if (createItem && createSubmenu) {
            const isExpanded = localStorage.getItem('创作expanded') === 'true';
            const icon = createItem.querySelector('.expand-icon');
            
            if (isExpanded) {
                icon.classList.add('rotated');
                createSubmenu.classList.add('expanded');
                
                createSubItems.forEach(item => {
                    item.classList.add('visible');
                });
            }
        }
        
        // 加载"配置管理"子菜单状态
        if (configItem && configSubmenu) {
            const isExpanded = localStorage.getItem('配置管理expanded') === 'true';
            const icon = configItem.querySelector('.expand-icon');
            
            if (isExpanded) {
                icon.classList.add('rotated');
                configSubmenu.classList.add('expanded');
                
                configSubItems.forEach(item => {
                    item.classList.add('visible');
                });
            }
        }
        
        // 加载"对话"子菜单状态
        if (dialogItem && dialogSubmenu) {
            // 检查本地存储或默认展开
            let isExpanded = localStorage.getItem('对话expanded');
            
            // 如果本地存储中没有值，则默认展开
            if (isExpanded === null) {
                isExpanded = true;
                localStorage.setItem('对话expanded', 'true');
            } else {
                isExpanded = isExpanded === 'true';
            }
            
            const icon = dialogItem.querySelector('.expand-icon');
            
            if (isExpanded) {
                icon.classList.add('rotated');
                dialogSubmenu.classList.add('expanded');
                
                dialogSubItems.forEach(item => {
                    item.classList.add('visible');
                });
            }
        }
        
        // 先加载子菜单状态，然后再加载激活的菜单项状态
        loadActiveMenuItemState();
    }
    
    // 页面加载完成后执行初始化
    initialize();
});

// 从本地存储获取用户信息
function loadUserInfo() {
    const username = localStorage.getItem('username');
    const userDisplay = document.querySelector('.user-info span');
    
    if (username && userDisplay) {
        userDisplay.textContent = username;
    }
}

// 页面加载时执行
window.onload = function() {
    loadUserInfo();
}; 