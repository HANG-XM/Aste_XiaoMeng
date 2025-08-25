# 模块常量
from decimal import Decimal, ROUND_HALF_UP  # 引入 Decimal 类型

ERROR_PREFIX = "❌ 操作提示"
SUCCESS_PREFIX = "✅ 操作完成"

# 签到奖励基础配置
CHECK_IN_FIRST_REWARD_GOLD = 500       # 首次签到奖励金币数
CHECK_IN_FIRST_REWARD_EXP = 100        # 首次签到奖励经验值
CHECK_IN_FIRST_REWARD_STAMINA = 98     # 首次签到奖励体力值

CHECK_IN_CONTINUOUS_REWARD_GOLD = 200  # 连续签到（非首次）奖励金币数
CHECK_IN_CONTINUOUS_REWARD_EXP = 30    # 连续签到（非首次）奖励经验值
CHECK_IN_CONTINUOUS_REWARD_STAMINA = 30 # 连续签到（非首次）奖励体力值

CHECK_IN_BREAK_REWARD_GOLD = 100       # 断签补偿金币数
CHECK_IN_BREAK_REWARD_EXP = 10         # 断签补偿经验值
CHECK_IN_BREAK_REWARD_STAMINA = 100    # 断签补偿体力值

WORK_DURATION_SECONDS = 3600                       # 单次打工任务的持续时间（单位：秒，当前为1小时）

JOB_HUNTING_PAGE_SIZE = 3   # 找工作每页显示数量
JOBS_POOL_PAGE_SIZE = 10   # 工作池每页显示数量

SUBMIT_RESUME_LIMIT = 5 # 投简历每日上限

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
ROB_FAILURE_EVENTS = [                 # 打劫失败时的随机事件列表（含文案、体力消耗、金币变化）
    {"text": "🚔 打劫途中你被巡逻的警察发现了，不仅没抢到，还被罚了 10 金币！",
     "stamina_loss": 1, "coin_change": -10},
    {"text": "🛡 对方一直躲在安全屋，你根本找不到机会下手，空手而归...",
     "stamina_loss": 1, "coin_change": 0},
    {"text": "🏃 对方是逃跑专家，你刚靠近他就消失得无影无踪！",
     "stamina_loss": 1, "coin_change": 0},
    {"text": "⚔️ 你试图动手，但对方反手制服了你，还抢走了你 8 金币！",
     "stamina_loss": 1, "coin_change": -8},
    {"text": "🌧️ 外面下起大雨，行动不便，你只好放弃这次打劫...",
     "stamina_loss": 1, "coin_change": 0},
    {"text": "🤖 你刚要动手，对方保镖突然出现，你只能灰溜溜地走了。",
     "stamina_loss": 1, "coin_change": 0},
    {"text": "🍀 虽然没抢到，但你在地上捡到了别人掉落的 1 金币！算是安慰奖吧！",
     "stamina_loss": 1, "coin_change": 1},
]