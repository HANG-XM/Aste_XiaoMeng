from pathlib import Path
import random
import time
from astrbot.api import logger

from model import constants
from model.directory import IniFileReader,FishFileHandler,ShopFileHandler,UnifiedCreelManager

def fish_menu():
    return (
        "🌊 您现在在湖边钓鱼～\n"
        "当前可选择操作：\n"
        "▸ 钓鱼（试试今天的手气！）\n"
        "▸ 提竿（看看钓到了什么～）\n"
        "▸ 我的鱼篓（检查战利品）\n"
        "▸ 钓鱼图鉴（了解鱼的信息）"
    )

def cast_fishing_rod(account:str, user_name:str, path) -> str:
    """
     处理用户抛竿钓鱼操作（优化版，增强校验与异常处理）
     :param account: 用户账号
     :param user_name: 用户昵称
     :param path: 项目根路径
     :return: 操作结果提示（含状态说明或错误信息）
     """
    # -------------------- 步骤1：读取基础数据（钓鱼状态/商店配置） --------------------
    try:
        # 读取钓鱼记录文件（记录当前钓鱼状态）
        fish_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Fish.data",
            encoding="utf-8",
        )
        fish_data = fish_manager.read_section(section=account,create_if_not_exists=True)
        # 读取商店配置（获取鱼竿基础参数）
        shop_manager = ShopFileHandler(
            project_root=path,
            subdir_name="City/Set_up",
            file_relative_path="Shop.res",
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"初始化数据读取器失败：{str(e)}", exc_info=True)
        return "系统繁忙，请稍后重试（数据加载异常）"

    # -------------------- 步骤2：校验当前钓鱼装备 --------------------
    # 校验鱼竿是否存在
    user_rod = fish_data.get("current_rod")
    if not user_rod:
        return f"{user_name} 当前未使用鱼竿\n发送'使用 鱼竿名'确定使用的鱼竿\n鱼竿可以前往'商店 鱼竿'进行购买"
    # 校验鱼饵是否存在
    user_bait = fish_data.get("current_bait")
    if not user_bait:
        return f"{user_name} 当前未使用鱼饵\n发送'使用 鱼饵名'确定使用的鱼饵\n鱼饵可以前往'商店 鱼饵'进行购买"

    # -------------------- 步骤3：读取购物篮数据（耐久/数量） --------------------
    try:
        basket_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Basket.info",
            encoding="utf-8",
        )
        basket_data = basket_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.error(f"读取错误：{str(e)}")
        return "系统繁忙，请稍后重试！"

    current_rod_endurance = basket_data.get(user_rod, 0)
    # 校验鱼竿耐久是否足够
    if current_rod_endurance <= 0:
        return f"{user_name} 当前鱼竿（{user_rod}）耐久已耗尽，无法使用！请更换新鱼竿。"
    current_bait_amount = basket_data.get(user_bait, 0)
    # 校验鱼饵数量是否足够
    if current_bait_amount <= 0:
        return f"{user_name} 当前鱼饵（{user_bait}）数量不足（剩余：{current_bait_amount}），请更换或购买新鱼饵！"

    # -------------------- 步骤4：生成钓鱼时间范围 --------------------
    rod_data = shop_manager.get_item_info(user_rod)
    now_time = time.time()
    # 生成随机延迟范围（范围=基础+附加）
    end_min = random.randint(a = constants.FISH_TIME_START,b = constants.FISH_TIME_END)
    end_max = end_min + constants.FISH_TIME_INTERVAL + rod_data.get("time",0)
    try:
        fish_manager.update_section_keys(section=account, data={
            "is_fishing": True,
            "start": now_time,
            "end_min": now_time + end_min,
            "end_max": now_time + end_max
        })
        fish_manager.save(encoding="utf-8")
    except Exception as e:
        logger.error(f"保存错误：{str(e)}")
        return "系统繁忙，请稍后重试！"
    # -------------------- 步骤5：更新购物篮数据 --------------------
    try:
        basket_manager.update_key(section=account, key=user_bait, value=current_bait_amount - 1)
        basket_manager.save(encoding="utf-8")
    except Exception as e:
        logger.error(f"扣减鱼饵数量失败：{str(e)}", exc_info=True)
        return "系统繁忙，请稍后重试（鱼饵数量更新失败）"
    # -------------------- 步骤6：返回成功提示 --------------------
    return (
        f"{user_name} 抛竿成功！\n"
        f"鱼竿：{user_rod}（耐久：{current_rod_endurance}）\n"
        f"鱼饵：{user_bait}（数量：{current_bait_amount - 1}）\n"
        f"请等待 {end_min}-{end_max} 秒后发送【提竿】获取渔获！"
    )

