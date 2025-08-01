import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import 'antd/dist/reset.css'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <ConfigProvider locale={zhCN}>
            <AntdApp>
                <App />
            </AntdApp>
        </ConfigProvider>
    </StrictMode>
)
