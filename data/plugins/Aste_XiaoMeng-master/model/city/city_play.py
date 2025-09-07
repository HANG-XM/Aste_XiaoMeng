import random
from model.data_managers import IniFileReader

def rock(msg:str):
    """
    猜拳游戏函数
    参数:
        msg: 用户输入的消息
    返回:
        根据输入返回相应的提示或游戏结果
    """

    if not msg.startswith("猜拳 "):
        return "猜拳格式：猜拳 石头/剪刀/布"
    
    user_choice = msg[3:].strip()  # 去掉"猜拳 "并去除前后空格

    # 检查用户选择是否有效
    valid_choices = ["石头", "剪刀", "布"]
    if user_choice not in valid_choices:
        return "猜拳格式：猜拳 石头/剪刀/布"
    
    # 电脑随机选择
    computer_choice = random.choice(valid_choices)

    # 判断输赢
    result = determine_winner(user_choice, computer_choice)

    # 返回结果
    return f"你出了{user_choice}，电脑出了{computer_choice}，{result}"

def determine_winner(user_choice, computer_choice):
    """
    判断猜拳游戏的输赢
    参数:
        user_choice: 用户的选择
        computer_choice: 电脑的选择
    返回:
        判断结果的字符串
    """
    # 平局情况
    if user_choice == computer_choice:
        return "平局！"
    
    # 用户获胜的情况
    winning_combinations = {
        "石头": "剪刀",
        "剪刀": "布",
        "布": "石头"
    }
    
    if winning_combinations[user_choice] == computer_choice:
        return "你赢了！"
    
    # 剩下的情况都是电脑赢
    return "你输了！"
    