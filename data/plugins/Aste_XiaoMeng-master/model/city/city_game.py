from ..data_managers import GameUpdateManager
from model import constants
def update_notice(msg:str,game_manager:GameUpdateManager):

    # 检查是否请求所有ID列表
    if msg == "更新公告":
        # 获取所有ID
        all_ids = game_manager.get_all_update_ids()
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
        notice_detail = game_manager.get_update_by_date(notice_id)
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
            f"1️⃣ 【来哔哩哔哩玩逃跑吧少年】\n"
            f"🎁 奖励：火箭筒碎片*24、手榴弹碎片*26、白金币*666、点券*188、粉玫瑰*16\n"
            f"2️⃣ 【关注逃跑吧少年快手号领福利】\n"
            f"🎁 奖励：白金币*2000、点券*200、粉玫瑰*20\n"
            f"3️⃣ 【DMM20180803】\n"
            f"🎁 奖励：白金币*2000、点券*200、粉玫瑰*20\n"
            f"💡 提示：在游戏内设置-兑换码中输入兑换")

def history_event(msg: str, game_manager: GameUpdateManager):
    """
    获取历史事件列表（分页显示）
    
    :param msg: 用户消息，可能包含页码
    :param game_manager: GameUpdateManager实例
    :return: 格式化后的历史事件字符串
    """
    # 默认每页显示
    page_size = constants.GAME_HISTORY_PER_PAGE
    
    # 尝试从消息中提取页码
    page = 1  # 默认页码
    if msg.strip() != "历史事件":
        try:
            # 尝试提取消息中的数字作为页码
            page = int(msg.replace("历史事件", "").strip())
            if page < 1:
                page = 1
        except ValueError:
            # 如果转换失败，使用默认页码
            pass
    
    # 获取所有历史记录日期并排序（最新的在前）
    all_dates = sorted(game_manager.get_all_history_dates(), reverse=True)
    total_records = len(all_dates)
    total_pages = (total_records + page_size - 1) // page_size  # 计算总页数
    
    # 确保页码在有效范围内
    if page > total_pages:
        page = total_pages
    
    # 计算当前页的起始和结束索引
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_records)
    
    # 获取当前页的历史记录
    current_page_dates = all_dates[start_idx:end_idx]
    
    # 构建结果字符串
    result = f"📜 逃跑吧少年历史事件 (第{page}/{total_pages}页)\n"
    
    # 添加当前页的历史记录
    for date in current_page_dates:
        history_content = game_manager.get_history_by_date(date)
        result += f"📅 {date}\n"
        result += f"   {history_content}\n\n"
    
    # 添加提示信息
    result += f"\n💡 提示：发送「历史事件 页码」查看指定页，例如：历史事件 2"
    
    return result

def game_menu():
    return """逃跑吧少年游戏助手\n1.更新公告\n2.兑换代码"""