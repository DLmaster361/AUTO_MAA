import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from loguru import logger
import shutil

from app.core import Config


def analyze_maa_logs(logs_directory: Path):
    """
    遍历 logs_directory 下所有 .log 文件，解析公招和掉落信息，
    - 生成单独的 JSON 文件（同名）
    - 生成总的 JSON 文件（合并所有 log）
    """
    if not logs_directory.exists():
        logger.error(f"目录不存在: {logs_directory}")
        return

    # 检查并删除超期日志
    clean_old_logs(logs_directory)

    # 设定 JSON 输出路径
    json_output_path = logs_directory / f"{logs_directory.name}.json" if logs_directory.parent.name == "maa_run_history" else logs_directory.parent / f"{logs_directory.name}.json"

    aggregated_data = {
        "recruit_statistics": defaultdict(int),  # 统计公招星级数量
        "drop_statistics": defaultdict(dict),  # 统计掉落信息
    }

    log_files = list(logs_directory.rglob("*.log"))
    if not log_files:
        logger.error(f"没有找到 .log 文件: {logs_directory}")
        return

    for log_file in log_files:
        single_file_data = {
            "recruit_statistics": defaultdict(int),
            "drop_statistics": defaultdict(dict),
        }
        analyze_single_log(log_file, single_file_data)

        # 生成单个 .log 文件对应的 .json 文件
        json_file_path = log_file.with_suffix(".json")
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(single_file_data, json_file, ensure_ascii=False, indent=4)
        logger.info(f"已生成 JSON: {json_file_path}")

        # 累积到总数据
        merge_aggregated_data(aggregated_data, single_file_data)

    # 生成汇总 JSON 文件
    with open(json_output_path, "w", encoding="utf-8") as json_file:
        json.dump(aggregated_data, json_file, ensure_ascii=False, indent=4)

    logger.info(f"统计完成：{json_output_path}")


def analyze_single_log(log_file_path: Path, aggregated_data):
    """
    解析单个 .log 文件，提取公招结果 & 关卡掉落数据
    """
    recruit_data = aggregated_data["recruit_statistics"]
    drop_data = aggregated_data["drop_statistics"]

    with open(log_file_path, "r", encoding="utf-8") as f:
        logs = f.readlines()

    # 公招统计（仅统计招募到的）
    confirmed_recruit = False
    current_star_level = None
    i = 0
    while i < len(logs):
        if "公招识别结果:" in logs[i]:
            current_star_level = None  # 每次识别公招时清空之前的星级
            i += 1
            while i < len(logs) and "Tags" not in logs[i]:  # 读取所有公招标签
                i += 1

            if i < len(logs) and "Tags" in logs[i]:  # 识别星级
                star_match = re.search(r"(\d+)\s*★ Tags", logs[i])
                if star_match:
                    current_star_level = f"{star_match.group(1)}★"

        if "已确认招募" in logs[i]:  # 只有确认招募后才统计
            confirmed_recruit = True

        if confirmed_recruit and current_star_level:
            recruit_data[current_star_level] += 1
            confirmed_recruit = False  # 重置，等待下一次公招
            current_star_level = None  # 清空已处理的星级

        i += 1

    # 掉落统计
    current_stage = None
    stage_drops = {}

    for i, line in enumerate(logs):
        drop_match = re.search(r"(\d+-\d+) 掉落统计:", line)
        if drop_match:
            # 发现新关卡，保存前一个关卡数据
            if current_stage and stage_drops:
                drop_data[current_stage] = stage_drops

            current_stage = drop_match.group(1)
            stage_drops = {}
            continue

        if current_stage:
            item_match = re.findall(r"([\u4e00-\u9fa5]+)\s*:\s*([\d,]+)(?:\s*\(\+\d+\))?", line)
            for item, total in item_match:
                # 解析数值时去掉逗号 （如 2,160 -> 2160）
                total = int(total.replace(",", ""))

                # 黑名单
                if item not in ["当前次数", "理智"]:
                    stage_drops[item] = total

    # 处理最后一个关卡的掉落数据
    if current_stage and stage_drops:
        drop_data[current_stage] = stage_drops

    logger.info(f"处理完成：{log_file_path}")


def merge_aggregated_data(aggregated_data, single_data):
    """
    将单个文件数据合并到总数据
    """
    # 合并公招统计
    for star_level, count in single_data["recruit_statistics"].items():
        aggregated_data["recruit_statistics"][star_level] += count

    # 合并掉落统计
    for stage, drops in single_data["drop_statistics"].items():
        if stage not in aggregated_data["drop_statistics"]:
            aggregated_data["drop_statistics"][stage] = {}  # 初始化关卡

        for item, count in drops.items():
            # 确保物品存在
            if item not in aggregated_data["drop_statistics"][stage]:
                aggregated_data["drop_statistics"][stage][item] = 0
            aggregated_data["drop_statistics"][stage][item] += count


def clean_old_logs(logs_directory: Path):
    """
    删除超过用户设定天数的日志文件（基于目录日期）
    """
    # 确保 logs_directory 是 maa_run_history 目录
    while logs_directory.name != "maa_run_history" and logs_directory.parent != logs_directory:
        logs_directory = logs_directory.parent

    retention_setting = Config.global_config.get(Config.global_config.function_LogRetentionDays)
    retention_days_mapping = {
        "7 天": 7,
        "15 天": 15,
        "30 天": 30,
        "60 天": 60,
        "90 天": 90,
        "180 天": 180,
        "365 天": 365,
        "永不清理": None
    }

    retention_days = retention_days_mapping.get(retention_setting, None)
    if retention_days is None:
        logger.info("用户设置日志保留时间为【永不清理】，跳过清理")
        return

    cutoff_date = datetime.now() - timedelta(days=retention_days)

    deleted_count = 0
    if not logs_directory.exists():
        logger.warning(f"日志目录不存在: {logs_directory}")
        return

    for date_folder in logs_directory.iterdir():
        if not date_folder.is_dir():
            continue  # 只处理日期文件夹

        try:
            # 只检查 `YYYY-MM-DD` 格式的文件夹
            folder_date = datetime.strptime(date_folder.name, "%Y-%m-%d")
            if folder_date < cutoff_date:
                # 递归删除整个日期目录
                shutil.rmtree(date_folder, ignore_errors=True)
                deleted_count += 1
                logger.info(f"已删除超期日志目录: {date_folder}")
        except ValueError:
            logger.warning(f"非日期格式的目录: {date_folder}")

    logger.info(f"清理完成: {deleted_count} 个日期目录")


# # 运行代码
# logs_directory = Path(r"E:\Github\AUTO_MAA\maa_run_history\2025-02-19\1\aoxuan")
# analyze_maa_logs(logs_directory)
