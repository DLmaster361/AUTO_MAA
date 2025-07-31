import React, {useState} from 'react';
import {Layout} from 'antd';
import Sidebar from './Sidebar';
import './MainLayout.css';

const { Content } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
  currentPage?: string;
  onPageChange?: (page: string) => void;
}

const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  currentPage = 'home',
  onPageChange,
}) => {
  const [collapsed] = useState(false);
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);

  const handleMenuSelect = (key: string) => {
    onPageChange?.(key);
    // 移动端选择菜单后自动关闭
    if (window.innerWidth <= 768) {
      setMobileMenuVisible(false);
    }
  };

  const toggleMobileMenu = () => {
    setMobileMenuVisible(!mobileMenuVisible);
  };

  return (
    <Layout className="main-layout">
      {/* 侧边栏 */}
      <div className={`sidebar-wrapper ${mobileMenuVisible ? 'mobile-visible' : ''}`}>
        <Sidebar
          collapsed={collapsed}
          selectedKey={currentPage}
          onMenuSelect={handleMenuSelect}
        />
      </div>

      {/* 移动端遮罩 */}
      {mobileMenuVisible && (
        <div className="mobile-overlay" onClick={() => setMobileMenuVisible(false)} />
      )}

      {/* 主内容区域 */}
      <Layout className={`content-layout ${collapsed ? 'collapsed' : ''}`}>
        {/* 移动端顶部栏 */}
        <div className="mobile-header">
          <button className="mobile-menu-btn" onClick={toggleMobileMenu}>
            <span></span>
            <span></span>
            <span></span>
          </button>
          <div className="mobile-title">AUTO_MAA</div>
        </div>

        <Content className="main-content">
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;