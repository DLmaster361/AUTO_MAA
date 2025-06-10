title = "主程序更新警示"
markdown = """
## 主程序更新警示

AUTO_MAA_v4.3.10-beta.2 发生严重错误，请不要升级到该版本！
"""
with open("notice.txt", "w", encoding="utf-8") as f:
    f.write(f'"{title}": "{markdown.replace("\n",r"\n")}"')
print(f'"{title}": "{markdown.replace("\n",r"\n")}"')
