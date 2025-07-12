import os
import io
import asyncio
import datetime
import edge_tts
import pygame

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def text_to_speech_and_play(text):
    """
    将文本转换为语音并播放
    
    参数:
        text (str): 要转换为语音的文本
    """
    try:
        # 配置语音合成参数
        voice_config = {
            'voice': "zh-CN-YunxiNeural",
            'rate': "+20%",  # 语速调整
            'volume': "+100%"  # 音量调整
        }
        
        # 生成语音流
        communicate = edge_tts.Communicate(text, **voice_config)
        stream = communicate.stream()
        
        # 收集音频数据
        audio_data = b''
        async for chunk in stream:
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        # 初始化音频系统
        pygame.mixer.init()
        
        # 播放音频
        with io.BytesIO(audio_data) as audio_file:
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
    except Exception as e:
        print(f"语音合成或播放出错: {e}")
        raise

async def monitor_file_and_play(file_path, check_interval=10, play_interval=1):
    """
    监控文件变化并播放语音
    
    参数:
        file_path (str): 要监控的文件路径
        check_interval (int): 文件检查间隔(秒)
        play_interval (int): 播放间隔(秒)
    """
    while True:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('')
                    
                if content:  # 检查内容是否为空
                    await text_to_speech_and_play(content)
                    content = content.split('\n')
                    print(f"{get_timestamp()} 已播放：{content}")
                
                await asyncio.sleep(play_interval)
            else:
                print(f"文件 {file_path} 不存在，等待 {check_interval} 秒后再次检查...")
                await asyncio.sleep(check_interval)
                
        except Exception as e:
            print(f"文件监控出错: {e}")
            await asyncio.sleep(check_interval)

async def main():
    """主函数"""
    try:
        file_to_monitor = "temp.txt"  # 替换为你需要监控的文件路径
        
        # 程序启动时清空文件
        with open(file_to_monitor, 'w', encoding='utf-8') as f:
            f.write('')
            
        # print(f"已清空并开始监控文件: {file_to_monitor}")
        print(f"\033[94m{get_timestamp()} 语音播报监测功能已启动进入就绪状态\033[0m")
        await monitor_file_and_play(file_to_monitor)
    except KeyboardInterrupt:
        print("\n程序已手动终止")
    except Exception as e:
        print(f"程序运行出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())