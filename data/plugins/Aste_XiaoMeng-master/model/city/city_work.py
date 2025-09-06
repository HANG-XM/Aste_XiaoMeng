from astrbot.api import logger

from model.data_managers import JobFileHandler,IniFileReader
from model.city_func import is_arabic_digit, format_salary
from model import constants

from collections import defaultdict
import math
import random
import time
from typing import Dict, List, Tuple
from datetime import datetime

def work_menu() -> str:
    """
    构建并返回打工系统主菜单字符串，包含基础操作、工作管理、进阶操作等分组说明。
    :return: 菜单文本
    """
    # ---------------------- 菜单内容定义 ----------------------
    welcome_msg = "📌 欢迎使用【打工助手】\n——————————————\n"

    # 用字典定义操作（键：显示名称，值：功能说明）
    operations = {
        "打工": "开始当前工作计时",
        "找工作": "查看最新招聘岗位",
        "加班": "延长当前工作时间",
        "领工资": "领取当前工作报酬",
        "辞职": "解除当前工作绑定",
        "查工作": "查看工作具体详情",
        "跳槽": "晋升更高的职位",
        "投简历": "向岗位投递简历",
        "工作池": "查当前所有工作"
    }

    menu_lines = []

    # 按功能分组展示（模拟分类菜单）
    menu_groups = [
        ("基础操作", ["打工", "找工作", "查工作"]),
        ("工作管理", ["加班", "领工资", "辞职"]),
        ("进阶操作", ["跳槽", "投简历", "工作池"])
    ]

    for group_name, ops in menu_groups:
        menu_lines.append(f"🔹 {group_name}：")
        for op in ops:
            desc = operations[op]
            menu_lines.append(f"  ▶ {op.ljust(6)} {desc}")  # 对齐排版

    menu_lines.append("——————————————\n 输入对应关键词即可操作")
    return f"{welcome_msg}{"\n".join(menu_lines)}"

def work(account,user_name,path,job_manager:JobFileHandler)->str:
    """
    执行打工操作：校验用户是否有工作、体力是否足够、是否已打工，更新打工状态和体力。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据根路径
    :param job_manager: 职位数据管理器
    :return: 操作结果提示文本
    """
    """
    'job_id': target_job_id,
    'job_name': job_detail['jobName'],
    'join_date': today,
    'work_date': '1970-01-01',
    'work_time': 0,
    'work_count': 0, 
    'overtime_count': 0,
    'hop_date': 0,
    "submit_date": 1970-01-01,
    "submit_count": 0
    """
    try:
        work_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Work.data",
            encoding="utf-8"
        )
        work_data = work_manager.read_section(account, create_if_not_exists=True) or {}
    except Exception as e:
        logger.error(f"打工读取错误：{str(e)}")
        return "系统繁忙，请稍后重试"

    job_id = work_data.get("job_id", 0)
    job_name = work_data.get("job_name")
    if job_id == 0 or job_name == "":
        # 没有工作
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)

    job_data = job_manager.get_job_info(str(job_id))
    if not job_data:
        # 工作数据异常
        _work_clear(account, work_manager)
        return random.choice(constants.WORK_ERROR_TEXTS)(job_name)

    job_stamina = job_data.get("physicalConsumption",0)

    user_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8"
    )
    user_stamina = user_manager.read_key(section=account, key="stamina",default=0)
    if job_stamina > user_stamina:
        return "体力不足，无法进行[打工]！"
    work_date = datetime.strptime(work_data.get("work_date", "1970-01-01"), "%Y-%m-%d").date()
    now_date = datetime.now().date()
    if work_date != now_date:
        # clear work_time，overtime_count
        work_manager.update_section_keys(account, {
            "work_date": now_date.strftime("%Y-%m-%d"),
            "work_time": 0,
            "work_count": 0,
            "overtime_count": 0
        })
        work_time = 0
        work_count = 0
    else:
        work_time = work_data.get("work_time", 0)
        work_count = work_data.get("work_count", 0)

    # 获取现在时间戳
    now_time = time.time()
    if work_time == 0:
        if work_count == 0:
            # 记录打工
            work_manager.update_section_keys(account, {
                "work_time": now_time,
                "work_count": 1
            })
            work_manager.save(encoding="utf-8")
            # 消耗体力
            new_stamina = user_stamina - job_stamina
            user_manager.update_key(section=account, key="stamina", value=new_stamina)
            user_manager.save(encoding="utf-8")
            return random.choice(constants.WORK_START_WORK_TEXTS)(user_name,job_name)
        else:
            # 今日已经打工，无需再次打工
            return random.choice(constants.WORK_OVER_TEXTS)(user_name,job_name)
    else:
        if work_time + constants.WORK_DURATION_SECONDS <= now_time:
            # 打工完成！
            return random.choice(constants.WORK_REWARD_READY_TEXTS)(user_name,job_name)

        remaining = work_time + constants.WORK_DURATION_SECONDS - now_time
        minutes = math.ceil(remaining / 60)
        return random.choice(constants.WORK_WORKING_TEXTS)(user_name,job_name,minutes)

