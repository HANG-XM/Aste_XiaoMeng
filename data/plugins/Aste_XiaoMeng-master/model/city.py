import math
import time
import random
import re
from decimal import Decimal, ROUND_HALF_UP  # 引入 Decimal 类型
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from datetime import datetime
import json

from .directory import IniFileReader,JobFileHandler,ShopFileHandler  # 导入专用读取函数
from .city_func import is_arabic_digit,get_by_qq,preprocess_date_str,calculate_delta_days,get_dynamic_rob_ratio
from . import constants

from astrbot.api import logger

def xm_main() -> str:
    return (
        f"🏠 小梦菜单 ✨"
        f"\n———————"
        f"\n✅ 签到"
        f"\n🔍 查询"
        f"\n🔗 绑定"
        f"\n💼 打工菜单"
        f"\n🏦 银行菜单"
        f"\n🏪 商店菜单"
        f"\n⚔️ 打劫菜单"
        )

def check_in(account,user_name:str,path)->str:
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
    now_time = datetime.now()
    today_str = now_time.strftime("%Y-%m-%d")
    # 处理上次签到时间（兼容旧格式）
    sign_data = sign_reader.read_section(account, create_if_not_exists=True)
    last_sign_str = preprocess_date_str(sign_data.get("sign_time", "1970-01-01"))
    # -------------------- 核心签到逻辑 --------------------
    if last_sign_str == today_str:
        continuous = int(sign_data.get("continuous_clock-in", 0))
        accumulated = int(sign_data.get("accumulated_clock-in", 0))
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
        first_sign_tips = [  # 首次签到提示
            f"🎉 {user_name}第一次签到成功！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，开启打工人的第一天～",
            f"🌟 恭喜{user_name}完成首次签到！{reward_coin}金币已到账，经验+{reward_exp}，体力+{reward_stamina}，继续加油哦～",
            f"🎊 {user_name}来啦！首次签到奖励已发放，{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，打工之路正式启程～"
        ]
        result_msg = random.choice(first_sign_tips).format(
            user_name=user_name,
            continuous_days=continuous_days,
            reward_coin=reward_coin,
            reward_exp=reward_exp
        )
    else:
        # 情况3：计算断签天数
        delta_days = calculate_delta_days(today_str,last_sign_str)

        if delta_days == 1:
            # 连续签到（间隔1天）
            reward_coin = constants.CHECK_IN_CONTINUOUS_REWARD_GOLD
            reward_exp = constants.CHECK_IN_CONTINUOUS_REWARD_EXP
            reward_stamina = constants.CHECK_IN_CONTINUOUS_REWARD_STAMINA
            continuous_days += 1
            continuous_tips = [  # 连续签到提示
                f"🔥 {user_name}连续签到{continuous_days}天！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，离全勤奖又近一步～",
                f"✅ {user_name}今日连签成功！连续{continuous_days}天，金币+{reward_coin}，经验+{reward_exp}，体力+{reward_stamina}，稳住别断～",
                f"💪 {user_name}连签记录更新！{continuous_days}天不停歇，奖励已到账，继续冲～"
            ]
            result_msg = random.choice(continuous_tips).format(
                user_name=user_name,
                continuous_days=continuous_days,
                reward_coin=reward_coin,
                reward_exp=reward_exp
            )
        else:
            # 断签后签到（间隔>1天）
            reward_coin = constants.CHECK_IN_BREAK_REWARD_GOLD
            reward_exp = constants.CHECK_IN_BREAK_REWARD_EXP
            reward_stamina = constants.CHECK_IN_BREAK_REWARD_STAMINA
            continuous_days = 1  # 重置连续天数
            break_tips = [  # 断签后签到提示
                f"🔄 {user_name}今日重新签到！虽然断了1天，但奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力已发放，明天继续连签吧～",
                f"⏳ {user_name}断签后归来！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，连续天数重置为1，今天开始重新累积～",
                f"🌱 {user_name}今日首次签到（上次断签）！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，坚持就是胜利～"
            ]
            result_msg = random.choice(break_tips).format(
                user_name=user_name,
                continuous_days=continuous_days,
                reward_coin=reward_coin,
                reward_exp=reward_exp
            )
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

    return result_msg

def query(account: str, user_name: str, path) -> str:
    """
    查询用户信息（含字段自动补全）
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 数据目录
    :return: 格式化后的用户信息字符串（优化后更友好、结构化）
    """
    # 预定义字段元数据（名称、单位、默认值）
    FIELD_METADATA: Dict[str, Dict[str, Any]] = {
        "level": {"name": "等级", "unit": "级", "default": 1},
        "exp": {"name": "经验", "unit": "点", "default": 0},
        "coin": {"name": "金币", "unit": "个", "default": 0},
        "charm": {"name": "魅力", "unit": "点", "default": 0},
        "stamina": {"name": "体力", "unit": "点", "default": 100}
    }

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

        # 标记是否需要更新文件（存在缺失字段时触发）
        need_save = False
        # 存储待更新的字段（键值对）
        updates: Dict[str, Any] = {}
        # 初始化结果行列表
        result_lines: List[str] = []

        # 遍历预定义字段，补全缺失值并生成结果行
        for field, meta in FIELD_METADATA.items():
            current_value = account_data.get(field)

            # 检查字段是否存在或类型是否合法（防止INI中存储非法类型）
            if current_value is None or not isinstance(current_value, type(meta["default"])):
                # 补全默认值
                updates[field] = meta["default"]
                # 同步到内存数据（用于生成结果）
                account_data[field] = meta["default"]
                need_save = True

            # 拼接结果行（使用当前值或补全后的默认值）
            result_line = f"{meta['name']}：{account_data[field]}{meta['unit']}"
            result_lines.append(result_line)

        # 批量更新缺失字段并保存（仅当有更新时）
        if need_save:
            file.update_section_keys(account, updates)
            file.save()

        # 优化返回文本：添加亲切问候、分隔线和项目符号
        header = f"你好呀，{user_name}👋～\n—————————\n"
        content = "\n".join([f"▸ {line}" for line in result_lines])
        return f"{header}{content}"

    except Exception as e:
        # 优化异常提示语气
        logger.error(f"用户[{account}]查询异常：{str(e)}")
        return "哎呀，查询时出了点小问题，请稍后再试哦～"

def bind(account: str, user_name: str, msg: str, path) ->str:
    """处理绑定《逃跑吧少年》手游账号的请求（优化版）"""
    # -------------------- 命令格式验证 --------------------
    if not msg.startswith("绑定 "):
        return "支持绑定《逃跑吧少年》手游账号\n绑定方法：绑定 游戏ID\n提示：一人仅支持绑定一次！"

    # 提取并验证游戏ID格式（示例：6位数字）
    parts = msg.split(maxsplit=1)
    if len(parts) < 2:
        return f"{constants.ERROR_PREFIX} 请提供有效游戏ID（如：绑定 123456）"
    game_id = parts[1].strip()
    if not game_id.isdigit() or len(game_id) > 9:
        return f"{constants.ERROR_PREFIX} 游戏ID需为纯数字且是正确的游戏ID"

    # -------------------- 初始化游戏管理器 --------------------
    try:
        game_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Game.info",
        )
    except Exception as e:
        logger.error(f"初始化游戏管理器失败（用户[{account}]）: {str(e)}")
        return "❌ 系统繁忙，请稍后重试！"

    # -------------------- 检查当前用户是否已绑定 --------------------
    try:
        game_data = game_manager.read_section(account, create_if_not_exists=True)
        current_bound_id = game_data.get("game_id", 0)
        if current_bound_id != 0:
            return f"{constants.ERROR_PREFIX} 您已绑定游戏ID：{current_bound_id}\n如需更换，请先联系群主解绑！"
    except Exception as e:
        logger.error(f"读取用户游戏数据失败（用户[{account}]）: {str(e)}")
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

