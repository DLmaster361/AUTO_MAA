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
import './Sidebar.css';

const { Sider } = Layout;

interface SidebarProps {
  collapsed?: boolean;
  selectedKey?: string;
  onMenuSelect?: (key: string) => void;
}

type MenuItem = Required<MenuProps>['items'][number];

const Sidebar: React.FC<SidebarProps> = ({
  collapsed = false,
  selectedKey = 'home',
  onMenuSelect,
}) => {
  // 主要菜单项（靠上）
  const mainMenuItems: MenuItem[] = [
    {
      key: 'home',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: 'scripts',
      icon: <ThunderboltOutlined />,
      label: '脚本管理',
    },
    {
      key: 'schedule',
      icon: <CalendarOutlined />,
      label: '计划管理',
    },
    {
      key: 'queue',
      icon: <UnorderedListOutlined />,
      label: '调度队列',
    },
    {
      key: 'center',
      icon: <DashboardOutlined />,
      label: '调度中心',
    },
  ];

  // 底部菜单项（靠下）
  const bottomMenuItems: MenuItem[] = [
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: '历史记录',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    onMenuSelect?.(e.key);
  };

  return (
    <Sider
      collapsed={collapsed}
      width={200}
      collapsedWidth={56}
      className="app-sidebar"
      theme="light"
    >
      {/* Logo 区域 */}
      <div className="sidebar-logo">
        <div className="logo-icon">
          <img
            src="/AUTO_MAA.ico"
            alt="AUTO_MAA Logo"
            style={{ width: '100%', height: '100%' }}
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        </div>
        {!collapsed && (
          <div className="logo-text">
            <span className="logo-title">AUTO_MAA</span>
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