import {useEffect, useState} from 'react';
import {ConfigProvider, theme} from 'antd';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { useTranslation } from 'react-i18next';
import './i18n';
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
    const { i18n } = useTranslation();
    
    // 获取当前语言对应的 Ant Design locale
    const getAntdLocale = () => {
        return i18n.language === 'en-US' ? enUS : zhCN;
    };

    // 初始化和监听主题变化
    useEffect(() => {
        // 初始化主题
        const initializeTheme = () => {
            const savedTheme = localStorage.getItem('theme-mode') as 'system' | 'light' | 'dark';
            let isDark: boolean;

            if (savedTheme && ['system', 'light', 'dark'].includes(savedTheme)) {
                switch (savedTheme) {
                    case 'dark':
                        isDark = true;
                        break;
                    case 'light':
                        isDark = false;
                        break;
                    case 'system':
                    default:
                        isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                        break;
                }
            } else {
                // 如果没有保存的主题设置，默认跟随系统
                isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                localStorage.setItem('theme-mode', 'system');
            }

            setIsDarkMode(isDark);
            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        };

        const checkTheme = () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            setIsDarkMode(currentTheme === 'dark');
        };

        // 初始化主题
        initializeTheme();

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

        // 监听系统主题变化（当设置为跟随系统时）
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleSystemThemeChange = () => {
            const savedTheme = localStorage.getItem('theme-mode');
            if (savedTheme === 'system' || !savedTheme) {
                const isDark = mediaQuery.matches;
                setIsDarkMode(isDark);
                document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
            }
        };

        mediaQuery.addEventListener('change', handleSystemThemeChange);

        return () => {
            observer.disconnect();
            mediaQuery.removeEventListener('change', handleSystemThemeChange);
        };
    }, []);

    const handleMenuSelect = (key: string) => {
        setCurrentPage(key);
    };

    const renderCurrentPage = () => {
        switch (currentPage) {
            case 'home':
                return <HomePage/>;
            case 'scripts':
                return <ScriptsPage/>;
            case 'schedule':
                return <SchedulePage/>;
            case 'queue':
                return <QueuePage/>;
            case 'center':
                return <CenterPage/>;
            case 'history':
                return <HistoryPage/>;
            case 'settings':
                return <SettingsPage/>;
            default:
                return <HomePage/>;
        }
    };

    return (
        <ConfigProvider
            locale={getAntdLocale()}
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
                <div className="app-body">
                    <Sidebar
                        selectedKey={currentPage}
                        onMenuSelect={handleMenuSelect}
                    />
                    <div className="main-content">
                        {renderCurrentPage()}
                    </div>
                </div>
            </div>
        </ConfigProvider>
    );
}

export default App;