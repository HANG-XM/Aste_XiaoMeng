# 模块常量
from decimal import Decimal  # 引入 Decimal 类型

ERROR_PREFIX = "❌ 操作提示"
SUCCESS_PREFIX = "✅ 操作完成"

# 签到奖励基础配置
CHECK_IN_FIRST_REWARD_GOLD = 500       # 首次签到奖励金币数
CHECK_IN_FIRST_REWARD_EXP = 100        # 首次签到奖励经验值
CHECK_IN_FIRST_REWARD_STAMINA = 68     # 首次签到奖励体力值
# 首次签到提示
CHECK_IN_FIRST_TIPS = [
    lambda user_name,reward_coin,reward_exp,reward_stamina:
        f"🎉 {user_name}第一次签到成功！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，开启打工人的第一天～",
    lambda user_name, reward_coin, reward_exp, reward_stamina:
        f"🌟 恭喜{user_name}完成首次签到！{reward_coin}金币已到账，经验+{reward_exp}，体力+{reward_stamina}，继续加油哦～",
    lambda user_name, reward_coin, reward_exp, reward_stamina:
        f"🎊 {user_name}来啦！首次签到奖励已发放，{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，打工之路正式启程～"
]

CHECK_IN_CONTINUOUS_REWARD_GOLD = 200  # 连续签到（非首次）奖励金币数
CHECK_IN_CONTINUOUS_REWARD_EXP = 28    # 连续签到（非首次）奖励经验值
CHECK_IN_CONTINUOUS_REWARD_STAMINA = 30 # 连续签到（非首次）奖励体力值
CHECK_IN_CONTINUOUS_TIPS = [  # 连续签到提示
    lambda user_name, continuous_days, reward_coin, reward_exp, reward_stamina:
        f"🔥 {user_name}连续签到{continuous_days}天！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，离全勤奖又近一步～",
    lambda user_name, continuous_days, reward_coin, reward_exp, reward_stamina:
        f"✅ {user_name}今日连签成功！连续{continuous_days}天，金币+{reward_coin}，经验+{reward_exp}，体力+{reward_stamina}，稳住别断～",
    lambda user_name, continuous_days, reward_coin, reward_exp, reward_stamina:
        f"💪 {user_name}连签记录更新！{continuous_days}天不停歇，奖励已到账，继续冲～"
]
CHECK_IN_BREAK_REWARD_GOLD = 100       # 断签补偿金币数
CHECK_IN_BREAK_REWARD_EXP = 10         # 断签补偿经验值
CHECK_IN_BREAK_REWARD_STAMINA = 58    # 断签补偿体力值
CHECK_IN_BREAK_TIPS = [  # 断签后签到提示
    lambda user_name, reward_coin, reward_exp, reward_stamina:
        f"🔄 {user_name}今日重新签到！虽然断了1天，但奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力已发放，明天继续连签吧～",
    lambda user_name, reward_coin, reward_exp, reward_stamina:
        f"⏳ {user_name}断签后归来！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，连续天数重置为1，今天开始重新累积～",
    lambda user_name, reward_coin, reward_exp, reward_stamina:
        f"🌱 {user_name}今日首次签到（上次断签）！奖励{reward_coin}金币+{reward_exp}经验+{reward_stamina}体力，坚持就是胜利～"
]


