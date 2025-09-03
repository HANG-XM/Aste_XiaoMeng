from astrbot.api import logger

from model import constants
from model.directory import IniFileReader
from model.city_func import get_by_qq,calculate_delta_days

import time
from datetime import datetime
from typing import Dict
from decimal import Decimal,ROUND_HALF_UP

def bank_menu() -> str:
    """
    返回适合 QQ 群文字游戏的银行菜单（简洁直观，带互动引导）
    """
    return ("""✦ 🏦 银 行 服 务 ✦\n———————————\n✨ 基础操作 → 存款 / 取款\n✨ 资金流转 → 贷款 / 还款\n
    ✨ 定期业务 → 存定期 / 取定期\n✨ 其他功能 → 查存款 / 转账\n——————————\n输入对应关键词使用，如「存款」""")

def deposit(account,user_name,msg,path) -> str:
    """
    存款
    :param account: 用户账号
    :param user_name:用户昵称
    :param msg:
    :param path:数据目录
    :return: 结果提示
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")  # 获取当前时间

    if not msg.startswith("存款 "):
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"存款格式应为：存款 [金额]（例：存款 {constants.DEPOSIT_MULTIPLE_BASE}）\n"
            f"✨ 温馨提示：金额需为{constants.DEPOSIT_MULTIPLE_BASE}的整数倍，"
            f"如{constants.DEPOSIT_MULTIPLE_BASE}、{constants.DEPOSIT_MULTIPLE_BASE*3}等。"
        )
    parts = msg.split()
    if len(parts) < 2:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"信息不完整呢~ 请补充完整的金额\n"
            f"📝 示例：存款 {constants.DEPOSIT_MULTIPLE_BASE}（表示存入{constants.DEPOSIT_MULTIPLE_BASE}金币）"
        )
    try:
        amount = int(parts[1])
    except ValueError:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"金额格式错误~ 请输入有效的整数"
        )
    if amount <= 0:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"金额不能为0或负数哦~ 请输入大于0的数值\n"
            f"💡 建议：至少存入{constants.DEPOSIT_MULTIPLE_BASE}金币（如：存款 {constants.DEPOSIT_MULTIPLE_BASE}）。"
        )
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"当前金额不符合要求呢~ 存款需为 {constants.DEPOSIT_MULTIPLE_BASE} 的整数倍\n"
            f"🔢 示例："
            f"{constants.DEPOSIT_MULTIPLE_BASE}（1倍）、"
            f"{constants.DEPOSIT_MULTIPLE_BASE * 2}（2倍）、"
            f"{constants.DEPOSIT_MULTIPLE_BASE * 5}（5倍）等。"
        )
    try:
        user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
        user_data = user_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"个人账户读取失败~ \n"
            f"⚠️ 错误原因：读取\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    user_gold = user_data.get("coin", 0)
    if user_gold < amount:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"余额不足，无法完成存款~ 😔\n"
            f"📊 当前账户：{user_gold} 个\n"
            f"🎯 拟存款金额：{amount} 个\n"
            f"📝 差额提示：还差 {amount - user_gold} 个金币\n"
            f"💪 建议：先通过任务或交易赚取更多金币后再尝试哦~"
        )
    # 业务逻辑：更新用户余额与银行存款
    new_gold = user_gold - amount
    try:
        user_manager.update_key(section=account, key="coin", value=new_gold)
        user_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"个人账户更新失败~ \n"
            f"⚠️ 错误原因：保存\n"
            f"💡 请联系管理员核查个人账户数据~"
        )
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        bank_data = bank_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"个人账户读取失败~ \n"
            f"⚠️ 错误原因：读取\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    user_deposit = bank_data.get("deposit", 0)
    new_deposit = user_deposit + amount
    try:
        bank_manager.update_key(section=account, key="deposit", value=new_deposit)
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"个人账户更新失败~ 银行账户已恢复\n"
            f"⚠️ 错误原因：保存\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    success_msg = (
        f"{constants.SUCCESS_PREFIX}\n"
        f"🎉 {user_name} 先生/女士，您的操作已成功！\n"
        f"⏰ 时间：{current_time}\n"
        f"💰 存入金额：{amount} 个金币\n"
        f"📉 个人账户：{new_gold} 个金币\n"
        f"🏦 银行账户：{new_deposit} 个金币\n"
        f"🌟 财富积累的每一步都值得记录！继续保持，未来的您一定会感谢现在努力的自己~ 💪"
    )
    return success_msg

def withdraw(account,user_name,msg,path) -> str:
    """
    取款
    :param account: 用户账号
    :param user_name:用户昵称
    :param msg:
    :param path:数据目录
    :return: 结果提示
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")  # 获取当前时间

    if not msg.startswith("取款 "):
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"取款格式应为：取款 [金额]（例：取款 {constants.DEPOSIT_MULTIPLE_BASE}）\n"
            f"✨ 温馨提示：金额需为{constants.DEPOSIT_MULTIPLE_BASE}的整数倍，"
            f"例如{constants.DEPOSIT_MULTIPLE_BASE}、{constants.DEPOSIT_MULTIPLE_BASE*5}等。"
        )
    parts = msg.split()
    if len(parts) < 2:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"信息不完整呢~ 请补充完整的取款金额\n"
            f"📝 示例：取款 {constants.DEPOSIT_MULTIPLE_BASE}（表示从银行取出{constants.DEPOSIT_MULTIPLE_BASE}金币）"
        )

    try:
        amount = int(parts[1])
    except ValueError:
        logger.error(f"取款错误金额{amount}")
        amount = 1

    if amount <= 0:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"金额不能为0或负数哦~ 请输入大于0的数值\n"
            f"💡 建议：至少取出{constants.DEPOSIT_MULTIPLE_BASE}金币（如：取款 {constants.DEPOSIT_MULTIPLE_BASE}）。"
        )
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"当前金额不符合要求呢~ 取款需为constants.DEPOSIT_MULTIPLE_BASE的整数倍\n"
            f"🔢 示例：{constants.DEPOSIT_MULTIPLE_BASE}（1倍）、"
            f"{constants.DEPOSIT_MULTIPLE_BASE*2}（2倍）、"
            f"{constants.DEPOSIT_MULTIPLE_BASE*5}（5倍）等。"
        )
    # ---------- 读取银行账户数据（含异常处理） ----------
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        bank_data: Dict[str, str] = bank_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"读取银行账户失败~ 请稍后再试\n"
            f"⚠️ 错误原因：读取"
        )
    bank_deposit = bank_data.get("deposit", 0)
    if bank_deposit < amount:
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"余额不足，无法完成取款~ 😔\n"
            f"📊 银行账户余额：{bank_deposit} 金币\n"
            f"🎯 本次拟取款金额：{amount} 金币\n"
            f"📝 差额提示：还差 {amount - bank_deposit} 金币\n"
            f"💪 建议：先存入更多金币到银行账户后再尝试取款哦~"
        )
    # ---------- 计算银行账户新余额（临时变量暂存，防事务失败） ----------
    new_deposit = bank_deposit - amount
    # ---------- 更新银行账户（含异常处理） ----------
    try:
        bank_manager.update_key(section=account, key="deposit", value=new_deposit)
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"银行账户更新失败~ 资金未变动\n"
            f"⚠️ 错误原因：保存\n"
            f"💡 请联系管理员核查数据~"
        )
    # ---------- 读取个人账户数据（含异常处理） ----------
    try:
        user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
        user_data: Dict[str, str] = user_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"个人账户读取失败~ 银行账户已恢复\n"
            f"⚠️ 错误原因：读取\n"
            f"💡 请联系管理员核查个人账户数据~"
        )
    # 计算个人账户新余额
    user_gold = user_data.get("coin", 0)
    new_gold = user_gold + amount
    # ---------- 更新个人账户（含异常处理） ----------
    try:
        user_manager.update_key(section=account, key="coin", value=new_gold)
        user_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return (
            f"{constants.ERROR_PREFIX}\n"
            f"个人账户更新失败~ 银行账户已恢复\n"
            f"⚠️ 错误原因：保存\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    success_msg = (
        f"{constants.SUCCESS_PREFIX}\n"
        f"🎉 {user_name} ，您的取款操作已成功！\n"
        f"⏰ 时间：{current_time}\n"
        f"💸 取出金额：{amount} 金币\n"
        f"🏦 银行账户：{new_deposit} 金币\n"
        f"💰 个人账户：{new_gold} 金币\n"
        f"🌟 资金灵活支配，合理规划每一笔金币，让财富为您创造更多可能~ 💼"
    )
    return success_msg

