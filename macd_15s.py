import loader
import tdxip
import mytt
import time
import datetime
import socket
import concurrent.futures
from pytdx.hq import TdxHq_API

cycle_time = '15秒钟'
cycle_code = 8
max_workers = 20
interval_time = 10
temp_text_list = []
tdx_ip = tdxip.get_available_ip(cycle_time)
data_list = loader.get_data_loader() # ['指数', 1, '000001', '上证指数']
start_process_num = 20
close_name_dict = {}
for data in data_list:
    type, market, code, name = data
    name = name.replace(' ', '')
    close_name_dict[name] = []

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def macd_monitor():
    global temp_text_list, close_name_dict
    temp_text = ''
    def function_map(api):
        return {'指数': api.get_index_bars, '股票': api.get_security_bars}
    def process_code(data):
        nonlocal temp_text
        type, market, code, name = data
        name = name.replace(' ', '')
        timestamp = get_timestamp()
        try:
            api = TdxHq_API()
            # 每个线程独立设置socket超时
            socket.setdefaulttimeout(10)
            with api.connect(tdx_ip, 7709):
                close = api.to_df(function_map(api)[type](cycle_code, market, code, 0, 1))['close'][0]
            close_name_dict[name].append(close)
            close_name_dict[name] = close_name_dict[name][-100:] if len(close_name_dict[name]) > 100 else close_name_dict[name]
            if len(close_name_dict[name]) >= start_process_num:
                # 计算MACD指标
                macd = mytt.MACD(close_name_dict[name])[-1]
                prev_macd = macd[-2]
                curr_macd = macd[-1]
                cross_type = None
                if prev_macd <= 0 and curr_macd > 0:
                    cross_type = ('金叉', '\033[91m')
                elif prev_macd >= 0 and curr_macd < 0:
                    cross_type = ('死叉', '\033[92m')
                if cross_type:
                    signal, color = cross_type
                    print(f'{color}{timestamp} {type} {name} {cycle_time}MACD{signal}信号\033[0m')
                    record = f'{name} {cycle_time}MACD{signal}信号\n'
                    if not any(record in text for text in temp_text_list[-3:]):
                        temp_text += record
        except Exception as e:
            print(f'{timestamp} 处理{name}时发生异常: {str(e)}')

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_code, data_list)

    # 写入文件, spoken程序会自动播放
    with open('temp.txt', 'a', encoding='utf-8') as f:
        f.write(temp_text)
    temp_text_list.append(temp_text)
    temp_text_list = temp_text_list[-3:]

if __name__ == "__main__":
    while True:
        try:
            start_time = datetime.datetime.now()
            current_second = start_time.second
            if current_second in [0, 15, 30, 45]:
                try:
                    macd_monitor()
                except Exception as e:
                    print(f'{get_timestamp()} {cycle_time}监测异常: {str(e)}')
                end_time = datetime.datetime.now()
                elapsed_time = (end_time - start_time).total_seconds()
                if len(close_name_dict['上证指数']) < start_process_num:
                    print(f'{get_timestamp()} {cycle_time}数据积累太少 计算不准确 请稍后')
                else:
                    print(f'{get_timestamp()} {cycle_time}监测执行完毕 共{len(data_list)}个标的 耗时{elapsed_time:.2f}秒')
                time.sleep(interval_time)
            time.sleep(0.1)
        except Exception as e:
            fatal_time = get_timestamp()
            print(f'{fatal_time} {cycle_time}监测线程致命错误: {str(e)}')
            # 发生致命错误后休眠10秒再重试
            time.sleep(10)