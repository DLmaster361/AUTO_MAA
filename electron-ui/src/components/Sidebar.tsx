import React from 'react';
import { Layout, Menu } from 'antd';
import {
    HomeOutlined,
    ThunderboltOutlined,
    CalendarOutlined,
    UnorderedListOutlined,
    DashboardOutlined,
    HistoryOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTranslation } from 'react-i18next';
import './Sidebar.css';

const { Sider } = Layout;

interface SidebarProps {
    collapsed?: boolean;
    selectedKey?: string;
    onMenuSelect?: (key: string) => void;
}

type MenuItem = Required<MenuProps>['items'][number];

const Sidebar: React.FC<SidebarProps> = ({
    selectedKey = 'home',
    onMenuSelect,
}) => {
    const { t } = useTranslation();
    
    // 侧边栏一直显示，不再响应屏幕尺寸变化
    const finalCollapsed = false;
    
    // 主要菜单项（靠上）
    const mainMenuItems: MenuItem[] = [
        {
            key: 'home',
            icon: <HomeOutlined />,
            label: t('sidebar.home'),
            title: t('sidebar.home'),
        },
        {
            key: 'scripts',
            icon: <ThunderboltOutlined />,
            label: t('sidebar.scripts'),
            title: t('sidebar.scripts'),
        },
        {
            key: 'schedule',
            icon: <CalendarOutlined />,
            label: t('sidebar.schedule'),
            title: t('sidebar.schedule'),
        },
        {
            key: 'queue',
            icon: <UnorderedListOutlined />,
            label: t('sidebar.queue'),
            title: t('sidebar.queue'),
        },
        {
            key: 'center',
            icon: <DashboardOutlined />,
            label: t('sidebar.center'),
            title: t('sidebar.center'),
        },
    ];

    // 底部菜单项（靠下）
    const bottomMenuItems: MenuItem[] = [
        {
            key: 'history',
            icon: <HistoryOutlined />,
            label: t('sidebar.history'),
            title: t('sidebar.history'),
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: t('sidebar.settings'),
            title: t('sidebar.settings'),
        },
    ];

    const handleMenuClick: MenuProps['onClick'] = (e) => {
        onMenuSelect?.(e.key);
    };

    return (
        <Sider
            collapsed={finalCollapsed}
            width={200}
            collapsedWidth={80}
            className="app-sidebar"
            theme="light"
        >
            {/* Logo 区域 */}
            <div className="sidebar-logo">
                <div className="logo-icon">
                    <img
                        src="/AUTO_MAA.ico"
                        alt="AUTO_MAA Logo"
                        style={{ width: '24px', height: '24px' }}
                        onError={(e) => {
                            // 如果图标加载失败，显示默认图标
                            e.currentTarget.style.display = 'none';
                            e.currentTarget.nextElementSibling?.setAttribute('style', 'display: flex');
                        }}
                    />
                    <ThunderboltOutlined style={{ display: 'none' }} />
                </div>
                {!finalCollapsed && (
                    <div className="logo-text">
                        <span className="logo-title">{t('sidebar.title')}</span>
                        <span className="logo-subtitle">{t('sidebar.subtitle')}</span>
                    </div>
                )}
            </div>

            {/* 主要菜单 */}
            <div className="sidebar-content">
                <Menu
                    mode="inline"
                    selectedKeys={[selectedKey]}
                    items={mainMenuItems}
                    onClick={handleMenuClick}
                    className="main-menu"
                />

                {/* 底部菜单 */}
                <Menu
                    mode="inline"
                    selectedKeys={[selectedKey]}
                    items={bottomMenuItems}
                    onClick={handleMenuClick}
                    className="bottom-menu"
                />
            </div>
        </Sider>
    );
};

export default Sidebar;