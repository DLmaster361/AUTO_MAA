import React from 'react';
import { Modal, Form, Input, Select, Switch, Tabs, Row, Col, Divider, Button, Space } from 'antd';
import { useTranslation } from 'react-i18next';

// ====== 类型定义 ======
interface UserConfig {
    Info: {
        Name: string;
        Id: string;
        Server: string;
        Status: boolean;
        Password: string;
        Notes: string;
        Stage: string;
        StageMode: string;
    };
    Task: {
        IfBase: boolean;
        IfCombat: boolean;
        IfMission: boolean;
        IfRecruiting: boolean;
    };
}

interface User {
    id: string;
    config: UserConfig;
}

interface UserModalProps {
    visible: boolean;
    editingUser: User | null;
    userForm: any;
    onCancel: () => void;
    onSubmit: (values: any) => void;
}

const UserModal: React.FC<UserModalProps> = ({
                                                 visible,
                                                 editingUser,
                                                 userForm,
                                                 onCancel,
                                                 onSubmit
                                             }) => {
    const { t } = useTranslation();
    const { Option } = Select;

    return (
        <Modal
            title={editingUser ? t('pages.scripts.editUser') : t('pages.scripts.addUser')}
            open={visible}
            onCancel={onCancel}
            footer={null}
            width={900}
        >
            <Form
                form={userForm}
                layout="vertical"
                onFinish={onSubmit}
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
                                                rules={[{ required: true, message: '请输入用户名' }]}
                                            >
                                                <Input placeholder="请输入用户名"/>
                                            </Form.Item>
                                        </Col>
                                        <Col span={12}>
                                            <Form.Item
                                                name={['config', 'Info', 'Id']}
                                                label="账号ID"
                                                rules={[{ required: true, message: '请输入账号ID' }]}
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
                                            >
                                                <Select>
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
                                                <Select>
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
                                                <Select>
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
                        <Button onClick={onCancel}>
                            {t('common.cancel')}
                        </Button>
                    </Space>
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default UserModal;
