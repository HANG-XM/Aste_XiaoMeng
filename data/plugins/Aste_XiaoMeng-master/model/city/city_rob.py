from astrbot.api import logger

from model import constants
from model.directory import IniFileReader
from model.city_func import get_by_qq,get_dynamic_rob_ratio

import time
import random
from datetime import datetime

def rob_menu() -> str:
    return ("f打劫专区 ️\n"
        f"—— 想当劫匪？先看清规则 ——\n"
        f"1.发起打劫[@目标]（入狱不可用）\n"
        f"👉 示例「打劫 @小明」\n"
        f"2.尝试越狱[体力 / 金币]\n"
        f"👉 示例「越狱」→ 搞点装备再跑\n"
        f"3.申请保释[@目标]（入狱后解锁）\n"
        f"👉 示例「保释 @对象」\n"
        f"4.发送出狱（自由状态自动恢复）\n"
        f"👉 示例「出狱」→ 重新获得自由\n"
        f" 输入上方指令，开始劫匪之旅 ")

def rob(account:str, user_name:str, msg:str, path) -> str:
    exp,victim_qq =  get_by_qq(msg)
    if not victim_qq:
        return "打劫格式请使用：打劫 @对象"

    try:
        user_manager = IniFileReader(
            project_root=path, subdir_name="City/Personal", file_relative_path="Briefly.info", encoding="utf-8"
        )
        rob_manager = IniFileReader(
            project_root=path, subdir_name="City/Record", file_relative_path="Rob.data", encoding="utf-8"
        )
        # 读取受害者与抢劫者的数据
        victim_data = user_manager.read_section(section=victim_qq, create_if_not_exists=True)
        robber_data = user_manager.read_section(section=account, create_if_not_exists=True)
        robber_rob_data = rob_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.error(f"读取用户数据失败: {e}")
        return "错误！功能错误！请稍后重试！"

    # ---- 新增：检查是否在狱中 ----
    jail_start_time = robber_rob_data.get("jail_time", 0)  # 默认0表示未入狱
    current_time = time.time()
    if jail_start_time > 0:
        # 计算剩余服刑时间（秒）
        remaining_seconds = max(0, constants.JAIL_TIME - int(current_time - jail_start_time))
        if remaining_seconds > 0:
            # 提示剩余时间，但不阻止打劫
            return f"⚠️ {user_name} 你正在服刑（剩余 {remaining_seconds} 秒），无法打劫！"
        else:
            # 刑期已满但未自动释放（手动触发释放）
            return f"ℹ️ {user_name} 你已刑满，需手动发送[出狱]操作！"

    current_robber_stamina = robber_data.get("stamina", 0)
    if current_robber_stamina < constants.ROB_STAMINA:
        return f"{user_name} 你现在没有体力了，无法继续打劫！"
    current_victim_gold = victim_data.get("coin", 0)
    if current_victim_gold <= 0:
        return f"{user_name} TA现在身无分文，打劫无意义！"
    current_robber_gold = robber_data.get("coin", 0)

    # 打劫次数控制（每日重置）
    today = datetime.today().isoformat()
    rob_count_today = robber_rob_data.get("rob_count_today", 0)
    last_rob_date = robber_rob_data.get("last_rob_date", "")

    if last_rob_date != today:
        rob_count_today = 0
        rob_manager.update_section_keys(
            section=account, data={"last_rob_date": today, "rob_count_today": 0}
        )
    # 减少打劫者体力
    new_robber_stamina = current_robber_stamina - constants.ROB_STAMINA
    user_manager.update_key(section=account, key="stamina", value=new_robber_stamina)

    # ---- 动态计算可抢金额 ----
    dynamic_ratio = get_dynamic_rob_ratio(current_victim_gold)
    max_rob = max(1, int(current_victim_gold * dynamic_ratio))
    rob_amount = random.randint(1, max_rob)

    # ---- 判断打劫结果 ----
    is_success = random.randint(1, 100) <= constants.ROB_SUCCESS_RATE

    if is_success:
        # 抢劫成功 ✅
        new_victim_gold = max(0, current_victim_gold - rob_amount)
        new_robber_gold = current_robber_gold + rob_amount

        # 更新数据
        user_manager.update_key(section=victim_qq, key="coin", value=new_victim_gold)
        user_manager.update_key(section=account, key="coin", value=new_robber_gold)

        result_text = f"{user_name} 🎉 恭喜！打劫成功！你获得了 {rob_amount} 金币！（对方损失 {rob_amount} 金币）"
    else:
        # ❌ 失败逻辑
        event = random.choice(constants.ROB_FAILURE_EVENTS)
        coin_change = event["coin_change"]
        stamina_loss = event["stamina_loss"]
        jail = event["jail"]

        new_robber_gold = max(0, current_robber_gold + coin_change)
        new_robber_stamina = max(0, current_robber_stamina - stamina_loss)
        # 更新用户数据（仅robber）
        user_manager.update_section_keys(section=account, data={
            "coin": new_robber_gold,
            "stamina": new_robber_stamina
        })
        result_text = event["text"]
        if jail:
            result_text += f"{user_name} 你因打劫被关进监狱，剩余入狱秒数：{constants.JAIL_TIME} 秒！"
            rob_manager.update_key(section=account,key="jail_time",value=time.time())

    # ---- 公共逻辑：更新打劫次数&日期 & 保存数据 ----
    rob_count_today += 1
    rob_manager.update_section_keys(
        section=account,
        data={"rob_count_today": rob_count_today, "last_rob_date": today}
    )
    try:
        user_manager.save(encoding="utf-8")
        rob_manager.save(encoding="utf-8")
    except Exception as e:
        logger.error(f"保存数据失败: {e}")
        return "保存数据时出错，请稍后再试！"

    return result_text

