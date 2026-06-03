import requests
import re
import json
import csv
from os import path, listdir
import pathlib
import shutil
from datetime import datetime, timezone, timedelta
import os

# 获取北京时间
def get_beijing_time():
    """返回当前北京时间"""
    return datetime.now(timezone(timedelta(hours=8)))

# 设置时区（优先使用环境变量）
TZ = os.environ.get('TZ', 'Asia/Shanghai')

# 使用北京时间创建月份目录
yr_mth = get_beijing_time().strftime("%Y-%m")
store_data_folder = "./data/%s/" % yr_mth
store_data_full = store_data_folder + "LongRiver.json"

# 创建目录
pathlib.Path(store_data_folder).mkdir(parents=True, exist_ok=True)

# 迁移旧文件：将 data 根目录下的旧文件移到当前月份文件夹
for fn in listdir("./data/"):
    if fn.endswith(".csv") or fn.endswith(".json"):
        thismove = shutil.move(path.join('./data/', fn), store_data_folder)
        print("MOVE", thismove)

def write_csv_header(data, fname_prefix):
    """写入 CSV 表头"""
    with open('{}.csv'.format(fname_prefix), 'w', newline='', encoding='utf-8') as f:
        headers = list(data.keys())
        csv.writer(f).writerow(headers)

def write_csv_row(data, fname_prefix):
    """追加 CSV 数据行"""
    with open('{}.csv'.format(fname_prefix), 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(list(data.values()))

def normalize_station_data(station):
    """
    标准化测站数据，处理 oq 字段可能包含两个值的情况
    如果 oq 包含逗号，拆分为 oq_in 和 oq_out
    """
    if 'oq' in station and ',' in str(station['oq']):
        oq_parts = str(station['oq']).split(',')
        station['oq_in'] = oq_parts[0].strip()
        station['oq_out'] = oq_parts[1].strip()
        # 保留原始 oq 字段，同时添加新字段
    return station

# 读取或初始化 JSON 汇总文件
if not path.isfile(store_data_full):
    LongRiverData = {}
else:
    with open(store_data_full, 'r', encoding='utf-8') as f:
        LongRiverData = json.load(f)

# 抓取网页数据
try:
    print(f"[{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取数据...")
    response = requests.get('http://www.cjh.com.cn/sqindex.html', timeout=30)
    response.raise_for_status()
    html = response.text
    
    # 提取 JSON 数据
    json_match = re.findall("var sssq = (.*);", html)
    if not json_match:
        print("警告：未找到 sssq 变量，网站结构可能已变更")
        river_now = []
    else:
        river_now = json.loads(json_match[0])
        print(f"成功获取 {len(river_now)} 个测站数据")
        
except requests.RequestException as e:
    print(f"网络请求失败: {e}")
    river_now = []
except json.JSONDecodeError as e:
    print(f"JSON 解析失败: {e}")
    river_now = []

# 处理每个测站
for station in river_now:
    # 标准化数据
    station = normalize_station_data(station)
    
    # 生成文件名（河流_测站名）
    fname_prefix = store_data_folder + '_'.join([station['rvnm'], station['stnm']])

    # 初始化文件在 JSON 中的记录
    if fname_prefix not in LongRiverData:
        LongRiverData[fname_prefix] = []
    
    # 去重：如果最后一条记录的时间戳相同，跳过
    if LongRiverData[fname_prefix] and LongRiverData[fname_prefix][-1].get('tm') == station.get('tm'):
        print(f"跳过 {fname_prefix}，时间戳未变化")
        continue
    
    # 添加到 JSON 数据
    LongRiverData[fname_prefix].append(station)
    
    # 写入 CSV
    csv_path = '{}.csv'.format(fname_prefix)
    if not path.isfile(csv_path):
        write_csv_header(station, fname_prefix)
        print(f"创建 CSV 文件: {csv_path}")
    write_csv_row(station, fname_prefix)
    print(f"追加数据: {fname_prefix} - 时间: {station.get('tm')}")

# 保存 JSON 汇总文件
with open(store_data_full, 'w', encoding='utf-8') as f:
    json.dump(LongRiverData, f, ensure_ascii=False, indent=0)

print(f"[{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}] 数据抓取完成，共处理 {len(river_now)} 个测站")
