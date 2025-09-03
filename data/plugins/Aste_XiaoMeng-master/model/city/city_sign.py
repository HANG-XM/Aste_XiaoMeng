from astrbot.api import logger

from model import constants
from model.directory import IniFileReader
from model.city_func import preprocess_date_str, calculate_delta_days

from datetime import datetime
import random

def xm_main() -> str:
    return (
        f"✨ 小梦菜单 ✨"
        f"\n————————————"
        f"\n✅ 签到        | 🔍 查询"
        f"\n🔗 绑定"
        f"\n💼 打工菜单 | ⚔️ 打劫菜单"
        f"\n🏦 银行菜单 | 🏪 商店菜单"
        f"\n🎣 钓鱼菜单 | 🏆 排行菜单"
        )

def check_in(account:str,user_name:str,path)->str:
    """
    签到功能
    :param account: 用户账号
    :param user_name:用户昵称
    :param path:数据目录
    :return: 签到结果提示（含随机趣味文案）
    """
    # ---------------------- 数据管理器初始化 ----------------------
    sign_reader  = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Sign_in.data",
        encoding="utf-8"
                         )
    user_reader = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8"
    )
    # -------------------- 读取/初始化签到数据 --------------------
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 处理上次签到时间（兼容旧格式）
    sign_data = sign_reader.read_section(account, create_if_not_exists=True)
    last_sign_str = preprocess_date_str(sign_data.get("sign_time", "1970-01-01"))
    # -------------------- 核心签到逻辑 --------------------
    if last_sign_str == today_str:
        continuous = sign_data.get("continuous_clock-in", 0)
        accumulated = sign_data.get("accumulated_clock-in", 0)
        return f"{user_name} 今天已经签到过啦！当前连续签到{continuous}天，累计签到{accumulated}天～"

    # 初始化奖励和天数变量
    reward_coin = 0
    reward_exp = 0
    continuous_days = sign_data.get("continuous_clock-in", 0)
    accumulated_days = sign_data.get("accumulated_clock-in", 0)

    # 情况2：首次签到（上次签名为初始日期）
    if last_sign_str == "1970-01-01":
        reward_coin = constants.CHECK_IN_FIRST_REWARD_GOLD
        reward_exp = constants.CHECK_IN_FIRST_REWARD_EXP
        reward_stamina = constants.CHECK_IN_FIRST_REWARD_STAMINA
        continuous_days = 1
        accumulated_days = 1
        result_msg = (random.choice(constants.CHECK_IN_FIRST_TIPS)
                      (user_name,reward_coin,reward_exp,reward_stamina))
    else:
        # 情况3：计算断签天数
        delta_days = calculate_delta_days(today_str,last_sign_str)

        if delta_days == 1:
            # 连续签到（间隔1天）
            reward_coin = constants.CHECK_IN_CONTINUOUS_REWARD_GOLD
            reward_exp = constants.CHECK_IN_CONTINUOUS_REWARD_EXP
            reward_stamina = constants.CHECK_IN_CONTINUOUS_REWARD_STAMINA
            continuous_days += 1
            result_msg = (random.choice(constants.CHECK_IN_CONTINUOUS_TIPS)
                          (user_name,continuous_days,reward_coin,reward_exp,reward_stamina))
        else:
            # 断签后签到（间隔>1天）
            reward_coin = constants.CHECK_IN_BREAK_REWARD_GOLD
            reward_exp = constants.CHECK_IN_BREAK_REWARD_EXP
            reward_stamina = constants.CHECK_IN_BREAK_REWARD_STAMINA
            continuous_days = 1  # 重置连续天数
            result_msg = (random.choice(constants.CHECK_IN_BREAK_TIPS)
                          (user_name,reward_coin,reward_exp,reward_stamina))
        accumulated_days += 1  # 累计天数始终+1


    # -------------------- 更新签到数据 --------------------
    sign_reader.update_section_keys(account, {
        "sign_time": today_str,
        "continuous_clock-in": continuous_days,
        "accumulated_clock-in": accumulated_days
    })

    # -------------------- 更新用户属性（金币/经验） --------------------
    # -------------------- 读取/初始化用户属性 --------------------
    user_section = user_reader.read_section(account, create_if_not_exists=True)
    current_coin = user_section.get("coin", 0)  # 当前金币（默认0）
    current_exp = user_section.get("exp", 0)    # 当前经验（默认0）
    current_stamina = user_section.get("stamina", 0)  # 当前经验（默认0）
    # 计算新值（防止负数）
    new_coin = max(current_coin + reward_coin, 0)
    new_exp = max(current_exp + reward_exp, 0)
    new_stamina = max(current_stamina + reward_stamina, 0)
    # 准备用户属性更新
    user_reader.update_section_keys(account, {
        "coin": new_coin,
        "exp": new_exp,
        "stamina":new_stamina
    })
    # -------------------- 保存双文件变更 --------------------
    sign_reader.save(encoding="utf-8")  # 保存签到数据
    user_reader.save(encoding="utf-8")  # 保存用户属性

    return (result_msg + "\n" +
            f"{random.choice(constants.CHECK_IN_RANDOM_TIPS)
            }")

