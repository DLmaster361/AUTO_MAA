import json
import psutil
import subprocess
import time
import os
import logging
import threading
import requests

# 配置部分
CHECK_INTERVAL = 60  # 每60秒检测一次
MAX_RUNTIME = 50 * 60  # 最大运行时间50分钟
MAX_MEMORY_USAGE = 7 * 1024 * 1024 * 1024  # 最大内存使用7GB
SCRIPT_CHECK_INTERVAL = 2 * 60 * 60  # 每两个小时检测一次脚本运行状态
LOG_FILE = 'monitor_log.txt'  # 监控日志文件路径
RUNNING_FILE_PATH = r'C:\Users\Administrator\Desktop\AUTO_MAA\state\RUNNING'  # RUNNING文件路径
BEGIN_FILE_PATH = r'C:\Users\Administrator\Desktop\AUTO_MAA\state\BEGIN'  # BEGIN文件路径
AUTO_MAA_SCRIPT_PATH = r'C:\Users\Administrator\Desktop\AUTO_MAA\AUTO_MAA.py'  # AUTO_MAA.py脚本路径
RUN_PY_SCRIPT_PATH = r'C:\Users\Administrator\Desktop\AUTO_MAA\run.py'  # run.py脚本路径
QQ_SEND_INTERVAL = 60 * 60  # 每小时发送一次消息

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=LOG_FILE)
logger = logging.getLogger(__name__)

last_script_check = 0

def log_message(message):
    logger.info(message)

def check_processes():
    ldplayer = None
    maa = None
    for proc in psutil.process_iter(['pid', 'name', 'create_time', 'memory_info']):
        if proc.info['name'] == 'ldplayer.exe':
            ldplayer = proc
        elif proc.info['name'] == 'Maa.exe':
            maa = proc
    return ldplayer, maa

def set_process_priority(proc, priority=psutil.HIGH_PRIORITY_CLASS):
    try:
        proc.nice(priority)
        log_message(f"设置进程 {proc.info['name']} (PID: {proc.info['pid']}) 的优先级为 {priority}")
    except Exception as e:
        log_message(f"设置进程 {proc.info['name']} (PID: {proc.info['pid']}) 优先级时出错: {e}")

def kill_process(proc):
    log_message(f"终止进程 {proc.info['name']} (PID: {proc.info['pid']})")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except psutil.NoSuchProcess:
        pass

def check_memory():
    mem = psutil.virtual_memory()
    return mem.used > MAX_MEMORY_USAGE

def run_auto_maa():
    log_message("运行 AUTO_MAA 脚本")
    proc = subprocess.Popen(['powershell.exe', AUTO_MAA_SCRIPT_PATH])
    set_process_priority(psutil.Process(proc.pid))

def is_auto_maa_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        if 'AUTO_MAA.py' in proc.info['cmdline']:
            return proc
    return None

def delete_files():
    if os.path.exists(RUNNING_FILE_PATH):
        os.remove(RUNNING_FILE_PATH)
        log_message("删除文件: RUNNING")
    if os.path.exists(BEGIN_FILE_PATH):
        os.remove(BEGIN_FILE_PATH)
        log_message("删除文件: BEGIN")

def check_auto_maa_hang():
    try:
        with open(LOG_FILE, 'r') as log_file:
            lines = log_file.readlines()
            if lines:
                last_line = lines[-1]
                last_log_time = time.mktime(time.strptime(last_line.split(' - ')[0], '%Y-%m-%d %H:%M:%S'))
                if time.time() - last_log_time > 15 * 60:  # 假设15分钟没有新日志输出即认为卡死
                    return True
    except Exception as e:
        log_message(f"检查 AUTO_MAA 日志错误: {e}")
    return False

def run_additional_script():
    log_message("运行附加脚本: run.py")
    proc = subprocess.Popen(['python', RUN_PY_SCRIPT_PATH])
    set_process_priority(psutil.Process(proc.pid))

def send_message(text):
    # 只写了群聊代理完推送。
    url = r'http://localhost:3000/send_msg'
    headers = {'Content-Type': 'application/json'}
    body = {
        'message_type': 'group',
        'message': text,
        'group_id': '123456778'
    }
    json_data = json.dumps(body)
    r = requests.post(url, headers=headers, data=json_data)

def send_log_to_qq():
    while True:
        time.sleep(QQ_SEND_INTERVAL)
        try:
            with open(LOG_FILE, 'r') as log_file:
                log_content = log_file.read()
            send_message_to_qq(log_content)
            log_message("日志发送到 QQ")
        except Exception as e:
            log_message(f"发送日志到 QQ 时出错: {e}")

def monitor_processes():
    global last_script_check
    while True:
        ldplayer, maa = check_processes()

        if ldplayer:
            set_process_priority(ldplayer)
            runtime = time.time() - ldplayer.create_time()
            if runtime > MAX_RUNTIME or check_memory():
                kill_process(ldplayer)
                if maa:
                    kill_process(maa)
                auto_maa = is_auto_maa_running()
                if auto_maa:
                    kill_process(auto_maa)
                delete_files()
                run_additional_script()  # 运行额外的run.py脚本
                run_auto_maa()

        if time.time() - last_script_check > SCRIPT_CHECK_INTERVAL:
            last_script_check = time.time()
            auto_maa = is_auto_maa_running()
            if not auto_maa:
                delete_files()
                run_auto_maa()
            elif check_auto_maa_hang():
                kill_process(auto_maa)
                delete_files()
                run_auto_maa()

        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    threading.Thread(target=monitor_processes, daemon=True).start()
    threading.Thread(target=send_log_to_qq, daemon=True).start()
