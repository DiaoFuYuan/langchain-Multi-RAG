// 公共侧边栏功能
class SidebarManager {
    constructor() {
        this.sidebar = document.querySelector('.sidebar');
        this.mainContent = document.querySelector('.main-content');
        this.sidebarToggle = document.querySelector('.sidebar-toggle');
        this.navLinks = document.querySelector('#navLinks');
        
        // 页面路由映射
        this.pageRoutes = {
            'dashboard': '/dashboard/home',
            'chat': '/chat/home',
            'knowledge': '/knowledge/knowledge_base',
            'agent-quick': '/agent/quick',
            'agent-workflow': '#',
            'plugin': '#',
            'database': '#',
            'model-config': '/config/model-config',
            'workflow-template': '#',
            'dashboard-admin': '#'
        };
        
        // 页面标题映射
        this.pageTitles = {
            'dashboard': { parent: '探索', child: '智能体商店' },
            'chat': { parent: '对话', child: '通用对话' },
            'knowledge': { parent: '创作', child: '知识库' },
            'agent-quick': { parent: '创作', child: '快捷智能体' },
            'agent-workflow': { parent: '创作', child: '工作流智能体' },
            'plugin': { parent: '创作', child: '插件' },
            'database': { parent: '创作', child: '数据库' },
            'model-config': { parent: '配置管理', child: '模型配置' },
            'workflow-template': { parent: '配置管理', child: '工作流模板' },
            'dashboard-admin': { parent: '配置管理', child: '运营面板' }
        };
        
        this.init();
    }
    
    init() {
        this.loadSidebarState();
        this.setupEventListeners();
        this.loadSubmenuState();
        this.loadActiveMenuItemState();
        this.updateTopNavigation();
        this.loadUserInfo();
    }
    
    // 设置事件监听器
    setupEventListeners() {
        // 侧边栏折叠/展开
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }
        
        // 子菜单展开/折叠
        const expandableItems = document.querySelectorAll('.sidebar-item .expand-icon');
        expandableItems.forEach(item => {
            item.addEventListener('click', (e) => this.toggleSubmenu(e));
        });
        
        // 主菜单项点击
        document.querySelectorAll('.sidebar-item').forEach(item => {
            const expandIcon = item.querySelector('.expand-icon');
            if (expandIcon) {
                item.addEventListener('click', (event) => {
                    if (event.target === expandIcon || event.target.closest('.expand-icon')) {
                        return;
                    }
                    expandIcon.click();
                });
            }
        });
        
