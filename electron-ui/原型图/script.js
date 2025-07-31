// 页面导航功能
document.addEventListener('DOMContentLoaded', function() {
    // 导航菜单点击事件
    const navItems = document.querySelectorAll('.nav-item');
    const pages = document.querySelectorAll('.page');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const targetPage = this.getAttribute('data-page');
            
            // 移除所有活动状态
            navItems.forEach(nav => nav.classList.remove('active'));
            pages.forEach(page => page.classList.remove('active'));
            
            // 添加活动状态
            this.classList.add('active');
            document.getElementById(targetPage).classList.add('active');
        });
    });
    
    // 用户卡片点击事件
    const userCards = document.querySelectorAll('.user-card');
    userCards.forEach(card => {
        card.addEventListener('click', function() {
            userCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            
            // 更新用户详细信息
            const userId = this.getAttribute('data-user');
            updateUserDetail(userId);
        });
    });
    
    // 设置页面标签切换
    const settingsNavItems = document.querySelectorAll('.settings-nav-item');
    const settingsTabs = document.querySelectorAll('.settings-tab');
    
    settingsNavItems.forEach(item => {
        item.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            settingsNavItems.forEach(nav => nav.classList.remove('active'));
            settingsTabs.forEach(tab => tab.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
    
    // 初始化进度条动画
    animateProgressBars();
    
    // 初始化实时日志
    startLogSimulation();
});

// 脚本管理相关函数
function toggleScript(button) {
    const scriptItem = button.closest('.script-item');
    const content = scriptItem.querySelector('.script-content');
    const isExpanded = content.classList.contains('expanded');
    
    if (isExpanded) {
        content.classList.remove('expanded');
        button.textContent = '▶️';
    } else {
        content.classList.add('expanded');
        button.textContent = '▼';
    }
}

function addScript() {
    const scriptList = document.querySelector('.script-list');
    const newScriptHtml = `
        <div class="script-item">
            <div class="script-header">
                <span class="script-name">新脚本 - 未命名</span>
                <button class="toggle-btn" onclick="toggleScript(this)">▶️</button>
            </div>
            <div class="script-content">
                <div class="run-section">
                    <h3>运行配置</h3>
                    <div class="run-options">
                        <label><input type="checkbox"> 自动运行</label>
                        <label><input type="checkbox"> 循环执行</label>
                        <select class="run-mode">
                            <option>普通模式</option>
                            <option>快速模式</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>
    `;
    scriptList.insertAdjacentHTML('beforeend', newScriptHtml);
    showNotification('脚本添加成功', 'success');
}

function deleteScript() {
    const selectedScript = document.querySelector('.script-item.selected');
    if (selectedScript) {
        selectedScript.remove();
        showNotification('脚本删除成功', 'success');
    } else {
        showNotification('请先选择要删除的脚本', 'warning');
    }
}

function moveScriptUp() {
    const selectedScript = document.querySelector('.script-item.selected');
    if (selectedScript && selectedScript.previousElementSibling) {
        selectedScript.parentNode.insertBefore(selectedScript, selectedScript.previousElementSibling);
        showNotification('脚本位置调整成功', 'success');
    }
}

function moveScriptDown() {
    const selectedScript = document.querySelector('.script-item.selected');
    if (selectedScript && selectedScript.nextElementSibling) {
        selectedScript.parentNode.insertBefore(selectedScript.nextElementSibling, selectedScript);
        showNotification('脚本位置调整成功', 'success');
    }
}

// 用户管理相关函数
function addUser() {
    const userPreview = document.querySelector('.user-preview');
    const userCount = userPreview.children.length + 1;
    const newUserHtml = `
        <div class="user-card" data-user="${userCount}">
            <div class="user-avatar">👤</div>
            <div class="user-info">
                <div class="user-name">用户${userCount}</div>
                <div class="user-status offline">离线</div>
            </div>
        </div>
    `;
    userPreview.insertAdjacentHTML('beforeend', newUserHtml);
    
    // 添加点击事件
    const newUserCard = userPreview.lastElementChild;
    newUserCard.addEventListener('click', function() {
        document.querySelectorAll('.user-card').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        updateUserDetail(this.getAttribute('data-user'));
    });
    
    showNotification('用户添加成功', 'success');
}

function deleteUser() {
    const activeUser = document.querySelector('.user-card.active');
    if (activeUser) {
        activeUser.remove();
        // 选择第一个用户
        const firstUser = document.querySelector('.user-card');
        if (firstUser) {
            firstUser.classList.add('active');
            updateUserDetail(firstUser.getAttribute('data-user'));
        }
        showNotification('用户删除成功', 'success');
    } else {
        showNotification('请先选择要删除的用户', 'warning');
    }
}

function moveUserLeft() {
    const activeUser = document.querySelector('.user-card.active');
    if (activeUser && activeUser.previousElementSibling) {
        activeUser.parentNode.insertBefore(activeUser, activeUser.previousElementSibling);
        showNotification('用户位置调整成功', 'success');
    }
}

function moveUserRight() {
    const activeUser = document.querySelector('.user-card.active');
    if (activeUser && activeUser.nextElementSibling) {
        activeUser.parentNode.insertBefore(activeUser.nextElementSibling, activeUser);
        showNotification('用户位置调整成功', 'success');
    }
}

function updateUserDetail(userId) {
    const userConfigs = {
        '1': { name: '用户1', device: 'Android', address: '127.0.0.1:5555', autoConnect: true },
        '2': { name: '用户2', device: 'iOS', address: '192.168.1.100:5555', autoConnect: false },
        '3': { name: '用户3', device: '模拟器', address: '127.0.0.1:7555', autoConnect: true }
    };
    
    const config = userConfigs[userId] || userConfigs['1'];
    const userDetail = document.querySelector('.user-detail');
    
    userDetail.querySelector('input[type="text"]').value = config.name;
    userDetail.querySelector('select').value = config.device;
    userDetail.querySelectorAll('input[type="text"]')[1].value = config.address;
    userDetail.querySelector('input[type="checkbox"]').checked = config.autoConnect;
}

// 计划表管理相关函数
function addSchedule() {
    const tbody = document.querySelector('.schedule-table tbody');
    const newRowHtml = `
        <tr>
            <td>新计划</td>
            <td>
                <select class="time-select">
                    <option>每天 06:00</option>
                    <option>每天 12:00</option>
                    <option>每天 18:00</option>
                </select>
            </td>
            <td>
                <select class="script-select">
                    <option>脚本1 - 日常任务</option>
                    <option>脚本2 - 活动任务</option>
                </select>
            </td>
            <td>
                <select class="user-select">
                    <option>用户1</option>
                    <option>用户2</option>
                    <option>用户3</option>
                </select>
            </td>
            <td><span class="status active">启用</span></td>
            <td>
                <button class="btn btn-sm btn-primary">编辑</button>
                <button class="btn btn-sm btn-danger">删除</button>
            </td>
        </tr>
    `;
    tbody.insertAdjacentHTML('beforeend', newRowHtml);
    showNotification('计划添加成功', 'success');
}

function editSchedule() {
    const selectedRow = document.querySelector('.schedule-table tr.selected');
    if (selectedRow) {
        showNotification('编辑功能开发中...', 'info');
    } else {
        showNotification('请先选择要编辑的计划', 'warning');
    }
}

function moveScheduleLeft() {
    showNotification('计划位置调整成功', 'success');
}

function moveScheduleRight() {
    showNotification('计划位置调整成功', 'success');
}

// 调度队列相关函数
function startQueue() {
    showNotification('队列已启动', 'success');
    updateQueueStatus('running');
}

function pauseQueue() {
    showNotification('队列已暂停', 'warning');
    updateQueueStatus('paused');
}

function stopQueue() {
    showNotification('队列已停止', 'danger');
    updateQueueStatus('stopped');
}

function clearQueue() {
    if (confirm('确定要清空队列吗？')) {
        showNotification('队列已清空', 'success');
    }
}

function updateQueueStatus(status) {
    // 更新队列状态显示
    console.log('Queue status updated to:', status);
}

// 进度条动画
function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
        }, 500);
    });
}

