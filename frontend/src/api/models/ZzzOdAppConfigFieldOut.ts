/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ComboBoxItem } from './ComboBoxItem';
/**
 * 任务级配置字段（元数据 + 当前值）
 */
export type ZzzOdAppConfigFieldOut = {
    /**
     * 配置字段名（app yml 中的键）
     */
    field: string;
    /**
     * 展示标题
     */
    title: string;
    /**
     * 当前值
     */
    value?: (string | null);
    /**
     * 可选项列表
     */
    options: Array<ComboBoxItem>;
};