def query(account: str, user_name: str, path) -> str:
    """
    查询用户信息
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据目录
    :return: 格式化后的用户信息字符串（优化后更友好、结构化）
    """
    try:
        # 初始化INI读取器（自动处理文件/节不存在）
        file = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )

        # 读取用户数据（节不存在时自动创建空Section）
        account_data = file.read_section(account, create_if_not_exists=True)

        # ------------------------------ 动态生成用户信息内容 ------------------------------
        # 定义用户信息字段配置（属性名、显示名称、单位）
        user_info_fields = [
            ("level", "等级", "级"),
            ("exp", "经验", "点"),
            ("coin", "金币", "个"),
            ("charm", "魅力", "点"),
            ("stamina", "体力", "点")
        ]

        # 动态拼接信息内容（通过配置生成，避免重复代码）
        content_lines = []
        for field_key, display_name, unit in user_info_fields:
            value = account_data.get(field_key, 0)  # 统一处理默认值
            content_lines.append(f"▸{display_name}：{value} {unit}")

            # 组合头部与内容（保持友好格式）
        header = f"你好呀，{user_name}👋～\n—————————\n"
        content = "\n".join(content_lines)  # 用换行符连接所有字段行
        return f"{header}{content}"

    except Exception as e:
        # 优化异常提示语气
        logger.error(f"用户[{account}]查询异常：{str(e)}")
        return "哎呀，查询时出了点小问题，请稍后再试哦～"

def bind(account: str, user_name: str, msg: str, path) ->str:
    """处理绑定《逃跑吧少年》手游账号的请求（优化版）"""
    # -------------------- 步骤1：验证命令格式 --------------------
    if not msg.startswith("绑定 "):
        return f"{user_name} 支持绑定《逃跑吧少年》手游账号\n绑定方法:绑定 游戏ID\n提示：一人仅支持绑定一次！"

    # -------------------- 步骤2：提取并验证游戏ID --------------------
    parts = msg.split(maxsplit=1)
    if len(parts) < 2:
        return f"{constants.ERROR_PREFIX} 请提供有效游戏ID（如:绑定 1234567）"
    game_id = parts[1].strip()
    if not game_id.isdigit() or len(game_id) > 9:
        return f"{constants.ERROR_PREFIX} 请提供有效游戏ID（如:绑定 1234567）"

    # -------------------- 初始化游戏管理器 --------------------
    try:
        game_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Game.info",
        )
    except Exception as e:
        logger.error(f"初始化游戏管理器失败(用户[{account}]): {str(e)}")
        return "❌ 系统繁忙，请稍后重试！"

    # -------------------- 检查当前用户是否已绑定 --------------------
    try:
        game_data = game_manager.read_section(account, create_if_not_exists=True)
        current_bound_id = game_data.get("game_id", 0)
        if current_bound_id != 0:
            return f"{constants.ERROR_PREFIX} 您已绑定游戏ID:{current_bound_id}\n如需更换，请先联系群主解绑！"
    except Exception as e:
        logger.error(f"读取用户游戏数据失败(用户[{account}]): {str(e)}")
        return "❌ 系统繁忙，请稍后重试！"

    # -------------------- 检查游戏ID是否被其他用户绑定 --------------------
    try:
        # 获取所有已绑定游戏的用户
        all_user_data = game_manager.read_all()  # 获取全量用户数据（格式：{账号: {键值对}}）
        for user_acc, user_data in all_user_data.items():
            if user_acc == account:
                continue  # 跳过当前用户
            if user_data.get("game_id") == game_id:
                return f"{constants.ERROR_PREFIX} 绑定失败：游戏ID {game_id} 已被账号 {user_acc} 绑定！"
    except Exception as e:
        logger.error(f"查询游戏ID绑定状态失败（游戏ID[{game_id}]）: {str(e)}")
        return "❌ 系统繁忙，请稍后重试！"

    # -------------------- 绑定并保存数据 --------------------
    try:
        game_manager.update_key(section=account, key="game_id", value=game_id)
        game_manager.save()
        return f"{constants.SUCCESS_PREFIX} 您的游戏ID已绑定为：{game_id}"
    except Exception as e:
        logger.error(f"保存绑定数据失败（用户[{account}]，游戏ID[{game_id}]）: {str(e)}")
        return "❌ 绑定成功但数据保存失败，请联系管理员！"