def loan(account,user_name,msg,path) -> str:
    """
    处理用户贷款请求，支持贷款申请并更新账户数据。

    :param account: 用户账号（INI 文件中的 Section 名称）
    :param user_name: 用户昵称（用于返回提示信息）
    :param msg: 用户输入的贷款请求消息（格式应为 "贷款 金额"）
    :param path: 数据目录路径（用于定位 Bank.data 文件）
    :return: 操作结果提示信息
    """

    if not msg.startswith("贷款 "):
        return f"{user_name}，贷款格式，请使用：贷款 金额（例：贷款 {constants.DEPOSIT_MULTIPLE_BASE}）"
    parts = msg.split()
    if len(parts) < 2:
        return f"{user_name}，格式不对哦~😢 正确姿势是：贷款 金额（例：贷款 {constants.DEPOSIT_MULTIPLE_BASE}）"
    try:
        amount = int(parts[1])
    except ValueError:
        return (f"{user_name}，金额必须是整数哦~😢 正确姿势是："
                f"贷款 {constants.DEPOSIT_MULTIPLE_BASE}/{constants.DEPOSIT_MULTIPLE_BASE*2}/..."
                f"（例：贷款 {constants.DEPOSIT_MULTIPLE_BASE}）")
    if amount <= 0:
        return f"{user_name}，贷款0个金币可不行~😜 至少贷款1个吧！"
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return f"{user_name}，金额需为{constants.DEPOSIT_MULTIPLE_BASE}的整数倍（例：{constants.DEPOSIT_MULTIPLE_BASE*2}）"

    # ---------- 读取账户数据 ----------
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        # 读取账户数据（若不存在则创建默认 Section）
        bank_data: Dict[str, str] = bank_manager.read_section(section=account, create_if_not_exists=True)
        # 解析字段（默认值处理 + 类型转换）
        current_loan = bank_data.get("loan", 0)
        bank_loan_time = bank_data.get("loan_time", 0)  # 最后一次贷款时间戳
        bank_deposit = bank_data.get("deposit", 0)
    except Exception as e:
        # 修复：捕获文件读取异常（如路径错误、权限不足）
        logger.info(str(e))
        return f"{user_name}，系统繁忙，请稍后再试！"

    # -------------------- 计算历史贷款利息 --------------------
    new_loan = current_loan  # 初始化为新贷款总额（后续累加利息和本次金额）
    now_time = time.time()
    if current_loan > 0 and bank_loan_time > 0:
        # 计算时间差（秒）：当前时间戳 - 最后一次贷款时间戳
        delta_seconds = Decimal(now_time) - Decimal(bank_loan_time)
        # 计算利息（年利率 × 本金 × 时间差秒数 / 一年的总秒数）
        # 公式：利息 = 本金 × (年利率 / 一年的总秒数) × 时间差秒数
        interest = (Decimal(current_loan) * constants.LOAN_ANNUAL_INTEREST_RATE * delta_seconds) / constants.SECONDS_PER_YEAR
        interest = interest.quantize(Decimal('1'), rounding=ROUND_HALF_UP)  # 四舍五入到整数
        new_loan += interest  # 本金+利息作为新本金
    # -------------------- 更新账户数据 --------------------
    new_loan += amount
    new_deposit = bank_deposit + amount

    # ---------- 保存数据并返回结果 ----------
    try:
        bank_manager.update_section_keys(
            section=account,
            data={
                "loan": new_loan,
                "loan_time": now_time,
                "deposit": new_deposit
            }
        )
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        # 问题修复：捕获数据保存异常
        logger.info(str(e))
        return f"{user_name}，贷款失败！请联系管理员。"

    return (
        f"{user_name}，贷款成功！\n"
        f"当前贷款：{new_loan}金币\n"
        f"本次贷款：{amount}金币"
    )

