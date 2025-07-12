import time
import datetime
import threading
import numpy as np
import pandas as pd
import concurrent.futures
from typing import List, Tuple
from pytdx.hq import TdxHq_API
import edge_tts
import asyncio
import pygame
import psutil
import socket
import io

# windows终端一行命令开启颜色支持
# reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1

# 根据通达信客户端的PID值获取通达信远程的IP地址
# netstat -ano | findstr 4060

# 最大线程数
MAX_WORKERS = 20
interval_time = 50

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_available_tdx_ip(default_ip='122.51.232.182'):
    api = TdxHq_API()
    try:
        with api.connect(default_ip, 7709):
            if api.get_security_bars(0, 0, '000001', 0, 1):
                print(f'{get_timestamp()} 已连接到通达信服务器 {default_ip}')
                return default_ip
    except:
        try:
            input(f'{get_timestamp()} 请先登录通达信客户端 然后按回车键继续')
            for proc in psutil.process_iter(['pid', 'name']):
                if 'tdxw.exe' in proc.info['name'].lower():
                    for conn in proc.net_connections(kind='inet'):
                        try:
                            ip = conn.raddr.ip
                            with api.connect(ip, 7709):
                                if api.get_security_bars(0, 0, '000001', 0, 1):
                                    print(f'{get_timestamp()} 已连接到通达信服务器 {ip}')
                                    return ip
                        except:
                            pass
        except:
            pass
    
    input(f'{get_timestamp()} 未连接到通达信服务器 请登录通达信后重新运行程序')
    return None

TDXIP = get_available_tdx_ip()

async def text_to_speech_and_play(text):
    communicate = edge_tts.Communicate(text,
        voice = "zh-CN-YunxiNeural",
        rate = "+20%",  # 语速调整
        volume = "+100%") # 音量调整
    stream = communicate.stream()   # 使用 edge_tts 生成音频数据流
    audio_data = b''
    async for chunk in stream:
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    audio_stream = io.BytesIO(audio_data)   # 将拼接后的音频数据加载到 BytesIO 对象中
    pygame.mixer.init()                          # 初始化 pygame 音频模块
    pygame.mixer.music.load(audio_stream, 'mp3')    # 将字节流加载到 pygame 中
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.quit()

# 创建语音播放队列
speech_queue = asyncio.Queue()

async def monitor_queue():
    """监控队列并播放语音"""
    while True:
        try:
            # 等待1秒超时获取队列元素
            text = await asyncio.wait_for(speech_queue.get(), timeout=1.0)
            await text_to_speech_and_play(text)
            speech_queue.task_done()
        except asyncio.TimeoutError:
            # 超时继续循环 实现每秒检测一次
            continue
        except asyncio.CancelledError:
            # 任务被取消时退出循环
            break

def RD(N,D=3):
    return np.round(N,D)

def EMA(S,N):  
    return pd.Series(S).ewm(span=N, adjust=False).mean().values

def MACD(CLOSE,SHORT=12,LONG=26,M=9):
    DIF = EMA(CLOSE,SHORT)-EMA(CLOSE,LONG)  
    DEA = EMA(DIF,M)
    MACD=(DIF-DEA)*2
    return RD(DIF),RD(DEA),RD(MACD)

def get_data_loader() -> List[Tuple[str, str, str]]:
    # 读取Excel并指定使用列
    df = pd.read_excel('监测股票列表.xlsx')
    data_list = []
    for i in df['指数'].dropna():
        code = str(int(i))[1:]
        if code.startswith('0'):
            data_list.append(['指数', 1, code])
        elif code.startswith('3'):
            data_list.append(['指数', 0, code])
    for i in df['股票'].dropna():
        code = str(int(i))[1:]
        if code.startswith('0') or code.startswith('3'):
            data_list.append(['股票', 0, code])
        elif code.startswith('6'):
            data_list.append(['股票', 1, code])
    return data_list

