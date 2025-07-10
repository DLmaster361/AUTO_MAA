title = "主程序更新警示之二"
markdown = """
## 主程序更新警示之二

- Mirror酱由于平台策略更新，相关更新服务暂不可用，请暂时删除cdk，使用一般更新渠道进行更新，预期将在 `v4.4.0-beta.2` 版本完成修复。

- `AUTO_MAA_v4.3` 向 `AUTO_MAA_v4.4` 版本更新时，提示权限不足属正常现象，直接关闭该窗口，手动打开 `AUTO_MAA` 即可。
"""
with open("notice.txt", "w", encoding="utf-8") as f:
    f.write(f'"{title}": "{markdown.replace("\n",r"\n")}"')
print(f'"{title}": "{markdown.replace("\n",r"\n")}"')