def overwork(account,user_name,path,job_manager:JobFileHandler)->str:
    """
    执行加班操作：校验用户是否有工作、体力是否足够、是否已打工，更新加班状态和体力。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据根路径
    :param job_manager: 职位数据管理器
    :return: 操作结果提示文本
    """
    # ---------------------- 初始化数据管理器 ----------------------
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    work_data: Dict[str, str] = work_manager.read_section(account, create_if_not_exists=True) or {}
    # ---------------------- 检查是否拥有有效工作 ----------------------
    job_id = work_data.get("job_id",0)
    job_name = work_data.get("job_name","")
    if job_id == 0 or job_name == "":
        # 没有工作
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)
    # ---------------------- 获取当前工作信息 ----------------------
    job_data = job_manager.get_job_info(str(job_id))
    if not job_data:
        # 清除异常工作数据并提示
        _work_clear(account, work_manager)
        return random.choice(constants.WORK_ERROR_TEXTS)(job_name)
    job_stamina = job_data.get("physicalConsumption", 0)
    user_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8"
    )
    user_stamina = user_manager.read_key(section=account, key="stamina",default=0)
    if user_stamina < job_stamina:
        return "体力不足，请获取体力再[加班]吧！"

    work_date = datetime.strptime(work_data.get("work_date", "1970-01-01"), "%Y-%m-%d").date()
    if work_date != datetime.now().date():
        # 提示开始打工而不是加班
        return random.choice(constants.WORK_DATE_RESET_TIPS)(user_name)

    # ---------------------- 处理加班逻辑 ----------------------
    overtime_count = work_data.get("overtime_count", 0)
    work_time = work_data.get("work_time", 0)
    # 获取现在时间戳
    now_time = time.time()

    if work_time == 0:
        # 未开始加班
        overtime_count += 1
        work_manager.update_section_keys(account, {
            "work_time": now_time,
            "overtime_count": overtime_count
        })
        work_manager.save(encoding="utf-8")
        new_stamina = user_stamina - job_stamina
        user_manager.update_key(section=account,key="stamina",value=new_stamina)
        user_manager.save(encoding="utf-8")
        return random.choice(constants.WORK_START_WORKOVER_TEXTS(user_name,job_name))  # 随机选择未开始提示
    else:
        # 已开始加班：计算当前状态
        now_time = time.time()
        if work_time + constants.WORK_DURATION_SECONDS <= now_time:
            return random.choice(constants.WORK_REWARD_READY_TEXTS)(user_name,job_name)  # 随机选择可领工资提示
        else:
            remaining = work_time + constants.WORK_DURATION_SECONDS - now_time
            minutes = math.ceil(remaining / 60)
            return random.choice(constants.WORK_WORKING_TEXTS)(user_name,job_name,minutes)

