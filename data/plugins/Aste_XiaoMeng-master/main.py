from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
import asyncio
from astrbot.api import logger

from typing import Callable, Dict, Any
import os
import sys
from pathlib import Path

current_plugin_path = Path(__file__).resolve()
# 获取插件根目录（即 model 目录的父目录）
plugin_root = current_plugin_path.parent
# 将插件根目录添加到搜索路径的最前面（确保优先级）
sys.path.insert(0, str(plugin_root))

from model import city,directory

@register("xiaomeng", "awan", "xiaomeng", "1.0.0")
class XIAOMENG(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context  # 保留但未使用（根据用户要求）
        self.directory: Path = Path()   # 最终数据目录路径

        try:
            # 1. 获取当前工作目录（基于 os.getcwd()，转换为 Path 对象）
            workdir = Path(os.getcwd())  # 关键：os.getcwd() 结果转为 Path
            logger.debug(f"当前工作目录（Path 对象）: {workdir}")

            # 2. 构造插件数据目录路径（Path 拼接，跨平台兼容）
            # 示例结构：当前工作目录/plugin_data/HANG-XM/Data
            relative_path = Path("data")/ "plugin_data" / "HANG-XM" / "Data"  # 相对路径拆分为 Path 对象
            self.directory = workdir / relative_path  # 拼接为完整路径（Path 对象）

            # 3. 确保目录存在且可写（使用 Path 方法）
            self._prepare_directory(self.directory)
            logger.info(f"插件数据目录初始化完成")

        except Exception as e:
            logger.error(f"插件数据目录初始化失败（关键错误）: {str(e)}", exc_info=True)  # 记录完整异常栈
            raise RuntimeError("插件初始化失败，请检查目录配置或当前工作目录") from e  # 友好提示

        try:
            # 初始化数据
            self.job_manager = directory.JobFileHandler(
                project_root=self.directory ,
                subdir_name="City/Set_up",
                file_relative_path="Job.res",
                encoding="utf-8"
            )
            self.fish_manager = directory.FishFileHandler(
                project_root=self.directory ,
                subdir_name="City/Set_up",
                file_relative_path="Fish.res",
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"插件数据初始化失败（关键错误）: {str(e)}", exc_info=True)  # 记录完整异常栈
            raise RuntimeError("插件数据初始化失败，请检查目录配置或当前工作目录") from e  # 友好提示

    def _prepare_directory(self, target_dir: Path) -> None:
        """确保目标目录（Path 对象）存在且可写"""
        try:
            # 创建目录（忽略已存在的情况，自动处理跨平台分隔符）
            target_dir.mkdir(parents=True, exist_ok=True)  # Path 的 mkdir 方法（支持 parents 和 exist_ok）
            logger.debug(f"目录已创建或已存在: {target_dir}")

            # 验证目录是否存在（Path 的 is_dir 方法）
            if not target_dir.is_dir():
                raise RuntimeError(f"目录创建后验证失败（路径不存在）: {target_dir}")

            # 验证可写权限（转换为字符串路径，或使用 Path 的 stat 方法）
            if not os.access(str(target_dir), os.W_OK):
                raise PermissionError(f"目录无写入权限: {target_dir}")

        except PermissionError as pe:
            logger.error(f"权限不足，无法创建/访问目录 {target_dir}: {str(pe)}")
            raise  # 权限问题无法解决，直接终止
        except Exception as e:
            logger.error(f"目录初始化失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"无法初始化目录 {target_dir}") from e

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """事件处理器"""
        msg = event.get_message_str()
        user_name = event.get_sender_name()
        user_account = event.get_sender_id()

        # 定义指令与处理函数的映射（核心优化：字典调度）
        command_handlers: Dict[str, Callable[[], str]] = {
            "小梦菜单":lambda: city.xm_main(),
            "签到": lambda: city.check_in(user_account,user_name,self.directory),
            "查询": lambda: city.query(user_account,user_name,self.directory),
            "绑定": lambda: city.bind(user_account,user_name,msg,self.directory),
            "打工菜单": lambda: city.work_menu(),
            "打工": lambda: city.work(user_account,user_name,self.directory,self.job_manager),
            "加班": lambda: city.overwork(user_account,user_name,self.directory,self.job_manager),
            "辞职": lambda: city.resign(user_account,user_name,self.directory,self.job_manager),
            "跳槽": lambda: city.job_hopping(user_account,user_name,self.directory,self.job_manager),
            "领工资": lambda: city.get_paid(user_account,user_name,self.directory,self.job_manager),
            "找工作": lambda: city.job_hunting(msg,self.job_manager),
            "查工作": lambda: city.check_job(msg,self.job_manager),
            "投简历":  lambda :city.submit_resume(user_account,user_name,msg,self.directory,self.job_manager),
            "工作池": lambda: city.jobs_pool(msg,self.directory,self.job_manager),
            "银行菜单": lambda: city.bank_menu(),
            "存款": lambda: city.deposit(user_account, user_name, msg,self.directory),
            "取款": lambda: city.withdraw(user_account,user_name,msg,self.directory),
            "贷款":lambda :city.loan(user_account,user_name,msg,self.directory),
            "还款":lambda :city.repayment(user_account,user_name,msg,self.directory),
            "存定期": lambda: city.fixed_deposit(user_account,user_name,msg,self.directory),
            "取定期": lambda: city.redeem_fixed_deposit(user_account,user_name,self.directory),
            "查存款":lambda :city.check_deposit(user_account,user_name,self.directory),
            "转账":lambda :city.transfer(user_account,user_name,msg,self.directory),
            "商店菜单":lambda :city.shop_menu(),
            "商店": lambda: city.shop(msg,self.directory),
            "查商品": lambda: city.check_goods(msg,self.directory),
            "购买": lambda: city.purchase(user_account,user_name,msg,self.directory),
            "背包": lambda: city.basket(user_account, user_name, self.directory),
            "使用": lambda: city.use(user_account, user_name,msg,self.directory),
            "打劫菜单": lambda: city.rob_menu(),
            "打劫": lambda: city.rob(user_account,user_name,msg,self.directory),
            "保释": lambda: city.post_bail(user_account,user_name,msg,self.directory),
            "越狱": lambda: city.prison_break(user_account,user_name,self.directory),
            "出狱": lambda: city.released(user_account,user_name,self.directory),
            "钓鱼菜单":lambda :city.fish_menu(),
            "钓鱼":lambda: city.cast_fishing_rod(user_account,user_name,self.directory),
            "提竿":lambda: city.lift_rod(user_account,user_name,self.directory,self.fish_manager),
            "金币排行":lambda: city.gold_rank(user_account,user_name,self.directory),
        }

        # 查找匹配的处理函数
        handler: Callable[..., Any] = command_handlers.get(msg.split()[0] if msg else "")  # 提取指令关键词

        # 执行处理函数（兼容同步/异步方法）
        if handler is None:
            pass
        else:
            if asyncio.iscoroutinefunction(handler):
                text = await handler()
            else:
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(None, handler)
            yield event.plain_result(text)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""