// 实时日志模拟
function startLogSimulation() {
    const logContainer = document.querySelector('.log-container');
    if (!logContainer) return;
    
    const logMessages = [
        { level: 'info', message: '系统启动完成' },
        { level: 'info', message: '开始检查设备连接状态' },
        { level: 'warn', message: '设备 127.0.0.1:5555 连接超时，正在重试...' },
        { level: 'info', message: '设备连接成功' },
        { level: 'info', message: '开始执行计划任务' },
        { level: 'info', message: '任务执行完成，等待下次调度' }
    ];
    
    let messageIndex = 0;
    setInterval(() => {
        if (messageIndex >= logMessages.length) messageIndex = 0;
        
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        const log = logMessages[messageIndex];
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-time">${timeStr}</span>
            <span class="log-level ${log.level}">${log.level.toUpperCase()}</span>
            <span class="log-message">${log.message}</span>
        `;
        
        logContainer.appendChild(logEntry);
        
        // 保持最多显示20条日志
        while (logContainer.children.length > 20) {
            logContainer.removeChild(logContainer.firstChild);
        }
        
        // 滚动到底部
        logContainer.scrollTop = logContainer.scrollHeight;
        
        messageIndex++;
    }, 3000);
}

// 通知系统
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 添加样式
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '6px',
        color: 'white',
        fontWeight: '500',
        zIndex: '9999',
        opacity: '0',
        transform: 'translateX(100%)',
        transition: 'all 0.3s ease'
    });
    
    // 设置背景色
    const colors = {
        success: '#27ae60',
        warning: '#f39c12',
        danger: '#e74c3c',
        info: '#3498db'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // 自动隐藏
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// 表格行选择功能
document.addEventListener('click', function(e) {
    // 脚本项选择
    if (e.target.closest('.script-item')) {
        const scriptItems = document.querySelectorAll('.script-item');
        scriptItems.forEach(item => item.classList.remove('selected'));
        e.target.closest('.script-item').classList.add('selected');
    }
    
    // 计划表行选择
    if (e.target.closest('.schedule-table tr') && !e.target.closest('thead')) {
        const rows = document.querySelectorAll('.schedule-table tbody tr');
        rows.forEach(row => row.classList.remove('selected'));
        e.target.closest('tr').classList.add('selected');
    }
});

// 模拟数据更新
setInterval(() => {
    // 更新统计数据
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(stat => {
        const currentValue = parseInt(stat.textContent);
        const change = Math.floor(Math.random() * 3) - 1; // -1, 0, 或 1
        const newValue = Math.max(0, currentValue + change);
        stat.textContent = newValue;
    });
    
    // 更新用户状态
    const userStatuses = document.querySelectorAll('.user-status');
    userStatuses.forEach(status => {
        if (Math.random() > 0.9) { // 10% 概率改变状态
            if (status.classList.contains('online')) {
                status.classList.remove('online');
                status.classList.add('offline');
                status.textContent = '离线';
            } else {
                status.classList.remove('offline');
                status.classList.add('online');
                status.textContent = '在线';
            }
        }
    });
}, 5000);

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    // Ctrl + 数字键切换页面
    if (e.ctrlKey && e.key >= '1' && e.key <= '7') {
        e.preventDefault();
        const pageIndex = parseInt(e.key) - 1;
        const navItems = document.querySelectorAll('.nav-item');
        if (navItems[pageIndex]) {
            navItems[pageIndex].click();
        }
    }
    
    // ESC 键关闭通知
    if (e.key === 'Escape') {
        const notifications = document.querySelectorAll('.notification');
        notifications.forEach(notification => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        });
    }
});

// 窗口大小改变时的响应式处理
window.addEventListener('resize', function() {
    // 移动端适配
    if (window.innerWidth <= 768) {
        document.body.classList.add('mobile');
    } else {
        document.body.classList.remove('mobile');
    }
});

// 初始化检查
window.addEventListener('load', function() {
    if (window.innerWidth <= 768) {
        document.body.classList.add('mobile');
    }
    
    console.log('AUTO_MAA 管理系统原型已加载完成');
    showNotification('系统初始化完成', 'success');
});