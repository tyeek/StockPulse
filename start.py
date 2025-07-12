from mytt import config
import multiprocessing
import subprocess
import time
import sys

def run_script(script_name):
    subprocess.call([sys.executable, script_name])

if __name__ == '__main__':
    print("\033[94m=\033[0m" * 50)
    print("\033[94m程序名称: 股票脉搏监测\033[0m")
    print("\033[94m=\033[0m" * 50)
    print("\033[94m该程序集成多周期的MACD监测、股票跳转以及语音播报功能\033[0m")
    print(f"\033[94m能准确识别MACD金叉、死叉交易信号 当前MACD参数{config}\033[0m")
    print("\033[94m=\033[0m" * 50)
    scripts = ['spoken.py', 'tk_tdx.py', 'macd_1m.py', 'macd_15m.py', 'macd_15s.py']
    processes = []

    for script in scripts:
        p = multiprocessing.Process(target=run_script, args=(script,))
        p.start()
        processes.append(p)
        time.sleep(1)

    for p in processes:
        p.join()

    print("All scripts have finished running.")