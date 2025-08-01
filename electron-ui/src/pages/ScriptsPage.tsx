import React, {useState} from 'react';
import {Button, Form, message, Space, Typography} from 'antd';
import {PlusOutlined,} from '@ant-design/icons';
import {useTranslation} from 'react-i18next';
import ScriptModal from "../components/spripts/ScriptModal.tsx";
import ScriptSettingsModal from "../components/spripts/ScriptSettingsModal.tsx";
import UserModal from "../components/spripts/UserModal.tsx";
import ScriptsTable from "../components/spripts/ScriptsTable.tsx";

const {Title} = Typography;

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
    t('pages.scripts.scriptName');
    t('pages.scripts.userCount');
    t('pages.scripts.actions');
// 用户列表列定义
    t('pages.scripts.username');
    t('pages.scripts.accountId');
    t('pages.scripts.server');
    t('pages.scripts.status');
    t('pages.scripts.actions');
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
    selectedScript ? users.filter(u => u.scriptId === selectedScript.id) : [];
// 文件选择处理函数
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

            <ScriptsTable
                scripts={scripts}
                users={users}
                onAddUser={handleAddUser}
                onEditUser={handleEditUser}
                onDeleteUser={handleDeleteUser}
                onDeleteScript={handleDeleteScript}
                onOpenScriptSettings={handleScriptSettings}
            />


            <ScriptModal
                visible={isScriptModalVisible}
                selectedScript={selectedScript}
                scriptForm={scriptForm}
                onCancel={() => {
                    setIsScriptModalVisible(false);
                    setSelectedScript(null);
                }}
                onSubmit={handleScriptSubmit}
            />

            <ScriptSettingsModal
                visible={isScriptSettingsVisible}
                selectedScript={selectedScript}
                users={users}
                scriptSettingsForm={scriptSettingsForm}
                onCancel={() => setIsScriptSettingsVisible(false)}
                onSubmit={handleScriptSettingsSubmit}
                onAddUser={() => handleAddUser(selectedScript!)}
            />

            <UserModal
                visible={isUserModalVisible}
                editingUser={editingUser}
                userForm={userForm}
                onCancel={() => {
                    setIsUserModalVisible(false);
                    setEditingUser(null);
                }}
                onSubmit={handleUserSubmit}
            />

        </div>
    );
};

export default ScriptsPage;