/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ZzzOdAppConfigOut } from '../models/ZzzOdAppConfigOut';
import type { ZzzOdAppConfigSaveIn } from '../models/ZzzOdAppConfigSaveIn';
import type { ZzzOdBackupListOut } from '../models/ZzzOdBackupListOut';
import type { ZzzOdBackupRestoreIn } from '../models/ZzzOdBackupRestoreIn';
import type { ZzzOdBackupRestoreOut } from '../models/ZzzOdBackupRestoreOut';
import type { ZzzOdCatalogOut } from '../models/ZzzOdCatalogOut';
import type { ZzzOdDirectBackupIn } from '../models/ZzzOdDirectBackupIn';
import type { ZzzOdDirectBackupOut } from '../models/ZzzOdDirectBackupOut';
import type { ZzzOdInstancesOut } from '../models/ZzzOdInstancesOut';
import type { ZzzOdLauncherOut } from '../models/ZzzOdLauncherOut';
import type { ZzzOdNativeConfigIn } from '../models/ZzzOdNativeConfigIn';
import type { ZzzOdNativeConfigOut } from '../models/ZzzOdNativeConfigOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ZzzOdService {
    /**
     * 获取 zzz-od 实例（账号）列表
     * 返回 zzz-od 实例列表（供「快速导入」选择来源实例）。
     * @param scriptId
     * @returns ZzzOdInstancesOut Successful Response
     * @throws ApiError
     */
    public static getZzzodInstancesApiApiScriptsZzzodInstancesGet(
        scriptId: string,
    ): CancelablePromise<ZzzOdInstancesOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/zzzod/instances',
            query: {
                'scriptId': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取一条龙任务目录
     * 静态解析安装目录下的应用注册信息，供用户配置渲染任务卡片中文名。
     * @param scriptId
     * @returns ZzzOdCatalogOut Successful Response
     * @throws ApiError
     */
    public static getZzzodCatalogApiApiScriptsZzzodCatalogGet(
        scriptId: string,
    ): CancelablePromise<ZzzOdCatalogOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/zzzod/catalog',
            query: {
                'scriptId': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取任务级配置（字段元数据 + 当前值）
     * 返回任务可配置字段、选项与当前值（直控传 instanceIdx 读原生实例，否则读绑定槽）。
     * @param scriptId
     * @param userId
     * @param appId
     * @param instanceIdx
     * @returns ZzzOdAppConfigOut Successful Response
     * @throws ApiError
     */
    public static getZzzodAppConfigApiApiScriptsZzzodAppConfigGet(
        scriptId: string,
        userId: string,
        appId: string,
        instanceIdx?: (number | null),
    ): CancelablePromise<ZzzOdAppConfigOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/zzzod/app-config',
            query: {
                'scriptId': scriptId,
                'userId': userId,
                'appId': appId,
                'instanceIdx': instanceIdx,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 保存任务级配置（绑定槽；直控传 instanceIdx 直接写原生实例）
     * 字段白名单校验后写入 per-app YAML（缺省写用户绑定槽，直控写指定原生实例）。
     * @param requestBody
     * @returns ZzzOdAppConfigOut Successful Response
     * @throws ApiError
     */
    public static saveZzzodAppConfigApiApiScriptsZzzodAppConfigSavePost(
        requestBody: ZzzOdAppConfigSaveIn,
    ): CancelablePromise<ZzzOdAppConfigOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/zzzod/app-config/save',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取实例原生配置（直控页面表单数据）
     * 读取所选实例 game_account.yml 与 _group.yml（含默认值合并与任务目录并入）。
     * @param scriptId
     * @param instanceIdx
     * @returns ZzzOdNativeConfigOut Successful Response
     * @throws ApiError
     */
    public static getZzzodNativeConfigApiApiScriptsZzzodNativeConfigGet(
        scriptId: string,
        instanceIdx: number,
    ): CancelablePromise<ZzzOdNativeConfigOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/zzzod/native-config',
            query: {
                'scriptId': scriptId,
                'instanceIdx': instanceIdx,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 保存实例原生配置（直控模式直接写回一条龙原始 YAML）
     * 白名单过滤后写回所选实例 game_account.yml、_group.yml 与 instance_run，随后回读最新数据。
     * @param requestBody
     * @returns ZzzOdNativeConfigOut Successful Response
     * @throws ApiError
     */
    public static saveZzzodNativeConfigApiApiScriptsZzzodNativeConfigSavePost(
        requestBody: ZzzOdNativeConfigIn,
    ): CancelablePromise<ZzzOdNativeConfigOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/zzzod/native-config/save',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 列出配置备份（onedragon=一条龙原生配置 / mas=MAS 用户槽）
     * 按时间倒序返回历史备份（运行/会话前自动归档，内容无变化跳过）。
     * @param scriptId
     * @param userId
     * @param target
     * @returns ZzzOdBackupListOut Successful Response
     * @throws ApiError
     */
    public static listZzzodBackupsApiApiScriptsZzzodBackupsGet(
        scriptId: string,
        userId: string,
        target: string = 'onedragon',
    ): CancelablePromise<ZzzOdBackupListOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/zzzod/backups',
            query: {
                'scriptId': scriptId,
                'userId': userId,
                'target': target,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 直控前置保护：进入直控前确保一条龙原生配置已有备份
     * 指纹对比当前原生配置与最近备份，无备份或内容已变则立即归档（防误操作）。
     * @param requestBody
     * @returns ZzzOdDirectBackupOut Successful Response
     * @throws ApiError
     */
    public static ensureZzzodDirectBackupApiApiScriptsZzzodDirectBackupEnsurePost(
        requestBody: ZzzOdDirectBackupIn,
    ): CancelablePromise<ZzzOdDirectBackupOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/zzzod/direct-backup/ensure',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取一条龙两种启动器的安装情况与默认项
     * 渲染「启动器」下拉用（直控/用户两态通用）：未安装的启动器选项禁用变灰。
     * @param scriptId
     * @returns ZzzOdLauncherOut Successful Response
     * @throws ApiError
     */
    public static getZzzodLaunchersApiApiScriptsZzzodLaunchersGet(
        scriptId: string,
    ): CancelablePromise<ZzzOdLauncherOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/zzzod/launchers',
            query: {
                'scriptId': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 把指定备份恢复到目标位置（onedragon=一条龙原生配置 / mas=MAS 用户配置）
     * onedragon：恢复一条龙原生配置（MAS 槽不触碰）；mas：恢复槽并全量回填本页字段。
     * @param requestBody
     * @returns ZzzOdBackupRestoreOut Successful Response
     * @throws ApiError
     */
    public static restoreZzzodBackupApiApiScriptsZzzodBackupRestorePost(
        requestBody: ZzzOdBackupRestoreIn,
    ): CancelablePromise<ZzzOdBackupRestoreOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/zzzod/backup/restore',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
