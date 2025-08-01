import React from 'react';
import { Modal, Form, Input, Radio, Space, Button } from 'antd';
import { useTranslation } from 'react-i18next';

// ===== 直接把 Script 类型复制到这里 =====
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
    status: 'active' | 'inactive';
    userCount: number;
    lastRun: string;
    description?: string;
    config: ScriptConfig;
}

// ===== ScriptModal Props 类型 =====
interface ScriptModalProps {
    visible: boolean;
    selectedScript: Script | null;
    scriptForm: any;
    onCancel: () => void;
    onSubmit: (values: any) => void;
}

const ScriptModal: React.FC<ScriptModalProps> = ({
                                                     visible,
                                                     selectedScript,
                                                     scriptForm,
                                                     onCancel,
                                                     onSubmit
                                                 }) => {
    const { t } = useTranslation();

    return (
        <Modal
            title={selectedScript ? t('pages.scripts.editScript') : t('pages.scripts.addScript')}
            open={visible}
            onCancel={onCancel}
            footer={null}
            width={600}
        >
            <Form
                form={scriptForm}
                layout="vertical"
                onFinish={onSubmit}
            >
                <Form.Item
                    name="name"
                    label={t('pages.scripts.scriptName')}
                    rules={[{ required: true, message: t('pages.scripts.pleaseEnterScriptName') }]}
                >
                    <Input placeholder={t('pages.scripts.pleaseEnterScriptName')} />
                </Form.Item>

                <Form.Item
                    name="type"
                    label="脚本类型（添加MAA类型脚本选择MAA，其他脚本请选择通用）"
                    initialValue="MAA"
                >
                    <Radio.Group>
                        <Radio value="MAA">MAA</Radio>
                        <Radio value="Universal">通用</Radio>
                    </Radio.Group>
                </Form.Item>

                <Form.Item>
                    <Space>
                        <Button type="primary" htmlType="submit">
                            {selectedScript ? t('pages.scripts.update') : t('common.add')}
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

export default ScriptModal;