def lift_rod(account:str, user_name:str, path:Path,fish_manager:FishFileHandler) -> str:
    try:
        use_data_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8",
        )
        user_stamina = use_data_manager.read_key(section=account, key="stamina", default=0)
        user_fish_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Fish.data",
            encoding="utf-8",
        )
        user_fish_data = user_fish_manager.read_section(section=account,create_if_not_exists=True)
    except Exception as e:
        logger.error(f"初始化用户读取器错误：{str(e)}", exc_info=True)
        return "系统繁忙！请稍后重试"

    if not user_fish_data.get("is_fishing",False):
        return f"{user_name} 当前你未在钓鱼！"

    # 检查时间
    now_time = time.time()

    # 减少体力
    if user_stamina < constants.FISH_STAMINA:
        return "体力不足，无法'提竿'"

    try:
        new_stamina = user_stamina - constants.FISH_STAMINA
        use_data_manager.update_key(section=account, key="stamina", value=new_stamina)
        use_data_manager.save(encoding="utf-8")
    except Exception as e:
        logger.error(f"保存数据错误：{str(e)}", exc_info=True)
        return "系统繁忙！请稍后重试"

    start_time = user_fish_data.get("end_min", 0)  # 新增：假设存储了允许的最早开始时间（时间戳）
    end_time = user_fish_data.get("end_max", 0)      # 新增：假设存储了允许的最晚结束时间（时间戳）
    # 检查时间是否在有效区间（原逻辑保留，新增偏差计算）
    if now_time < start_time:
        delay_seconds = int(start_time - now_time)  # 计算早到秒数
        return f"{user_name} 你来得太早啦！当前时间还早 {delay_seconds} 秒，下次耐心等等~"
    elif now_time > end_time:
        delay_seconds = int(now_time - end_time)    # 计算晚到秒数
        return f"{user_name} 你来得太晚啦！钓鱼时间已结束 {delay_seconds} 秒前，下次早点来~"

    user_bait = user_fish_data.get("current_bait")
    random_fish = fish_manager.get_random_fish_by_bait(user_bait)
    logger.info(random_fish)

    if not random_fish:
        return "没有找到匹配该鱼饵的鱼。"

    # 提取鱼名和详细信息
    fish_name = next(iter(random_fish.keys()))  # 获取鱼名（如 "鲫鱼"）
    base_weight = random_fish[fish_name]["weight"]  # 获取鱼的重量信息

    # 计算浮动范围（±20%）并生成随机重量（核心逻辑）
    min_weight = base_weight * 0.8  # 最小重量：基准的 80%
    max_weight = base_weight * 1.2  # 最大重量：基准的 120%
    random_weight = random.uniform(min_weight, max_weight)  # 生成随机浮点数
    final_weight = round(random_weight, 1)  # 保留一位小数（如 2.3kg、5.6kg）

    creel_manager = UnifiedCreelManager(
            save_dir=path,
            subdir="City/Record",
            data_filename="Creel.json"
        )

    creel_manager.add_fish_weight(
        account=account,
        fish_name=fish_name,
        weight=final_weight,
    )

    user_fish_manager.update_key(section=account,key="is_fishing",value=False)
    user_fish_manager.save(encoding="utf-8")

    return f"好耶！{user_name}钓到了{final_weight}斤重的{fish_name}让我们恭喜TA吧！"

def my_creel(account:str, user_name:str, path) -> str:
    """
    查看用户渔获概览（总次数、总重量、各鱼种重量）

    :param account: 用户账号（如 "user123"）
    :param user_name: 用户昵称（如 "小明"）
    :param path: 数据保存根目录（Path 对象）
    :return: 渔获信息字符串（含友好提示）
    """
    try:
        # 初始化渔获管理器并获取用户概览
        creel_manager = UnifiedCreelManager(
            save_dir=path,
            subdir="City/Record",
            data_filename="Creel.json"
        )
        user_summary = creel_manager.get_user_summary(account=account)

    except ValueError as e:
        # 用户不存在时返回提示
        return f"⚠️ {user_name}，查询失败：{str(e)}"

    # 构建基础信息字符串
    base_info = [
        f"🎣 {user_name} 的渔获概览",
        f"——————————",
        f"总捕获：{user_summary['total_catches']} 次",
        f"总重量：{user_summary['total_weight']} 斤",  # 假设单位是“斤”，可根据实际调整
        f"鱼的种类：{user_summary['fish_types']} 种"
    ]

    # 处理无渔获记录的情况
    if user_summary["fish_types"] == 0:
        base_info.append("当前还没有钓到任何鱼哦~ 快去钓鱼吧！")
        return "\n".join(base_info)

    # 拼接各鱼种重量详情
    fish_details = ["\n各鱼种重量统计："]
    for fish_name, total in user_summary["fish_weights"].items():
        fish_details.append(f"  • {fish_name}：{total} 斤")  # 同样假设单位是“斤”

    # 合并所有信息并返回
    return "\n".join(base_info + fish_details)

def fishing_encyclopedia(account:str, user_name:str, path) -> str:
    pass