def repayment(account,user_name,msg,path) -> str:
    """
    处理用户还款请求（支持活期转贷款还款，精确计算贷款利息）。

    :param account: 用户账号（INI 文件 Section 名称）
    :param user_name: 用户昵称（用于提示信息）
    :param msg: 用户输入的还款请求消息（格式："还款 金额"）
    :param path: 数据目录路径（定位 Bank.data 文件）
    :return: 操作结果提示信息
    """
    # -------------------- 常量定义 --------------------
    if not msg.startswith("还款 "):
        f"{constants.ERROR_PREFIX}\n还款格式请使用：还款 金额（例：还款 {constants.DEPOSIT_MULTIPLE_BASE}）"
    parts = msg.split()
    if len(parts) < 2:
        return f"{constants.ERROR_PREFIX}\n格式不对哦~😢 正确姿势是：还款 金额（例：还款 {constants.DEPOSIT_MULTIPLE_BASE}）"
    try:
        amount = int(parts[1])
    except ValueError:
        return f"{constants.ERROR_PREFIX}\n金额必须是有效的整数（例：{constants.DEPOSIT_MULTIPLE_BASE}）"
    if amount <= 0:
        return f"{constants.ERROR_PREFIX}\n还款金额不能少于0金币！"
    try:
        user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
        user_data = user_manager.read_section(section=account, create_if_not_exists=True)
        user_gold = user_data.get("coin", 0)
    except Exception as e:
        logger.info(str(e))
        return f"{constants.ERROR_PREFIX}\n读取用户账户信息失败，请稍后再试。"

    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        bank_data: Dict[str, str] = bank_manager.read_section(section=account, create_if_not_exists=True)
        bank_loan = bank_data.get("loan", 0)
    except Exception as e:
        logger.info(str(e))
        return f"{constants.ERROR_PREFIX}\n读取银行贷款信息失败，请稍后再试。"

    if bank_loan == 0:
        return f"{user_name}你未有贷款项目，无需还款！"
    # -------------------- 计算贷款利息（直接使用秒数，精确到极小时间差） --------------------
    loan_time = bank_data.get("loan_time", 0)
    interest = Decimal('0')
    if loan_time > 0:
        # 计算时间差（秒）：当前时间戳 - 最后贷款时间戳（精确到微秒）
        now_time = time.time()  # 当前时间戳（浮点数，含微秒）
        delta_seconds = Decimal(now_time) - Decimal(loan_time)  # 转换为 Decimal 保留精度

        # 利息公式：本金 × 年利率 × 时间差（秒） / 一年的总秒数
        # 公式推导：年利息 = 本金 × 年利率 → 日利息 = 年利息 / 365 → 秒利息 = 日利息 / 86400
        # 等价于：秒利息 = 本金 × 年利率 × 秒差 / (365×86400) = 本金 × 年利率 × 秒差 / SECONDS_PER_YEAR
        interest = (Decimal(bank_loan) * constants.LOAN_ANNUAL_INTEREST_RATE * delta_seconds) / constants.SECONDS_PER_YEAR

        # 四舍五入到整数（金币最小单位为 1）
        interest = interest.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        bank_loan += interest
    # -------------------- 校验还款金额是否足够 --------------------
    if amount < bank_loan:
        return (
            f"{constants.ERROR_PREFIX}\n还款金额不足！\n"
            f"当前需还款：{bank_loan}金币（本金 + 利息）\n"
            f"请至少还款{bank_loan}金币。"
        )
    new_gold = user_gold - amount
    try:
        user_manager.update_key(section=account, key="coin", value=new_gold)
        user_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return f"{constants.ERROR_PREFIX}\n用户活期余额更新失败，资金未变动。"

    new_loan = bank_loan - amount
    try:
        bank_manager.update_section_keys(section=account, data={
            "loan": new_loan,
            "loan_time": 0
        })
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return f"{constants.ERROR_PREFIX}\n银行贷款信息更新失败，资金未变动。"

    # -------------------- 返回结果（清晰透明） --------------------
    # 复利  年利息 = 本金 × 年利率→ 秒利息 = 年利息 / 一年总秒数→ 总利息 = 本金 × 年利率 × 时间差秒数 / 一年总秒数。
    return f"{constants.SUCCESS_PREFIX}\n{user_name}\n已还：{amount}金币\n剩余本金：{new_loan}金币"

