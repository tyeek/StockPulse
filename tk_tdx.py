import tkinter as tk
from tkinter import ttk
import pygetwindow as gw
import pyautogui
import time
import loader
import datetime

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class StockCodeViewer:
    def __init__(self, root_window, stock_codes):
        self.root = root_window
        self.root.title("tk_tdx")
        
        # 定义大按钮样式
        style = ttk.Style()
        style.configure('Large.TButton', font=('SimHei', 12))
        self.root.geometry("300x800")  # 设置窗口大小
        self.root.attributes('-topmost', True)  # 窗口置顶
        self.stock_codes = stock_codes

        # 创建滚动条
        scrollbar = ttk.Scrollbar(root)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建框架放置按钮
        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 添加按钮
        self.add_code_buttons()

    def add_code_buttons(self):
        """添加股票代码按钮"""
        if not self.stock_codes:
            ttk.Label(self.frame, text="没有找到股票代码数据").pack(pady=20)
            return

        # 按类型分组显示
        index_codes = [code for code in self.stock_codes if code[0] == '指数']
        stock_codes = [code for code in self.stock_codes if code[0] == '股票']

        if index_codes:
            ttk.Label(self.frame, text="====== 指数 ======", font=('SimHei', 12, 'bold')).pack(anchor=tk.W, pady=(10, 5))
            for code in index_codes:
                self.create_code_button(code)

        if stock_codes:
            ttk.Label(self.frame, text="====== 股票 ======", font=('SimHei', 12, 'bold')).pack(anchor=tk.W, pady=(10, 5))
            for code in stock_codes:
                self.create_code_button(code)

    def create_code_button(self, code):
        """创建单个代码按钮"""
        btn = ttk.Button(
            self.frame,
            text=code[3],
            command=lambda: self.open_line(code[2]),
            width=20,
            style='Large.TButton'
        )
        btn.pack(anchor=tk.W, pady=2)

    def open_line(self, code):
        window = gw.getWindowsWithTitle('通达信金融终端')[0]
        window.activate()
        window.maximize()
        time.sleep(0.3)
        pyautogui.typewrite(code)
        time.sleep(0.2)
        pyautogui.press('enter')

if __name__ == "__main__":
    # 从loader加载数据
    stock_codes = loader.get_data_loader()
    
    # 创建GUI界面
    root = tk.Tk()
    app = StockCodeViewer(root, stock_codes)
    print(f'\033[94m{get_timestamp()} 快捷跳转通达信功能已启动进入就绪状态\033[0m')
    root.mainloop()

