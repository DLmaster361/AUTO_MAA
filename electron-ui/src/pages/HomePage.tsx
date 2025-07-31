import React from 'react';
import {Button, Card, Typography} from 'antd';

const {Title, Paragraph} = Typography;

const HomePage: React.FC = () => {
    return (
        <div>
            {/* 主要内容 */}
            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>欢迎使用 AUTO_MAA</Title>
                    <Paragraph>
                        这是一个现代化的桌面应用程序。
                    </Paragraph>
                    <Paragraph>
                        左侧导航栏可以切换不同的功能模块，底部的开关可以切换深浅色主题。
                    </Paragraph>
                    <div style={{marginTop: 24}}>
                        <Button type="primary" size="large" style={{marginRight: 16}}>
                            开始使用
                        </Button>
                        <Button size="large">
                            查看文档
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};

export default HomePage;