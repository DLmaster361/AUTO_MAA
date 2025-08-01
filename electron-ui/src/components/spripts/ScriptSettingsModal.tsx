import React from 'react';
import {Button, Col, Form, Input, InputNumber, Modal, Row, Select, Space, Table, Tabs} from 'antd';
import {PlusOutlined} from '@ant-design/icons';
import {useTranslation} from 'react-i18next';

// ====== 类型定义 ======
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

interface Script {
    id: string;
    name: string;
    config: ScriptConfig;
}

interface User {
    id: string;
    scriptId: string;
    config: any;
}

interface ScriptSettingsModalProps {
    visible: boolean;
    selectedScript: Script | null;
    users: User[];
    scriptSettingsForm: any;
    onCancel: () => void;
    onSubmit: (values: any) => void;
    onAddUser: () => void;
}

// ====== 组件 ======
const ScriptSettingsModal: React.FC<ScriptSettingsModalProps> = ({
                                                                     visible,
                                                                     selectedScript,
                                                                     users,
                                                                     scriptSettingsForm,
                                                                     onCancel,
                                                                     onSubmit,
                                                                     onAddUser
                                                                 }) => {
    const { t } = useTranslation();
    const { Option } = Select;

    const currentScriptUsers = selectedScript ? users.filter(u => u.scriptId === selectedScript.id) : [];

    return (
        <Modal
            title={`${t('pages.scripts.scriptSettings')} - ${selectedScript?.name}`}
            open={visible}
            onCancel={onCancel}
            footer={null}
            width={800}
        >
            <Form
                form={scriptSettingsForm}
                layout="vertical"
                onFinish={onSubmit}
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
                                                label="实例名称"
                                                name={['MaaSet', 'Name']}
                                            >
                                                <Input placeholder="请输入实例名称"/>
                                            </Form.Item>
                                        </Col>
                                        <Col span={12}>
                                            <Form.Item
                                                label="MAA目录"
                                                name={['MaaSet', 'Path']}
                                            >
                                                <Input placeholder="请选择MAA.exe所在目录"/>
                                            </Form.Item>
                                        </Col>
                                    </Row>

                                    <Row gutter={16}>
                                        <Col span={12}>
                                            <Form.Item
                                                label="任务切换方式"
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
                                                label="ADB端口号查找范围"
                                                name={['RunSet', 'ADBSearchRange']}
                                            >
                                                <InputNumber min={1} max={100} style={{width: '100%'}}/>
                                            </Form.Item>
                                        </Col>
                                    </Row>

                                    <Row gutter={16}>
                                        <Col span={12}>
                                            <Form.Item
                                                label="剿灭每周代理上限"
                                                name={['RunSet', 'AnnihilationWeeklyLimit']}
                                            >
                                                <Select>
                                                    <Option value="true">是</Option>
                                                    <Option value="false">否</Option>
                                                </Select>
                                            </Form.Item>
                                        </Col>
                                        <Col span={12}>
                                            <Form.Item
                                                label="剿灭最大代理时长（分钟）"
                                                name={['RunSet', 'AnnihilationTimeLimit']}
                                            >
                                                <InputNumber min={1} max={999} style={{width: '100%'}}/>
                                            </Form.Item>
                                        </Col>
                                    </Row>

                                    <Form.Item>
                                        <Space>
                                            <Button type="primary" htmlType="submit">
                                                保存设置
                                            </Button>
                                            <Button onClick={onCancel}>
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
                                            onClick={onAddUser}
                                        >
                                            {t('pages.scripts.addUser')}
                                        </Button>
                                    </div>
                                    <Table
                                        columns={[
                                            {
                                                title: t('pages.scripts.username'),
                                                dataIndex: ['config', 'Info', 'Name'],
                                                key: 'username',
                                            }
                                        ]}
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
    );
};

export default ScriptSettingsModal;
