# 模块常量
from decimal import Decimal, ROUND_HALF_UP  # 引入 Decimal 类型

ERROR_PREFIX = "❌ 操作提示"
SUCCESS_PREFIX = "✅ 操作完成"

# 签到奖励基础配置
CHECK_IN_FIRST_REWARD_GOLD = 500       # 首次签到奖励金币数
CHECK_IN_FIRST_REWARD_EXP = 100        # 首次签到奖励经验值
CHECK_IN_FIRST_REWARD_STAMINA = 68     # 首次签到奖励体力值

CHECK_IN_CONTINUOUS_REWARD_GOLD = 200  # 连续签到（非首次）奖励金币数
CHECK_IN_CONTINUOUS_REWARD_EXP = 28    # 连续签到（非首次）奖励经验值
CHECK_IN_CONTINUOUS_REWARD_STAMINA = 30 # 连续签到（非首次）奖励体力值

CHECK_IN_BREAK_REWARD_GOLD = 100       # 断签补偿金币数
CHECK_IN_BREAK_REWARD_EXP = 10         # 断签补偿经验值
CHECK_IN_BREAK_REWARD_STAMINA = 58    # 断签补偿体力值

WORK_DURATION_SECONDS = 3600                       # 单次打工任务的持续时间（单位：秒，当前为1小时）

JOB_HUNTING_PAGE_SIZE = 3   # 找工作每页显示数量
JOBS_POOL_PAGE_SIZE = 10   # 工作池每页显示数量
SUBMIT_RESUME_LIMIT = 5 # 投简历每日上限

# 工作异常状态（job_data不存在）
WORK_ERROR_TEXTS = [
    lambda user_name:
        f"{user_name} 检测到工作信息异常～可能是之前的工作已被撤销！系统已重置记录，快发送[找工作]找新机会吧～",
    lambda user_name:
        f"{user_name} 哎呀，工作数据好像丢失了～别慌，已自动清空旧记录，重新[找工作]就能恢复打工状态啦～",
    lambda user_name:
        f"注意！{user_name}的工作记录异常（可能是系统错误）～已帮你重置，发送[找工作]获取最新岗位列表吧～"
]
WORK_NO_JOB_TEXTS = [
    lambda user_name:
        f"{user_name} 现在还没有绑定任何工作哦～快发送[找工作]，看看附近有哪些适合的岗位在招人吧！",
    lambda user_name:
        f"嘿{user_name}，当前工位空着呢～输入[找工作]，说不定能刷到和你匹配的高薪工作！",
    lambda user_name:
        f"{user_name} 的打工档案还是空的？别犹豫，发送[找工作]开启你的第一份虚拟职业体验，比如'程序员、设计师'都很缺人哦～",
    lambda user_name:
        f"检测到{user_name}还未入职～是不是还在挑工作？发送[找工作]，'热门'岗位列表已为你准备好！"
]
# 开始工作状态
WORK_START_WORK_TEXTS = [
    lambda user_name,jobname:
        f"🎉 {user_name} 成功入职{jobname}！时钟开始转动，专注1小时就能领取今日工资啦～加油冲！",
    lambda user_name,jobname:
        f"叮咚～{user_name}的{jobname}工作签到成功！现在开始工作，1小时后工资自动到账～",
    lambda user_name,jobname:
        f"欢迎{user_name}加入{jobname}团队！工作倒计时启动，坚持1小时，工资马上到账～",
    lambda user_name,jobname:
        f"{user_name} 已选择{jobname}作为今日工作～倒计时开始，1小时后就能收获劳动成果啦！",
    lambda user_name,jobname:
        f"不错哦{user_name}！{jobname}的工作开始～就完事了～"
]
# 工作中剩余时间提示（动态计算）
WORK_WORKING_TEXTS = [
    lambda user_name, job_name, minutes_remaining:
        f"{user_name} 正在{job_name}岗位上专注工作～再坚持{minutes_remaining}分钟，就能下班领工资啦！加油！",
    lambda user_name, job_name, minutes_remaining:
        f"加油{user_name}！{job_name}的工作还剩{minutes_remaining}分钟，完成就能收获工资～坚持就是胜利～",
    lambda user_name, job_name, minutes_remaining:
        f"专注{user_name}！{job_name}岗位计时：剩余{minutes_remaining}分钟，工资马上到账～再忍忍哦～",
    lambda user_name, job_name, minutes_remaining:
        f"{user_name} 的{job_name}工作时间进度：还差{minutes_remaining}分钟完成～冲鸭，工资在向你招手！",
    lambda user_name, job_name, minutes_remaining:
        f"嘿{user_name}，{job_name}的工作还剩{minutes_remaining}分钟～坚持住，马上就能领工资喝奶茶啦～"
]
# 可领取工资状态（工作完成）
WORK_REWARD_READY_TEXTS = [
    lambda user_name,jobname:
        f"⏰ {user_name} 的{jobname}工作时间已满！点击[领工资]，辛苦1小时的报酬马上到账～",
    lambda user_name,jobname:
        f"完工！{user_name} 专注工作1小时，{jobname}的工资已备好，发送[领工资]就能领取啦～",
    lambda user_name,jobname:
        f"时间到～{user_name} 的{jobname}打工任务圆满完成！[领工资]按钮已点亮，速来查收工资～",
    lambda user_name,jobname:
        f"{user_name} 坚持了1小时{jobname}工作！系统检测到任务完成，现在发送[领工资]就能收获报酬啦～"
]
WORK_DATE_RESET_TIPS = [
    lambda user_name:f"🌞 新的一天开始啦！{user_name}昨天的工作记录已清空，快去[打工]领取今日份工资吧～",
    lambda user_name:f"📅 日期切换成功！{user_name}当前工作日期已重置，今天先去[打工]开始新的奋斗吧～",
    lambda user_name:f"⏰ 时间到啦！{user_name}昨天的工作已结束，今天重新[打工]1小时就能领工资咯～"
]