def macd_monitor(period: str, data_list: List[Tuple[str, str, str]], loop):
    period_map = {'1': 8, '15': 1}
    def function_map(api):
        return {'指数': api.get_index_bars, '股票': api.get_security_bars}
    def process_code(data: Tuple[str, str, str]):
        type, market, code = data
        timestamp = get_timestamp()
        try:
            # 设置socket超时为10秒
            socket.setdefaulttimeout(10)
            api = TdxHq_API()
            with api.connect(TDXIP, 7709):
                df = api.to_df(function_map(api)[type](period_map[period], market, code, 0, 100))
            # 计算MACD指标
            df['DIF'], df['DEA'], df['MACD'] = MACD(df['close'])
            
            # 确保有足够的数据点
            if len(df) >= 2:
                prev_row, curr_row = df.iloc[-2], df.iloc[-1]

                if prev_row['MACD'] <= 0 and curr_row['MACD'] > 0:
                    # 红色文本：\033[91m 重置：\033[0m
                    print(f'\033[91m{timestamp} {type} {code} {period}分钟MACD金叉信号\033[0m')
                    future = asyncio.run_coroutine_threadsafe(
                        speech_queue.put(f'{type} {code}, {period}分钟MACD金叉信号'),
                        loop
                    )
                    # 等待任务完成
                    future.result()
                elif prev_row['MACD'] >= 0 and curr_row['MACD'] < 0:
                    # 绿色文本：\033[92m 重置：\033[0m
                    print(f'\033[92m{timestamp} {type} {code} {period}分钟MACD死叉信号\033[0m')
                    future = asyncio.run_coroutine_threadsafe(
                        speech_queue.put(f'{type} {code}, {period}分钟MACD死叉信号'),
                        loop
                    )
                    # 等待任务完成
                    future.result()
            else:
                print(f'{timestamp} {type} {code} 数据不足 无法计算MACD')

        except Exception as e:
            print(f'{timestamp} 处理{code}时发生异常: {str(e)}')

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务并设置超时
        futures = {executor.submit(process_code, code): code for code in data_list}
        # 记录开始时间用于监控总耗时
        start_time = datetime.datetime.now()
        for future in concurrent.futures.as_completed(futures, timeout=40):
            code = futures[future]
            try:
                future.result()
            except concurrent.futures.TimeoutError:
                print(f'{get_timestamp()} 处理{code}超时')
            except Exception as e:
                print(f'{get_timestamp()} 处理{code}异常: {str(e)}')

async def main_async():
    # 创建事件循环和监控任务
    monitor_task = asyncio.create_task(monitor_queue())
    
    # 返回当前的事件循环以供线程使用
    return monitor_task

def main():
    data_list = get_data_loader()
    period_list = ['1', '15']
    threads = []
    
    # 使用新的asyncio API创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 启动监控队列的协程
    monitor_task = loop.run_until_complete(asyncio.gather(main_async()))[0]
    
    def create_monitor_loop(period):
        def monitor_loop():
            while True:
                try:
                    cycle_start_time = datetime.datetime.now()
                    try:
                        macd_monitor(period, data_list, loop)
                    except Exception as e:
                        error_time = get_timestamp()
                        print(f'{error_time} {period}分钟监测异常: {str(e)}')
                    
                    # 计算实际耗时并动态调整休眠时间
                    cycle_end_time = datetime.datetime.now()
                    elapsed_time = (cycle_end_time - cycle_start_time).total_seconds()
                    end_time_str = cycle_end_time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f'{end_time_str} {period}分钟监测执行完毕 共{len(data_list)}个标的 耗时{elapsed_time:.2f}秒')
                    time.sleep(interval_time)
                except Exception as e:
                    fatal_time = get_timestamp()
                    print(f'{fatal_time} {period}分钟监测线程致命错误: {str(e)}')
                    time.sleep(10)  # 发生致命错误后休眠10秒再重试
        return monitor_loop
    
    # 启动监测线程
    for period in period_list:
        monitor_loop = create_monitor_loop(period)
        thread = threading.Thread(target=monitor_loop, daemon=True, name=f'{period}min')
        thread.start()
        threads.append(thread)
    
    try:
        # 保持事件循环运行
        loop.run_forever()
    except KeyboardInterrupt:
        print("程序被用户中断")
    finally:
        # 取消监控任务
        monitor_task.cancel()
        
        # 等待任务完成取消
        loop.run_until_complete(asyncio.gather(monitor_task, return_exceptions=True))
        
        # 关闭事件循环
        loop.close()
        
        print("程序已退出")

if __name__ == "__main__":
    main()
