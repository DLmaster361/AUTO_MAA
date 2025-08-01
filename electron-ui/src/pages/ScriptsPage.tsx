import React, {useState} from 'react';
import {
    Badge,
    Button,
    Card,
    Col,
    Divider,
    Form,
    Input,
    InputNumber,
    message,
    Modal,
    Popconfirm,
    Radio,
    Row,
    Select,
    Space,
    Switch,
    Table,
    Tabs,
    Tag,
    Tooltip,
    Typography
} from 'antd';
import {
    DeleteOutlined,
    DownOutlined,
    EditOutlined,
    PlusOutlined,
    RightOutlined,
    SettingOutlined,
    UserAddOutlined,
    UserOutlined,
} from '@ant-design/icons';
import {useTranslation} from 'react-i18next';

const {Title} = Typography;
const {Option} = Select;

// 脚本配置类型
interface ScriptConfig {
    MaaSet: {
        Name: string;
        Path: string;
    };
    RunSet: {
        ADBSearchRange: number;
        AnnihilationTimeLimit: number;
        AnnihilationWeeklyLimit: boolean;
        ProxyTimesLimit: number;
        RoutineTimeLimit: number;
        RunTimesLimit: number;
        TaskTransitionMethod: string;
    };
}

// 脚本数据类型
interface Script {
    id: string;
    name: string;
    status: 'active' | 'inactive';
    userCount: number;
    lastRun: string;
    description?: string;
    config: ScriptConfig;
}

// 用户配置类型
interface UserConfig {
    Data: {
        CustomInfrastPlanIndex: string;
        IfPassCheck: boolean;
        LastAnnihilationDate: string;
        LastProxyDate: string;
        LastSklandDate: string;
        ProxyTimes: number;
    };
    Info: {
        Annihilation: string;
        Id: string;
        IfSkland: boolean;
        InfrastMode: string;
        MedicineNumb: number;
        Mode: string;
        Name: string;
        Notes: string;
        Password: string;
        RemainedDay: number;
        Routine: boolean;
        SeriesNumb: string;
        Server: string;
        SklandToken: string;
        Stage: string;
        StageMode: string;
        Stage_1: string;
        Stage_2: string;
        Stage_3: string;
        Stage_Remain: string;
        Status: boolean;
    };
    Notify: {
        CompanyWebHookBotUrl: string;
        Enabled: boolean;
        IfCompanyWebHookBot: boolean;
        IfSendMail: boolean;
        IfSendSixStar: boolean;
        IfSendStatistic: boolean;
        IfServerChan: boolean;
        ServerChanChannel: string;
        ServerChanKey: string;
        ServerChanTag: string;
        ToAddress: string;
    };
    Task: {
        IfAutoRoguelike: boolean;
        IfBase: boolean;
        IfCombat: boolean;
        IfMall: boolean;
        IfMission: boolean;
        IfReclamation: boolean;
        IfRecruiting: boolean;
        IfWakeUp: boolean;
    };
}

// 用户数据类型
interface User {
    id: string;
    scriptId: string;
    config: UserConfig;
}

