/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MaaFWAgentEnvPrepareIn } from '../models/MaaFWAgentEnvPrepareIn';
import type { MaaFWAgentEnvPrepareOut } from '../models/MaaFWAgentEnvPrepareOut';
import type { MaaFWInterfacePreviewIn } from '../models/MaaFWInterfacePreviewIn';
import type { MaaFWInterfacePreviewOut } from '../models/MaaFWInterfacePreviewOut';
import type { MaaFWManagedGcIn } from '../models/MaaFWManagedGcIn';
import type { MaaFWManagedGcOut } from '../models/MaaFWManagedGcOut';
import type { MaaFWManagedImportIn } from '../models/MaaFWManagedImportIn';
import type { MaaFWManagedImportOut } from '../models/MaaFWManagedImportOut';
import type { MaaFWManagedInventoryOut } from '../models/MaaFWManagedInventoryOut';
import type { MaaFWManagedMigrateIn } from '../models/MaaFWManagedMigrateIn';
import type { MaaFWManagedMigrateOut } from '../models/MaaFWManagedMigrateOut';
import type { MaaFWManagedSwitchIn } from '../models/MaaFWManagedSwitchIn';
import type { MaaFWManagedVersionDeleteIn } from '../models/MaaFWManagedVersionDeleteIn';
import type { MaaFWManagedVersionsIn } from '../models/MaaFWManagedVersionsIn';
import type { MaaFWManagedVersionsOut } from '../models/MaaFWManagedVersionsOut';
import type { MaaFWProjectUpdateIn } from '../models/MaaFWProjectUpdateIn';
import type { MaaFWProjectUpdateOut } from '../models/MaaFWProjectUpdateOut';
import type { OutBase } from '../models/OutBase';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MaaFwService {
    /**
     * 导入 MFW 项目到托管 Store
     * 把本地目录或 ZIP 发行包导入不可变 Store，并可选地绑定到一个托管脚本。
     *
     * 绑定不是可有可无的一步：只写 projectId/version 而不带 Store 身份，运行时会被
     * 「脚本缺少可验证的 Project Store 身份」直接拒掉。
     * @param requestBody
     * @returns MaaFWManagedImportOut Successful Response
     * @throws ApiError
     */
    public static importManagedMaafwProjectApiScriptsMaafwManagedImportPost(
        requestBody: MaaFWManagedImportIn,
    ): CancelablePromise<MaaFWManagedImportOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/import',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 把自选目录的 MFW 脚本转为托管
     * 导入现有项目目录、原地把脚本换成托管类型，可选地删掉原目录。
     *
     * 转换是**原地**的：脚本 ID 不变，队列成员、计划表、通知绑定和 ``data/<uid>/``
     * 下的用户数据全都留着。新建一个托管脚本再删旧的会把这些一并丢掉。
     *
     * 删原目录是不可撤销的，只在 ``deleteSource`` 为真时做，并且一定排在导入与
     * 转换都成功之后；删除失败不回滚迁移——项目已经在 Store 里了，把它撤回去反而
     * 更糟，如实报告让用户自己删。
     * @param requestBody
     * @returns MaaFWManagedMigrateOut Successful Response
     * @throws ApiError
     */
    public static migrateMaafwScriptToManagedApiScriptsMaafwManagedMigratePost(
        requestBody: MaaFWManagedMigrateIn,
    ): CancelablePromise<MaaFWManagedMigrateOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/migrate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 列出托管项目的版本
     * @param requestBody
     * @returns MaaFWManagedVersionsOut Successful Response
     * @throws ApiError
     */
    public static listManagedMaafwVersionsApiScriptsMaafwManagedVersionsPost(
        requestBody: MaaFWManagedVersionsIn,
    ): CancelablePromise<MaaFWManagedVersionsOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/versions',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 切换托管项目的当前版本
     * @param requestBody
     * @returns OutBase Successful Response
     * @throws ApiError
     */
    public static switchManagedMaafwVersionApiScriptsMaafwManagedSwitchPost(
        requestBody: MaaFWManagedSwitchIn,
    ): CancelablePromise<OutBase> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/switch',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除托管项目的一个版本
     * 删除受 current / pinned / references / lease 阻断——阻断理由原样返回。
     * @param requestBody
     * @returns OutBase Successful Response
     * @throws ApiError
     */
    public static deleteManagedMaafwVersionApiScriptsMaafwManagedVersionDeletePost(
        requestBody: MaaFWManagedVersionDeleteIn,
    ): CancelablePromise<OutBase> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/version/delete',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 查看托管 Store 的占用
     * @returns MaaFWManagedInventoryOut Successful Response
     * @throws ApiError
     */
    public static getManagedMaafwInventoryApiScriptsMaafwManagedInventoryPost(): CancelablePromise<MaaFWManagedInventoryOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/inventory',
        });
    }
    /**
     * 回收托管 Store 中无人引用的版本
     * @param requestBody
     * @returns MaaFWManagedGcOut Successful Response
     * @throws ApiError
     */
    public static collectManagedMaafwGarbageApiScriptsMaafwManagedGcPost(
        requestBody: MaaFWManagedGcIn,
    ): CancelablePromise<MaaFWManagedGcOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/managed/gc',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 预览 MFW interface
     * 读取 MaaFW 项目 interface，并返回 controller/resource/task 摘要。
     * @param requestBody
     * @returns MaaFWInterfacePreviewOut Successful Response
     * @throws ApiError
     */
    public static previewMaafwInterfaceApiScriptsMaafwPreviewPost(
        requestBody: MaaFWInterfacePreviewIn,
    ): CancelablePromise<MaaFWInterfacePreviewOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/preview',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 检查或执行 MFW 项目更新
     * 按脚本 ``Update.*`` 配置检查或应用 MaaFW 项目目录更新。
     *
     * ``action=check`` 只读取 interface 版本与更新源元数据，返回是否有新版本；
     * ``action=apply`` 触发下载并原地应用更新包。失败时返回明确 ``message``。
     * @param requestBody
     * @returns MaaFWProjectUpdateOut Successful Response
     * @throws ApiError
     */
    public static updateMaafwProjectApiScriptsMaafwUpdatePost(
        requestBody: MaaFWProjectUpdateIn,
    ): CancelablePromise<MaaFWProjectUpdateOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/update',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 预备 MFW 运行环境
     * 按项目 interface 预备 Runner 运行时与各 agent 的 Python 环境。
     *
     * 在项目引导里读到 interface 之后调用，把首次运行才会付出的下载与建环境
     * 成本提前到配置阶段。与 ``/maafw/update`` 一样是同步端点：整个准备过程
     * 在请求内完成，首次冷启动可能耗时数分钟。
     *
     * 编辑页每打开一次就会调一次，所以先比一遍项目输入指纹：项目没更新过、上次
     * 准备的环境也还在盘上，就直接还回上次的结果，不再取锁起进程。用户手动重试
     * 时前端带 ``force``，跳过这层缓存。
     * @param requestBody
     * @returns MaaFWAgentEnvPrepareOut Successful Response
     * @throws ApiError
     */
    public static prepareMaafwAgentEnvApiScriptsMaafwAgentEnvPreparePost(
        requestBody: MaaFWAgentEnvPrepareIn,
    ): CancelablePromise<MaaFWAgentEnvPrepareOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/scripts/maafw/agent-env/prepare',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 读取 MFW 项目内的图片资源
     * 把 MFW 项目目录内的图片按需读给前端。
     *
     * 任务说明（interface 的 ``doc`` / ``description``）是 markdown，里面的图片写的是
     * **项目内相对路径**，浏览器没法直接读本地文件，必须由后端转一手。
     *
     * 前端侧对应 ``buildMaaFWAssetUrl``：它已经拦掉了绝对路径、UNC、上跳与远程 URL，
     * 但那只是省一次往返，安全边界在这里 —— 请求可以绕过前端直接打过来。
     * @param root MFW 项目根目录
     * @param path 项目根目录内的相对图片路径
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getMaafwAssetApiScriptsMaafwAssetGet(
        root: string,
        path: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/scripts/maafw/asset',
            query: {
                'root': root,
                'path': path,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