def job_hunting(msg: str,job_manager:JobFileHandler) -> str:
    """
    查询招聘市场职位列表，支持分页显示，展示职位ID、名称、薪资、晋升次数、要求等信息。
    :param msg: 用户输入消息（可包含页码）
    :param job_manager: 职位数据管理器
    :return: 招聘市场文本
    """
    # -------------------- 数据校验与预处理 --------------------
    if not job_manager.data:
        return "⚠️ 职位数据库为空，请联系管理员初始化数据！"

    # -------------------- 收集所有有效职位ID（按数字升序排序） --------------------
    all_jobs = []
    # 按series_key的数字顺序遍历（如"20"→"30"→"40"）
    for series_key in sorted(job_manager.data.keys(), key=lambda x: int(x)):
        # 按job_id的数字顺序遍历（如"2000"→"2001"→"2002"）
        for job_id_str in sorted(job_manager.data[series_key].keys(), key=lambda x: int(x)):
            if len(job_id_str) == 4 and job_id_str.isdigit():
                all_jobs.append(job_id_str)

    # -------------------- 分页逻辑处理（修正输入解析） --------------------
    page_size = constants.JOB_HUNTING_PAGE_SIZE
    total_pages = (len(all_jobs) + page_size - 1) // page_size
    current_page = 1  # 默认第一页

    # 提取用户输入的页码（支持"找工作 2"或"找工作 第2页"格式）
    import re
    page_match = re.search(r'\d+', msg)  # 匹配任意位置的数字
    if page_match:
        try:
            current_page = int(page_match.group())
            current_page = max(1, min(current_page, total_pages))  # 限制在有效页码范围
        except ValueError:
            pass  # 无效数字则保持默认

    # -------------------- 构建输出内容 --------------------
    output_lines = ["★★★★ 招聘市场 ★★★★"]
    for job_id_str in all_jobs[(current_page-1)*page_size : current_page*page_size]:
        try:
            job_details = job_manager.get_job_info(job_id_str)
            base_salary = job_details["baseSalary"]
            salary_low = round(base_salary * 0.8, 1)
            salary_high = round(base_salary * 1.2, 1)
            salary_display = f"{salary_low/1000:.1f}k-{salary_high/1000:.1f}k"

            promotion_count = job_manager.get_promote_num(job_id_str)  # 假设该方法存在

            job_entry = (
                f"ID {job_id_str}\n"
                f"职业 {job_details['jobName']}\n"
                f"薪金 {salary_display} {promotion_count}晋升\n"
                f"要求 经验{job_details['recruitRequirements']['experience']} 魅力{job_details['recruitRequirements']['charm']}\n"
                "----"
            )
            output_lines.append(job_entry)

        except KeyError as e:
            print(f"警告：职位 {job_id_str} 数据缺失，跳过显示。错误详情：{e}")
            continue
        except Exception as e:
            print(f"警告：处理职位 {job_id_str} 时发生异常，跳过显示。错误详情：{e}")
            continue

    # -------------------- 生成分页导航 --------------------
    pagination_info = (
        f"\n---------第{current_page}/{total_pages}页---------"
        f"\n'找工作 X' '查工作 X' 查询"
    )

    return "\n".join(output_lines) + pagination_info

