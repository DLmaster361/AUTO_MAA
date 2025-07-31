import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

const QueuePage: React.FC = () => {
  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">调度队列</Title>
      </div>
      
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Title level={3}>调度队列页面</Title>
          <p>这里将显示调度队列功能</p>
        </div>
      </Card>
    </div>
  );
};

export default QueuePage;