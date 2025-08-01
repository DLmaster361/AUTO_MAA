import React from 'react';
import {Card, Typography} from 'antd';
import { useTranslation } from 'react-i18next';

const {Title} = Typography;

const CenterPage: React.FC = () => {
    const { t } = useTranslation();
    
    return (
        <div>
            <div className="page-header">
                <Title level={2} className="page-title">{t('pages.center.title')}</Title>
            </div>

            <Card>
                <div style={{textAlign: 'center', padding: '40px 0'}}>
                    <Title level={3}>{t('pages.center.title')}</Title>
                    <p>{t('pages.center.description')}</p>
                </div>
            </Card>
        </div>
    );
};

export default CenterPage;