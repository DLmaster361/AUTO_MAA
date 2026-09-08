# 本地打包

使用 PowerShell 7。后台更新需要桌面和 Runtime 同时使用新代码；当前钉扎的旧 Runtime
版本尚未包含该能力，发布前须先发布新 Runtime，再更新 `res/runtime.json` 的 `version`
与 `sha256`（哈希取自该 Release 的 `SHA256SUMS.txt`，两者必须同时改，否则构建会失败）。
该文件是 Runtime 版本的唯一来源：发布 CI、本地打包脚本和装机后的桌面端读的都是它，
桌面端还会在本体更新后按它把用户机器上的 Runtime 换成同一版。
CI 会拒绝缺少后台更新协议的二进制，防止生成无法正常启动的安装包。

本地验证可直接使用本次源码构建的 Runtime，不必等待 Release：

```powershell
Set-Location D:/Github/AUTO-MAS-Runtime
$env:GOCACHE = Join-Path $env:TEMP 'auto-mas-runtime-verify'
go build -buildvcs=false -o bin/auto-mas-runtime.exe ./cmd/auto-mas-runtime
if ($LASTEXITCODE -ne 0) { throw 'Runtime build failed' }

Set-Location D:/Github/AUTO-MAS
pwsh -NoProfile -File scripts/build-local-package.ps1 `
  -LocalRuntimePath D:/Github/AUTO-MAS-Runtime/bin/auto-mas-runtime.exe `
  -VerifyRuntimeOnly -SkipInstall
if ($LASTEXITCODE -ne 0) { throw 'Runtime verification failed' }
```

去掉 `-VerifyRuntimeOnly` 后执行完整本地打包。脚本校验源码版本一致性、Runtime SHA-256、
`workspace stage` 和 `bootstrap --if-needed`，然后生成携带指定 Runtime 的安装包和解压目录。
`-SkipInstall` 仅适用于前端依赖已经安装的环境；脚本不会发布或上传安装包。

**运行 `-LocalRuntimePath` 打出来的包时必须设置 `AUTO_MAS_RUNTIME_EXE`。** 桌面端每次
managed 启动都会拿 `<app-root>/repo/res/runtime.json` 的钉扎去核对 exe 自报的版本，本地
构建的 Runtime 自报 `dev`，与钉扎不一致就会被下载的发布版原地覆盖——之后跑的就不是你
要验证的那一份了。`repo/` 是 Runtime 从发布分支克隆的，安装包不带 `res/runtime.json`，
所以打包脚本改不了这份钉扎；唯一的逃生口是让桌面端认出这是开发者自带的 Runtime：

```powershell
$env:AUTO_MAS_RUNTIME_EXE = 'D:/Github/AUTO-MAS-Runtime/bin/auto-mas-runtime.exe'
& 'D:/Github/AUTO-MAS/dist/AUTO-MAS-<版本>-local-<时间戳>/win-unpacked/AUTO-MAS.exe'
```

变量要出现在 `AUTO-MAS.exe` 的进程环境里，所以要**从设置了它的管理员 PowerShell 启动**：
双击图标不算，从普通终端启动也不算——`AUTO-MAS.exe` 的清单是 `requireAdministrator`，
未提权时会经 UAC 重新拉起，提权后的进程拿不到调用方的环境变量。
桌面端用它指向的 exe 启动 Runtime，并跳过随本体更新。

运行行为：managed 模式启动后首次检查当前 release 分支，之后每 10 分钟检查一次；
发现更新就后台下载，完成后标题栏提示下次启动生效。下载不改变当前后端和环境；
下次启动替换仓库并同步所需依赖。无更新时跳过依赖同步。依赖同步失败仍需通过已有修复入口重试。
