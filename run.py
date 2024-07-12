#   <AUTO_MAA:A MAA Multi Account Management and Automation Tool>
#   Copyright © <2024> <DLmaster361>

#   This file is part of AUTO_MAA.

#   AUTO_MAA is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published
#   by the Free Software Foundation, either version 3 of the License,
#   or (at your option) any later version.

#   AUTO_MAA is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
#   the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with AUTO_MAA. If not, see <https://www.gnu.org/licenses/>.

#   DLmaster_361@163.com

import os
import sys
import subprocess
import atexit
import sqlite3
import datetime
import time
import json
import requests
from termcolor import colored


def send_message(msg_type, qq_id, text):
    # 为适配后续机器人而写
    url = r'http://localhost:3000/send_msg'
    headers = {'Content-Type': 'application/json'}
    body = {
        'message_type': msg_type,
        'message': text
    }
    if msg_type == 'private':
        body.update({'user_id': qq_id})
    else:
        body.update({'group_id': qq_id})
    json_data = json.dumps(body)
    r = requests.post(url, headers=headers, data=json_data)


def send_and_log_message(msg_type, qq_id, text, log_file):
    # 发送消息到QQ群
    send_message(msg_type, qq_id, text)

    # 将消息记录到文本文件
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# 配置MAA运行参数
def setmaa(s, tel, game, spare_game, spare_game_2):
    # 根据个人需要，删除了剿灭有关。
    # 计划把函数重写为一个可以根据实际需要而自行设置的自定义函数
    with open(setpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if s == 0:
        data["Configurations"]["Default"]["MainFunction.ActionAfterCompleted"] = "ExitEmulatorAndSelf"  # 完成后退出MAA和模拟器
        data["Configurations"]["Default"]["Start.RunDirectly"] = "True"  # 启动MAA后直接运行
        data["Configurations"]["Default"]["Start.StartEmulator"] = "True"  # 启动MAA后自动开启模拟器
    elif s == 2:
        data["Configurations"]["Default"]["Start.AccountName"] = tel[:3] + "****" + tel[7:]  # 账号切换
        data["Configurations"]["Default"]["TaskQueue.WakeUp.IsChecked"] = "True"  # 开始唤醒
        data["Configurations"]["Default"]["TaskQueue.Recruiting.IsChecked"] = "True"  # 自动公招
        data["Configurations"]["Default"]["TaskQueue.Base.IsChecked"] = "True"  # 基建换班
        data["Configurations"]["Default"]["TaskQueue.Combat.IsChecked"] = "True"  # 刷理智
        data["Configurations"]["Default"]["TaskQueue.Mission.IsChecked"] = "True"  # 领取奖励
        data["Configurations"]["Default"]["TaskQueue.Mall.IsChecked"] = "True"  # 获取信用及购物
        data["Configurations"]["Default"]["MainFunction.Stage1"] = game  # 主关卡
        data["Configurations"]["Default"]["MainFunction.Stage2"] = spare_game  # 备选关卡1，新增
        data["Configurations"]["Default"]["MainFunction.Stage3"] = spare_game_2  # 备选关卡2，新增
        data["Configurations"]["Default"]["Fight.RemainingSanityStage"] = "1-7"  # 剩余理智关卡
        data["Configurations"]["Default"]["Penguin.IsDrGrandet"] = "False"  # 博朗台模式
        data["Configurations"]["Default"]["GUI.CustomStageCode"] = "True"  # 手动输入关卡名
        data["Configurations"]["Default"]["GUI.UseAlternateStage"] = "True"  # 使用备选关卡
        data["Configurations"]["Default"]["Fight.UseRemainingSanityStage"] = "False"  # 使用剩余理智
        data["Configurations"]["Default"]["Fight.UseExpiringMedicine"] = "True"  # 无限吃48小时内过期的理智药
    with open(setpath, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return True


def runmaa(id, tel, spare_game, spare_game_2, game, qq_id, num=3):
    # 开始运行
    for i in range(num):
        global idnew, idold, idfail, idall
        runbook = False
        # 配置MAA
        setmaa(2, tel, game, spare_game, spare_game_2)
        # 创建MAA任务
        print(colored("等待中~", 'yellow'))
        time.sleep(10)
        maa = subprocess.Popen([maapath])
        maapid = maa.pid
        # 等待MAA启动
        idsuccess = idnew + idold
        idwait = [idx for idx in idall if not idx in idsuccess + idfail + [id]]
        os.system('cls')
        print(colored("正在代理：", 'white') + colored(id + "-日常", 'blue'))
        print(colored("等待代理：", 'white') + colored('，'.join(idwait), 'yellow'))
        print(colored("代理成功：", 'white') + colored('，'.join(idsuccess), 'green'))
        print(colored("代理失败：", 'white') + colored('，'.join(idfail), 'red'))
        print(colored("运行日志：", 'white') + colored("等待MAA初始化", 'light_green'))
        time.sleep(60)
        # 监测MAA运行状态
        while True:
            # 打印基本信息
            os.system('cls')
            print(colored("正在代理：", 'white') + colored(id + "-日常", 'blue'))
            print(colored("等待代理：", 'white') + colored('，'.join(idwait), 'yellow'))
            print(colored("代理成功：", 'white') + colored('，'.join(idsuccess), 'green'))
            print(colored("代理失败：", 'white') + colored('，'.join(idfail), 'red'))
            print(colored("运行日志：", 'white'))
            # 读取并保存MAA日志
            with open(logpath, 'r', encoding='utf-8') as f:
                logs = f.readlines()[-1:-11:-1]
                new_log = ''.join(logs[::-1])
                update_log(new_log)  # 更新日志和时间戳
                print(colored(new_log, 'light_green'), end='')
            # 判断MAA程序运行状态
            # 这里出问题的可能性很大，没有实际测试过
            log_content, _ = logx[logi - 1]  # 获取最新的日志内容
            if "任务已全部完成！" in log_content:
                # 消息推送渠道
                send_message('private', qq_id, '任务已经全部完成')
                runbook = True
                break
            elif "请检查连接设置或尝试重启模拟器与 ADB 或重启电脑" in log_content or "已停止" in log_content or "MaaAssistantArknights GUI exited" in log_content or timeout():
                os.system('taskkill /F /T /PID ' + str(maapid))
                break
            time.sleep(10)
        if runbook:
            return True
    return False


# 检查是否超时
# 源代码写法很精妙，但是实际环境这样排查问题很难
def update_log(new_log):
    global logx, logi
    # 更新日志并附上当前时间戳
    logx[logi] = (new_log, time.time())
    logi = (logi + 1) % len(logx)


def timeout():
    global logx
    # 获取当前时间
    current_time = time.time()
    # 检查最新的日志更新时间
    _, last_log_time = logx[-1]  # 访问最新日志的时间戳
    # 如果超过40分钟未更新，则返回True
    if current_time - last_log_time > 1800:  # 2400秒等于40分钟
        return True
    return False


# 更新已完成用户的数据
def updata(id):
    db = sqlite3.connect(DATABASE)
    cur = db.cursor()
    cur.execute("SELECT * FROM adminx WHERE admin=?", (id,))
    info = cur.fetchall()
    cur.execute("UPDATE adminx SET day=? WHERE admin=?", (info[0][2] - 1, id))
    db.commit()
    cur.execute("UPDATE adminx SET last=? WHERE admin=?", (curdate, id))
    db.commit()
    cur.close()
    db.close()
    return 0


# 资源回收
def cleanup():
    if os.path.exists("state/RUNNING"):
        os.remove("state/RUNNING")


if __name__ == "__main__":
    # 读取运行情况
    if os.path.exists("state/RUNNING"):
        os._exit(1)
    # 标记当前正在运行
    else:
        os.makedirs('state', exist_ok=True)
        with open("state/RUNNING", "w", encoding="utf-8") as f:
            print("RUNNING", file=f)
    # 设置回调函数
    atexit.register(cleanup)
    # 获取PATH与用户数据
    DATABASE = r"C:\Users\Administrator\Desktop\AUTO_MAA\data\data.db"
    db = sqlite3.connect(DATABASE)
    cur = db.cursor()
    cur.execute("SELECT * FROM pathset WHERE True")
    path = cur.fetchall()
    path = str(path[0][0])
    setpath = path + "/config/gui.json"
    logpath = path + "/debug/gui.log"
    maapath = path + "/MAA.exe"
    cur.execute("SELECT * FROM adminx WHERE True")
    data = cur.fetchall()
    data = [list(row) for row in data]
    cur.close()
    db.close()
    # 开始执行
    curdate = datetime.date.today().strftime('%Y-%m-%d')
    begintime = datetime.datetime.now().strftime("%H:%M")
    idnew = []
    idold = []
    idfail = []
    idall = [data[i][0] for i in range(len(data))]
    LOGXLEN = 60
    logx = [(None, time.time())] * 10  # 存储10个日志条目，每个条目包括日志和时间戳
    logi = 0
    # MAA预配置
    setmaa(0, 0, 0, 0, 0)
    # 优先代理今日未完成的用户
    for i in range(len(data)):
        if data[i][3] == 'y' and data[i][4] != curdate and data[i][2] > 0:
            book = runmaa(data[i][0], data[i][1], data[i][7], data[i][8], data[i][5], data[i][9])
            if book:
                updata(data[i][0])
                idnew.append(data[i][0])
            else:
                idfail.append(data[i][0])
    # 次优先重复代理
    for i in range(len(data)):
        if data[i][3] == 'y' and data[i][4] == curdate and data[i][2] > 0:
            book = runmaa(data[i][0], data[i][1], data[i][7], data[i][8], data[i][5], data[i][9])
            if book:
                idold.append(data[i][0])
            else:
                idall.remove(data[i][0])
    endtime = datetime.datetime.now().strftime("%H:%M")
    # 构建要记录的消息文本
    message_text = f"任务开始时间：{begintime}，结束时间：{endtime}\n"
    message_text += f"已完成数：{len(idnew)}，未完成数：{len(idfail)}，重复执行数：{len(idold)}\n"
    if len(idfail) != 0:
        message_text += "代理未完成的用户：\n"
        for i in idfail:
            message_text += f"{i}\n"

    # 调用新的方法来发送和记录消息
    send_and_log_message("group", 12234456, message_text, "log.txt")
    send_and_log_message('private', 1121334, message_text, 'log.txt')

    # 检查状态文件并更新
    if os.path.exists("state/BEGIN"):
        with open("state/END", "w", encoding="utf-8") as f:
            print("END", file=f)

    sys.exit(0)