import time
import datetime
import threading
import numpy as np
import pandas as pd
import concurrent.futures
from typing import List, Tuple
from pytdx.hq import TdxHq_API
import edge_tts
import asyncio
import pygame
import psutil
import socket
import io

# windows终端一行命令开启颜色支持
# reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1

# 根据通达信客户端的PID值获取通达信远程的IP地址
# netstat -ano | findstr 4060

# 最大线程数
MAX_WORKERS = 20
interval_time = 50

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_available_tdx_ip(default_ip='122.51.232.182'):
    api = TdxHq_API()
    try:
        with api.connect(default_ip, 7709):
            if api.get_security_bars(0, 0, '000001', 0, 1):
                print(f'{get_timestamp()} 已连接到通达信服务器 {default_ip}')
                return default_ip
    except:
        try:
            input(f'{get_timestamp()} 请先登录通达信客户端 然后按回车键继续')
            for proc in psutil.process_iter(['pid', 'name']):
                if 'tdxw.exe' in proc.info['name'].lower():
                    for conn in proc.net_connections(kind='inet'):
                        try:
                            ip = conn.raddr.ip
                            with api.connect(ip, 7709):
                                if api.get_security_bars(0, 0, '000001', 0, 1):
                                    print(f'{get_timestamp()} 已连接到通达信服务器 {ip}')
                                    return ip
                        except:
                            pass
        except:
            pass
    
    input(f'{get_timestamp()} 未连接到通达信服务器 请登录通达信后重新运行程序')
    return None

TDXIP = get_available_tdx_ip()

async def text_to_speech_and_play(text):
    communicate = edge_tts.Communicate(text,
        voice = "zh-CN-YunxiNeural",
        rate = "+20%",  # 语速调整
        volume = "+100%") # 音量调整
    stream = communicate.stream()   # 使用 edge_tts 生成音频数据流
    audio_data = b''
    async for chunk in stream:
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    audio_stream = io.BytesIO(audio_data)   # 将拼接后的音频数据加载到 BytesIO 对象中
    pygame.mixer.init()                          # 初始化 pygame 音频模块
    pygame.mixer.music.load(audio_stream, 'mp3')    # 将字节流加载到 pygame 中
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.quit()

# 创建语音播放队列
speech_queue = asyncio.Queue()

async def monitor_queue():
    """监控队列并播放语音"""
    while True:
        try:
            # 等待1秒超时获取队列元素
            text = await asyncio.wait_for(speech_queue.get(), timeout=1.0)
            await text_to_speech_and_play(text)
            speech_queue.task_done()
        except asyncio.TimeoutError:
            # 超时继续循环 实现每秒检测一次
            continue
        except asyncio.CancelledError:
            # 任务被取消时退出循环
            break

def RD(N,D=3):
    return np.round(N,D)

def EMA(S,N):  
    return pd.Series(S).ewm(span=N, adjust=False).mean().values

def MACD(CLOSE,SHORT=12,LONG=26,M=9):
    DIF = EMA(CLOSE,SHORT)-EMA(CLOSE,LONG)  
    DEA = EMA(DIF,M)
    MACD=(DIF-DEA)*2
    return RD(DIF),RD(DEA),RD(MACD)

def get_data_loader() -> List[Tuple[str, str, str]]:
    # 读取Excel并指定使用列
    df = pd.read_excel('监测股票列表.xlsx')
    data_list = []
    for i in df['指数'].dropna():
        code = str(int(i))[1:]
        if code.startswith('0'):
            data_list.append(['指数', 1, code])
        elif code.startswith('3'):
            data_list.append(['指数', 0, code])
    for i in df['股票'].dropna():
        code = str(int(i))[1:]
        if code.startswith('0') or code.startswith('3'):
            data_list.append(['股票', 0, code])
        elif code.startswith('6'):
            data_list.append(['股票', 1, code])
    return data_list