def work(account,user_name,path,job_manager:JobFileHandler)->str:
    """
    打工功能
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
    # 需加班状态（次数超限）
    overtime_prompt_texts = [
        lambda jobname: f"{user_name} 今日{jobname}打工次数已达上限～想继续赚钱？发送[加班]，开启额外工作模式吧～",
        lambda jobname: f"次数已满{user_name}～但勤劳的人值得更多！发送[加班]，继续为{jobname}奋斗多赚一份工资～",
        lambda jobname: f"{user_name} 今天的{jobname}打工次数用完啦～要挑战[加班]模式，再赚一波吗？多劳多得哦～",
        lambda jobname: f"叮～{user_name}，{jobname}今日打工次数已达上限～发送[加班]，解锁隐藏的「加班工资」吧～"
    ]
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
        work_manager.update_section_keys(account, {
            "job_id": 0,
            "job_name": '',
            "join_date": '1970-01-01',
            "work_date": '1970-01-01',
            "work_time": 0,
            "work_count": 0,
            "overtime_count": 0
                            })
        work_manager.save(encoding="utf-8")
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
        work_data = work_manager.read_section(account, create_if_not_exists=True) or {}
        work_time = 0
    else:
        work_time = work_data.get("work_time", 0)

    # 获取现在时间戳
    now_time = time.time()
    if work_time == 0:
        if work_data.get("work_count", 0) == 0:
            # 未开始打工
            work_manager.update_section_keys(account, {
                "work_time": now_time,
                "work_count": 1
            })
            work_manager.save(encoding="utf-8")
            new_stamina = user_stamina - job_stamina
            user_manager.update_key(section=account, key="stamina", value=new_stamina)
            user_manager.save(encoding="utf-8")
            return random.choice(constants.WORK_START_WORK_TEXTS)(user_name,job_name)
        else:
            # 今日已经打工，无需再次打工
            return random.choice(overtime_prompt_texts)(job_name)
    else:
        if work_time + constants.WORK_DURATION_SECONDS <= now_time:
            # 打工完成！
            return random.choice(constants.WORK_REWARD_READY_TEXTS)(user_name,job_name)

        remaining = work_time + constants.WORK_DURATION_SECONDS - now_time
        minutes = math.ceil(remaining / 60)
        return random.choice(constants.WORK_WORKING_TEXTS)(user_name,job_name,minutes)

def overwork(account,user_name,path,job_manager:JobFileHandler)->str:
    # ---------------------- 随机提示语库 ----------------------
    not_started_tips = [
        f"{user_name}，你开始加班了哦～现在开始工作，1小时后就能领工资啦！",
        f"🚀 加班倒计时开始！{user_name}点击确认开始工作，1小时后收获今日工资～",
        f"💼 工作已就绪！{user_name}现在开始加班，1小时后即可领取劳动所得～"
    ]

    # ---------------------- 初始化数据管理器 ----------------------
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    work_data: Dict[str, str] = work_manager.read_section(account, create_if_not_exists=True) or {}
    # ---------------------- 检查是否拥有有效工作 ----------------------
    job_id = work_data.get("job_id")
    job_name = work_data.get("job_name")
    if not job_id or not str(job_id).strip() or not job_name or not str(job_name).strip():
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)
    # ---------------------- 获取当前工作信息 ----------------------
    job_data = job_manager.get_job_info(str(job_id))
    if not job_data:
        # 清除异常工作数据并提示
        work_manager.update_section_keys(account, {
            "job_id": 0,
            "job_name": '',
            "join_date": '1970-01-01',
            "work_date": '1970-01-01',
            "work_time": 0,
            "work_count": 0,
            "overtime_count": 0
                            })
        work_manager.save(encoding="utf-8")
        return random.choice(constants.WORK_ERROR_TEXTS)(job_name)
    job_stamina = job_data.get("physicalConsumption", 0)
    user_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Personal",
        file_relative_path="Briefly.info",
        encoding="utf-8"
    )
    user_data = user_manager.read_section(account, create_if_not_exists=True) or {}
    user_stamina = user_data.get("stamina",0)
    if user_stamina < job_stamina:
        return "体力不足，请[签到]获取体力再加班吧！"

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
        return random.choice(not_started_tips)  # 随机选择未开始提示
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
    # -------------------- 数据校验与预处理 --------------------
    if "jobSeries" not in job_manager.data:
        return "⚠️ 职位数据库结构异常，缺少'jobSeries'字段！"

    job_series_data = job_manager.data["jobSeries"]
    if not job_series_data:
        return "⚠️ 职位数据库为空，请联系管理员初始化数据！"

    # -------------------- 收集所有有效职位ID（按数字升序排序） --------------------
    all_jobs = []
    # 按series_key的数字顺序遍历（如"20"→"30"→"40"）
    for series_key in sorted(job_series_data.keys(), key=lambda x: int(x)):
        # 按job_id的数字顺序遍历（如"2000"→"2001"→"2002"）
        for job_id_str in sorted(job_series_data[series_key].keys(), key=lambda x: int(x)):
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
    # 定义随机提示语库（可根据需求扩展）
    daily_limit_tips = [
        f"{user_name}，今天已经跳过一次槽啦！职场如战场，稳扎稳打更重要，明天再来尝试吧～",
        f"今日跳槽额度已用完～{user_name}先在新岗位上积累经验，明天再挑战更好的机会！",
        f"跳槽冷却时间未到哦～{user_name}今天先好好工作，明天此时再发送[跳槽]刷新记录～"
    ]
    max_position_tips = [
        f"厉害！{user_name}已经是当前行业的天花板了～暂时没有更高的职位等你挑战啦！",
        f"{user_name}已登顶该行业，现有岗位中没有能匹配你能力的新选择，继续保持优势吧～",
        f"你已经是这个领域的顶尖选手啦！当前没有更适合的高阶职位，享受你的王者时刻～"
    ]
    fail_tips = [
        f"{user_name}这次跳槽差了点火候～再提升下等级/经验/魅力/金币，下次一定能拿下更好的岗位！",
        f"新岗位的要求还没完全满足哦～当前{user_name}的等级/经验/魅力/金币还差一点，继续加油冲！",
        f"跳槽失败～新公司的HR觉得你还可以更优秀！提升下属性，下次带着更亮眼的数据来应聘吧～"
    ]
    success_tips = [
        f"🎉恭喜{user_name}！跳槽成功！新公司的offer已送达，准备好迎接新挑战了吗？",
        f"✨{user_name}今日职场进阶！成功入职新岗位，新的同事和项目正在等你解锁～",
        f"🚀{user_name}完成完美跳槽！从今天起，你将以更优的身份开启职业新篇章，冲就完事！"
    ]
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    work_data = work_manager.read_section(account, create_if_not_exists=True)
    job_id = work_data.get("job_id")
    job_name = work_data.get("job_name")
    if not job_id or not str(job_id).strip() or not job_name or not str(job_name).strip():
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)

    # 检测今日跳槽次数
    today_str = datetime.today().strftime("%Y-%m-%d")
    job_hop_date = work_data.get("hop_date")
    if job_hop_date == today_str:
        return random.choice(daily_limit_tips)  # 随机选择今日限制提示

    work_manager.update_key(section=account, key='hop_date', value=today_str)
    work_manager.save(encoding="utf-8")

    next_job_data = job_manager.get_next_job_info(str(job_id))

    if not next_job_data:
        return random.choice(max_position_tips)

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
        return random.choice(success_tips)  # 随机选择成功提示
    return random.choice(fail_tips) # 随机选择失败提示

def get_paid(account,user_name,path,job_manager:JobFileHandler) -> str:
    # ---------------------- 随机提示语库 ----------------------
    not_started_tips = [
        f"{user_name}，你还没开始工作呢～发送[打工]或[加班]，赶紧去公司搬砖吧！",
        f"工位还空着呢～{user_name}快去[打工]打卡，坐满1小时就能领工资啦～",
        f"今日份的工作还没开始哦～{user_name}发送[打工]，马上进入工作状态～"
    ]
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
    # ---------------------- 检查是否已开始工作 ----------------------
    work_time = work_data.get("work_time", 0)
    if work_time == 0:
        return random.choice(not_started_tips)  # 随机选择未开始提示
    now_time = time.time()
    required_time = work_time + constants.WORK_DURATION_SECONDS  # 预计完成时间戳（秒）
    if now_time < required_time:
        # 计算剩余时间（分钟）和进度百分比
        remaining_seconds = required_time - now_time
        remaining_minutes = int(remaining_seconds // 60)
        progress = (now_time - work_time) / constants.WORK_DURATION_SECONDS   # 已工作时长占比

        # 动态生成提示语（变量已计算完成）
        not_finished_tips = [
            f"{user_name}，工作还没做完呢！再坚持{remaining_minutes}分钟，完成就能领工资啦～",
            f"离发工资还差一点～{user_name}当前工作进度：{'%.1f' % (progress * 100)}%，加油冲刺！",
            f"别着急～{user_name}再工作{remaining_minutes}分钟，就能拿到今天的工资啦，冲就完事！"
        ]

        return random.choice(not_finished_tips).format(
            remaining_time=f"{remaining_minutes}分钟",
            progress=f"{progress:.0%}"  # 例如：50%
        )
    # ---------------------- 获取职位信息（含错误处理） ----------------------
    job_data = job_manager.get_job_info(str(job_id))
    if not job_data or "baseSalary" not in job_data:
        # 工作数据异常
        work_manager.update_section_keys(account, {
            "job_id": 0,
            "job_name": '',
            "join_date": '1970-01-01',
            "work_date": '1970-01-01',
            "work_time": 0,
            "work_count": 0,
            "overtime_count": 0
                            })
        work_manager.save(encoding="utf-8")
        return random.choice(constants.WORK_ERROR_TEXTS)  # 随机选择信息错误提示

    job_salary = job_data["baseSalary"]
    if job_salary <= 0:
        return "⚠️ 注意：当前岗位无薪资，建议发送[辞职]更换有报酬的工作～"
    # ---------------------- 计算用户当前金币并更新 ----------------------
    user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
    user_data = user_manager.read_section(account, create_if_not_exists=True)

    # 防止金币字段缺失或类型错误（默认0）
    current_coin = int(user_data.get("coin", 0))
    new_coin = current_coin + job_salary
    user_manager.update_key(account, "coin", new_coin)
    user_manager.save(encoding="utf-8")

    # ---------------------- 重置工作时间并保存 ----------------------
    work_manager.update_key(section=account, key="work_time", value="0")  # 明确存储为字符串
    work_manager.save(encoding="utf-8")

    # ---------------------- 计算工作时长（用于成功提示） ----------------------
    work_duration = (required_time - work_time) // 3600  # 固定1小时（秒转小时）

    success_tips = [
        f"🎉 {user_name}工资到账！辛苦搬砖{work_duration}小时，获得{job_salary}金币～新钱包已鼓起，冲鸭！",
        f"✨ {user_name}今日份努力有回报！领工资啦～{job_salary}金币已到账，够不够买杯奶茶奖励自己？",
        f"🚀 {user_name}完成工作！工资发放成功～{job_salary}金币入账，打工人的快乐就是这么简单～"
    ]

    return random.choice(success_tips).format(
        job_salary=job_salary,
        work_duration=f"{work_duration}小时"
    )

def resign(account,user_name,path,job_manager:JobFileHandler) -> str:
    def work_clear(account: str, work_manager: IniFileReader) -> None:
        """
        清除指定用户的工作数据（重置为初始状态）
        :param account: 用户账号
        :param work_manager: 工作数据管理器
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
        work_manager.update_section_keys(account, initial_data)

    # ---------------------- 随机提示语库 ----------------------

    invalid_job_tips = [
        f"哎呀，系统检测到当前工作信息异常～{user_name}别担心，辞职后自动清除异常记录！",
        f"工作数据加载失败～{user_name}可能是系统bug，辞职操作已帮你清空无效岗位信息！",
        f"注意：当前岗位信息丢失～{user_name}辞职后可直接重新找工作，不影响后续操作！"
    ]

    # ---------------------- 初始化数据管理器 ----------------------
    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    # ---------------------- 检查是否拥有有效工作 ----------------------
    work_data = work_manager.read_section(account, create_if_not_exists=True) or {}
    job_id = work_data.get("job_id")
    job_name = work_data.get("job_name")
    # 严格检查工作有效性（排除0、空字符串等情况）
    if not (job_id and str(job_id).strip() and job_name and str(job_name).strip()):
        return random.choice(constants.WORK_NO_JOB_TEXTS)(user_name)  # 随机选择无工作提示
    # ---------------------- 获取当前工作信息 ----------------------
    job_data = job_manager.get_job_info(str(job_id))
    if not job_data:
        # 清除异常工作数据并提示
        work_clear(account, work_manager)
        return random.choice(invalid_job_tips)  # 随机选择工作异常提示

    # ---------------------- 计算辞职赔偿金额 ----------------------
    # 处理字段缺失（默认0）和类型转换（确保数值）
    resign_gold = int(job_data.get("baseSalary", 0))
    if resign_gold <= 0:
        return "⚠️ 提示：当前岗位无违约金，发送[辞职]可直接离职～"

    # ---------------------- 检查用户金币是否足够 ----------------------
    user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
    user_data: Dict[str, str] = user_manager.read_section(account, create_if_not_exists=True) or {}
    user_gold = int(user_data.get("coin", 0))
    if user_gold < resign_gold:
        not_enough_tips = [
            f"辞职需要赔偿{resign_gold}金币，但你只有{user_gold}金币～再攒攒再辞职吧！",
            f"老板说离职要赔{resign_gold}金币，你钱包不够呀～要不先[打工]赚点金币？",
            f"赔偿金额{resign_gold}金币超过你的存款啦～{user_name}再工作几天凑够钱再辞职！"
        ]
        return random.choice(not_enough_tips).format(
            resign_gold=resign_gold,
            user_gold=user_gold
        )
    # ---------------------- 执行辞职操作 ----------------------
    new_coin = user_gold - resign_gold
    user_manager.update_key(account, "coin", new_coin)
    user_manager.save(encoding="utf-8")
    # 清除工作数据
    work_clear(account, work_manager)
    work_manager.save(encoding="utf-8")
    # ---------------------- 返回成功提示 ----------------------
    success_tips = [
        f"📝 {user_name}提交辞职申请成功！系统自动扣除{resign_gold}金币作为违约金～",
        f"✅ 辞职流程完成！{user_name}已清空当前工作记录，赔偿{resign_gold}金币后余额为{user_gold}～",
        f"🚪 {user_name}正式离职！违约金{resign_gold}金币已扣除，随时可以重新找工作啦～"
    ]

    return random.choice(success_tips)