def fixed_deposit(account,user_name,msg,path) -> str:
    """
    处理用户存定期请求（支持活期转定期，记录存入时间与期限）。

    :param account: 用户账号（INI 文件 Section 名称）
    :param user_name: 用户昵称（用于提示信息）
    :param msg: 用户输入的存定期请求消息（格式："存定期 金额"）
    :param path: 数据目录路径（定位 Bank.data 文件）
    :return: 操作结果提示信息
    """
    if not msg.startswith("存定期 "):
        return (f"{user_name}，存定期格式请使用：存定期 金额"
                f"（例：存定期 {constants.FIXED_DEPOSIT_MULTIPLE_BASE}）")
    parts = msg.split()
    if len(parts) < 2:
        return f"{user_name}，格式不对哦~😢 正确姿势是：存定期 金额（例：存定期 {constants.FIXED_DEPOSIT_MULTIPLE_BASE}）"
    try:
        amount = int(parts[1])
    except ValueError:
        return (f"{user_name}，金额必须是整数哦~😢 "
                f"正确姿势是：存定期 {constants.FIXED_DEPOSIT_MULTIPLE_BASE}/{constants.FIXED_DEPOSIT_MULTIPLE_BASE*2}/..."
                f"（例：存定期 {constants.FIXED_DEPOSIT_MULTIPLE_BASE}）")
    if amount <= 0:
        return "存定期0个金币可不行~😜 至少存定期1个吧！"
    if amount % constants.FIXED_DEPOSIT_MULTIPLE_BASE != 0:
        return f"{user_name}，存定期金额必须是{constants.FIXED_DEPOSIT_MULTIPLE_BASE}的整数倍哦~😢 "
    # -------------------- 读取账户数据（含异常处理） --------------------
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        bank_data = bank_manager.read_section(section=account, create_if_not_exists=True)
        # 读取字段（默认值处理）
        current_fixed_deposit = bank_data.get("fixed_deposit", 0)  # 当前定期存款总额
        current_deposit = bank_data.get("deposit", 0)  # 当前活期存款余额
        # last_fixed_date = bank_data.get("fixed_deposit_date", "1970-01-01")  # 上次定期存入日期（用于续存判断）
    except Exception as e:
        logger.info(str(e))
        return f"{user_name}，系统繁忙，请稍后再试！"
    # -------------------- 业务逻辑校验 --------------------
    # 校验1：存在未到期的定期存款（未取出的定期）
    if current_fixed_deposit > 0:
        # 可选：检查是否到期（假设定期期限为1年，可根据业务调整）
        # 若已到期，允许覆盖（自动取出旧定期并存入新定期）
        # 这里简化为强制要求先取定期（根据原始需求）
        return f"{user_name}，尚有未到期的定期存款{current_fixed_deposit}金币，请先发送[取定期]取出后再操作！"
    # 校验2：活期存款不足
    if current_deposit < amount:
        return f"{user_name}，活期存款不足（当前仅{current_deposit}金币），请先存款后再操作！"
    new_deposit = current_deposit - amount
    new_fixed_deposit = current_fixed_deposit + amount
    new_fixed_deposit_date = datetime.now().strftime("%Y-%m-%d")
    # -------------------- 执行存定期操作 --------------------
    try:
        bank_manager.update_section_keys(section=account, data={"deposit": new_deposit,
                                                                "fixed_deposit": new_fixed_deposit,
                                                                "fixed_deposit_date": new_fixed_deposit_date})
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return f"{user_name}，存定期失败！请联系管理员。（错误原因：保存）"

    # -------------------- 返回结果 --------------------
    return (
        f"{user_name}，存定期成功！\n"
        f"存入金额：{amount}金币\n"
        f"定期年利率：{constants.FIXED_DEPOSIT_ANNUAL_INTEREST_RATE * 100}%\n"
        f"存入日期：{new_fixed_deposit_date}\n"
        f"当前活期余额：{new_deposit} 金币\n"
        f"当前定期总额：{new_fixed_deposit} 金币\n"
        f"预计每日利息：{(Decimal(new_fixed_deposit) * Decimal(constants.FIXED_DEPOSIT_ANNUAL_INTEREST_RATE)
            / Decimal('360') * Decimal("1")
           ).quantize(Decimal('1'), rounding=ROUND_HALF_UP)} 金币"
    )

