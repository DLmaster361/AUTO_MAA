import React from 'react';
import {Button} from 'antd';
import {
    MinusOutlined,
    BorderOutlined,
    CloseOutlined
} from '@ant-design/icons';
import './TitleBar.css';

interface TitleBarProps {
    title?: string;
}

const TitleBar: React.FC<TitleBarProps> = ({title = 'AUTO_MAA'}) => {
    const handleMinimize = () => {
        // 通过IPC与主进程通信来最小化窗口
        if (window.electronAPI) {
            window.electronAPI.minimize().catch(console.error);
        } else {
            console.log('最小化窗口 (Web环境下无效)');
        }
    };

    const handleMaximize = () => {
        // 通过IPC与主进程通信来最大化/还原窗口
        if (window.electronAPI) {
            window.electronAPI.maximize().catch(console.error);
        } else {
            console.log('最大化/还原窗口 (Web环境下无效)');
        }
    };

    const handleClose = () => {
        // 通过IPC与主进程通信来关闭窗口
        if (window.electronAPI) {
            window.electronAPI.close().catch(console.error);
        } else {
            console.log('关闭窗口 (Web环境下无效)');
        }
    };

    return (
        <div className="custom-title-bar">
            {/* 左侧Logo和标题 */}
            <div className="title-bar-left">
                <div className="logo-icon">
                    <img
                        src="/AUTO_MAA.ico"
                        alt="AUTO_MAA Logo"
                        style={{width: '75%', height: '75%'}}
                        onError={(e) => {
                            e.currentTarget.style.display = 'none';
                        }}
                    />
                </div>
                <span className="title-bar-title">{title}</span>
            </div>

            {/* 中间可拖拽区域 */}
            <div className="title-bar-drag-region"/>

            {/* 右侧窗口控制按钮 */}
            <div className="title-bar-controls">
                <Button
                    type="text"
                    size="small"
                    icon={<MinusOutlined/>}
                    className="title-bar-button minimize-button"
                    onClick={handleMinimize}
                />
                <Button
                    type="text"
                    size="small"
                    icon={<BorderOutlined/>}
                    className="title-bar-button maximize-button"
                    onClick={handleMaximize}
                />
                <Button
                    type="text"
                    size="small"
                    icon={<CloseOutlined/>}
                    className="title-bar-button close-button"
                    onClick={handleClose}
                />
            </div>
        </div>
    );
};

export default TitleBar;