def job_hopping(account,user_name,path,job_manager:JobFileHandler) -> str:
    """
    执行跳槽操作：校验用户是否满足晋升条件，扣除金币，更新为下一级职位。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据根路径
    :param job_manager: 职位数据管理器
    :return: 操作结果提示文本
    """
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    work_data = work_manager.read_section(account, create_if_not_exists=True)
    job_id = work_data.get("job_id",0)
    job_name = work_data.get("job_name",None)
    if job_id == 0 or not job_name:
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)

    # 检测今日跳槽
    today_str = datetime.today().strftime("%Y-%m-%d")
    job_hop_date = work_data.get("hop_date")
    if job_hop_date == today_str:
        return random.choice(constants.JOB_HOPPING_LIMIT_TEXTS)(user_name)  # 随机选择今日限制提示

    work_manager.update_key(section=account, key='hop_date', value=today_str)
    work_manager.save(encoding="utf-8")

    next_job_data = job_manager.get_next_job_info(str(job_id))
    if not next_job_data:
        return random.choice(constants.JOB_HOPPING_MAX_POSITION_TEXTS)(user_name)

    user_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8"
    )
    user_data = user_manager.read_section(account, create_if_not_exists=True)

    # 提取职位要求和用户属性（避免KeyError）
    next_req = next_job_data.get("recruitRequirements", {})
    user_level = user_data.get("level", 0)
    user_exp = user_data.get("exp", 0)
    user_coin = user_data.get("coin", 0)
    user_charm = user_data.get("charm", 0)

    req_level = next_req.get("level", 0)
    req_exp = next_req.get("experience", 0)
    req_gold = next_req.get("gold", 0)
    req_charm = next_req.get("charm", 0)

    if (req_level < user_level and
            req_exp < user_exp and
            req_gold <= user_coin and  # 确保金币足够支付
            req_charm < user_charm):
        work_manager.update_section_keys(
            section=account,
            data={
            "job_id": next_job_data.get("jobid"),
            "job_name": next_job_data.get("jobName"),
            "join_date": today_str
        }
        )
        # 扣除金币并保存
        new_coin = user_coin - req_gold
        user_manager.update_key(section=account,key="coin",value=new_coin)
        user_manager.save(encoding="utf-8")
        work_manager.save(encoding="utf-8")
        return random.choice(constants.JOB_HOPPING_SUCCESS_TEXTS)(user_name)  # 随机选择成功提示
    return random.choice(constants.JOB_HOPPING_FAILED_TEXTS)(user_name) # 随机选择失败提示

def get_paid(account,user_name,path,job_manager:JobFileHandler) -> str:
    """
    领取工资：校验打工是否完成，发放工资，重置打工状态。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据根路径
    :param job_manager: 职位数据管理器
    :return: 操作结果提示文本
    """
    # ---------------------- 初始化数据管理器 ----------------------
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    # ---------------------- 检查是否拥有有效工作 ----------------------
    work_data = work_manager.read_section(account, create_if_not_exists=True)
    job_id = work_data.get("job_id",0)
    if job_id == 0:
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)  # 随机选择无工作提示
    # ---------------------- 获取职位信息（含错误处理） ----------------------
    job_data = job_manager.get_job_info(str(job_id))
    if not job_data:
        # 工作数据异常
        _work_clear(account, work_manager)
        return random.choice(constants.WORK_ERROR_TEXTS)  # 随机选择信息错误提示
    # ---------------------- 检查是否已开始工作 ----------------------
    work_time = work_data.get("work_time", 0)
    if work_time == 0:
        return random.choice(constants.WORK_DATE_RESET_TIPS)  # 随机选择未开始提示
    now_time = time.time()
    required_time = work_time + constants.WORK_DURATION_SECONDS  # 预计完成时间戳（秒）
    if now_time < required_time:
        # 计算剩余时间（分钟）和进度百分比
        remaining_minutes = int(required_time - now_time // 60)
        return random.choice(constants.WORK_WORKING_TEXTS)(user_name,remaining_minutes)
    # ---------------------- 计算用户当前金币并更新 ----------------------
    user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
    current_coin = user_manager.read_key(section=account,key="coin",default=0)
    job_salary = job_data["baseSalary"]

    new_coin = current_coin + job_salary
    user_manager.update_key(section=account, key="coin", value=new_coin)
    user_manager.save(encoding="utf-8")

    # ---------------------- 重置工作时间并保存 ----------------------
    work_manager.update_key(section=account, key="work_time", value="0")  # 明确存储为字符串
    work_manager.save(encoding="utf-8")

    # ------------------------- 成功提示 -------------------------
    return random.choice(constants.GET_PAID_SUCCESS_TEXTS)(user_name,job_salary)

def resign(account,user_name,path,job_manager:JobFileHandler) -> str:
    """
    执行辞职操作：校验金币是否足够支付赔偿金，扣除金币，清除工作数据。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据根路径
    :param job_manager: 职位数据管理器
    :return: 操作结果提示文本
    """
    # ---------------------- 初始化数据管理器 ----------------------
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    # ---------------------- 检查是否拥有有效工作 ----------------------
    work_data = work_manager.read_section(account, create_if_not_exists=True) or {}
    job_id = work_data.get("job_id",0)
    job_name = work_data.get("job_name",None)
    # 严格检查工作有效性（排除0、空字符串等情况）
    if job_id == 0 or not job_name:
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)  # 随机选择无工作提示
    # ---------------------- 获取当前工作信息 ----------------------
    job_data = job_manager.get_job_info(str(job_id))
    if not job_data:
        # 清除异常工作数据并提示
        _work_clear(account, work_manager)
        return random.choice(constants.WORK_ERROR_TEXTS)(user_name)  # 随机选择工作异常提示

    # ---------------------- 计算辞职赔偿金额 ----------------------
    resign_gold = job_data.get("baseSalary", 0)
    # ---------------------- 检查用户金币是否足够 ----------------------
    user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
    user_gold = user_manager.read_key(section=account,key="coin",default=0)
    if user_gold < resign_gold:
        return random.choice(constants.RESIGN_NOT_ENOUGH_TEXTS)(user_name,resign_gold, user_gold)
    # ---------------------- 执行辞职操作 ----------------------
    new_coin = user_gold - resign_gold
    user_manager.update_key(account, "coin", new_coin)
    user_manager.save(encoding="utf-8")
    # 清除工作数据
    _work_clear(account, work_manager)
    work_manager.save(encoding="utf-8")
    # ---------------------- 返回成功提示 ----------------------
    return random.choice(constants.RESIGN_SUCCESS_TEXTS)(user_name, resign_gold, user_gold)