def redeem_fixed_deposit(account,user_name,path) -> str:
    """
     处理用户取定期请求（连本带息转入活期，需定期已到期）。

     :param account: 用户账号（INI 文件 Section 名称）
     :param user_name: 用户昵称（用于提示信息）
     :param path: 数据目录路径（定位 Bank.data 文件）
     :return: 操作结果提示信息
     """
    # -------------------- 读取账户数据（含类型校验） --------------------
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        bank_data: Dict[str, str] = bank_manager.read_section(section=account, create_if_not_exists=True)
        current_deposit = bank_data.get("deposit", 0)
        current_fixed_deposit  = bank_data.get("fixed_deposit", 0)
        fixed_deposit_date = bank_data.get("fixed_deposit_date", "1970-01-01")
    except Exception as e:
        logger.info(str(e))
        # 生产环境应记录日志（如 logging.error）
        return f"{user_name}，系统繁忙，请稍后再试！"
    # -------------------- 业务逻辑校验（核心） --------------------
    # 校验1：无未到期定期存款
    if current_fixed_deposit == 0:
        return f"{user_name}，尚未有定期存款项目！"
    # 计算利息（连本带息）
    # 存期天数 = 当前时间 - 存入日期
    now_date = datetime.now().strftime("%Y-%m-%d")
    delta_days = calculate_delta_days(now_date, fixed_deposit_date)
    interest = (Decimal(current_fixed_deposit) * Decimal(constants.FIXED_DEPOSIT_ANNUAL_INTEREST_RATE)
            / Decimal('360') * Decimal(delta_days)
           ).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    new_deposit = current_deposit + current_fixed_deposit + interest
    try:
        bank_manager.update_section_keys(section=account, data={"deposit": new_deposit,
                                                                "fixed_deposit": 0,
                                                                "fixed_deposit_date":"1970-01-01"})
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.info(str(e))
        return f"{user_name}，取定期失败！请联系管理员。"
    # -------------------- 返回结果 --------------------\
    # 利息 = 本金 × 年利率 ÷ 365 × 存期天数
    return (
        f"{user_name}，取定期成功！\n"
        f"取出本金：{current_fixed_deposit}金币\n"
        f"获得利息：{interest}金币\n"
        f"当前活期余额：{new_deposit}金币"
    )

