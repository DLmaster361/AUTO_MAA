title = "主程序更新警示之三"
markdown = """
## 主程序更新警示之三

- 由于开发者犯蠢，`v4.4.1-beta.1` 版本出现大量莫名其妙的崩溃弹窗，应用内更新也无法进行，相关问题已在 `v4.4.1-beta.3` 版本中修复，但您需要手动下载 `v4.4.1-beta.3` 版本进行覆盖安装。

- 若您无法直接访问Github，请使用[此临时链接](http://221.236.27.82:10197/d/AUTO_MAA/AUTO_MAA_v4.4.1-beta.3.zip)进行下载。

- 此次异常仅影响公测版用户，稳定版用户无需理会。
"""
with open("notice.txt", "w", encoding="utf-8") as f:
    f.write(f'"{title}": "{markdown.replace("\n",r"\n")}"')
print(f'"{title}": "{markdown.replace("\n",r"\n")}"')