def check_job(msg,job_manager:JobFileHandler) -> str:
    """
    根据输入消息查询职位信息并格式化输出
    :param msg: 输入消息（如："查工作"、"查工作 2000"、"查工作 2001"）
    :param job_manager:
    :return: 格式化后的职位信息字符串
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
            return f"未找到ID为 {target_id} 的职位信息"
        # 步骤4：提取并格式化各字段
        # 基础信息
        job_name = job_detail["jobName"]
        base_salary = job_detail["baseSalary"] / 1000.0  # 假设单位为元，转换为k单位
        lower = base_salary * 0.8  # 下限 = 基准值 × 80%
        upper = base_salary * 1.2  # 上限 = 基准值 × 120%
        salary_str = f"{lower:.1f}k-{upper:.1f}k"  # 如500元→0.5k

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
            return f"未找到ID为 {target_id} 的职位信息"

        # 步骤4：提取并格式化各字段
        # 基础信息
        job_name = job_detail["jobName"]
        base_salary = job_detail["baseSalary"] / 1000.0  # 假设单位为元，转换为k单位
        lower = base_salary * 0.8  # 下限 = 基准值 × 80%
        upper = base_salary * 1.2  # 上限 = 基准值 × 120%
        salary_str = f"{lower:.1f}k-{upper:.1f}k"  # 如500元→0.5k

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

def jobs_pool(msg: str,path,job_manager:JobFileHandler) -> str:
    """
    根据指令分页或分类展示职位信息，支持三种模式：
    1. "工作池"：显示所有公司的职位概览（总职位数、公司总数、公司列表）。
    2. "工作池 X"（X为正整数）：分页显示所有职位（含当前页、总页数、总职位数）。
    3. "工作池 公司名"：显示指定公司的所有职位（无需分页）。
    :param msg: 指令字符串（如"工作池"、"工作池 1"、"工作池 腾讯"）
    :param path:
    :param job_manager
    :return: 格式化后的职位信息字符串
    """
    page_size = constants.JOBS_POOL_PAGE_SIZE  # 每页显示10条职位

    # ---------------------- 输入解析与校验 ----------------------
    parts = msg.strip().split()
    if not parts or parts[0] != "工作池":
        return "⚠️ 错误：指令格式无效\n请使用以下格式：\n- 工作池（查看所有职位概览）\n- 工作池 X（分页查看所有职位，X为页码）\n- 工作池 公司名（查看指定公司所有职位）"

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

def work_menu() -> str:
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

def submit_resume(account,user_name,msg,path,job_manager:JobFileHandler) -> str:
    # ---------------------- 随机提示语库 ----------------------
    # 无工作提示（用户已有工作时触发）
    has_job_tips = [
        f"{user_name}，你已经有工作啦～想换工作的话记得先发送[辞职]哦！",
        f"当前已有岗位在身～{user_name}要是想跳槽，先辞职腾位置吧！",
        f"打工人的身份已锁定～{user_name}已有工作，投简历前记得先辞职解除绑定～"
    ]

    # 引导投递提示（用户仅发送"投简历"时触发）
    guide_tips = [
        "想投简历却不知道选哪家？发送[找工作]查看最新招聘，找到心仪岗位后用'投简历 X'（X是职位ID）试试～",
        "投简历需要目标哦～先发送[找工作]浏览岗位，选中喜欢的职位ID，再来'投简历 X'就行啦！",
        "不知道投哪个？先[找工作]看看近期热招岗位，确定目标后用'投简历 X'（X为职位ID）提交申请～"
    ]

    # 格式错误提示（用户输入格式不正确时触发）
    format_error_tips = [
        f"投递格式有点小问题～正确姿势是'投简历 X'，X是职位ID（比如'投简历 101'），再来一次？",
        f"抱歉没看懂～请使用'投简历 X'格式（X为职位ID），比如'投简历 203'，我会帮你处理～",
        f"格式需要调整哦～正确的投递指令是'投简历 X'（X是职位ID），比如'投简历 305'，试试看？"
    ]

    work_manager = IniFileReader(
        project_root=path,
        subdir_name="City/Record",
        file_relative_path="Work.data",
        encoding="utf-8"
    )
    # ---------------------- 检查是否已有工作 ----------------------
    work_data = work_manager.read_section(account,create_if_not_exists=True)
    if work_data.get('job_id',0) != 0:
        return random.choice(has_job_tips)
    # ---------------------- 处理"投简历"指令引导 ----------------------
    if msg.strip() == "投简历":
        return random.choice(guide_tips)
    # ---------------------- 解析目标职位ID ----------------------
    msg_parts = msg.strip().split(maxsplit=1)
    if len(msg_parts) < 2:
        return random.choice(format_error_tips)
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
        # 次数超限提示（当日投递超过时触发）
        limit_tips = [
            f"{user_name}今日已投递{current_submit_num}份简历，HR小姐姐说太多了～明天再来刷新记录吧！",
            f"今日投递额度已达{constants.SUBMIT_RESUME_LIMIT}次上限～{user_name}先歇会儿，明天此时再发送'投简历 X'试试～",
            f"已经投了{current_submit_num}份啦！今天的简历通道即将关闭，明天再来投递新岗位～"
        ]
        return random.choice(limit_tips).format(current_submit_num=current_submit_num)

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

        # 成功入职提示（投递通过时触发）
        success_tips = [
            f"🎉 恭喜{user_name}！成功入职[{job_name}]～新公司的工位和同事已准备就绪，职场新征程开始啦！",
            f"✨ {user_name}太棒了！{job_name}的offer已送达，准备好迎接新任务和团队小伙伴了吗？冲就完事～",
            f"🚀 {user_name}完成完美投递！从今天起，你将以新身份在[{job_name}]开启职业升级，未来可期～"
        ]

        return random.choice(success_tips).format(job_name=job_name)

    # 属性不足提示（用户未达标时触发）
    fail_tips = [
        f"很遗憾～{job_name}的HR觉得你还可以更优秀！当前等级/经验/魅力/金币还差一点，继续提升吧～",
        f"{user_name}这次差了点火候～{job_name}要求等级≥{req_level}、经验≥{req_exp}、魅力≥{req_charm}、金币≥{req_gold}，加油冲！",
        f"抱歉～{job_name}的岗位要求你再努把力！等级/经验/魅力/金币还没达标，提升后下次再来挑战～"
    ]
    return random.choice(fail_tips).format(
        job_name=job_name,
        req_level=req_level,
        req_exp=req_exp,
        req_charm=req_charm,
        req_gold=req_gold
    )

def bank_menu() -> str:
    """
    返回适合 QQ 群文字游戏的银行菜单（简洁直观，带互动引导）
    """
    return """✦ 🏦 银 行 服 务 ✦\n———————————\n✨ 基础操作 → 存款 / 取款\n✨ 资金流转 → 贷款 / 还款\n✨ 定期业务 → 存定期 / 取定期\n✨ 其他功能 → 查存款 / 转账\n——————————\n输入对应关键词使用，如「存款」"""

def deposit(account,user_name,msg,path) -> str:
    """
    存款
    :param account: 用户账号
    :param user_name:用户昵称
    :param msg:
    :param path:数据目录
    :return: 结果提示
    """
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")  # 获取当前时间
    # 统一错误提示前缀（可选）
    error_prefix = "❌ 存款操作提示"
    success_prefix = "✅ 存款操作完成"

    if not msg.startswith("存款 "):
        return (
            f"{error_prefix}\n"
            f"存款格式应为：存款 [金额]（例：存款 {constants.DEPOSIT_MULTIPLE_BASE}）\n"
            f"✨ 温馨提示：金额需为{constants.DEPOSIT_MULTIPLE_BASE}的整数倍，"
            f"如{constants.DEPOSIT_MULTIPLE_BASE}、{constants.DEPOSIT_MULTIPLE_BASE*3}等。"
        )
    parts = msg.split()
    if len(parts) < 2:
        return (
            f"{error_prefix}\n"
            f"信息不完整呢~ 请补充完整的存款金额\n"
            f"📝 示例：存款 {constants.DEPOSIT_MULTIPLE_BASE}（表示存入{constants.DEPOSIT_MULTIPLE_BASE}金币）"
        )
    try:
        amount = int(parts[1])
    except ValueError:
        return (
            f"{error_prefix}\n"
            f"金额格式错误~ 请输入有效的整数"
        )
    if amount <= 0:
        return (
            f"{error_prefix}\n"
            f"金额不能为0或负数哦~ 请输入大于0的数值\n"
            f"💡 建议：至少存入{constants.DEPOSIT_MULTIPLE_BASE}金币（如：存款 {constants.DEPOSIT_MULTIPLE_BASE}）。"
        )
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return (
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
            f"个人账户读取失败~ \n"
            f"⚠️ 错误原因：读取\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    user_gold = user_data.get("coin", 0)
    if user_gold < amount:
        return (
            f"{error_prefix}\n"
            f"余额不足，无法完成存款~ 😔\n"
            f"📊 当前个人账户：{user_gold} 个\n"
            f"🎯 本次拟存款金额：{amount} 个\n"
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
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
            f"个人账户更新失败~ 银行账户已恢复\n"
            f"⚠️ 错误原因：保存\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    success_msg = (
        f"{success_prefix}\n"
        f"🎉 {user_name} 先生/女士，您的存款操作已成功！⏰ 时间：{current_time}\n"
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
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")  # 获取当前时间
    # 统一提示前缀（可选）
    error_prefix = "❌ 取款操作提示"
    success_prefix = "✅ 取款操作完成"

    if not msg.startswith("取款 "):
        return (
            f"{error_prefix}\n"
            f"取款格式应为：取款 [金额]（例：取款 {constants.DEPOSIT_MULTIPLE_BASE}）\n"
            f"✨ 温馨提示：金额需为{constants.DEPOSIT_MULTIPLE_BASE}的整数倍，"
            f"例如{constants.DEPOSIT_MULTIPLE_BASE}、{constants.DEPOSIT_MULTIPLE_BASE*5}等。"
        )
    parts = msg.split()
    if len(parts) < 2:
        return (
            f"{error_prefix}\n"
            f"信息不完整呢~ 请补充完整的取款金额\n"
            f"📝 示例：取款 {constants.DEPOSIT_MULTIPLE_BASE}（表示从银行取出{constants.DEPOSIT_MULTIPLE_BASE}金币）"
        )

    amount = parts[1]

    if amount <= 0:
        return (
            f"{error_prefix}\n"
            f"金额不能为0或负数哦~ 请输入大于0的数值\n"
            f"💡 建议：至少取出{constants.DEPOSIT_MULTIPLE_BASE}金币（如：取款 {constants.DEPOSIT_MULTIPLE_BASE}）。"
        )
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return (
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
            f"读取银行账户失败~ 请稍后再试\n"
            f"⚠️ 错误原因：读取"
        )
    bank_deposit = bank_data.get("deposit", 0)
    if bank_deposit < amount:
        return (
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
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
            f"{error_prefix}\n"
            f"个人账户更新失败~ 银行账户已恢复\n"
            f"⚠️ 错误原因：保存\n"
            f"💡 请联系管理员核查个人账户数据~"
        )

    success_msg = (
        f"{success_prefix}\n"
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
    MIN_REPAYMENT = 1  # 最小还款金额（1 金币）
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
        return f"{constants.ERROR_PREFIX}\n还款金额不能少于{MIN_REPAYMENT}金币！"
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
                f"（例：存定期 {constants.DEPOSIT_MULTIPLE_BASE}）")
    parts = msg.split()
    if len(parts) < 2:
        return f"{user_name}，格式不对哦~😢 正确姿势是：存定期 金额（例：存定期 {constants.DEPOSIT_MULTIPLE_BASE}）"
    try:
        amount = int(parts[1])
    except ValueError:
        return (f"{user_name}，金额必须是整数哦~😢 "
                f"正确姿势是：存定期 {constants.DEPOSIT_MULTIPLE_BASE}/{constants.DEPOSIT_MULTIPLE_BASE*2}/..."
                f"（例：存定期 {constants.DEPOSIT_MULTIPLE_BASE}）")
    if amount <= 0:
        return "存定期0个金币可不行~😜 至少存定期1个吧！"
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return f"{user_name}，存定期金额必须是{constants.DEPOSIT_MULTIPLE_BASE}的整数倍哦~😢 "
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
        current_deposit  = bank_data.get("deposit", 0)
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
    result_msg = [f"📊 {user_name}，您的账户信息查询结果："]
    # 活期存款（明确标注）
    result_msg.append(f"✅ 活期存款：{current_deposit} 金币")
    result_msg.append(f"💰 当前贷款：{current_loan} 金币")
    result_msg.append(f"📅 定期存款：{current_fixed_deposit} 金币")
    # 温馨提示结尾
    result_msg.append("如有任何疑问，欢迎随时联系客服小助手~❤️")

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
    content = msg
    # 正则表达式：同时匹配两个数字
    transfer_pattern = r'^转账 (\d+)\[at:(\w+)\]$'
    match = re.match(transfer_pattern, msg.strip())
    if not match:
        return f"❌ 转账格式错误。正确格式：转账 金额@对象（示例：转账 {constants.DEPOSIT_MULTIPLE_BASE}@小梦）"
    amount = int(match.group(1))  # 提取金额（整数）
    if amount % constants.DEPOSIT_MULTIPLE_BASE != 0:
        return f"{user_name}，存定期金额必须是{constants.DEPOSIT_MULTIPLE_BASE}的整数倍哦~😢 "
    receiver_account = match.group(2)  # 提取接收者账户（INI的section名）
    # -------------------- 2. 初始化INI文件管理器（含异常处理） --------------------
    try:
        bank_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Bank.data",
            encoding="utf-8"
        )
        sender_data = bank_manager.read_section(section=account, create_if_not_exists=True)
        receiver_data = bank_manager.read_section(section=receiver_account, create_if_not_exists=True)
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
        bank_manager.update_key(section=receiver_account, key="deposit", value=receiver_new_deposit)
        bank_manager.save(encoding="utf-8")
    except Exception as e:
        logger.error(f"转账操作失败（发送者：{account}，接收者：{receiver_account}）：{str(e)}")
        return f"❌ 系统错误：转账操作失败!"
    # -------------------- 7. 返回详细成功信息（用户友好） --------------------
    return (
        f"✅ 转账成功！\n"
        f"发送者：{user_name}\n"
        f"接收者：{receiver_account}\n"
        f"转账金额：{amount}\n"
        f"手续费（{constants.TRANSFER_PROCESSING_FEE_RATE * 100}%）：{amount * constants.TRANSFER_PROCESSING_FEE_RATE}金币\n"
        f"发送者原余额：{sender_deposit} → 新余额：{sender_new_deposit} 金币\n"
        f"接收者原余额：{receiver_deposit} → 新余额：{receiver_new_deposit} 金币"
    )

def shop_menu():
    return (
        f"✦ ✦ 🏪 商 店 菜 单 ✨ ✦ ✦"
        f"\n————————————"
        f"\n🏬 商店：浏览所有上架商品"
        f"\n🔍 查商品：查看具体的信息"
        f"\n💰 购买：选择商品直接下单"
        f"\n🎒 背包：查看已购买的物品"
        f"\n🛠️ 使用：使用背包里的道具"
    )

def shop(account, user_name, msg, path) -> str:
    ITEMS_PER_PAGE = 7  # 每页显示数量

    def format_price(price: int) -> str:
        """格式化价格：>10000 显示为 X.XXk 格式（保留两位小数）"""
        if price > 1000:
            k_value = price / 1000  # 转换为千单位
            return f"{k_value:.2f}k"  # 保留两位小数（自动四舍五入，末尾补零）
        else:
            return str(price)  # 普通价格直接显示
    """
    处理商店查询命令，返回格式化字符串结果（取消商品详情模式）

    :param msg: 用户输入命令（如"商店"、"商店 2"、"商店 gift"）
    :param shop_handler: ShopFileHandler实例（已加载商店数据）
    :return: 格式化后的查询结果字符串
    """
    # 统一去除首尾空格并分割命令
    msg_clean = msg.strip()
    if not msg_clean.startswith("商店"):
        return "❌ 无效命令：请以'商店'开头"

    shop_handler = ShopFileHandler(
        project_root=path,
        subdir_name="City/Set_up",
        file_relative_path="Shop.res",
        encoding="utf-8"
    )

    # 分割主命令和参数
    parts = msg_clean.split(maxsplit=1)
    param = parts[1].strip() if len(parts) > 1 else ""

    # ====================== 模式一：总览 ======================
    if not param:
        total_items = len(shop_handler.data)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        return (
            f"📦 小梦商店总览\n"
            f"总商品数：{total_items} 件\n"
            f"总页数：{total_pages} 页\n"
            f"每页显示 {ITEMS_PER_PAGE} 件\n"
            f"类别：游戏/礼物/鱼竿/鱼饵/体力/经验\n"
            f"指令：'商店 X' X为类别/页数\n"
            f"其他指令：购买/查商品/背包/使用"
        )

    # ====================== 模式二：分页查询 ======================
    if param.isdigit():
        page = int(param)
        total_items = len(shop_handler.data)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

        # 页码有效性检查
        if page < 1:
            return "❌ 页码错误：页码不能小于1"
        if page > total_pages:
            return f"❌ 页码错误：当前只有 {total_pages} 页"

        # 计算分页数据
        start = (page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_items = list(shop_handler.data.items())[start:end]

        # 格式化商品列表
        item_list = "\n".join(
            [f"{i + 1}. {name} - {format_price(info['price'])} 金币(余:{info['quantity']})"
             for i, (name, info) in enumerate(page_items)]
        )
        return (
            f"📖 小梦商店 第{page}/{total_pages}页\n"
            f"--------------------------\n"
            f"{item_list}"
        )

    # ====================== 模式三：类别查询 ======================

    category_mapping = {
        "游戏": "game",
        "礼物": "gift",
        "经验": "exp",
        "体力": "stamina",
        "鱼竿": "fishing_rod",
        "鱼饵": "fishing_bait"
    }

    # 尝试匹配中文或英文类别
    if param in category_mapping:
        category_key = category_mapping[param]
        display_name = param  # 使用中文作为显示名称
    else:
        return f"ℹ️ 未知类别：{param}"

    # 获取对应类别商品并按价格排序
    category_items = sorted(
        [(name, info) for name, info in shop_handler.data.items()
         if info["category"] == category_key],
        key=lambda x: x[1]['price']
    )

    if not category_items:
        return f"ℹ️ {display_name}类别下暂无商品"

    # 构建商品列表
    item_list = "\n".join(
        [f"{i + 1}. {name} - {format_price(info['price'])} 金币(余:{info['quantity']})"
         for i, (name, info) in enumerate(category_items)]
    )

    return (
        f"📦 {display_name}类别商品\n"
        f"--------------------------\n"
        f"{item_list}\n"
        f"--------------------------\n"
        f"获取详情：查商品 商品名"
    )

def purchase(account,user_name,msg,path) -> str:
    """
    购买功能
    """
    if not msg.startswith("购买 "):
        return "想要购买什么呢？发送[小梦商店]查看心仪的商品吧！\n购买格式示例：购买 小心心"

    goods_name = msg[3:].strip()
    if not goods_name:
        return "请输入要购买的商品名称！\n购买格式示例：购买 小心心"

    # -------------------- 初始化商店处理器 --------------------
    try:
        shop_handler = ShopFileHandler(
            project_root=path,
            subdir_name="City/Set_up",
            file_relative_path="Shop.res",
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"初始化商店处理器失败（用户[{account}]，商品[{goods_name}]）: {str(e)}")
        return "系统繁忙，请稍后重试！"

    # -------------------- 商品基础校验 --------------------
    # 校验商品存在性及可用状态
    if goods_name not in shop_handler.data:
        similar_goods = shop_handler.get_similar_items(item_name=goods_name,similarity_threshold=0.5,top_n_name=3)
        hint = f"未找到商品「{goods_name}」"
        if similar_goods:
            hint += f"，猜你想要：{'、'.join(similar_goods[0])}？"
        hint += "\n发送[小梦商店]查看所有商品"
        return hint

    goods_data = shop_handler.data[goods_name]
    goods_category = goods_data.get("category")
    goods_price = goods_data.get("price", 0)
    goods_quantity = goods_data.get("quantity",0)
    goods_available = goods_data.get("available", False)

    # 商品状态校验（提前终止无效流程）
    if not goods_available:
        return f"该商品{goods_name}暂不可售，请留意商店公告！"
    if goods_price < 1:
        logger.warning(f"商品「{goods_name}」价格异常（用户[{account}]）: {goods_price}")
        return "商品价格异常，请联系管理员！"
    if goods_quantity < 1:
        return f"该商品{goods_name}已售完，请留意商店公告！"
    # -------------------- 读取用户数据 --------------------
    try:
        user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
        )
        user_data = user_manager.read_section(section=account, create_if_not_exists=True)
        user_gold = user_data.get("coin", 0)
    except Exception as e:
        logger.error(f"读取用户[{account}]数据失败（商品[{goods_name}]）: {str(e)}")
        return "系统繁忙，请稍后重试！"
    # -------------------- 金币校验 --------------------
    if user_gold < goods_price:
        return f"金币不足（当前{user_gold}，需要{goods_price}），无法购买「{goods_name}」"

    # -------------------- 事务准备 --------------------
    files_to_save: List[tuple[str, IniFileReader]] = [
        ("Briefly.res", user_manager),  # 用户金币数据
        ("Shop.res", shop_handler)  # 商店库存数据
    ]

    if goods_category in ("exp", "stamina","gift","fishing_rod", "fishing_bait"):
        basket_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Basket.info",
        )
        files_to_save.append(("Basket.info", basket_manager))
        basket_data = basket_manager.read_section(section=account, create_if_not_exists=True) or {}
        if goods_category in ("exp", "stamina","gift","fishing_bait"):
            basket_manager.update_key(section=account, key=goods_name, value=basket_data.get(goods_name, 0) + 1)

        elif goods_category == "fishing_rod":
            if goods_name in basket_data:
                return f"您已拥有鱼竿「{goods_name}」！若需更换耐久，请使用[修复 {goods_name}]功能"
            basket_manager.update_key(section=account, key=goods_name,value=100)

    elif goods_category in ("game",):
        game_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Game.info",
        )
        game_data = game_manager.read_section(section=account, create_if_not_exists=True) or {}
        if game_data.get("game_id",0) == 0:
            return "当前未绑定逃跑吧少年手游账号！发送'绑定 游戏ID'可以进行绑定"
        files_to_save.append(("Game.info", game_manager))
        game_manager.update_key(section=account, key=goods_name, value=game_data.get(goods_name, 0) + 1)
    # -------------------- 扣减 --------------------
    shop_handler.update_data(key=f"{goods_name}.quantity", value=goods_quantity - 1,validate=True)
    user_manager.update_key(section=account, key="coin", value=user_gold - goods_price)
    # -------------------- 提交所有修改 --------------------
    try:
        for file_name, manager in files_to_save:
            manager.save("utf-8")  # 保存钓鱼数据等其他文件
    except Exception as e:
        logger.error(f"保存数据失败（用户[{account}]，商品[{goods_name}]）: {str(e)}")
        return "购买成功，但数据保存失败，请联系管理员！"

    # -------------------- 构造成功提示 --------------------
    effect_msg = goods_data.get("effect_msg", "祝您游戏愉快～")
    success_tips = {
        "game": f"购买成功！该商品{user_name}为群主礼物赠送，时间不固定！"
    }.get(goods_category, f"购买成功！该{goods_name}已经放入[背包]")

    return f"{success_tips}\n{effect_msg}"

def basket(account: str, user_name: str, path) -> str:
    """
    查询用户购物篮信息（优化版，支持多类型物品友好显示）
    :param account: 用户账号
    :param user_name: 用户昵称
    :param path: 项目根路径
    :return: 友好格式的购物篮信息或错误提示
    """
    try:
        basket_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Basket.info",
            encoding="utf-8",
        )
        basket_data = basket_manager.read_section(section=account, create_if_not_exists=True) or {}
    except Exception as e:
        logger.error(f"初始化读取器错误！{str(e)}")
        return "系统繁忙，请稍后重试！"

    # 处理空购物篮的情况
    if not basket_data:
        return "你的购物篮空空如也～快去商店逛逛吧！🛍️"

    items_list = []

    for item, value in basket_data.items():
        # 处理钓鱼装备类物品（特殊格式）
        if item in ["fishing_rod"]:
            # 验证数据格式：应为列表，元素为包含name和endurance的字典
            items_list.append(f"· {item}：{value}耐久")
        # 处理普通物品（数值型数量）
        else:
            # 兼容多种数值格式（字符串/数字）
            try:
                count = int(value)
                if count > 0:  # 数量大于0才显示
                    items_list.append(f"· {item}：{count}个")
            except (ValueError, TypeError):
                # 非数值类型或无法转换的情况（如"小心心=0"可能存储为字符串"0"）
                logger.debug(f"用户{user_name}的{item}非数值类型，值：{value}")

    # 最终结果拼接（根据是否有有效物品显示不同内容）
    if items_list:
        header = f"📦 {user_name}的购物篮里有这些宝贝："
        footer = "\n使用提示：发送「使用 X」可查看/使用物品（X为物品名，如「使用 银鱼竿」）"
        return f"{header}\n" + "\n".join(items_list) + footer
    else:
        return "你的购物篮里暂时没有可用物品～快去商店看看吧！🛍️"

def check_goods(account:str, user_name:str, msg:str, path):
    """
    查询商品详细信息（优化版，增强健壮性与用户体验）

    :param account: 用户账号
    :param user_name: 用户昵称（未使用，保留参数兼容）
    :param msg: 用户输入消息（如"查商品 小心心"）
    :param path: 项目根路径
    :return: 商品信息描述或错误提示
    """
    if not msg.startswith("查商品 "):
        return "查商品格式：查商品 商品名，如：查商品 小心心"

    # 提取商品名（处理"查商品"后多个空格的情况）
    parts = msg.split(maxsplit=1)  # 最多分割1次
    if len(parts) < 2 or not parts[1].strip():
        return "⚠️ 查询格式错误！请使用：查商品 商品名（如：查商品 小心心）"

    good_name = parts[1].strip()
    if not good_name:
        return "⚠️ 商品名不能为空！请重新输入。"

    try:
        # 初始化商店处理器（假设ShopFileHandler已正确实现）
        shop_manager = ShopFileHandler(
            project_root=path,
            subdir_name="City/Set_up",
            file_relative_path="Shop.res",
            encoding="utf-8",
        )
        # 获取商品详情（若不存在返回空字典）
        shop_data = shop_manager.get_item_info(good_name)
    except Exception as e:
        logger.error(f"初始化商品读取器错误！{str(e)}")
        return "😢 系统繁忙，商品查询暂时异常，请稍后重试！"

    # -------------------- 商品存在性校验 --------------------
    if not shop_data:
        # 获取相似商品（优化：限制最多3个推荐）
        similar_goods = shop_manager.get_similar_items(item_name=good_name,similarity_threshold=0.5, top_n_name=3)
        similar_names = [item[0] for item in similar_goods] if similar_goods else ["无"]
        return f"❌ 未找到商品「{good_name}」～猜你可能想找：{', '.join(similar_names)}"

    # -------------------- 信息格式化（结构化+可配置化） --------------------
    # 类型映射（支持扩展新商品类型，如后续新增"装备"类）
    CATEGORY_MAPPING = {
        "fishing_rod": ("鱼竿", ["strength", "time"]),          # (类型名称, 关联字段列表)
        "gift": ("礼物", ["charm_value"]),
        "exp": ("经验类", ["exp_value"]),
        "stamina": ("体力类", ["recover_value"]),
        "fishing_bait": ("鱼饵", ["strength"]),
        "game": ("游戏", []),
    }
    # 获取类型名称和需要展示的字段（避免硬编码if-elif）
    category_info = CATEGORY_MAPPING.get(shop_data.get("category"), ("未知类型", []))
    category_name, related_fields = category_info

    # 基础信息（必选字段）
    base_info = [
        f"📦 物品名称：{good_name}",
        f"📌 类型：{category_name}",
        f"💰 价格：{shop_data.get('price', 0)} 金币",
        f"💎 剩余：{shop_data.get('quantity', 0)} 个"
    ]

    # 扩展信息（根据类型动态生成，支持字段缺失时显示"无"）
    ext_info = []
    # 1. 类型相关属性（如魅力值、钓力等）
    for field in related_fields:
        value = shop_data.get(field, 0)
        field_alias = {
            "charm_value": "✨ 魅力值",
            "exp_value": "✨ 经验值",
            "recover_value": "✨ 体力值",
            "strength": "🎣 钓力",
            "time": "⏱️ 时间窗"
        }.get(field)  # 字段别名映射（避免硬编码字段名）
        ext_info.append(f"{field_alias}：{value} 点" if field != "time" else f"{field_alias}：{value} 秒")

    # 通用描述（必选）
    ext_info.append(f"📝 描述：{shop_data.get("effect_msg", "无效果描述")}")
    ext_info.append(f"ℹ️ 购买方法：购买 {good_name}")
    # 合并基础信息与扩展信息（基础信息后空一行，扩展信息用短横线分隔）
    all_info = base_info + ["---", *ext_info]
    return "\n".join(all_info)

def use(account,user_name,msg,path) -> str:
    if not msg.startswith("使用 "):
        return f"{user_name} 使用方法：使用 物品。各项物品可前往[小梦商店]查看"

    try:
        basket_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Basket.info",
            encoding="utf-8",
        )
        basket_data = basket_manager.read_section(section=account, create_if_not_exists=True)
        shop_manager = ShopFileHandler(
            project_root=path,
            subdir_name="City/Set_up",
            file_relative_path="Shop.res",
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"读取配置错误！{str(e)}")
        return "系统繁忙，请稍后重试！"

    # 提取商品名（处理"查商品"后多个空格的情况）
    parts = msg.split(maxsplit=1)  # 最多分割1次
    if len(parts) < 2 or not parts[1].strip():
        return "⚠️ 使用格式错误！请使用：使用 商品名（如：使用 经验药水）"
    # 适配含艾特的情况 使用 XX[at:XX]
    good_name,target_qq = get_by_qq(msg)
    if not good_name in basket_data:
        return f"{user_name} 你未拥有该物品 {good_name}"
    shop_data = shop_manager.get_item_info(good_name)
    if not shop_data:
        return f"{user_name} 数据库不存在该物品 {good_name}"
    current_amount = basket_data.get(good_name, 0)
    if current_amount < 1:
        return f"{user_name} 你拥有的 {good_name} 数量不足（当前：{current_amount}）"

    good_category = shop_data.get("category")
    if good_category in ["gift","exp","stamina"]:
        user_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8",
        )

        if target_qq is None:
            # 如果使用对象未指定，则给自身使用
            target_qq = account
        account_data = user_manager.read_section(section=target_qq, create_if_not_exists=True)

        new_amount = current_amount - 1
        basket_manager.update_key(section=account,key=good_name,value=new_amount)

        goods_category = {
            "gift": {"account_key": "charm", "shop_key": "charm_value"},
            "exp": {"account_key": "exp", "shop_key": "exp_value"},
            "stamina": {"account_key": "stamina", "shop_key": "recover_value"},
        }
        category_info = goods_category.get(good_category)
        new_charm = account_data.get(category_info.get("account_key"), 0) + shop_data.get(category_info.get("shop_key"), 0)
        user_manager.update_key(section=target_qq,
                                key=category_info.get("account_key"),
                                value=new_charm)
        user_manager.save(encoding="utf-8")
        basket_manager.save(encoding="utf-8")
        return f"{user_name} 成功使用 {good_name}！"
    elif good_category in ("fishing_rod", "fishing_bait"):
        try:
            fish_manager = IniFileReader(
                project_root=path,
                subdir_name="City/Record",
                file_relative_path="Fish.data",
                encoding="utf-8",
            )
            fish_data = fish_manager.read_section(section=account, create_if_not_exists=True)
        except Exception as e:
            logger.error(f"初始化用于钓鱼系统数据错误：{str(e)}")
            return "系统繁忙，请稍后重试"

        if good_category == "fishing_rod":
            fish_manager.update_key(section=account,key="current_rod",value=good_name)
        elif good_category == "fishing_bait":
            fish_manager.update_key(section=account, key="current_bait", value=good_name)
        fish_manager.save(encoding="utf-8")
        return "使用成功！"
    return "意外的商品！无法使用！"

def rob_menu() -> str:
    return ("f⚔️ 打劫专区 ⚔️\n"
        f"—— 想当劫匪？先看清规则 ——\n"
        f"1.发起打劫[@目标]（入狱不可用）\n"
        f"👉 示例「打劫 @小明」→ 试试手气！\n"
        f"2.尝试越狱[工具 / 技能]\n"
        f"👉 示例「越狱」→ 搞点装备再跑\n"
        f"3.申请保释[好友]（入狱后解锁）\n"
        f"👉 示例「保释@对象」→ 拿钱换自由\n"
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

def fish_menu():
    return (
        "🌊 您现在在湖边钓鱼～\n"
        "当前可选择操作：\n"
        "▸ 抛竿（试试今天的手气！）\n"
        "▸ 提竿（看看钓到了什么～）\n"
        "▸ 我的鱼篓（检查战利品）\n"
        "▸ 我的鱼塘（罕见鱼存储地）\n"
        "▸ 钓鱼图鉴（了解鱼的信息）\n"
    )

def cast_fishing_rod(account:str, user_name:str, path) -> str:
    """
    钓鱼
    """
    try:
        fish_manager = IniFileReader(
            project_root=path,
            subdir_name="City/Record",
            file_relative_path="Fish.data",
            encoding="utf-8",
        )
        fish_data = fish_manager.read_section(section=account,create_if_not_exists=True)
        shop_manager = ShopFileHandler(
            project_root=path,
            subdir_name="City/Set_up",
            file_relative_path="Shop.res",
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"读取错误：{str(e)}")
        return "系统繁忙，请稍后重试！"
    user_rod = fish_data.get("current_rod")
    if not user_rod:
        return f"{user_name} 当前未使用鱼竿"
    user_bait = fish_data.get("current_bait")
    if not user_bait:
        return f"{user_name} 当前未使用鱼饵"

    rod_data = shop_manager.get_item_info(user_rod)
    now_time = time.time()
    end_min = random.randint(a = 12,b = 22)
    end_max = end_min + constants.FISH_TIME_INTERVAL + rod_data.get("time",0)
    fish_manager.update_section_keys(section=account, data={
        "fish":True,
        "start":now_time,
        "end_min":now_time + end_min,
        "end_max":now_time + end_max
    })

    return f"开始钓鱼了，请在{end_min}秒{end_max}后发送[提竿]"

def lift_rod(account:str, user_name:str, path) -> str:
    """手动释放用户（出狱）"""
    try:
        rob_manager = IniFileReader(
            project_root=path, subdir_name="City/Record", file_relative_path="Rob.data", encoding="utf-8"
        )
        # 检测当前入狱状态（可选）
        current_jail_time = rob_manager.read_key(section=account, key="jail_time",default=0)
        if current_jail_time <= 0:
            return f"{user_name} 你未入狱，无需出狱！"
        # 正确判断：入狱开始时间 + 刑期 > 当前时间 → 未服完刑
        if current_jail_time + constants.JAIL_TIME > time.time():
            remaining = int(current_jail_time + constants.JAIL_TIME - time.time())
            return f"{user_name} 未到出狱时间，还需服刑 {remaining} 秒！"

        user_manager = IniFileReader(
            project_root=path,subdir_name="City/Personal",file_relative_path="Briefly.info",encoding="utf-8"
        )
        user_stamina =user_manager.read_key(section=account, key="stamina",default=0)
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
    except Exception as e:
        logger.error(f"释放用户 {account} 失败: {e}")
        return "出狱过程中发生错误，请联系管理员。"
    pass

def my_creel(account:str, user_name:str, path) -> str:
    """手动释放用户（出狱）"""
    try:
        rob_manager = IniFileReader(
            project_root=path, subdir_name="City/Record", file_relative_path="Rob.data", encoding="utf-8"
        )
        # 检测当前入狱状态（可选）
        current_jail_time = rob_manager.read_key(section=account, key="jail_time",default=0)
        if current_jail_time <= 0:
            return f"{user_name} 你未入狱，无需出狱！"
        # 正确判断：入狱开始时间 + 刑期 > 当前时间 → 未服完刑
        if current_jail_time + constants.JAIL_TIME > time.time():
            remaining = int(current_jail_time + constants.JAIL_TIME - time.time())
            return f"{user_name} 未到出狱时间，还需服刑 {remaining} 秒！"

        user_manager = IniFileReader(
            project_root=path,subdir_name="City/Personal",file_relative_path="Briefly.info",encoding="utf-8"
        )
        user_stamina =user_manager.read_key(section=account, key="stamina",default=0)
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
    except Exception as e:
        logger.error(f"释放用户 {account} 失败: {e}")
        return "出狱过程中发生错误，请联系管理员。"
    pass

def my_pond(account:str, user_name:str, path) -> str:
    """手动释放用户（出狱）"""
    try:
        rob_manager = IniFileReader(
            project_root=path, subdir_name="City/Record", file_relative_path="Rob.data", encoding="utf-8"
        )
        # 检测当前入狱状态（可选）
        current_jail_time = rob_manager.read_key(section=account, key="jail_time",default=0)
        if current_jail_time <= 0:
            return f"{user_name} 你未入狱，无需出狱！"
        # 正确判断：入狱开始时间 + 刑期 > 当前时间 → 未服完刑
        if current_jail_time + constants.JAIL_TIME > time.time():
            remaining = int(current_jail_time + constants.JAIL_TIME - time.time())
            return f"{user_name} 未到出狱时间，还需服刑 {remaining} 秒！"

        user_manager = IniFileReader(
            project_root=path,subdir_name="City/Personal",file_relative_path="Briefly.info",encoding="utf-8"
        )
        user_stamina =user_manager.read_key(section=account, key="stamina",default=0)
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
    except Exception as e:
        logger.error(f"释放用户 {account} 失败: {e}")
        return "出狱过程中发生错误，请联系管理员。"
    pass

def fishing_encyclopedia(account:str, user_name:str, path) -> str:
    """手动释放用户（出狱）"""
    try:
        rob_manager = IniFileReader(
            project_root=path, subdir_name="City/Record", file_relative_path="Rob.data", encoding="utf-8"
        )
        # 检测当前入狱状态（可选）
        current_jail_time = rob_manager.read_key(section=account, key="jail_time",default=0)
        if current_jail_time <= 0:
            return f"{user_name} 你未入狱，无需出狱！"
        # 正确判断：入狱开始时间 + 刑期 > 当前时间 → 未服完刑
        if current_jail_time + constants.JAIL_TIME > time.time():
            remaining = int(current_jail_time + constants.JAIL_TIME - time.time())
            return f"{user_name} 未到出狱时间，还需服刑 {remaining} 秒！"

        user_manager = IniFileReader(
            project_root=path,subdir_name="City/Personal",file_relative_path="Briefly.info",encoding="utf-8"
        )
        user_stamina =user_manager.read_key(section=account, key="stamina",default=0)
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
    except Exception as e:
        logger.error(f"释放用户 {account} 失败: {e}")
        return "出狱过程中发生错误，请联系管理员。"
    pass
if __name__ == "__main__":
    pass