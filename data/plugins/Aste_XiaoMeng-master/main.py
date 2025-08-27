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
        msg = event.get_message_str().strip()  # 去除首尾空格
        user_name = event.get_sender_name()
        user_account = event.get_sender_id()

        # 定义指令与处理函数的映射（直接引用函数，而非lambda）
        command_handlers: Dict[str, Callable] = {
            "小梦菜单": city.xm_main,
            "签到": city.check_in,
            "查询": city.query,
            "绑定": city.bind,
            "打工菜单": city.work_menu,
            "打工": city.work,
            "加班": city.overwork,
            "辞职": city.resign,
            "跳槽": city.job_hopping,
            "领工资": city.get_paid,
            "找工作": city.job_hunting,
            "查工作": city.check_job,
            "投简历":  city.submit_resume,
            "工作池": city.jobs_pool,
            "银行菜单": city.bank_menu,
            "存款": city.deposit,
            "取款": city.withdraw,
            "贷款": city.loan,
            "还款": city.repayment,
            "存定期": city.fixed_deposit,
            "取定期": city.redeem_fixed_deposit,
            "查存款": city.check_deposit,
            "转账": city.transfer,
            "商店菜单": city.shop_menu,
            "商店": city.shop,
            "查商品": city.check_goods,
            "购买": city.purchase,
            "背包": city.basket,
            "使用": city.use,
            "打劫菜单": city.rob_menu,
            "打劫": city.rob,
            "保释": city.post_bail,
            "越狱": city.prison_break,
            "出狱": city.released,
            "钓鱼菜单": city.fish_menu,
            "钓鱼": city.cast_fishing_rod,
            "提竿": city.lift_rod,
            "金币排行": city.gold_rank,  # 直接引用异步函数
        }

        # 匹配指令（优先完整匹配）
        command = next((cmd for cmd in command_handlers if msg.startswith(cmd)), None)
        if not command:
            return  # 无匹配指令，不响应

        handler = command_handlers[command]
        try:
            # 执行函数（同步/异步分离）
            if asyncio.iscoroutinefunction(handler):
                # 异步函数（无参数，直接 await）
                if command in ["金币排行"]:
                    text = await handler(user_account,user_name,self.directory)
            else:
                # 同步函数（根据参数数量传递参数）
                if command in ["小梦菜单", "打工菜单","银行菜单","商店菜单","打劫菜单","钓鱼菜单"]:
                    # 无参数函数
                    text = handler()
                elif command in ["签到", "查询", "取定期","查存款","背包","越狱","出狱","钓鱼"]:
                    # 3 个参数：account, user_name, path
                    text = handler(user_account, user_name, self.directory)
                elif command in ["绑定","存款","取款","还款","贷款","取定期","转账","购买","使用","打劫","保释"]:
                    # 4 个参数：account, user_name, msg, path
                    text = handler(user_account, user_name, msg, self.directory)
                elif command in ["打工", "加班", "跳槽", "辞职", "领工资"]:
                    # 4 个参数：account, user_name, path, job_data
                    text = handler(user_account,user_name, self.directory,self.job_manager)
                elif command in ["找工作", "查工作", "工作池"]:
                    # 2 个参数：msg, job_data
                    text = handler(msg,self.job_manager)
                elif command in ["投简历"]:
                    # 5 个参数：account, user_name, msg, path, job_data
                    text = handler(user_account,user_name,msg, self.directory,self.job_manager)
                elif command in ["商店","查商品"]:
                    # 2 个参数：msg, path
                    text = handler(msg, self.directory)
                elif command in ["提竿"]:
                    # 2 个参数：msg, path
                    text = handler(user_account,user_name,msg,self.fish_manager)
                else:
                    # 其他情况（根据实际函数补充）
                    text = handler()
            # 返回结果
            yield event.plain_result(text)
        except Exception as e:
            logger.error(f"执行指令「{command}」失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"执行指令时出错：{str(e)}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""