def released(account:str, user_name:str, path) -> str:
    """手动释放用户（出狱）"""
    try:
        rob_manager = IniFileReader(
            project_root=path, subdir_name="City/Record", file_relative_path="Rob.data", encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"释放用户 {account} 失败: {e}")
        return "出狱过程中发生错误，请联系管理员。"
    # 检测当前入狱状态（可选）
    current_jail_time = rob_manager.read_key(section=account, key="jail_time", default=0)
    if current_jail_time <= 0:
        return f"{user_name} 你未入狱，无需出狱！"
    # 正确判断：入狱开始时间 + 刑期 > 当前时间 → 未服完刑
    if current_jail_time + constants.JAIL_TIME > time.time():
        remaining = int(current_jail_time + constants.JAIL_TIME - time.time())
        return f"{user_name} 未到出狱时间，还需服刑 {remaining} 秒！"
    try:
        user_manager = IniFileReader(
            project_root=path, subdir_name="City/Personal", file_relative_path="Briefly.info", encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"释放用户 {account} 失败: {e}")
        return "出狱过程中发生错误，请联系管理员。"

    user_stamina = user_manager.read_key(section=account, key="stamina", default=0)
    if user_stamina < constants.RELEASED_STAMINA:
        return f"{user_name} 体力不足，休息一会再出狱吧！"
    new_stamina = user_stamina - constants.RELEASED_STAMINA
    user_manager.update_key(section=account, key="stamina", value=new_stamina)
    user_manager.save(encoding="utf-8")
    # 清除入狱时间（设置为0表示未入狱）
    rob_manager.update_key(section=account, key="jail_time", value=0)
    rob_manager.save(encoding="utf-8")
    # 可选：同步其他状态（如体力、金币）
    return f"用户 {user_name} 已成功出狱！"

def post_bail(account:str, user_name:str,msg:str, path):
    """处理玩家保释请求"""
    if not msg.startswith("保释 "):
        return "保释方法：请输入「保释 @目标QQ」发起保释请求"
    content,target_qq = get_by_qq(msg)
    if not target_qq:
        return "目标格式错误，请@正确的QQ号（5-11位数字）"

    if target_qq == account:
        return f"{user_name} 你不能自己保释自己哦！"
    # 读取入狱记录（带异常处理）
    try:
        rob_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Rob.data",
            encoding="utf-8",
        )
    except Exception as e:
        # 记录异常日志（需引入logging模块）
        logger.error(f"保释操作异常：{str(e)}")
        return "系统繁忙，请稍后再试！"

    rob_time = rob_manager.read_key(section=target_qq, key="jail_time",default=0)
    if rob_time == 0:
        return f"{user_name} 他没有在监狱中哦！"

    user_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8",
    )
    user_gold = user_manager.read_key(section=account, key="coin",default=0)
    if user_gold < constants.BAIL_FEE:
        return f"{user_name} 保释需要 {constants.BAIL_FEE} 金币，你的金币不足！"
    new_gold = user_gold - constants.BAIL_FEE
    user_manager.update_key(section=account, key="coin", value=new_gold)
    user_manager.save(encoding="utf-8")
    rob_manager.update_key(section=account, key="jail_time", value=0)
    rob_manager.save(encoding="utf-8")
    return f"{user_name} 保释成功！你支付了 {constants.BAIL_FEE} 金币～"

def prison_break(account:str, user_name:str, path):
    """
    处理用户越狱操作：
    1. 读取当前监禁时间和用户体力
    2. 校验是否可越狱（未监禁/体力足够）
    3. 扣除体力并尝试越狱（随机成功率）
    4. 更新监禁时间或回滚体力（事务性）

    Args:
        account: 用户账号（用于配置文件分区）
        user_name: 用户昵称（用于返回提示）
        path: 项目根路径（配置文件所在目录）

    Returns:
        操作结果提示（成功/失败/错误信息）
    """
    try:
        rob_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Rob.data",
            encoding="utf-8",
        )
        rob_time = rob_manager.read_key(section=account, key="jail_time",default=0)
    except Exception as e:
        logger.error(f"读取打劫数据错误：{str(e)}")
        return "系统繁忙！请稍后重试！"

    if rob_time == 0:
        return f"{user_name} 当前你未在监狱里面！无需越狱！"
    try:
        user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8",
        )
        user_stamina = user_manager.read_key(section=account, key="stamina",default=0)
    except Exception as e:
        logger.error(f"读取打劫数据错误：{str(e)}")
        return "系统繁忙！请稍后重试！"

    if user_stamina < constants.PRISON_BREAK_STAMINA:
        return f"{user_name} 体力不足，无法越狱！"
    new_stamina = user_stamina - constants.PRISON_BREAK_STAMINA
    user_manager.update_key(section=account, key="stamina", value=new_stamina)
    user_manager.save(encoding="utf-8")
    if random.randint(a = 1,b = 100) <= constants.PRISON_BREAK_SUCCESS_RATE:
        rob_manager.update_key(section=account, key="jail_time", value=0)
        return f"{user_name} 越狱成功！"
    return f"{user_name} 越狱失败！"