from ..data_managers import GameUpdateManager
from model.data_managers import IniFileReader
from model import constants
from pathlib import Path
from astrbot.api import logger
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

def delta_special_code():
    return (f"三角洲每日密码\n"
            f"一、潮汐监狱\n"
            f"密码门密码：6097\n"
            f"二、零号大坝\n"
            f"密码门密码：8246\n"
            f"三、长弓溪谷\n"
            f"密码门密码：8193\n"
            f"四、巴克什\n"
            f"密码门密码：6617\n"
            f"五、航空基地\n"
            f"密码门密码：4913")

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
    result += f"💡 提示：发送「历史事件 页码」查看指定页，例如：历史事件 2"
    
    return result

def bind(account: str, user_name: str, msg: str, path:Path) ->str:
    """
    处理绑定《逃跑吧少年》手游账号的请求，支持格式校验、唯一性校验和详细异常提示。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param msg: 用户输入的绑定命令
    :param path: 数据目录
    :return: 绑定结果提示
    """
    # 步骤1：验证命令格式
    if not msg.startswith("游戏绑定 "):
        return (
            f"{user_name} 支持绑定《逃跑吧少年》手游账号\n"
            f"绑定方法:游戏绑定 游戏ID\n"
            f"提示：一人仅支持绑定一次！"
        )
    # 步骤2：提取并验证游戏ID
    parts = msg.split(maxsplit=1)
    if len(parts) < 2:
        return f"{constants.ERROR_PREFIX} 请提供有效游戏ID（如:游戏绑定 1234567）"
    game_id = parts[1].strip()
    if not game_id.isdigit() or len(game_id) > 9:
        return f"{constants.ERROR_PREFIX} 请提供有效游戏ID（如:游戏绑定 1234567）"


  # 步骤3：初始化游戏管理器
    try:
        game_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Game.info",
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"初始化游戏管理器失败(用户[{account}]): {str(e)}", exc_info=True)
        return f"{constants.ERROR_PREFIX} 系统繁忙，初始化失败，请稍后重试！"


    # 步骤4：检查当前用户是否已绑定
    try:
        game_data = game_manager.read_section(account, create_if_not_exists=True)
        current_bound_id = game_data.get("game_id", 0)
        if current_bound_id != 0:
            return (
                f"{constants.ERROR_PREFIX} 您已绑定游戏ID:{current_bound_id}\n"
                f"如需更换，请先联系群主解绑！"
            )
    except Exception as e:
        logger.error(f"读取用户游戏数据失败(用户[{account}]): {str(e)}", exc_info=True)
        return f"{constants.ERROR_PREFIX} 读取绑定信息失败，请稍后重试！"


    # 步骤5：检查游戏ID是否被其他用户绑定
    try:
        all_user_data = game_manager.read_all()
        for user_acc, user_data in all_user_data.items():
            if user_acc == account:
                continue
            if user_data.get("game_id") == game_id:
                return (
                    f"{constants.ERROR_PREFIX} 绑定失败：游戏ID {game_id} 已被账号 {user_acc} 绑定！"
                )
    except Exception as e:
        logger.error(f"查询游戏ID绑定状态失败（游戏ID[{game_id}]）: {str(e)}", exc_info=True)
        return f"{constants.ERROR_PREFIX} 查询绑定状态失败，请稍后重试！"

    # 步骤6：绑定并保存数据
    try:
        game_manager.update_key(section=account, key="game_id", value=game_id)
        game_manager.save()
        return f"{constants.SUCCESS_PREFIX} 您的游戏ID已绑定为：{game_id}"
    except Exception as e:
        logger.error(f"保存绑定数据失败（用户[{account}]，游戏ID[{game_id}]）: {str(e)}", exc_info=True)
        return f"{constants.ERROR_PREFIX} 绑定成功但数据保存失败，请联系管理员！"

def game_menu():
    return (f"🎮 逃跑吧少年游戏助手\n"
            f"1️⃣ 游戏绑定\n"
            f"   绑定唯一逃少游戏账号\n"
            f"2️⃣ 更新公告\n"
            f"   查看游戏最新更新内容\n"
            f"3️⃣ 逃少代码\n"
            f"   获取逃少内可用兑换码\n"
            f"4️⃣ 历史事件\n"
            f"   浏览游戏历史事件记录\n"
            f"💡 提示：发送对应名称选择功能，例如：更新公告")