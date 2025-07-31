import React from 'react';
import {Card, Typography} from 'antd';

const {Title} = Typography;

const CenterPage: React.FC = () => {
    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">调度中心</Title>
            </div>

            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>调度中心页面</Title>
                    <p>这里将显示调度中心功能</p>
                </div>
            </Card>
        </div>
    );
};

export default CenterPage;