        // 子菜单项点击
        this.setupSubmenuItemClickEvents();
    }
    
    // 侧边栏折叠/展开
    toggleSidebar() {
        const isCollapsed = this.sidebar.classList.toggle('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
        
        // 更新图标
        const toggleIcon = this.sidebarToggle.querySelector('i');
        if (toggleIcon) {
            toggleIcon.className = isCollapsed ? 
                'fas fa-angle-double-right' : 'fas fa-angle-double-left';
        }
        
        // 调整主内容区域
        if (this.mainContent) {
            this.mainContent.style.marginLeft = isCollapsed ? '50px' : '200px';
        }
        
        if (!isCollapsed) {
            requestAnimationFrame(() => {
                this.loadSubmenuState();
            });
        }
    }
    
    // 子菜单展开/折叠
    toggleSubmenu(e) {
        e.stopPropagation();
        
        const parentItem = e.target.parentElement;
        const parentText = parentItem.querySelector('span').textContent;
        
        // 切换图标旋转状态
        e.target.classList.toggle('rotated');
        
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
        
        if (submenuContainer) {
            requestAnimationFrame(() => {
                const isNowExpanded = submenuContainer.classList.toggle('expanded');
                
                if (subItems.length > 0) {
                    subItems.forEach(subItem => {
                        if (isNowExpanded) {
                            subItem.classList.add('visible');
                        } else {
                            subItem.classList.remove('visible');
                        }
                    });
                }
                
                localStorage.setItem(parentText + 'expanded', isNowExpanded);
            });
        }
    }
    
    // 设置子菜单项点击事件
    setupSubmenuItemClickEvents() {
        const submenuItems = document.querySelectorAll('.sidebar-item[data-page]');
        
        submenuItems.forEach(item => {
            item.addEventListener('click', (event) => {
                event.stopPropagation();
                
                const pageKey = item.getAttribute('data-page');
                const itemText = item.querySelector('span').textContent.trim();
                
                // 更新活动状态
                this.setActiveMenuItem(item, itemText);
                
                // 更新导航栏
                this.updateNavigationLinks(pageKey);
                
                // 页面跳转
                this.navigateToPage(pageKey);
            });
        });
    }
    
    // 设置活动菜单项
    setActiveMenuItem(activeItem, itemText) {
        // 移除所有菜单项的active类
        const allMenuItems = document.querySelectorAll('.sidebar-item');
        allMenuItems.forEach(menuItem => {
            menuItem.classList.remove('active');
        });
        
        // 为当前点击的菜单项添加active类
        activeItem.classList.add('active');
        
        // 保存到本地存储
        localStorage.setItem('activeMenuItem', itemText);
        
        console.log('选中菜单项:', itemText);
    }
    
    // 更新顶部导航链接
    updateNavigationLinks(pageKey) {
        if (!this.navLinks || !this.pageTitles[pageKey]) return;
        
        const { parent, child } = this.pageTitles[pageKey];
        const href = this.pageRoutes[pageKey];
        
        this.navLinks.innerHTML = '';
        
        const navLink = document.createElement('a');
        navLink.href = href;
        navLink.className = 'nav-link active';
        navLink.textContent = `${parent} / ${child}`;
        this.navLinks.appendChild(navLink);
    }
    
    // 页面导航
    navigateToPage(pageKey) {
        const url = this.pageRoutes[pageKey];
        
        if (url && url !== '#') {
            // 对于知识库页面，设置刷新标记
            if (pageKey === 'knowledge') {
                localStorage.setItem('refreshKnowledgeBase', 'true');
            }
            
            window.location.href = url;
        } else {
            console.log('页面尚未实现:', pageKey);
        }
    }
    
    // 加载侧边栏状态
    loadSidebarState() {
        if (!this.sidebar) return;
        
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        
        if (isCollapsed) {
            this.sidebar.classList.add('collapsed');
            if (this.mainContent) {
                this.mainContent.style.marginLeft = '50px';
            }
            if (this.sidebarToggle && this.sidebarToggle.querySelector('i')) {
                this.sidebarToggle.querySelector('i').className = 'fas fa-angle-double-right';
            }
        }
    }
    
    // 加载子菜单状态
    loadSubmenuState() {
        const menuConfigs = [
            { key: '探索', itemClass: 'explore-item', submenuId: 'explore-submenu', subItemClass: null },
            { key: '创作', itemClass: 'create-item', submenuId: 'create-submenu', subItemClass: 'create-sub-item' },
            { key: '配置管理', itemClass: 'config-item', submenuId: 'config-submenu', subItemClass: 'config-sub-item' },
            { key: '对话', itemClass: 'dialog-item', submenuId: 'dialog-submenu', subItemClass: 'dialog-sub-item' }
        ];
        
        menuConfigs.forEach(config => {
            const menuItem = document.querySelector(`.sidebar-item.${config.itemClass}`);
            const submenu = document.getElementById(config.submenuId);
            
            if (menuItem && submenu) {
                // 对话菜单默认展开
                let isExpanded = localStorage.getItem(config.key + 'expanded');
                if (config.key === '对话' && isExpanded === null) {
                    isExpanded = true;
                    localStorage.setItem(config.key + 'expanded', 'true');
                } else {
                    isExpanded = isExpanded === 'true';
                }
                
                const icon = menuItem.querySelector('.expand-icon');
                
                if (isExpanded) {
                    icon.classList.add('rotated');
                    submenu.classList.add('expanded');
                    
                    if (config.subItemClass) {
                        const subItems = document.querySelectorAll(`.sidebar-item.${config.subItemClass}`);
                        subItems.forEach(item => {
                            item.classList.add('visible');
                        });
                    }
                }
            }
        });
        
        // 加载活动菜单项状态
        this.loadActiveMenuItemState();
    }
    
    // 加载活动菜单项状态
    loadActiveMenuItemState() {
        const activeItemText = localStorage.getItem('activeMenuItem');
        
        // 获取通用对话菜单项作为默认项
        const genericDialogItem = Array.from(document.querySelectorAll('.sidebar-item[data-page]')).find(item => 
            item.querySelector('span').textContent.trim() === '通用对话'
        );
        
        if (activeItemText) {
            // 查找匹配的菜单项
            const allMenuItems = document.querySelectorAll('.sidebar-item[data-page]');
            const matchedItem = Array.from(allMenuItems).find(item => {
                const itemText = item.querySelector('span')?.textContent.trim();
                return itemText === activeItemText;
            });
            
            if (matchedItem) {
                this.setActiveMenuItem(matchedItem, activeItemText);
            } else if (genericDialogItem) {
                this.setActiveMenuItem(genericDialogItem, '通用对话');
            }
        } else if (genericDialogItem) {
            this.setActiveMenuItem(genericDialogItem, '通用对话');
        }
    }
    
    // 更新顶部导航栏
    updateTopNavigation() {
        const activeItem = document.querySelector('.sidebar-item.active[data-page]');
        if (!activeItem) return;
        
        const pageKey = activeItem.getAttribute('data-page');
        if (pageKey) {
            this.updateNavigationLinks(pageKey);
        }
    }
    
    // 加载用户信息
    loadUserInfo() {
        const username = localStorage.getItem('username');
        const userDisplay = document.querySelector('.user-info span');
        
        if (username && userDisplay) {
            userDisplay.textContent = username;
        }
    }
    
    // 根据当前页面设置活动菜单项
    setActiveMenuByPage(pageKey) {
        const menuItem = document.querySelector(`.sidebar-item[data-page="${pageKey}"]`);
        if (menuItem) {
            const itemText = menuItem.querySelector('span').textContent.trim();
            this.setActiveMenuItem(menuItem, itemText);
            this.updateNavigationLinks(pageKey);
        }
    }
}

// 等待DOM加载完成后初始化侧边栏
document.addEventListener('DOMContentLoaded', function() {
    window.sidebarManager = new SidebarManager();
});

// 页面加载完成后加载用户信息
window.addEventListener('load', function() {
    if (window.sidebarManager) {
        window.sidebarManager.loadUserInfo();
    }
}); 