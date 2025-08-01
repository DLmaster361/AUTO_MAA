import React from 'react';
import {Button, Card, Typography} from 'antd';
import { useTranslation } from 'react-i18next';

const {Title, Paragraph} = Typography;

const HomePage: React.FC = () => {
    const { t } = useTranslation();
    
    return (
        <div>
            {/* 主要内容 */}
            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>{t('pages.home.welcome')}</Title>
                    <Paragraph>
                        {t('pages.home.description')}
                    </Paragraph>
                    <div style={{marginTop: 24}}>
                        <Button type="primary" size="large" style={{marginRight: 16}}>
                            {t('common.add')}
                        </Button>
                        <Button size="large">
                            {t('common.search')}
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};

export default HomePage;