def macd_monitor(period: str, data_list: List[Tuple[str, str, str]], loop):
    period_map = {'1': 8, '15': 1}
    def function_map(api):
        return {'指数': api.get_index_bars, '股票': api.get_security_bars}
    def process_code(data: Tuple[str, str, str]):
        type, market, code = data
        timestamp = get_timestamp()
        try:
            # 设置socket超时为10秒
            socket.setdefaulttimeout(10)
            api = TdxHq_API()
            with api.connect(TDXIP, 7709):
                df = api.to_df(function_map(api)[type](period_map[period], market, code, 0, 100))
            # 计算MACD指标
            df['DIF'], df['DEA'], df['MACD'] = MACD(df['close'])
            
            # 确保有足够的数据点
            if len(df) >= 2:
                prev_row, curr_row = df.iloc[-2], df.iloc[-1]

                if prev_row['MACD'] <= 0 and curr_row['MACD'] > 0:
                    # 红色文本：\033[91m 重置：\033[0m
                    print(f'\033[91m{timestamp} {type} {code} {period}分钟MACD金叉信号\033[0m')
                    future = asyncio.run_coroutine_threadsafe(
                        speech_queue.put(f'{type} {code}, {period}分钟MACD金叉信号'),
                        loop
                    )
                    # 等待任务完成
                    future.result()
                elif prev_row['MACD'] >= 0 and curr_row['MACD'] < 0:
                    # 绿色文本：\033[92m 重置：\033[0m
                    print(f'\033[92m{timestamp} {type} {code} {period}分钟MACD死叉信号\033[0m')
                    future = asyncio.run_coroutine_threadsafe(
                        speech_queue.put(f'{type} {code}, {period}分钟MACD死叉信号'),
                        loop
                    )
                    # 等待任务完成
                    future.result()
            else:
                print(f'{timestamp} {type} {code} 数据不足 无法计算MACD')

        except Exception as e:
            print(f'{timestamp} 处理{code}时发生异常: {str(e)}')

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务并设置超时
        futures = {executor.submit(process_code, code): code for code in data_list}
        # 记录开始时间用于监控总耗时
        start_time = datetime.datetime.now()
        for future in concurrent.futures.as_completed(futures, timeout=40):
            code = futures[future]
            try:
                future.result()
            except concurrent.futures.TimeoutError:
                print(f'{get_timestamp()} 处理{code}超时')
            except Exception as e:
                print(f'{get_timestamp()} 处理{code}异常: {str(e)}')

async def main_async():
    # 创建事件循环和监控任务
    monitor_task = asyncio.create_task(monitor_queue())
    
    # 返回当前的事件循环以供线程使用
    return monitor_task

def main():
    data_list = get_data_loader()
    period_list = ['1', '15']
    threads = []
    
    # 使用新的asyncio API创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 启动监控队列的协程
    monitor_task = loop.run_until_complete(asyncio.gather(main_async()))[0]
    
    def create_monitor_loop(period):
        def monitor_loop():
            while True:
                try:
                    cycle_start_time = datetime.datetime.now()
                    try:
                        macd_monitor(period, data_list, loop)
                    except Exception as e:
                        error_time = get_timestamp()
                        print(f'{error_time} {period}分钟监测异常: {str(e)}')
                    
                    # 计算实际耗时并动态调整休眠时间
                    cycle_end_time = datetime.datetime.now()
                    elapsed_time = (cycle_end_time - cycle_start_time).total_seconds()
                    end_time_str = cycle_end_time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f'{end_time_str} {period}分钟监测执行完毕 共{len(data_list)}个标的 耗时{elapsed_time:.2f}秒')
                    time.sleep(interval_time)
                except Exception as e:
                    fatal_time = get_timestamp()
                    print(f'{fatal_time} {period}分钟监测线程致命错误: {str(e)}')
                    time.sleep(10)  # 发生致命错误后休眠10秒再重试
        return monitor_loop
    
    # 启动监测线程
    for period in period_list:
        monitor_loop = create_monitor_loop(period)
        thread = threading.Thread(target=monitor_loop, daemon=True, name=f'{period}min')
        thread.start()
        threads.append(thread)
    
    try:
        # 保持事件循环运行
        loop.run_forever()
    except KeyboardInterrupt:
        print("程序被用户中断")
    finally:
        # 取消监控任务
        monitor_task.cancel()
        
        # 等待任务完成取消
        loop.run_until_complete(asyncio.gather(monitor_task, return_exceptions=True))
        
        # 关闭事件循环
        loop.close()
        
        print("程序已退出")

if __name__ == "__main__":
    main()
