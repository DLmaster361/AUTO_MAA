当然可以！下面是为你的 **AUTO_MAA electron-ui** 前端子项目量身定制的完整版 `README.md`，内容涵盖**项目简介、技术栈、安装与运行、yarn 包管理说明、目录结构、开发/打包脚本、编码规范、贡献建议等**，可直接复制到你的 `electron-ui/README.md`。

---

# 🚀 AUTO_MAA electron-ui（Electron 重构前端）

---

## 🛠️ 技术栈

| 层级         | 技术                  | 说明                       |
|--------------|----------------------|----------------------------|
| 桌面框架     | Electron@30.5.1      | 跨平台桌面应用             |
| 前端框架     | React@18.2.0 + Vite  | 组件化开发，极速构建        |
| 组件库       | Ant Design@5.15.4    | 统一、现代的 UI 组件体系    |
| 类型系统     | TypeScript@5.4.5     | 强类型开发体验              |
| 构建/打包    | electron-builder@26   | 生产环境桌面包              |
| 插件        | vite-plugin-electron  | Vite 与 Electron 集成       |

---

## 📦 安装与运行

### 1. 统一使用 Yarn 安装依赖

> **本项目推荐全员使用 Yarn 作为包管理器！不要混用 npm/pnpm。**

```bash
npm install -g yarn
yarn install
```
>  请勿执行 `npm install` 或 `pnpm install`，以避免产生 `package-lock.json`/`pnpm-lock.yaml` 文件。


---

### 2. 启动开发环境

```bash
yarn dev
```
> 会自动同时启动 Vite 前端与 Electron 桌面窗口。

---

### 3. 构建与打包

#### 构建前端静态文件

```bash
yarn build
```

#### 打包生成桌面应用

```bash
yarn electron:build
```
> 会输出 Windows/Mac/Linux 对应平台的安装包（配置在 `package.json` 里的 build 字段）

---

## 📁 目录结构简览

```plaintext
electron-ui/
├── electron/            # Electron 主进程代码
│   └── main.ts
├── public/              # 静态资源
├── src/                 # React 前端源码
│   ├── components/      # 公共组件
│   ├── pages/           # 页面模块
│   ├── services/        # API 封装
│   ├── App.tsx          # 应用主入口
│   ├── main.tsx         # React 入口
│   └── ...
├── package.json         # 项目依赖与脚本
├── vite.config.ts       # Vite 配置
├── tsconfig.json        # TypeScript 配置
└── yarn.lock            # 依赖锁定文件
```

---

## 🎨 编码规范

- 一律使用 **TypeScript**，开启 strict 模式
- 组件全部使用**函数组件 + Hooks**，禁止类组件
- 每个组件文件建议不超过 300 行，并单独定义 Props 类型
- 文件/文件夹用 kebab-case，变量/函数 camelCase，组件/类 PascalCase
- 推荐通过 Ant Design 组件和主题变量控制 UI 样式，如需自定义用 CSS Modules 或 styled-components，避免全局污染

---

## 📝 Git 提交规范

- 推荐使用 [Commitizen](https://github.com/commitizen/cz-cli) 规范提交格式
- 提交类型包括：
    - feat: 新功能
    - fix: 修复 Bug
    - refactor: 代码重构
    - style: 格式调整
    - docs: 文档更新
    - test: 测试相关
    - chore: 工具/配置更新

---

## 🤝 贡献与协作

- 全员使用 yarn 协作，**只提交 `yarn.lock`**，不要有 `package-lock.json`/`pnpm-lock.yaml`
- 代码规范和 lint 由 ESLint/Prettier 自动检查，推送前请自查