# 利率配置（年利率，使用 Decimal 保证精度）
LOAN_ANNUAL_INTEREST_RATE = Decimal('0.1')          # 贷款年利率（10%）
FIXED_DEPOSIT_ANNUAL_INTEREST_RATE = Decimal('0.04')# 定期存款年利率（4%）

# 金额/时间基准配置
DEPOSIT_MULTIPLE_BASE = 100                         # 存款/贷款/取款的最小额度（如：至少存100金币）
SECONDS_PER_YEAR = Decimal('31104000')              # 一年的总秒数（360天×86400秒/天，用于利息计算）

# 转账手续费配置
TRANSFER_PROCESSING_FEE_RATE = 0.05                 # 转账手续费率（5%，即转账金额的5%作为手续费）

ROB_SUCCESS_RATE = 50                  # 打劫基础成功率（50%）
JAIL_TIME = 60                         # 打劫失败入狱时长（单位：秒）
BAIL_FEE = 200                         # 保释费用
RELEASED_STAMINA = 2                   # 出狱消耗体力
ROB_STAMINA = 2                        # 打劫消耗体力
ROB_FAILURE_EVENTS = [                 # 打劫失败时的随机事件列表（含文案、体力消耗、金币变化）
    {"text": "🚔 打劫途中你被巡逻的警察发现了，不仅没抢到，还被罚了 10 金币！",
     "stamina_loss": 1, "coin_change": -10, "jail": False},
    {"text": "🛡 对方一直躲在安全屋，你根本找不到机会下手，空手而归...",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🏃 对方是逃跑专家，你刚靠近他就消失得无影无踪！",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "⚔️ 你试图动手，但对方反手制服了你，还抢走了你 8 金币！",
     "stamina_loss": 1, "coin_change": -8, "jail": False},
    {"text": "🌧️ 外面下起大雨，行动不便，你只好放弃这次打劫...",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🤖 你刚要动手，对方保镖突然出现，你只能灰溜溜地走了。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🍀 虽然没抢到，但你在地上捡到了别人掉落的 1 金币！算是安慰奖吧！",
     "stamina_loss": 1, "coin_change": 1, "jail": False},
]