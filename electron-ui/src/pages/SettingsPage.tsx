import React, { useState, useEffect } from 'react';
import {
    Card,
    Typography,
    Tabs,
    Radio,
    Space,
    Switch,
    Select,
    InputNumber,
    Divider,
    Button,
    message
} from 'antd';
import {
    SunOutlined,
    MoonOutlined,
    DesktopOutlined,
    BellOutlined,
    SettingOutlined,
    ExperimentOutlined
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

// 主题管理类型
type ThemeMode = 'system' | 'light' | 'dark';

const SettingsPage: React.FC = () => {
    const [currentTheme, setCurrentTheme] = useState<ThemeMode>('system');
    const [isDarkMode, setIsDarkMode] = useState(false);

    // 其他设置状态
    const [autoStart, setAutoStart] = useState(true);
    const [minimizeToTray, setMinimizeToTray] = useState(false);
    const [maxConcurrentTasks, setMaxConcurrentTasks] = useState(3);
    const [taskTimeout, setTaskTimeout] = useState(30);
    const [autoRetry, setAutoRetry] = useState(true);
    const [retryCount, setRetryCount] = useState(3);

    useEffect(() => {
        // 初始化主题
        const savedTheme = localStorage.getItem('theme-mode') as ThemeMode;
        if (savedTheme && ['system', 'light', 'dark'].includes(savedTheme)) {
            setCurrentTheme(savedTheme);
        }

        // 检查当前是否为深色模式
        const checkDarkMode = () => {
            const currentThemeValue = savedTheme || 'system';
            let isDark = false;

            switch (currentThemeValue) {
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

            setIsDarkMode(isDark);
            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        };

        checkDarkMode();
    }, []);

    const handleThemeChange = (theme: ThemeMode) => {
        setCurrentTheme(theme);
        localStorage.setItem('theme-mode', theme);

        let isDark = false;
        switch (theme) {
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

        setIsDarkMode(isDark);
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');

        // 强制触发页面重新渲染，确保所有组件都应用新主题
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 100);

        const themeLabels = {
            'light': '浅色',
            'dark': '深色',
            'system': '跟随系统'
        };

        message.success(`已切换到${themeLabels[theme]}模式`);
    };



    const handleResetSettings = () => {
        setAutoStart(true);
        setMinimizeToTray(false);
        setMaxConcurrentTasks(3);
        setTaskTimeout(30);
        setAutoRetry(true);
        setRetryCount(3);
        handleThemeChange('system');
        message.success('设置已重置为默认值');
    };

    const tabItems = [
        {
            key: 'appearance',
            label: (
                <span>
                    <SunOutlined />
                    外观设置
                </span>
            ),
            children: (
                <div style={{ maxWidth: 600 }}>
                    <Title level={4}>主题模式</Title>
                    <Paragraph type="secondary">
                        选择应用程序的外观主题。跟随系统将根据您的操作系统设置自动切换。
                    </Paragraph>

                    <Radio.Group
                        value={currentTheme}
                        onChange={(e) => handleThemeChange(e.target.value)}
                        size="large"
                    >
                        <Space direction="vertical" size="middle">
                            <Radio value="system">
                                <Space>
                                    <DesktopOutlined />
                                    <span>跟随系统</span>
                                    <span style={{  fontSize: '12px' }}>
                                        (当前: {isDarkMode ? '深色' : '浅色'})
                                    </span>
                                </Space>
                            </Radio>
                            <Radio value="light">
                                <Space>
                                    <SunOutlined />
                                    <span>浅色模式</span>
                                </Space>
                            </Radio>
                            <Radio value="dark">
                                <Space>
                                    <MoonOutlined />
                                    <span>深色模式</span>
                                </Space>
                            </Radio>
                        </Space>
                    </Radio.Group>

                    <Divider />

                    <Title level={4}>启动设置</Title>
                    <Space direction="vertical" size="middle">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>开机自启动</span>
                            <Switch checked={autoStart} onChange={setAutoStart} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>最小化到系统托盘</span>
                            <Switch checked={minimizeToTray} onChange={setMinimizeToTray} />
                        </div>
                    </Space>
                </div>
            ),
        },
        {
            key: 'schedule',
            label: (
                <span>
                    <SettingOutlined />
                    功能设置
                </span>
            ),
            children: (
                <div style={{ maxWidth: 600 }}>
                    <Title level={4}>任务执行</Title>
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>最大并发任务数</span>
                            <InputNumber
                                min={1}
                                max={10}
                                value={maxConcurrentTasks}
                                onChange={(value) => setMaxConcurrentTasks(value || 3)}
                            />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>任务超时时间 (分钟)</span>
                            <InputNumber
                                min={5}
                                max={120}
                                value={taskTimeout}
                                onChange={(value) => setTaskTimeout(value || 30)}
                            />
                        </div>
                    </Space>

                    <Divider />

                    <Title level={4}>失败处理</Title>
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>失败任务自动重试</span>
                            <Switch checked={autoRetry} onChange={setAutoRetry} />
                        </div>
                        {autoRetry && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span>重试次数</span>
                                <InputNumber
                                    min={1}
                                    max={5}
                                    value={retryCount}
                                    onChange={(value) => setRetryCount(value || 3)}
                                />
                            </div>
                        )}
                    </Space>
                </div>
            ),
        },
        {
            key: 'notification',
            label: (
                <span>
                    <BellOutlined />
                    通知设置
                </span>
            ),
            children: (
                <div style={{ maxWidth: 600 }}>
                    <Title level={4}>任务通知</Title>
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>任务完成通知</span>
                            <Switch defaultChecked />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>任务失败通知</span>
                            <Switch defaultChecked />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>系统错误通知</span>
                            <Switch />
                        </div>
                    </Space>
                </div>
            ),
        },
        {
            key: 'advanced',
            label: (
                <span>
                    <ExperimentOutlined />
                    更新设置
                </span>
            ),
            children: (
                <div style={{ maxWidth: 600 }}>
                    <Title level={4}>日志设置</Title>
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>日志级别</span>
                            <Select
                                defaultValue="INFO"
                                style={{ width: 120 }}
                                options={[
                                    { value: 'DEBUG', label: 'DEBUG' },
                                    { value: 'INFO', label: 'INFO' },
                                    { value: 'WARN', label: 'WARN' },
                                    { value: 'ERROR', label: 'ERROR' },
                                ]}
                            />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>日志保留天数</span>
                            <InputNumber
                                min={1}
                                max={365}
                                defaultValue={30}
                            />
                        </div>
                    </Space>

                    <Divider />

                    <Title level={4}>开发者选项</Title>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>启用调试模式</span>
                        <Switch />
                    </div>
                </div>
            ),
        },
    ];

    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">设置</Title>
                <div className="page-actions">
                    <Button onClick={handleResetSettings}>重置默认</Button>
                </div>
            </div>

            <Card>
                <Tabs defaultActiveKey="appearance" size="large" items={tabItems} />
            </Card>
        </div>
    );
};

export default SettingsPage;