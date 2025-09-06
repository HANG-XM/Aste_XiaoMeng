from ..data_managers import GameUpdateManager
def update_notice(msg:str,manager:GameUpdateManager):

    # 检查是否请求所有ID列表
    if msg == "更新公告":
        # 获取所有ID
        all_ids = manager.get_all_update_ids()
        # 每四个ID一行进行格式化
        formatted_ids = []
        for i in range(0, len(all_ids), 4):
            # 获取当前行的ID（最多4个）
            line_ids = all_ids[i:i+4]
            # 将这一行的ID连接成一个字符串
            line = ", ".join(line_ids)
            formatted_ids.append(line)
        # 将所有行用换行符连接
        result = "📋 可用的更新公告ID:\n" + "\n".join(formatted_ids)
        result += "\n\n💡 提示：发送「更新公告 ID」查看具体内容，例如：更新公告 250731"
        return result
    else:
        # 提取特定的ID
        notice_id = msg.replace("更新公告 ", "")
        # 获取并返回特定ID的内容
        notice_detail = manager.get_update_by_date(notice_id)
        # 添加标题和分隔线
        if notice_detail != "未找到该日期的更新公告":
            result = f"📢 更新公告 ID: {notice_id}\n"
            result += notice_detail
            result += "💡 提示：发送「更新公告」查看所有可用ID"
            return result
        else:
            return f"❌ {notice_detail}\n💡 提示：发送「更新公告」查看所有可用ID"

def special_code():
    return (f"🎮 逃跑吧少年兑换码\n"
            f"1️⃣ 【追风杯小组赛开战】\n"
            f"🎁 奖励：干杯快乐水*1、粉玫瑰*66\n"
            f"2️⃣ 【来哔哩哔哩玩逃跑吧少年】\n"
            f"🎁 奖励：火箭筒碎片*24、手榴弹碎片*26、白金币*666、点券*188、粉玫瑰*16\n"
            f"3️⃣ 【关注逃跑吧少年快手号领福利】\n"
            f"🎁 奖励：白金币*2000、点券*200、粉玫瑰*20\n"
            f"4️⃣ 【DMM20180803】\n"
            f"🎁 奖励：白金币*2000、点券*200、粉玫瑰*20\n"
            f"💡 提示：在游戏内设置-兑换码中输入兑换")

def history_event():
    return """历史事件"""

def game_menu():
    return """逃跑吧少年游戏助手\n1.更新公告\n2.兑换代码"""