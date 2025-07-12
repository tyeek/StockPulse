import psutil
from pytdx.hq import TdxHq_API
import datetime

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_available_ip(period):
    """
    获取可用的通达信服务器IP地址
    :param primary_server_ip: 首选服务器IP地址
    :return: 可用的服务器IP地址或None
    """
    api = TdxHq_API()
    primary_server_ip='122.51.232.182'
    try:
        with api.connect(primary_server_ip, 7709):
            if api.get_security_bars(0, 0, '000001', 0, 1):
                print(f'\033[94m{get_timestamp()} {period}MACD监测功能已启动进入就绪状态\033[0m')
                return primary_server_ip
    except:
        try:
            input(f'{get_timestamp()} 请先登录通达信客户端 然后按回车键继续')
            for process in psutil.process_iter(['pid', 'name']):
                if 'tdxw.exe' in process.info['name'].lower():
                    for connection in process.net_connections(kind='inet'):
                        try:
                            server_ip = connection.raddr.ip
                            with api.connect(server_ip, 7709):
                                if api.get_security_bars(0, 0, '000001', 0, 1):
                                    print(f'{get_timestamp()} 已连接到通达信服务器 {server_ip}')
                                    return server_ip
                        except:
                            pass
        except:
            pass
    
    input(f'{get_timestamp()} 未连接到通达信服务器 请登录通达信后重新运行程序')
    return None

if __name__ == '__main__':
    TDXIP = get_available_ip()