def check_job(msg,job_manager:JobFileHandler) -> str:
    """
    查询指定职位的详细信息，支持通过ID或名称查询，返回格式化职位详情。
    :param msg: 用户输入消息（如"查工作 2000"）
    :param job_manager: 职位数据管理器
    :return: 职位详情文本
    """
    # 步骤1：解析输入消息，提取目标ID
    if not msg.startswith("查工作 "):
        return "请使用格式：查工作 [职位ID]（如：查工作 2000）"

    parts = msg.strip().split(maxsplit=1)  # 最多分割1次，避免长名字被截断
    if len(parts) < 2:
        return "请使用格式：查工作 [职位ID]（如：查工作 2000）"
    # 提取ID
    target_id = parts[1]

    # 步骤2：初始化职位管理器（需根据实际项目路径调整参数）
        # 参数传入
    # 步骤3：查询职位详情
    if is_arabic_digit(target_id):
        # 数字ID
        job_detail = job_manager.get_job_info(str(target_id))

        if not job_detail:
            return f"未找到ID为 {target_id} 的职位信息，请检测该ID是否存在！"
        # 步骤4：提取并格式化各字段
        # 基础信息
        job_name = job_detail["jobName"]
        salary_str = format_salary(job_detail["baseSalary"])

        # 招聘要求（包含基础要求和体力）
        req = job_detail["recruitRequirements"]
        physical = job_detail["physicalConsumption"]
        req_str = f"等级{req['level']} 经验{req['experience']} 魅力{req['charm']}"

        # 晋升链（通过管理器方法获取完整链）
        promotion_chain = '→'.join(job_manager.get_promote_chain(target_id))

        # 职位描述
        description = job_detail["description"]

        # 步骤5：组合输出（严格按示例格式）
        return (f"ID: {target_id}\n"
                f"所属：{job_detail['company']}\n"
                f"工名：{job_name}\n"
                f"工资：{salary_str}\n"
                f"体耗：{physical}点\n"
                f"要求：{req_str}\n"
                f"晋升链：{promotion_chain}\n"
                f"内容：{description}\n"
                f"应聘：投简历 {target_id}")
    else:
        # 职位名
        job_details = job_manager.get_job_info_ex(target_id)
        more_jobs = ','.join([job["jobName"] for job in job_details[:3]])
        job_detail = job_details[0]

        if not job_detail:
            return f"未找到ID为 {target_id} 的职位信息，请检测该ID是否存在！"

        # 步骤4：提取并格式化各字段
        # 基础信息
        job_name = job_detail["jobName"]
        salary_str = format_salary(job_detail["baseSalary"])

        # 招聘要求（包含基础要求和体力）
        req = job_detail["recruitRequirements"]
        physical = job_detail["physicalConsumption"]
        req_str = f"等级{req['level']} 经验{req['experience']} 魅力{req['charm']}"

        # 职位描述
        description = job_detail["description"]

        # 步骤5：组合输出（严格按示例格式）
        return (f"ID: {job_detail['jobid']}\n"
                        f"所属：{job_detail['company']}\n"
                        f"工名：{job_name}\n"
                        f"工资：{salary_str}\n"
                        f"体耗：{physical}点\n"
                        f"要求：{req_str}\n"
                        f"内容：{description}\n"
                        f"应聘：投简历 {job_detail['jobid']}\n"
                        f"相似职位：{more_jobs}")

