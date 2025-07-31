import React from 'react';
import {Card, Typography} from 'antd';

const {Title} = Typography;

const ScriptsPage: React.FC = () => {
    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">脚本管理</Title>
            </div>

            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>脚本管理页面</Title>
                    <p>这里将显示脚本管理功能</p>
                </div>
            </Card>
        </div>
    );
};

export default ScriptsPage;