import pandas as pd
from typing import List, Tuple

# 常量定义
DEFAULT_UNKNOWN_STOCK = '未知股票'
DEFAULT_UNKNOWN_INDEX = '未知指数'

def get_data_loader() -> List[Tuple[str, int, str, str]]:
    """
    从Excel文件加载股票和指数数据
    
    返回:
        List[Tuple[str, int, str, str]]: 包含(类型, 市场, 代码, 名称)的元组列表
    """
    df0 = pd.read_excel('监测股票列表.xlsx', sheet_name='0')
    df1 = pd.read_excel('监测股票列表.xlsx', sheet_name='1')
    data_list = []
    for i in df0['指数'].dropna():
        code = str(int(i))[1:]
        try:
            name = df1[(df1['代码'] == i) & (df1['类型'] == '指数')]['名称'].values[0]
        except (IndexError, KeyError):
            name = DEFAULT_UNKNOWN_INDEX
        if code.startswith('0'):
            data_list.append(['指数', 1, code, name])
        elif code.startswith('3') or code.startswith('9'):
            data_list.append(['指数', 0, code, name])
    for i in df0['股票'].dropna():
        code = str(int(i))[1:]
        try:
            name = df1[(df1['代码'] == i) & (df1['类型'] == '股票')]['名称'].values[0]
        except (IndexError, KeyError):
            name = DEFAULT_UNKNOWN_STOCK
        if code.startswith('6'):
            data_list.append(['股票', 1, code, name])
        elif code.startswith('0') or code.startswith('3'):
            data_list.append(['股票', 0, code, name])
    return data_list

if __name__ == '__main__':
    """主函数用于测试数据加载功能"""
    data_list = get_data_loader()
    print(f'加载的数据条目数: {len(data_list)}')
    print('前5条数据:')
    for item in data_list[:5]:
        print(item)
