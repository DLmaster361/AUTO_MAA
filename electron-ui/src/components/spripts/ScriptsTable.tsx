import React from 'react';
import { Card, Table, Tooltip, Button, Space, Tag, Badge, Popconfirm } from 'antd';
import { SettingOutlined, UserAddOutlined, DeleteOutlined, UserOutlined, DownOutlined, RightOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

// ====== 类型定义 ======
interface Script {
    id: string;
    name: string;
    status: 'active' | 'inactive';
    userCount: number;
    lastRun: string;
}

interface User {
    id: string;
    scriptId: string;
    config: any;
}

interface ScriptsTableProps {
    scripts: Script[];
    users: User[];
    onAddUser: (script: Script) => void;
    onEditUser: (user: User) => void;
    onDeleteUser: (userId: string) => void;
    onDeleteScript: (scriptId: string) => void;
    onOpenScriptSettings: (script: Script) => void;
}

const ScriptsTable: React.FC<ScriptsTableProps> = ({
                                                       scripts,
                                                       users,
                                                       onAddUser,
                                                       onEditUser,
                                                       onDeleteUser,
                                                       onDeleteScript,
                                                       onOpenScriptSettings
                                                   }) => {
    const { t } = useTranslation();

    // 脚本列表列
    const scriptColumns = [
        {
            title: t('pages.scripts.scriptName'),
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <span style={{fontWeight: 500}}>{text}</span>,
        },
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
        {
            title: t('pages.scripts.actions'),
            key: 'action',
            render: (_: any, record: Script) => (
                <Space>
                    <Button type="text" icon={<SettingOutlined />} onClick={() => onOpenScriptSettings(record)}>
                        脚本管理
                    </Button>
                    <Button type="text" icon={<UserAddOutlined />} onClick={() => onAddUser(record)}>
                        新增用户
                    </Button>
                    <Popconfirm
                        title={t('pages.scripts.confirmDeleteScript')}
                        onConfirm={() => onDeleteScript(record.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                    >
                        <Button type="text" danger icon={<DeleteOutlined />}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    // 用户列表列
    const userColumns = [
        {
            title: t('pages.scripts.username'),
            dataIndex: ['config', 'Info', 'Name'],
            key: 'username',
            render: (text: string, record: User) => (
                <Space>
                    <Badge status={record.config.Info.Status ? 'success' : 'default'} />
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
            title: t('pages.scripts.actions'),
            key: 'action',
            render: (_: any, record: User) => (
                <Space>
                    <Button type="text" icon={<SettingOutlined />} onClick={() => onEditUser(record)}>
                        配置
                    </Button>
                    <Popconfirm
                        title={t('pages.scripts.confirmDeleteUser')}
                        onConfirm={() => onDeleteUser(record.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                    >
                        <Button type="text" danger icon={<DeleteOutlined />}>
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
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
                                        <UserOutlined style={{fontSize: '24px', marginBottom: '8px', color: '#d9d9d9'}}/>
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
    );
};

export default ScriptsTable;
