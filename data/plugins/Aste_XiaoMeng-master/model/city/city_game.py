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
        result = "可用的更新公告ID:\n" + "\n".join(formatted_ids)
        return result
    else:
        # 提取特定的ID
        notice_id = msg.replace("更新公告 ", "")
        # 获取并返回特定ID的内容
        notice_detail = manager.get_update_by_date(notice_id)
        return notice_detail

def special_code():
    return """兑换代码"""

def history_event():
    return """历史事件"""

def game_menu():
    return """逃跑吧少年游戏助手\n1.更新公告\n2.兑换代码"""