def check_deposit(account,user_name,path) -> str:
    """
     处理用户查存款请求

     :param account: 用户账号（INI 文件 Section 名称）
     :param user_name: 用户昵称（用于提示信息）
     :param path: 数据目录路径（定位 Bank.data 文件）
     :return: 操作结果提示信息
     """
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        bank_data = bank_manager.read_section(section=account, create_if_not_exists=True)
    except Exception as e:
        logger.error(f"查询存款失败（账号：{account}）: {str(e)}")
        return f"{user_name}，系统繁忙，请稍后再试~😢"
    current_deposit = bank_data.get("deposit", 0)
    current_loan = bank_data.get("loan", 0)
    bank_loan_time = bank_data.get("loan_time", 0)
    current_fixed_deposit = bank_data.get("fixed_deposit", 0)
    # 计算贷款
    if current_loan > 0 and bank_loan_time > 0:
        # 计算时间差（秒）：当前时间戳 - 最后贷款时间戳（精确到微秒）
        now_time = time.time()  # 当前时间戳（浮点数，含微秒）
        delta_seconds = Decimal(now_time) - Decimal(bank_loan_time)  # 转换为 Decimal 保留精度

        # 利息公式：本金 × 年利率 × 时间差秒数 / 一年总秒数
        interest = (Decimal(current_loan)
                    * constants.LOAN_ANNUAL_INTEREST_RATE
                    * delta_seconds
                   ) / constants.SECONDS_PER_YEAR
        interest = interest.quantize(Decimal('1'), rounding=ROUND_HALF_UP)  # 四舍五入到整数
        current_loan += interest

    # -------------------- 优化提示信息 --------------------
    # 友好开头
    result_msg = [f"📊 {user_name}，您的账户信息查询结果：", f"✅ 活期存款：{current_deposit} 金币",
                  f"💰 当前贷款：{current_loan} 金币", f"📅 定期存款：{current_fixed_deposit} 金币",
                  "如有任何疑问，欢迎随时联系客服小助手~❤️"]

    return "\n".join(result_msg)

