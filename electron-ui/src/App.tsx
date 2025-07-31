import React, {useEffect, useState} from 'react';
import {ConfigProvider, theme} from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Sidebar from './components/Sidebar';
import HomePage from './pages/HomePage';
import ScriptsPage from './pages/ScriptsPage';
import SchedulePage from './pages/SchedulePage';
import QueuePage from './pages/QueuePage';
import CenterPage from './pages/CenterPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [isDarkMode, setIsDarkMode] = useState(false);

  // 监听DOM属性变化来更新主题
  useEffect(() => {
    const checkTheme = () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      setIsDarkMode(currentTheme === 'dark');
    };

    // 初始检查
    checkTheme();

    // 监听主题变化
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
          checkTheme();
        }
      });
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });

    return () => observer.disconnect();
  }, []);

  const handleMenuSelect = (key: string) => {
    setCurrentPage(key);
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage />;
      case 'scripts':
        return <ScriptsPage />;
      case 'schedule':
        return <SchedulePage />;
      case 'queue':
        return <QueuePage />;
      case 'center':
        return <CenterPage />;
      case 'history':
        return <HistoryPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
          // 禁用所有焦点样式
          controlOutline: 'none',
          controlOutlineWidth: 0,
        },
        components: {
          // 禁用按钮焦点样式
          Button: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
          // 禁用Radio焦点样式
          Radio: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
          // 禁用Switch焦点样式
          Switch: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
          // 禁用Select焦点样式
          Select: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
          // 禁用InputNumber焦点样式
          InputNumber: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
          // 禁用Input焦点样式
          Input: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
          // 禁用Tabs焦点样式
          Tabs: {
            controlOutline: 'none',
            controlOutlineWidth: 0,
          },
        },
      }}
    >
      <div className="app-container">
        <Sidebar
          selectedKey={currentPage}
          onMenuSelect={handleMenuSelect}
        />
        <div className="main-content">
          {renderCurrentPage()}
        </div>
      </div>
    </ConfigProvider>
  );
}

export default App;