const ScriptsPage: React.FC = () => {
    const {t} = useTranslation();

    const [scripts, setScripts] = useState<Script[]>([
        {
            id: '1',
            name: '脚本 1',
            status: 'active',
            userCount: 1,
            lastRun: '2024-01-01 10:30:00',
            description: 'MAA自动化脚本',
            config: {
                MaaSet: {
                    Name: "1",
                    Path: "D:/MAA_For_AutoMAA"
                },
                RunSet: {
                    ADBSearchRange: 3,
                    AnnihilationTimeLimit: 40,
                    AnnihilationWeeklyLimit: true,
                    ProxyTimesLimit: 0,
                    RoutineTimeLimit: 10,
                    RunTimesLimit: 5,
                    TaskTransitionMethod: "NoAction"
                }
            }
        }
    ]);

    const [users, setUsers] = useState<User[]>([
        {
            id: '1',
            scriptId: '1',
            config: {
                Data: {
                    CustomInfrastPlanIndex: "0",
                    IfPassCheck: true,
                    LastAnnihilationDate: "2025-07-28",
                    LastProxyDate: "2025-08-01",
                    LastSklandDate: "2000-01-01",
                    ProxyTimes: 1
                },
                Info: {
                    Annihilation: "Close",
                    Id: "8668",
                    IfSkland: false,
                    InfrastMode: "Normal",
                    MedicineNumb: 0,
                    Mode: "简洁",
                    Name: "aoxuan",
                    Notes: "无",
                    Password: "encrypted_password",
                    RemainedDay: -1,
                    Routine: false,
                    SeriesNumb: "0",
                    Server: "Official",
                    SklandToken: "",
                    Stage: "1-7",
                    StageMode: "固定",
                    Stage_1: "-",
                    Stage_2: "-",
                    Stage_3: "-",
                    Stage_Remain: "-",
                    Status: true
                },
                Notify: {
                    CompanyWebHookBotUrl: "",
                    Enabled: false,
                    IfCompanyWebHookBot: false,
                    IfSendMail: false,
                    IfSendSixStar: false,
                    IfSendStatistic: false,
                    IfServerChan: false,
                    ServerChanChannel: "",
                    ServerChanKey: "",
                    ServerChanTag: "",
                    ToAddress: ""
                },
                Task: {
                    IfAutoRoguelike: false,
                    IfBase: true,
                    IfCombat: true,
                    IfMall: true,
                    IfMission: true,
                    IfReclamation: false,
                    IfRecruiting: true,
                    IfWakeUp: true
                }
            }
        }
    ]);
    const [selectedScript, setSelectedScript] = useState<Script | null>(null);
    const [isScriptModalVisible, setIsScriptModalVisible] = useState(false);
    const [isUserModalVisible, setIsUserModalVisible] = useState(false);
    const [isScriptSettingsVisible, setIsScriptSettingsVisible] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [scriptForm] = Form.useForm();
    const [userForm] = Form.useForm();
    const [scriptSettingsForm] = Form.useForm();

    // HTTP请求函数（后期实现）
    const toggleScriptStatus = async (scriptId: string, status: 'active' | 'inactive') => {
        // TODO: 实现HTTP请求
        console.log(`Toggling script ${scriptId} to ${status}`)
        return new Promise(resolve => setTimeout(resolve, 500));
    };


    // 脚本列表列定义
    const scriptColumns = [
        {
            title: t('pages.scripts.scriptName'),
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => (
                <span style={{fontWeight: 500}}>{text}</span>
            ),
        },
        // {
        //     title: t('pages.scripts.status'),
        //     dataIndex: 'status',
        //     key: 'status',
        //     render: (status: string, record: Script) => (
        //         <Switch
        //             checked={status === 'active'}
        //             onChange={(checked) => handleToggleScript(record, checked)}
        //             checkedChildren="运行"
        //             unCheckedChildren="停止"
        //         />
        //     ),
        // },
        {
            title: t('pages.scripts.userCount'),
            dataIndex: 'userCount',
            key: 'userCount',
            render: (count: number, record: Script) => {
                const scriptUsers = users.filter(u => u.scriptId === record.id);
                const userNames = scriptUsers.map(u => u.config.Info.Name).join(', ');

                return (
                    <Tooltip title={userNames || '暂无用户'}>
                        <span style={{cursor: 'pointer', color: '#1677ff'}}>{count}</span>
                    </Tooltip>
                );
            },
        },
        // {
        //     title: t('pages.scripts.lastRun'),
        //     dataIndex: 'lastRun',
        //     key: 'lastRun',
        // },
        {
            title: t('pages.scripts.actions'),
            key: 'action',
            render: (_: any, record: Script) => (
                <Space>
                    <Button
                        type="text"
                        icon={<SettingOutlined/>}
                        onClick={() => handleScriptSettings(record)}
                    >
                        脚本管理
                    </Button>
                    <Button
                        type="text"
                        icon={<UserAddOutlined/>}
                        onClick={() => handleAddUser(record)}
                    >
                        新增用户
                    </Button>
                    <Popconfirm
                        title={t('pages.scripts.confirmDeleteScript')}
                        onConfirm={() => handleDeleteScript(record.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                    >
                        <Button type="text" danger icon={<DeleteOutlined/>}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];
    // 用户列表列定义
    const userColumns = [
        {
            title: t('pages.scripts.username'),
            dataIndex: ['config', 'Info', 'Name'],
            key: 'username',
            render: (text: string, record: User) => (
                <Space>
                    <Badge status={record.config.Info.Status ? 'success' : 'default'}/>
                    <span style={{fontWeight: 500}}>{text}</span>
                </Space>
            ),
        },
        {
            title: t('pages.scripts.accountId'),
            dataIndex: ['config', 'Info', 'Id'],
            key: 'accountId',
        },
        {
            title: t('pages.scripts.server'),
            dataIndex: ['config', 'Info', 'Server'],
            key: 'server',
            render: (server: string) => <Tag>{server === 'Official' ? '官服' : 'B服'}</Tag>,
        },
        {
            title: t('pages.scripts.status'),
            dataIndex: ['config', 'Info', 'Status'],
            key: 'status',
            render: (status: boolean) => (
                <Tag color={status ? 'green' : 'default'}>
                    {status ? t('pages.scripts.active') : t('pages.scripts.inactive')}
                </Tag>
            ),
        },
        {
            title: '最后代理日期',
            dataIndex: ['config', 'Data', 'LastProxyDate'],
            key: 'lastProxy',
        },
        // todo 这一块根据返回值进行修改
        {
            title: '代理情况',
            dataIndex: ['config', 'Data', 'LastLogin'],
            key: 'lastLogin',
        },
        {
            title: t('pages.scripts.actions'),
            key: 'action',
            render: (_: any, record: User) => (
                <Space>
                    <Button
                        type="text"
                        icon={<SettingOutlined/>}
                        onClick={() => handleEditUser(record)}>
                        配置
                    </Button>
                    <Popconfirm
                        title={t('pages.scripts.confirmDeleteUser')}
                        onConfirm={() => handleDeleteUser(record.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                    >
                        <Button type="text" danger icon={<DeleteOutlined/>}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];
    // 处理函数
    const handleAddScript = () => {
        setSelectedScript(null);
        setIsScriptModalVisible(true);
        scriptForm.resetFields();
    };

    const handleScriptSettings = (script: Script) => {
        setSelectedScript(script);
        setIsScriptSettingsVisible(true);
        scriptSettingsForm.setFieldsValue(script.config);
    };

    const handleToggleScript = async (script: Script, checked: boolean) => {
        const newStatus = checked ? 'active' : 'inactive';

        try {
            await toggleScriptStatus(script.id, newStatus);
            setScripts(scripts.map(s =>
                s.id === script.id ? {...s, status: newStatus} : s
            ));
            message.success(newStatus === 'active' ? t('pages.scripts.scriptStarted') : t('pages.scripts.scriptStopped'));
        } catch (error) {
            message.error('状态切换失败');
        }
    };

    const handleDeleteScript = (scriptId: string) => {
        setScripts(scripts.filter(s => s.id !== scriptId));
        setUsers(users.filter(u => u.scriptId !== scriptId));
        message.success(t('pages.scripts.scriptDeleted'));
    };


    const handleAddUser = (script: Script) => {
        setSelectedScript(script);
        setEditingUser(null);
        setIsUserModalVisible(true);
        userForm.resetFields();
    };

    const handleEditUser = (user: User) => {
        setEditingUser(user);
        setIsUserModalVisible(true);
        userForm.setFieldsValue(user);
    };

    const handleDeleteUser = (userId: string) => {
        setUsers(users.filter(u => u.id !== userId));
        const user = users.find(u => u.id === userId);
        if (user) {
            setScripts(scripts.map(s =>
                s.id === user.scriptId ? {...s, userCount: s.userCount - 1} : s
            ));
        }
        message.success(t('pages.scripts.userDeleted'));
    };
    const handleScriptSubmit = (values: any) => {
        if (selectedScript) {
            setScripts(scripts.map(s =>
                s.id === selectedScript.id ? {...s, ...values} : s
            ));
            message.success(t('pages.scripts.scriptUpdated'));
            setIsScriptModalVisible(false);
            setSelectedScript(null);
        } else {
            const newScript: Script = {
                id: Date.now().toString(),
                ...values,
                status: 'inactive',
                userCount: 0,
                lastRun: t('pages.scripts.neverRun'),
                config: {
                    MaaSet: {
                        Name: values.name || "新脚本",
                        Path: "D:/MAA_For_AutoMAA"
                    },
                    RunSet: {
                        ADBSearchRange: 3,
                        AnnihilationTimeLimit: 40,
                        AnnihilationWeeklyLimit: true,
                        ProxyTimesLimit: 0,
                        RoutineTimeLimit: 10,
                        RunTimesLimit: 5,
                        TaskTransitionMethod: "NoAction"
                    }
                }
            };
            setScripts([...scripts, newScript]);
            message.success(t('pages.scripts.scriptAdded'));
            setIsScriptModalVisible(false);
            setSelectedScript(null);

            // 添加完脚本后直接打开设置页面
            setTimeout(() => {
                setSelectedScript(newScript);
                setIsScriptSettingsVisible(true);
                scriptSettingsForm.setFieldsValue(newScript.config);
            }, 100);
        }
    };

    const handleUserSubmit = (values: any) => {
        if (editingUser) {
            setUsers(users.map(u =>
                u.id === editingUser.id ? {...u, ...values} : u
            ));
            message.success(t('pages.scripts.userUpdated'));
        } else {
            const newUser: User = {
                id: Date.now().toString(),
                scriptId: selectedScript?.id || '',
                config: {
                    Data: {
                        CustomInfrastPlanIndex: "0",
                        IfPassCheck: true,
                        LastAnnihilationDate: "2000-01-01",
                        LastProxyDate: "2000-01-01",
                        LastSklandDate: "2000-01-01",
                        ProxyTimes: 0
                    },
                    Info: {
                        Annihilation: "Close",
                        Id: values.config?.Info?.Id || "",
                        IfSkland: false,
                        InfrastMode: "Normal",
                        MedicineNumb: 0,
                        Mode: "简洁",
                        Name: values.config?.Info?.Name || "",
                        Notes: "无",
                        Password: values.config?.Info?.Password || "",
                        RemainedDay: -1,
                        Routine: false,
                        SeriesNumb: "0",
                        Server: values.config?.Info?.Server || "Official",
                        SklandToken: "",
                        Stage: "1-7",
                        StageMode: "固定",
                        Stage_1: "-",
                        Stage_2: "-",
                        Stage_3: "-",
                        Stage_Remain: "-",
                        Status: values.config?.Info?.Status || true
                    },
                    Notify: {
                        CompanyWebHookBotUrl: "",
                        Enabled: false,
                        IfCompanyWebHookBot: false,
                        IfSendMail: false,
                        IfSendSixStar: false,
                        IfSendStatistic: false,
                        IfServerChan: false,
                        ServerChanChannel: "",
                        ServerChanKey: "",
                        ServerChanTag: "",
                        ToAddress: ""
                    },
                    Task: {
                        IfAutoRoguelike: false,
                        IfBase: true,
                        IfCombat: true,
                        IfMall: true,
                        IfMission: true,
                        IfReclamation: false,
                        IfRecruiting: true,
                        IfWakeUp: true
                    }
                }
            };
            setUsers([...users, newUser]);
            setScripts(scripts.map(s =>
                s.id === selectedScript?.id ? {...s, userCount: s.userCount + 1} : s
            ));
            message.success(t('pages.scripts.userAdded'));
        }
        setIsUserModalVisible(false);
        setEditingUser(null);
    };

    const handleScriptSettingsSubmit = (values: any) => {
        if (selectedScript) {
            setScripts(scripts.map(s =>
                s.id === selectedScript.id ? {...s, config: values} : s
            ));
            message.success('脚本设置已更新');
        }
        setIsScriptSettingsVisible(false);
    };

    const currentScriptUsers = selectedScript ? users.filter(u => u.scriptId === selectedScript.id) : [];

    // 文件选择处理函数
    const handleSelectMaaDirectory = async () => {
        try {
            if (window.electronAPI && window.electronAPI.selectDirectory) {
                const selectedPath = await window.electronAPI.selectDirectory();
                if (selectedPath) {
                    // 更新表单中的MAA目录路径
                    scriptSettingsForm.setFieldsValue({
                        MaaSet: {
                            ...scriptSettingsForm.getFieldValue(['MaaSet']),
                            Path: selectedPath
                        }
                    });
                    message.success('MAA目录选择成功');
                } else {
                    message.info('未选择目录');
                }
            } else {
                message.warning('文件选择功能仅在桌面应用中可用');
            }
        } catch (error) {
            console.error('文件选择错误:', error);
            message.error('文件选择失败');
        }
    };

    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">{t('pages.scripts.title')}</Title>
                <div className="page-actions">
                    <Space>
                        <Button
                            type="primary"
                            icon={<PlusOutlined/>}
                            onClick={handleAddScript}
                        >
                            {t('pages.scripts.addScript')}
                        </Button>
                    </Space>
                </div>
            </div>

            <Card>
                <Table
                    columns={scriptColumns}
                    dataSource={scripts}
                    rowKey="id"
                    pagination={false}
                    expandable={{
                        expandedRowRender: (record: Script) => {
                            const scriptUsers = users.filter(u => u.scriptId === record.id);
                            return (
                                <div style={{margin: 0}}>
                                    {scriptUsers.length > 0 ? (
                                        <Table
                                            columns={userColumns}
                                            dataSource={scriptUsers}
                                            rowKey="id"
                                            pagination={false}
                                            size="small"
                                            showHeader={true}
                                        />
                                    ) : (
                                        <div style={{
                                            textAlign: 'center',
                                            padding: '40px',
                                            color: '#999',
                                            backgroundColor: '#fafafa',
                                            borderRadius: '6px'
                                        }}>
                                            <UserOutlined
                                                style={{fontSize: '24px', marginBottom: '8px', color: '#d9d9d9'}}/>
                                            <div>暂无用户，点击"新增用户"按钮添加用户</div>
                                        </div>
                                    )}
                                </div>
                            );
                        },
                        defaultExpandAllRows: true,
                        expandIcon: ({expanded, onExpand, record}) => (
                            <Button
                                type="text"
                                size="small"
                                icon={expanded ? <DownOutlined/> : <RightOutlined/>}
                                onClick={e => onExpand(record, e)}
                                style={{
                                    color: expanded ? '#1677ff' : '#666',
                                    transition: 'all 0.2s'
                                }}
                            />
                        )
                    }}
                />
            </Card>

            {/* 脚本添加/编辑模态框 */}
            <Modal
                title={selectedScript ? t('pages.scripts.editScript') : t('pages.scripts.addScript')}
                open={isScriptModalVisible}
                onCancel={() => {
                    setIsScriptModalVisible(false);
                    setSelectedScript(null);
                }}
                footer={null}
                width={600}
            >
                <Form
                    form={scriptForm}
                    layout="vertical"
                    onFinish={handleScriptSubmit}
                >
                    <Form.Item
                        name="name"
                        label={t('pages.scripts.scriptName')}
                        rules={[{required: true, message: t('pages.scripts.pleaseEnterScriptName')}]}
                    >
                        <Input placeholder={t('pages.scripts.pleaseEnterScriptName')}/>
                    </Form.Item>
                    <Form.Item
                        name="type"
                        label="脚本类型（添加MAA类型脚本选择MAA，其他脚本请选择通用）"
                        initialValue="MAA"
                    >
                        <Radio.Group>
                            <Radio value="MAA"> MAA </Radio>
                            <Radio value="Universal"> 通用 </Radio>
                        </Radio.Group>
                    </Form.Item>
                    <Form.Item>
                        <Space>
                            <Button type="primary" htmlType="submit">
                                {selectedScript ? t('pages.scripts.update') : t('common.add')}
                            </Button>
                            <Button onClick={() => {
                                setIsScriptModalVisible(false);
                                setSelectedScript(null);
                            }}>
                                {t('common.cancel')}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
            {/* 脚本设置模态框 */}
            <Modal
                title={`${t('pages.scripts.scriptSettings')} - ${selectedScript?.name}`}
                open={isScriptSettingsVisible}
                onCancel={() => setIsScriptSettingsVisible(false)}
                footer={null}
                width={800}
            >
                <Form
                    form={scriptSettingsForm}
                    layout="vertical"
                    onFinish={handleScriptSettingsSubmit}
                >
                    <Tabs
                        defaultActiveKey="basic"
                        items={[
                            {
                                key: 'basic',
                                label: t('pages.scripts.basicSettings'),
                                children: (
                                    <div>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            实例名称
                                                            <Tooltip title="为这个脚本实例设置一个便于识别的名称">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['MaaSet', 'Name']}
                                                >
                                                    <Input placeholder="请输入实例名称"/>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            MAA目录
                                                            <Tooltip title="选择MAA.exe文件所在的目录路径">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                >
                                                    <Input.Group compact>
                                                        <Form.Item
                                                            name={['MaaSet', 'Path']}
                                                            noStyle
                                                        >
                                                            <Input
                                                                placeholder="请选择MAA.exe所在目录"
                                                                style={{width: 'calc(100% - 80px)'}}
                                                                readOnly
                                                            />
                                                        </Form.Item>
                                                        <Button
                                                            onClick={handleSelectMaaDirectory}
                                                        >
                                                            选择
                                                        </Button>
                                                    </Input.Group>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            任务切换方式
                                                            <Tooltip
                                                                title="设置在切换用户时采用的方式：直接切换账号、重启明日方舟或重启模拟器">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'TaskTransitionMethod']}
                                                >
                                                    <Select>
                                                        <Option value="SwitchAccount">直接切换账号</Option>
                                                        <Option value="RestartArknights">重启明日方舟</Option>
                                                        <Option value="RestartEmulator">重启模拟器</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            ADB端口号查找范围
                                                            <Tooltip
                                                                title="设置ADB端口号的查找范围，用于连接模拟器或设备">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'ADBSearchRange']}
                                                >
                                                    <InputNumber min={1} max={100} style={{width: '100%'}}/>
                                                </Form.Item>
                                            </Col>

                                        </Row>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            剿灭每周代理上限
                                                            <Tooltip title="是否启用每周剿灭代理次数限制">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'AnnihilationWeeklyLimit']}
                                                    valuePropName="checked"
                                                >
                                                    <Select>
                                                        <Option value="true">是</Option>
                                                        <Option value="false">否</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>

                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            剿灭最大代理时长（分钟）
                                                            <Tooltip
                                                                title="设置单次剿灭任务的最大执行时间，超时后会停止任务">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'AnnihilationTimeLimit']}
                                                >
                                                    <InputNumber min={1} max={999} style={{width: '100%'}}/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                        <Row gutter={16}>


                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            用户单日代理次数上限
                                                            <Tooltip
                                                                title="设置每个用户每天最多可以代理的次数，0表示无限制">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'ProxyTimesLimit']}
                                                >
                                                    <InputNumber min={0} max={100} style={{width: '100%'}}/>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            代理重试次数上限
                                                            <Tooltip title="设置任务失败时的最大重试次数">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'RunTimesLimit']}
                                                >
                                                    <InputNumber min={0} max={20} style={{width: '100%'}}/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    label={
                                                        <span>
                                                            每周常规代理时长上限（分钟）
                                                            <Tooltip title="设置每周常规任务代理的最大时长">
                                                                <span style={{marginLeft: 4, color: '#999'}}>(?)</span>
                                                            </Tooltip>
                                                        </span>
                                                    }
                                                    name={['RunSet', 'RoutineTimeLimit']}
                                                >
                                                    <InputNumber min={1} max={1000} style={{width: '100%'}}/>
                                                </Form.Item>
                                            </Col>

                                        </Row>
                                        <Form.Item>
                                            <Space>
                                                <Button type="primary" htmlType="submit">
                                                    保存设置
                                                </Button>
                                                <Button onClick={() => setIsScriptSettingsVisible(false)}>
                                                    取消
                                                </Button>
                                            </Space>
                                        </Form.Item>
                                    </div>
                                )
                            },
                            {
                                key: 'users',
                                label: t('pages.scripts.userManagement'),
                                children: (
                                    <div>
                                        <div style={{marginBottom: 16}}>
                                            <Button
                                                type="primary"
                                                icon={<PlusOutlined/>}
                                                onClick={handleAddUser}
                                            >
                                                {t('pages.scripts.addUser')}
                                            </Button>
                                        </div>
                                        <Table
                                            columns={userColumns}
                                            dataSource={currentScriptUsers}
                                            rowKey="id"
                                            pagination={false}
                                            size="small"
                                        />
                                    </div>
                                )
                            }
                        ]}
                    />
                </Form>
            </Modal>
            {/* 用户添加/编辑模态框 */}
            <Modal
                title={editingUser ? t('pages.scripts.editUser') : t('pages.scripts.addUser')}
                open={isUserModalVisible}
                onCancel={() => {
                    setIsUserModalVisible(false);
                    setEditingUser(null);
                }}
                footer={null}
                width={900}
            >
                <Form
                    form={userForm}
                    layout="vertical"
                    onFinish={handleUserSubmit}
                >
                    <Tabs
                        defaultActiveKey="basic"
                        items={[
                            {
                                key: 'basic',
                                label: '基本信息',
                                children: (
                                    <div>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Name']}
                                                    label="用户名"
                                                    rules={[{required: true, message: '请输入用户名'}]}
                                                >
                                                    <Input placeholder="请输入用户名"/>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Id']}
                                                    label="账号ID"
                                                    rules={[{required: true, message: '请输入账号ID'}]}
                                                >
                                                    <Input placeholder="请输入账号ID"/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Server']}
                                                    label="服务器"
                                                    rules={[{required: true, message: '请选择服务器'}]}
                                                >
                                                    <Select placeholder="请选择服务器">
                                                        <Option value="Official">官服</Option>
                                                        <Option value="Bilibili">B服</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Status']}
                                                    label="用户状态"
                                                    valuePropName="checked"
                                                >
                                                    <Switch checkedChildren="启用" unCheckedChildren="禁用"/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Password']}
                                                    label="密码"
                                                >
                                                    <Input.Password placeholder="请输入密码"/>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Notes']}
                                                    label="备注"
                                                >
                                                    <Input placeholder="请输入备注"/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                    </div>
                                )
                            },
                            {
                                key: 'stage',
                                label: '关卡设置',
                                children: (
                                    <div>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'Stage']}
                                                    label="关卡选择"
                                                >
                                                    <Select defaultValue="1-7">
                                                        <Option value="1-7">1-7</Option>
                                                        <Option value="CE-6">CE-6</Option>
                                                        <Option value="AP-5">AP-5</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Info', 'StageMode']}
                                                    label="关卡模式"
                                                >
                                                    <Select defaultValue="固定">
                                                        <Option value="固定">固定</Option>
                                                        <Option value="轮换">轮换</Option>
                                                    </Select>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                    </div>
                                )
                            },
                            {
                                key: 'task',
                                label: '任务设置',
                                children: (
                                    <div>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Task', 'IfBase']}
                                                    label="基建换班"
                                                    valuePropName="checked"
                                                >
                                                    <Switch checkedChildren="开启" unCheckedChildren="关闭"/>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Task', 'IfCombat']}
                                                    label="刷理智"
                                                    valuePropName="checked"
                                                >
                                                    <Switch checkedChildren="开启" unCheckedChildren="关闭"/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                        <Row gutter={16}>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Task', 'IfMission']}
                                                    label="领取奖励"
                                                    valuePropName="checked"
                                                >
                                                    <Switch checkedChildren="开启" unCheckedChildren="关闭"/>
                                                </Form.Item>
                                            </Col>
                                            <Col span={12}>
                                                <Form.Item
                                                    name={['config', 'Task', 'IfRecruiting']}
                                                    label="公开招募"
                                                    valuePropName="checked"
                                                >
                                                    <Switch checkedChildren="开启" unCheckedChildren="关闭"/>
                                                </Form.Item>
                                            </Col>
                                        </Row>
                                    </div>
                                )
                            }
                        ]}
                    />
                    <Divider/>
                    <Form.Item>
                        <Space>
                            <Button type="primary" htmlType="submit">
                                {editingUser ? t('pages.scripts.update') : t('common.add')}
                            </Button>
                            <Button onClick={() => {
                                setIsUserModalVisible(false);
                                setEditingUser(null);
                            }}>
                                {t('common.cancel')}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default ScriptsPage;