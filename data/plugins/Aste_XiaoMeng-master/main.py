from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
import asyncio
from astrbot.api import logger
import astrbot.api.message_components as Comp

from typing import Callable, Dict
import os
import sys
from pathlib import Path
import inspect

current_plugin_path = Path(__file__).resolve()
# 获取插件根目录（即 model 目录的父目录）
plugin_root = current_plugin_path.parent
# 将插件根目录添加到搜索路径的最前面（确保优先级）
sys.path.insert(0, str(plugin_root))

from model import city,data_managers

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
            self.job_manager = data_managers.JobFileHandler(
                project_root=self.directory ,
                subdir_name="City/Set_up",
                file_relative_path="Job.res",
                encoding="utf-8"
            )
            self.fish_manager = data_managers.FishFileHandler(
                project_root=self.directory ,
                subdir_name="City/Set_up",
                file_relative_path="Fish.res",
                encoding="utf-8"
            )
            self.game_manager = data_managers.GameUpdateManager()
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
        """极简事件处理器（自动参数匹配版，支持图片/文字响应）"""
        # ---------------------- 预处理上下文参数 ----------------------
        msg = event.get_message_str().strip()  # 去除首尾空格
        user_name = event.get_sender_name()
        user_account = event.get_sender_id()
        path = self.directory
        job_manager = self.job_manager
        fish_manager = self.fish_manager
        game_manager = self.game_manager

        # 上下文参数字典（所有可能的参数）
        ctx = {
            "account": user_account,
            "user_name": user_name,
            "msg": msg,
            "path": path,
            "job_manager": job_manager,
            "fish_manager": fish_manager,
            "game_manager": game_manager,
        }

        # ---------------------- 指令与处理函数映射（直接引用，无参数） ----------------------
        command_handlers: Dict[str, Callable] = {
            "小梦菜单": city.xm_main,
            "签到": city.check_in,
            "查询": city.query,
            "绑定": city.bind,
            #"打工菜单": city.work_menu,
            #"打工": city.work,
            #"加班": city.overwork,
            #"辞职": city.resign,
            #"跳槽": city.job_hopping,
            #"领工资": city.get_paid,
            #"找工作": city.job_hunting,
            #"查工作": city.check_job,
            #"投简历":  city.submit_resume,
            #"工作池": city.jobs_pool,
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
            "我的鱼篓": city.my_creel,
            "金币排行": city.gold_rank,  # 直接引用异步函数
            "魅力排行": city.charm_rank,  # 直接引用异步函数
            "游戏助手": city.game_menu,
            "更新公告": city.update_notice,
            "兑换代码": city.special_code,
        }

        # ---------------------- 匹配指令（优先完整匹配） ----------------------
        command = next((cmd for cmd in command_handlers if msg.startswith(cmd)), None)
        if not command:
            return  # 无匹配指令

        handler = command_handlers[command]

        try:
            # ---------------------- 自动推断参数并调用（核心逻辑） ----------------------
            # 获取函数参数签名（自动识别需要哪些参数）
            sig = inspect.signature(handler)
            params = sig.parameters

            # 动态生成参数值（按参数名从上下文中取）
            kwargs = {}
            for name in params:
                if name in ctx:
                    kwargs[name] = ctx[name]
                else:
                    # 缺失必要参数时抛出异常（明确提示）
                    raise ValueError(f"函数 {handler.__name__} 缺少必要参数: {name}")

            # 执行函数（同步/异步分离）
            if asyncio.iscoroutinefunction(handler):
                result  = await handler(**kwargs)  # 异步函数用 await
            else:
                result  = handler(**kwargs)  # 同步函数直接调用

            # 返回结果
            """
            chain = [
                Comp.At(qq=event.get_sender_id()),  # At 消息发送者
                Comp.Plain("来看这个图："),
                Comp.Image.fromURL("https://example.com/image.jpg"),  # 从 URL 发送图片
                Comp.Image.fromFileSystem("path/to/image.jpg"),  # 从本地文件目录发送图片
                Comp.Plain("这是一个图片。")
            ]
            yield event.chain_result(chain)
            """
            # ---------------------- 响应类型判断与构造 ----------------------
            if isinstance(result, str):
                # 情况1：返回的是图片 URL（网络地址）
                if result.startswith(("http://", "https://")):
                    chain = [
                        Comp.At(qq=event.get_sender_id()),  # @消息发送者
                        Comp.Plain("来看这个图："),
                        Comp.Image.fromURL(result),  # 从网络 URL 加载图片
                        Comp.Plain("（图片来自网络）")
                    ]
                    yield event.chain_result(chain)
                # 情况2：返回的是本地图片路径（需验证文件存在）
                elif result.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                    # 检查文件是否存在（可选，根据实际需求决定是否添加）
                    if Path(result).exists():
                        chain = [
                            # Comp.At(qq=event.get_sender_id()),  # @消息发送者
                            # Comp.Plain("来看这个图："),
                            Comp.Image.fromFileSystem(result),  # 从本地文件加载图片
                            # Comp.Plain("（图片来自本地存储）")
                        ]
                        yield event.chain_result(chain)
                    else:
                        yield event.plain_result(f"⚠️ 图片文件不存在：{result}")
                # 情况3：普通文字响应
                else:
                    yield event.plain_result(result)
            # 情况4：非字符串返回值（如二进制数据，需根据实际处理函数调整）
            else:
                yield event.plain_result(f"⚠️ 无效的返回类型：{type(result)}（仅支持字符串）")
        except Exception as e:
            logger.error(f"执行指令「{command}」失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"执行指令时出错：{str(e)}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""