def jobs_pool(msg: str,job_manager:JobFileHandler) -> str:
    """
    展示所有职位信息，支持公司概览、分页、按公司名筛选三种模式。
    :param msg: 用户输入消息（如"工作池"、"工作池 1"、"工作池 腾讯"）
    :param job_manager: 职位数据管理器
    :return: 职位池文本
    """
    page_size = constants.JOBS_POOL_PAGE_SIZE  # 每页显示10条职位

    # ---------------------- 输入解析与校验 ----------------------
    parts = msg.strip().split()
    if not parts or parts[0] != "工作池":
        return "工作池请使用以下格式：\n- 工作池（查看所有职位概览）\n- 工作池 X（分页查看所有职位，X为页码）\n- 工作池 公司名（查看指定公司所有职位）"

    args = parts[1:]  # 去除开头的"工作池"

    # ---------------------- 读取职位数据（含异常处理） ----------------------
    try:
        all_jobs = job_manager.get_all_jobs_and_companies()  # 获取原始职位数据
    except Exception as e:
        logger.error(f"读取职位数据失败：{str(e)}", exc_info=True)
        return "⚠️ 错误：无法读取职位数据，请稍后再试"

    # ---------------------- 模式一：无参数，显示所有职位概览 ----------------------
    if len(args) == 0:
        # 统计公司职位数
        company_job_counts: Dict[str, int] = defaultdict(int)
        for job in all_jobs:
            try:
                company = job["company"]
                company_job_counts[company] += 1
            except KeyError as e:
                logger.warning(f"跳过缺失字段 {e} 的职位：{job}")
                continue

        total_jobs = sum(company_job_counts.values())
        companies = list(company_job_counts.keys())
        company_count = len(companies)

        # 构建输出（添加符号，无空行）
        output_lines = ["★ 所有职位概览 ★"]
        if total_jobs == 0:
            output_lines.append("❌ 暂无职位数据")
        else:
            output_lines.append(f"▸ 总职位数：{total_jobs}")
            output_lines.append(f"▸ 公司总数：{company_count}")
            output_lines.append("▸ 公司列表（按名称排序）：")
            # 按公司名排序，确保输出顺序稳定
            for company in sorted(company_job_counts.keys()):
                output_lines.append(f"  - {company}（{company_job_counts[company]}职位）")
        # 统一添加分页提示（无论是否有数据）
        output_lines.append("工作池 X（分页查看职位，X为页码或公司名）")
        return '\n'.join(output_lines)

    # ---------------------- 模式二：数字参数，分页显示所有职位 ----------------------
    elif args[0].isdigit():
        current_page = int(args[0])
        if current_page < 1:
            return "⚠️ 错误：页码不能小于1"

        # 按公司分组并展开为全局职位列表（保留公司顺序）
        grouped_jobs: Dict[str, List[str]] = defaultdict(list)
        for job in all_jobs:
            try:
                company = job["company"]
                job_name = job["jobName"]
                grouped_jobs[company].append(job_name)
            except KeyError as e:
                logger.warning(f"跳过缺失字段 {e} 的职位：{job}")
                continue

        # 按公司名排序后展开为全局列表（确保分页顺序稳定）
        sorted_companies = sorted(grouped_jobs.keys())
        flattened_jobs: List[Tuple[str, str]] = []
        for company in sorted_companies:
            flattened_jobs.extend([(company, job) for job in grouped_jobs[company]])

        total_jobs = len(flattened_jobs)
        total_pages = (total_jobs + page_size - 1) // page_size if total_jobs > 0 else 0

        # 处理无职位或页码越界
        if total_jobs == 0:
            return "★ 所有职位分页 ★\n❌ 暂无职位数据"
        if current_page > total_pages:
            return f"⚠️ 错误：当前页码 {current_page} 超过总页数 {total_pages}"

        # 提取当前页数据并按公司分组
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        current_page_jobs = flattened_jobs[start_idx:end_idx]

        # 按公司分组当前页的职位（保留当前页公司出现顺序）
        page_companies: Dict[str, List[str]] = defaultdict(list)
        for company, job in current_page_jobs:
            page_companies[company].append(job)

        # 构建输出（添加符号，无空行）
        output_lines = [f"▶ 所有职位分页（第 {current_page} 页 / 共 {total_pages} 页，总职位数：{total_jobs}）"]
        for company in sorted(page_companies.keys()):  # 按当前页公司名排序
            jobs = page_companies[company]
            output_lines.append(f"◆ {company}：")
            output_lines.extend([f"  • {job}" for job in jobs])  # 职位前加•
        return '\n'.join(output_lines)

    # ---------------------- 模式三：公司名参数，显示该公司所有职位 ----------------------
    else:
        company_name = ' '.join(args)  # 合并参数为公司名（支持空格）

        # 筛选该公司下的所有职位
        company_jobs: List[str] = []
        for job in all_jobs:
            try:
                if job["company"] == company_name:
                    company_jobs.append(job["jobName"])
            except KeyError as e:
                logger.warning(f"跳过缺失字段 {e} 的职位：{job}")
                continue

        # 构建输出（添加符号，无空行）
        output_lines = [f"★ {company_name} 职位列表 ★"]
        if not company_jobs:
            output_lines.append("❌ 暂无相关职位数据")
        else:
            output_lines.append(f"（共 {len(company_jobs)} 个职位）")
            output_lines.extend([f"  • {job}" for job in company_jobs])  # 职位前加•
        return '\n'.join(output_lines)

