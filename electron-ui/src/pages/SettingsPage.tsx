import React, {useState, useEffect} from 'react';
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
    ExperimentOutlined,
    GlobalOutlined
} from '@ant-design/icons';
import {useTranslation} from 'react-i18next';

const {Title, Paragraph} = Typography;

// 主题管理类型
type ThemeMode = 'system' | 'light' | 'dark';

const SettingsPage: React.FC = () => {
    const {t, i18n} = useTranslation();
    const [currentTheme, setCurrentTheme] = useState<ThemeMode>('system');
    const [isDarkMode, setIsDarkMode] = useState(false);
    const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

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
            let isDark: boolean;

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

        let isDark: boolean;
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

        // const themeLabels = {
        //     'light': '浅色',
        //     'dark': '深色',
        //     'system': '跟随系统'
        // };

        // message.success(`已切换到${themeLabels[theme]}模式`);
    };


    const handleLanguageChange = (language: string) => {
        setCurrentLanguage(language);
        i18n.changeLanguage(language);
        localStorage.setItem('language', language);
        message.success(t('pages.settings.actions.languageChanged'));
    };

    const handleResetSettings = () => {
        setAutoStart(true);
        setMinimizeToTray(false);
        setMaxConcurrentTasks(3);
        setTaskTimeout(30);
        setAutoRetry(true);
        setRetryCount(3);
        handleThemeChange('system');
        handleLanguageChange('zh-CN');
        message.success(t('pages.settings.actions.resetSuccess'));
    };

    const tabItems = [
        {
            key: 'appearance',
            label: (
                <span>
                    <SunOutlined/>
                    {t('pages.settings.tabs.appearance')}
                </span>
            ),
            children: (
                <div style={{maxWidth: 600}}>
                    <Title level={4}>{t('pages.settings.appearance.theme.title')}</Title>
                    <Paragraph type="secondary">
                        {t('pages.settings.appearance.theme.description')}
                    </Paragraph>

                    <Radio.Group
                        value={currentTheme}
                        onChange={(e) => handleThemeChange(e.target.value)}
                        size="large"
                    >
                        <Space direction="vertical" size="middle">
                            <Radio value="system">
                                <Space>
                                    <DesktopOutlined/>
                                    <span>{t('pages.settings.appearance.theme.system')}</span>
                                    <span style={{fontSize: '12px'}}>
                                        ({t('pages.settings.appearance.theme.current')}: {isDarkMode ? t('pages.settings.appearance.theme.dark') : t('pages.settings.appearance.theme.light')})
                                    </span>
                                </Space>
                            </Radio>
                            <Radio value="light">
                                <Space>
                                    <SunOutlined/>
                                    <span>{t('pages.settings.appearance.theme.light')}</span>
                                </Space>
                            </Radio>
                            <Radio value="dark">
                                <Space>
                                    <MoonOutlined/>
                                    <span>{t('pages.settings.appearance.theme.dark')}</span>
                                </Space>
                            </Radio>
                        </Space>
                    </Radio.Group>

                    <Divider/>

                    <Title level={4}>{t('pages.settings.appearance.language.title')}</Title>
                    <Paragraph type="secondary">
                        {t('pages.settings.appearance.language.description')}
                    </Paragraph>

                    <Radio.Group
                        value={currentLanguage}
                        onChange={(e) => handleLanguageChange(e.target.value)}
                        size="large"
                    >
                        <Space direction="vertical" size="middle">
                            <Radio value="zh-CN">
                                <Space>
                                    <GlobalOutlined/>
                                    <span>{t('pages.settings.appearance.language.chinese')}</span>
                                </Space>
                            </Radio>
                            <Radio value="en-US">
                                <Space>
                                    <GlobalOutlined/>
                                    <span>{t('pages.settings.appearance.language.english')}</span>
                                </Space>
                            </Radio>
                        </Space>
                    </Radio.Group>

                    <Divider/>

                    <Title level={4}>{t('pages.settings.appearance.startup.title')}</Title>
                    <Space direction="vertical" size="middle">
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.appearance.startup.autoStart')}</span>
                            <Switch checked={autoStart} onChange={setAutoStart}/>
                        </div>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.appearance.startup.minimizeToTray')}</span>
                            <Switch checked={minimizeToTray} onChange={setMinimizeToTray}/>
                        </div>
                    </Space>
                </div>
            ),
        },
        {
            key: 'function',
            label: (
                <span>
                    <SettingOutlined/>
                    {t('pages.settings.tabs.function')}
                </span>
            ),
            children: (
                <div style={{maxWidth: 600}}>
                    <Title level={4}>{t('pages.settings.function.execution.title')}</Title>
                    <Space direction="vertical" size="large" style={{width: '100%'}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.function.execution.maxConcurrent')}</span>
                            <InputNumber
                                min={1}
                                max={10}
                                value={maxConcurrentTasks}
                                onChange={(value) => setMaxConcurrentTasks(value || 3)}
                            />
                        </div>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.function.execution.timeout')}</span>
                            <InputNumber
                                min={5}
                                max={120}
                                value={taskTimeout}
                                onChange={(value) => setTaskTimeout(value || 30)}
                            />
                        </div>
                    </Space>

                    <Divider/>

                    <Title level={4}>{t('pages.settings.function.failure.title')}</Title>
                    <Space direction="vertical" size="middle" style={{width: '100%'}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.function.failure.autoRetry')}</span>
                            <Switch checked={autoRetry} onChange={setAutoRetry}/>
                        </div>
                        {autoRetry && (
                            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                <span>{t('pages.settings.function.failure.retryCount')}</span>
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
                    <BellOutlined/>
                    {t('pages.settings.tabs.notification')}
                </span>
            ),
            children: (
                <div style={{maxWidth: 600}}>
                    <Title level={4}>{t('pages.settings.notification.title')}</Title>
                    <Space direction="vertical" size="middle" style={{width: '100%'}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.notification.taskComplete')}</span>
                            <Switch defaultChecked/>
                        </div>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.notification.taskFailed')}</span>
                            <Switch defaultChecked/>
                        </div>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.notification.systemError')}</span>
                            <Switch/>
                        </div>
                    </Space>
                </div>
            ),
        },
        {
            key: 'advanced',
            label: (
                <span>
                    <ExperimentOutlined/>
                    {t('pages.settings.tabs.advanced')}
                </span>
            ),
            children: (
                <div style={{maxWidth: 600}}>
                    <Title level={4}>{t('pages.settings.advanced.log.title')}</Title>
                    <Space direction="vertical" size="large" style={{width: '100%'}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.advanced.log.level')}</span>
                            <Select
                                defaultValue="INFO"
                                style={{width: 120}}
                                options={[
                                    {value: 'DEBUG', label: 'DEBUG'},
                                    {value: 'INFO', label: 'INFO'},
                                    {value: 'WARN', label: 'WARN'},
                                    {value: 'ERROR', label: 'ERROR'},
                                ]}
                            />
                        </div>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.advanced.log.retention')}</span>
                            <InputNumber
                                min={1}
                                max={365}
                                defaultValue={30}
                            />
                        </div>
                    </Space>

                    <Divider/>

                    <Title level={4}>{t('pages.settings.advanced.developer.title')}</Title>
                    <Space direction="vertical" size="middle" style={{width: '100%'}}>
                        {/*<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>*/}
                        {/*    <span>{t('pages.settings.advanced.developer.debugMode')}</span>*/}
                        {/*    <Switch/>*/}
                        {/*</div>*/}
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                            <span>{t('pages.settings.advanced.developer.devTools')}</span>
                            <Button
                                type="primary"
                                onClick={() => {
                                    if (window.electronAPI) {
                                        window.electronAPI.openDevTools().catch(console.error);
                                        message.success(t('pages.settings.actions.devToolsOpened'));
                                    } else {
                                        message.warning(t('pages.settings.actions.devToolsUnavailable'));
                                    }
                                }}
                            >
                                {t('pages.settings.advanced.developer.openF12')}
                            </Button>
                        </div>
                    </Space>
                </div>
            ),
        },
    ];

    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">{t('pages.settings.title')}</Title>
                <div className="page-actions">
                    <Button onClick={handleResetSettings}>{t('pages.settings.actions.reset')}</Button>
                </div>
            </div>

            <Card>
                <Tabs defaultActiveKey="appearance" size="large" items={tabItems}/>
            </Card>
        </div>
    );
};

export default SettingsPage;