def transfer(account,user_name,msg,path) -> str:
    """
    转账功能
    :param account: 发送者账户（INI文件中的section名）
    :param user_name: 发送者用户名（用于日志/反馈）
    :param msg: 用户输入消息（格式：转账 金额@接收者账户）
    :param path: 项目根路径（用于定位Bank.data）
    :return: 转账结果提示（含详细信息）
    """
    # -------------------- 1. 输入格式校验（修正正则匹配） --------------------
    if not msg.startswith("转账 "):
        return f"❌ 转账正确格式：转账 金额@对象（示例：转账 {constants.DEPOSIT_MULTIPLE_BASE}@小梦）"
    amount,target_qq=get_by_qq(msg)
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return f"{user_name}，存定期金额必须是{constants.DEPOSIT_MULTIPLE_BASE}的整数倍哦~😢 "
    if not target_qq:
        return "请确认转账对象！正确格式：转账 金额@对象（示例：转账 {constants.DEPOSIT_MULTIPLE_BASE}@小梦）"
    # -------------------- 2. 初始化INI文件管理器（含异常处理） --------------------
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        sender_data = bank_manager.read_section(section=account, create_if_not_exists=True)
        receiver_data = bank_manager.read_section(section=target_qq, create_if_not_exists=True)
    except Exception as e:
        logger.error(f"初始化INI文件管理器失败：{str(e)}")
        return "❌ 系统错误：无法加载账户数据，请联系管理员"

    # -------------------- 5. 校验余额是否充足（含手续费） --------------------
    # 实际需扣除的总金额 = 转账金额 + 手续费（手续费从发送者余额中扣除）
    total_deduction = amount * (1 + constants.TRANSFER_PROCESSING_FEE_RATE)
    sender_deposit = sender_data.get("deposit", 0)
    receiver_deposit = receiver_data.get("deposit", 0)
    if sender_deposit < total_deduction:
        return (
            f"❌ 转账失败。余额不足（当前余额：{sender_deposit}，需扣除：{total_deduction}）\n"
            f"（转账金额：{amount}，手续费率：{constants.TRANSFER_PROCESSING_FEE_RATE * 100}%）"
        )

    # -------------------- 6. 执行转账操作 --------------------
    # 计算新余额（INI值为整数，直接运算）
    sender_new_deposit = sender_deposit - total_deduction
    receiver_new_deposit = receiver_deposit + amount
    try:
        bank_manager.update_key(section=account, key="deposit", value=sender_new_deposit)
        bank_manager.update_key(section=target_qq, key="deposit", value=receiver_new_deposit)
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.error(f"转账操作失败（发送者：{account}，接收者：{target_qq}）：{str(e)}")
        return f"❌ 系统错误：转账操作失败!"
    # -------------------- 7. 返回详细成功信息（用户友好） --------------------
    return (
        f"✅ 转账成功！\n"
        f"发送者：{user_name}\n"
        f"接收者：{target_qq}\n"
        f"转账金额：{amount}\n"
        f"手续费（{constants.TRANSFER_PROCESSING_FEE_RATE * 100}%）：{amount * constants.TRANSFER_PROCESSING_FEE_RATE}金币\n"
        f"发送者原余额：{sender_deposit} → 新余额：{sender_new_deposit} 金币\n"
        f"接收者原余额：{receiver_deposit} → 新余额：{receiver_new_deposit} 金币"
    )