def submit_resume(account,user_name,msg,path,job_manager:JobFileHandler) -> str:
    """
    投递简历：校验是否已有工作、每日投递次数、用户属性是否满足职位要求，更新工作和用户数据。
    :param account: 用户账号
    :param user_name: 用户昵称
    :param msg: 用户输入消息（如"投简历 2001"）
    :param path: 数据根路径
    :param job_manager: 职位数据管理器
    :return: 操作结果提示文本
    """
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    # ---------------------- 检查是否已有工作 ----------------------
    work_data = work_manager.read_section(account,create_if_not_exists=True)
    if work_data.get('job_id',0) != 0:
        return "想投简历却不知道怎么做～正确姿势是'投简历 X'，X是职位ID（比如'投简历 1001'），再来一次？"
    # ---------------------- 处理"投简历"指令引导 ----------------------
    if msg.strip() == "投简历":
        return "想投简历却不知道怎么做～正确姿势是'投简历 X'，X是职位ID（比如'投简历 1001'），再来一次？"
    # ---------------------- 解析目标职位ID ----------------------
    msg_parts = msg.strip().split(maxsplit=1)
    if len(msg_parts) < 2:
        return "投递格式有点小错误，正确姿势是'投简历 X'，X是职位ID（比如'投简历 1001'），再来一次？"
    target_job_id = msg_parts[1].strip()
    # ---------------------- 获取职位信息 ----------------------

    job_data = job_manager.get_job_info(target_job_id)
    if not job_data:# 未找到时候返回空字典{}
        return f"未找到ID为[{target_job_id}]的职位信息，可能是ID输入错误或岗位已下架～"
    # ---------------------- 特殊职位 ----------------------
    special_job = job_manager.get_last_n_job_ids(target_job_id)
    if target_job_id in special_job:
        return "该职位已经被内定，你无法通过投简历的方式被雇用！"

    # ---------------------- 处理每日投递次数限制 ----------------------
    today = datetime.now().date()
    last_submit_date = datetime.strptime(work_data.get('submit_date', '1970-01-01'), "%Y-%m-%d").date()
    if last_submit_date != today:
        # 新日期重置计数
        work_manager.update_section_keys(
            section=account,
            data={"submit_date": today.strftime("%Y-%m-%d"), "submit_count": 0}
        )
        work_manager.save(encoding="utf-8")
        current_submit_num = 0
    else:
        current_submit_num = work_data.get("submit_count", 0)

    # 检查当日投递上限
    if current_submit_num > constants.SUBMIT_RESUME_LIMIT:
        return random.choice(constants.SUBMIT_RESUME_LIMIT_TEXTS)(user_name,current_submit_num)

    # 计数+1
    current_submit_num += 1
    work_manager.update_key(section=account,key="submit_count", value=current_submit_num)
    work_manager.save(encoding="utf-8")

    # ---------------------- 读取用户数据并验证属性 ----------------------
    user_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8"
    )
    user_data: Dict[str, str] = user_manager.read_section(account, create_if_not_exists=True) or {}

    # 提取职位要求（带默认值防KeyError）
    req = job_data.get('recruitRequirements', {})
    req_level = int(req.get('level', 0))
    req_exp = int(req.get('experience', 0))
    req_gold = int(req.get('gold', 0))
    req_charm = int(req.get('charm', 0))
    job_name = job_data.get('jobName', '未知岗位')  # 防止职位名称缺失

    # 验证用户属性完整性（设置默认值防止缺失）
    user_stats = {
        'level': int(user_data.get('level', 0)),
        'exp': int(user_data.get('exp', 0)),
        'charm': int(user_data.get('charm', 0)),
        'coin': int(user_data.get('coin', 0))
    }
    # ---------------------- 验证是否符合要求 ----------------------
    condition_met = (
            user_stats['level'] >= req_level and
            user_stats['exp'] >= req_exp and
            user_stats['charm'] >= req_charm and
            user_stats['coin'] >= req_gold
    )
    if condition_met:
        # 扣除求职金币（确保金币非负）
        new_coin = max(user_stats['coin'] - req_gold, 0)
        new_exp = max(user_stats['exp'] - req_exp, 0)
        user_manager.update_section_keys(
            section=account,
            data={
                "coin": new_coin,
                "exp": new_exp,
            }
        )

        # 更新工作信息（重置工作统计）
        work_manager.update_section_keys(
            section=account,
            data={
                'job_id': target_job_id,
                'job_name': job_name,
                'join_date': today.strftime("%Y-%m-%d"),
                'work_date': '1970-01-01',
                'work_time': 0,
                'overtime_count': 0
            }
        )
        user_manager.save(encoding="utf-8")
        work_manager.save(encoding="utf-8")

        return random.choice(constants.SUBMIT_RESUME_SUCCESS_TEXTS)(user_name,job_name)

    return random.choice(constants.SUBMIT_RESUME_FAIL_TEXTS)(user_name,job_name,req_level,req_exp,req_charm,req_gold)

def _work_clear(account_id: str, manager: IniFileReader) -> None:
    """
    清除指定用户的工作数据（重置为初始状态）
    :param account_id: 用户账号
    :param manager: 工作数据管理器
    """
    initial_data = {
        "job_id": 0,
        "job_name": '',
        "join_date": '1970-01-01',
        "work_date": '1970-01-01',
        "work_time": 0,
        "work_count": 0,
        "overtime_count": 0
    }
    manager.update_section_keys(account_id, initial_data)