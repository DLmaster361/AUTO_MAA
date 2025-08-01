import React from 'react';
import {Card, Typography} from 'antd';
import { useTranslation } from 'react-i18next';

const {Title} = Typography;

const HistoryPage: React.FC = () => {
    const { t } = useTranslation();
    
    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">{t('pages.history.title')}</Title>
            </div>

            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>{t('pages.history.title')}</Title>
                    <p>{t('pages.history.description')}</p>
                </div>
            </Card>
        </div>
    );
};

export default HistoryPage;