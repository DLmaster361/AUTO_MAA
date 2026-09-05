/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ZzzOdPreviewField } from './ZzzOdPreviewField';
import type { ZzzOdPreviewTask } from './ZzzOdPreviewTask';
/**
 * 一条龙备份摘要中的实例条目（可展开查看账号/任务明细）
 */
export type ZzzOdPreviewInstance = {
    /**
     * 实例下标
     */
    idx: number;
    /**
     * 实例名称
     */
    name: string;
    /**
     * 是否为当前活跃实例
     */
    active: boolean;
    /**
     * 是否参与「全部实例」模式的一条龙
     */
    active_in_od: boolean;
    /**
     * 该实例的账号字段（来自备份目录内 game_account.yml）
     */
    account: Array<ZzzOdPreviewField>;
    /**
     * 该实例的任务编排（来自备份目录内 _group.yml）
     */
    tasks: Array<ZzzOdPreviewTask>;
};

