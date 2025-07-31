import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

const HistoryPage: React.FC = () => {
  return (
    <div>
      <div className="page-header">
        <Title level={2} className="page-title">历史记录</Title>
      </div>
      
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Title level={3}>历史记录页面</Title>
          <p>这里将显示历史记录功能</p>
        </div>
      </Card>
    </div>
  );
};

export default HistoryPage;