CHECK_IN_RANDOM_TIPS = [
    "⌈找工作⌋ 可以寻找心仪的工作哦",
    "⌈查询⌋ 可以查询当前的个人信息",
    "⌈背包⌋ 可以查看从商店购买的物品",
    "⌈领工资⌋ 可以领取辛勤工作的奖励",
    "预防⌈商店⌋商品不足 尽量提前购买哦",
]

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
# 没有工作
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
# 开始打工状态
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
# 开始加班状态
WORK_START_WORKOVER_TEXTS = [
    lambda user_name, jobname:
        f"{user_name}，你开始加班了哦～现在开始工作{jobname}，1小时后就能领工资啦！",
    lambda user_name, jobname:
        f"🚀 加班倒计时开始！{user_name}确认开始工作{jobname}，1小时后收获今日工资～",
    lambda user_name, jobname:
        f"💼 {jobname}工作已就绪！{user_name}现在开始加班，1小时后即可领取劳动所得～"
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
        f"嘿{user_name}，{job_name}的工作还剩{minutes_remaining}分钟～坚持住，马上就能领工资喝奶茶啦～",
    lambda user_name, job_name, minutes_remaining:
        f"{user_name}，工作还没做完呢！再坚持{minutes_remaining}分钟，完成就能领工资啦～",
    lambda user_name, job_name, minutes_remaining:
        f"别着急～{user_name}再工作{minutes_remaining}分钟，就能拿到今天的工资啦，冲就完事！"
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
# 需加班状态（次数超限）
WORK_OVER_TEXTS = [
    lambda user_name,jobname:
        f"{user_name} 今日{jobname}打工次数已达上限～想继续赚钱？发送[加班]，开启额外工作模式吧～",
    lambda user_name,jobname:
        f"次数已满{user_name}～但勤劳的人值得更多！发送[加班]，继续为{jobname}奋斗多赚一份工资～",
    lambda user_name,jobname:
        f"{user_name} 今天的{jobname}打工次数用完啦～要挑战[加班]模式，再赚一波吗？多劳多得哦～",
    lambda user_name,jobname:
        f"叮～{user_name}，{jobname}今日打工次数已达上限～发送[加班]，解锁隐藏的「加班工资」吧～"
]
# 新的一天建议打工
WORK_DATE_RESET_TIPS = [
    lambda user_name:f"🌞 新的一天开始啦！{user_name}昨天的工作记录已清空，快去[打工]领取今日份工资吧～",
    lambda user_name:f"📅 日期切换成功！{user_name}当前工作日期已重置，今天先去[打工]开始新的奋斗吧～",
    lambda user_name:f"⏰ 时间到啦！{user_name}昨天的工作已结束，今天重新[打工]1小时就能领工资咯～"
]
# 投简历次数超限提示（当日投递超过时触发）
SUBMIT_RESUME_LIMIT_TEXTS = [
    lambda user_name,current_submit_num:
        f"{user_name}今日已投递{current_submit_num}份简历，HR小姐姐说太多了～明天再来刷新记录吧！",
    lambda user_name, current_submit_num:
        f"今日投递额度已达{current_submit_num}次上限～{user_name}先歇会儿，明天此时再发送'投简历 X'试试～",
    lambda user_name, current_submit_num:
        f"{user_name}你已经投了{current_submit_num}份啦！今天的简历通道即将关闭，明天再来投递新岗位～"
]
# 成功领取工资
GET_PAID_SUCCESS_TEXTS = [
    lambda user_name, job_salary:
        f"🎉 {user_name}工资到账！辛苦搬砖{WORK_DURATION_SECONDS}小时，获得{job_salary}金币～新钱包已鼓起，冲鸭！",
    lambda user_name, job_salary:
        f"✨ {user_name}今日份努力有回报！领工资啦～{job_salary}金币已到账，够不够买杯奶茶奖励自己？",
    lambda user_name, job_salary:
        f"🚀 {user_name}完成工作！工资发放成功～{job_salary}金币入账，打工人的快乐就是这么简单～"
]
# 辞职缴纳费用失败
RESIGN_NOT_ENOUGH_TEXTS = [
    lambda user_name, resign_gold, user_gold:
        f"{user_name} 辞职需要赔偿{resign_gold}金币，但你只有{user_gold}金币～再攒攒再辞职吧！",
    lambda user_name, resign_gold, user_gold:
        f"{user_name} 老板说离职要赔{resign_gold}金币，你钱包不够呀～要不先[打工]赚点金币？",
    lambda user_name, resign_gold, user_gold:
        f"赔偿金额{resign_gold}金币超过你的钱包啦～{user_name}再工作几天凑够钱再辞职！"
]
# 辞职成功提示
RESIGN_SUCCESS_TEXTS = [
    lambda user_name, resign_gold, user_gold:
        f"📝 {user_name}提交辞职申请成功！系统自动扣除{resign_gold}金币作为违约金～",
    lambda user_name, resign_gold, user_gold:
        f"✅ 辞职流程完成！{user_name}已清空当前工作记录，赔偿{resign_gold}金币后余额为{user_gold}～",
    lambda user_name, resign_gold, user_gold:
        f"🚪 {user_name}正式离职！违约金{resign_gold}金币已扣除，随时可以重新找工作啦～"
]

JOB_HOPPING_MAX_POSITION_TEXTS = [
    lambda user_name:
        f"厉害！{user_name}已经是当前行业的天花板了～暂时没有更高的职位等你挑战啦！",
    lambda user_name:
        f"{user_name}已登顶该行业，现有岗位中没有能匹配你能力的新选择，继续保持优势吧～",
    lambda user_name:
        f"{user_name}你已经是这个领域的顶尖选手啦！当前没有更适合的高阶职位，享受你的王者时刻～"
]
JOB_HOPPING_LIMIT_TEXTS = [
    lambda user_name:
        f"{user_name}，今天已经跳过一次槽啦！职场如战场，稳扎稳打更重要，明天再来尝试吧～",
    lambda user_name:
        f"今日跳槽额度已用完～{user_name}先在新岗位上积累经验，明天再挑战更好的机会！",
    lambda user_name:
        f"跳槽冷却时间未到哦～{user_name}今天先好好工作，明天此时再发送[跳槽]刷新记录～"
]
JOB_HOPPING_FAILED_TEXTS = [
    lambda user_name:
        f"{user_name}这次跳槽差了点火候～再提升下等级/经验/魅力/金币，下次一定能拿下更好的岗位！",
    lambda user_name:
        f"新岗位的要求还没完全满足哦～当前{user_name}的等级/经验/魅力/金币还差一点，继续加油冲！",
    lambda user_name:
        f"跳槽失败～新公司的HR觉得你还可以更优秀！提升下属性，下次带着更亮眼的数据来应聘吧～"
]
JOB_HOPPING_SUCCESS_TEXTS = [
    lambda user_name:
        f"🎉恭喜{user_name}！跳槽成功！新公司的offer已送达，准备好迎接新挑战了吗？",
    lambda user_name:
        f"✨{user_name}今日职场进阶！成功入职新岗位，新的同事和项目正在等你解锁～",
    lambda user_name:
        f"🚀{user_name}完成完美跳槽！从今天起，你将以更优的身份开启职业新篇章，冲就完事！"
]

# 利率配置（年利率，使用 Decimal 保证精度）
LOAN_ANNUAL_INTEREST_RATE = Decimal('0.1')          # 贷款年利率（10%）
FIXED_DEPOSIT_ANNUAL_INTEREST_RATE = Decimal('0.04')# 定期存款年利率（4%）

# 金额/时间基准配置
DEPOSIT_MULTIPLE_BASE = 100                         # 存款/贷款/取款的最小额度（如：至少存款100个金币）
FIXED_DEPOSIT_MULTIPLE_BASE = 10000                 # 存定期的最小额度（如：至少存款10000个金币）
SECONDS_PER_YEAR = Decimal('31104000')              # 一年的总秒数（360天×86400秒/天，用于利息计算）

# 转账手续费配置
TRANSFER_PROCESSING_FEE_RATE = 0.05                 # 转账手续费率（5%，即转账金额的5%作为手续费）

ROB_SUCCESS_RATE = 50                  # 打劫基础成功率（50%）
PRISON_BREAK_SUCCESS_RATE = 50         # 越狱基础成功率（50%）
JAIL_TIME = 60                         # 打劫失败入狱时长（单位：秒）
BAIL_FEE = 200                         # 保释费用
RELEASED_STAMINA = 2                   # 出狱消耗体力
PRISON_BREAK_STAMINA = 3               # 越狱消耗体力
ROB_STAMINA = 2                        # 打劫消耗体力
ROB_SUCCESS_EVENTS = [  # 打劫成功时的随机事件列表（含文案、体力消耗、金币变化）
    lambda user_name, robbed_name, coin_amount:
        {"text": f"💰 {user_name} 成功打劫了 {robbed_name}，抢到 {coin_amount} 金币！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🎯 {user_name} 计划周密，悄无声息地从 {robbed_name} 手中夺走了 {coin_amount} 金币！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🕶️ {user_name} 化身夜行侠，趁 {robbed_name} 不备，轻松拿下 {coin_amount} 金币！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🤑 {user_name} 运气爆棚，{robbed_name} 钱包大开，{coin_amount} 金币到手！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🦹‍♂️ {user_name} 展现高超身手，{robbed_name} 还没反应过来，{coin_amount} 金币已被顺走！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🎩 {user_name} 乔装打扮，骗过了 {robbed_name}，成功获得 {coin_amount} 金币！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🚗 {user_name} 打劫后迅速驾车离开，{robbed_name} 只能目送 {coin_amount} 金币远去！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🧤 {user_name} 动作干净利落，{robbed_name} 毫无察觉，{coin_amount} 金币轻松到手！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🎲 {user_name} 赌上一把，结果大获全胜，从 {robbed_name} 那里赢得 {coin_amount} 金币！"},
    lambda user_name, robbed_name, coin_amount:
        {"text": f"🕵️‍♂️ {user_name} 伪装成侦探，巧妙骗取了 {robbed_name} 的 {coin_amount} 金币！"},
]
ROB_FAILURE_EVENTS = [                 # 打劫失败时的随机事件列表（含文案、体力消耗、金币变化、入狱）
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
    {"text": "😱 你刚靠近目标，对方突然大喊“抓小偷！”，你吓得拔腿就跑，体力消耗不少。",
     "stamina_loss": 2, "coin_change": 0, "jail": False},
    {"text": "🚨 警报响起，附近巡逻机器人将你驱赶离开，什么都没捞到。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🪤 你踩到了对方设下的陷阱，狼狈逃脱，损失了 5 金币。",
     "stamina_loss": 1, "coin_change": -5, "jail": False},
    {"text": "👮‍♂️ 警察突然出现，你被带去警局问话，耽误了不少时间。",
     "stamina_loss": 2, "coin_change": 0, "jail": False},
    {"text": "🧱 你翻墙时裤子被钩破了，除了丢脸什么都没得到。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🧑‍⚖️ 路人见义勇为将你拦下，你只好灰溜溜地离开。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🔒 目标家门紧锁，你连门都没摸到。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🥚 你被泼了一身脏水，什么都没抢到还丢了面子。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
    {"text": "🚓 你被便衣警察盯上，直接被送进了监狱！",
     "stamina_loss": 2, "coin_change": -20, "jail": True},
    {"text": "🪙 虽然没抢到，但在慌乱中捡到2枚硬币，聊胜于无。",
     "stamina_loss": 1, "coin_change": 2, "jail": False},
    {"text": "🦶 你刚想动手，结果被对方一脚踹飞，损失了 3 金币。",
     "stamina_loss": 1, "coin_change": -3, "jail": False},
    {"text": "🧃 你被对方泼了一杯饮料，狼狈逃走，啥也没捞到。",
     "stamina_loss": 1, "coin_change": 0, "jail": False},
]

FISH_TIME_INTERVAL = 5                   # 钓鱼时间间隔
FISH_TIME_START = 12                     # 钓鱼开始时间
FISH_TIME_END = 22                       # 钓鱼结束时间
FISH_STAMINA = 2                         # 钓鱼消耗体力

RANK_TOP_N = 8                           # 排行显示个数

SHOP_ITEMS_PER_PAGE = 7                  # 商店每页显示个数