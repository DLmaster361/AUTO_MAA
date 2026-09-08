/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 把指定备份恢复到目标位置（onedragon=一条龙原生配置 / mas=MAS 用户配置）
 */
export type ZzzOdBackupRestoreIn = {
    /**
     * 所属脚本ID
     */
    scriptId: string;
    /**
     * 目标用户ID
     */
    userId: string;
    /**
     * 备份时间戳
     */
    time: string;
    /**
     * 恢复目标：onedragon=把一条龙原生配置备份恢复到一条龙本身（one_dragon.yml + 原生实例目录，MAS 槽不触碰，恢复前自动归档当前）；mas=把 MAS 用户槽备份恢复到绑定槽并全量回填本页字段（配队等随槽回到该时点）
     */
    target?: ZzzOdBackupRestoreIn.target;
};
export namespace ZzzOdBackupRestoreIn {
    /**
     * 恢复目标：onedragon=把一条龙原生配置备份恢复到一条龙本身（one_dragon.yml + 原生实例目录，MAS 槽不触碰，恢复前自动归档当前）；mas=把 MAS 用户槽备份恢复到绑定槽并全量回填本页字段（配队等随槽回到该时点）
     */
    export enum target {
        ONEDRAGON = 'onedragon',
        MAS = 'mas',
    }
}

