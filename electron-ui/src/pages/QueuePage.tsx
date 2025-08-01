import React from 'react';
import {Card, Typography} from 'antd';
import { useTranslation } from 'react-i18next';

const {Title} = Typography;

const QueuePage: React.FC = () => {
    const { t } = useTranslation();
    
    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">{t('pages.queue.title')}</Title>
            </div>

            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>{t('pages.queue.title')}</Title>
                    <p>{t('pages.queue.description')}</p>
                </div>
            </Card>
        </div>
    );
};

export default QueuePage;