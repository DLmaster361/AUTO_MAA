title = "代理风险预警通告"
markdown = """
## 代理风险预警通告

MAA在`v5.15.4`版本中修改了目录结构，为适配这一情况，您必须立刻将AUTO_MAA更新到`v4.3.4`或更高版本。

请注意，这一更新需要与MAA的`v5.15.4`版本更新同步进行，在仅有任意一方被更新到最新版时，自动代理将无法使用。

由于本次稳定版更新较为仓促，部分新增功能未在公测中经过充分测试，遇到bug时请及时向项目组反馈。

感谢您对本项目的支持与信任，预祝您度过一个愉快的6周年！
"""
with open("notice.txt", "w", encoding="utf-8") as f:
    f.write(f'"{title}": "{markdown.replace("\n",r"\n")}"')
print(f'"{title}": "{markdown.replace("\n",r"\n")}"')
