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
        """主消息处理器，负责协调各个处理步骤"""
        # 1. 准备上下文
        context = self._prepare_context(event)
        if not context["msg"]:  # 空消息直接返回
            return
        
        # 2. 获取指令处理器
        command_handlers = self._get_command_handlers()
        
        # 3. 匹配指令
        command = self._match_command(context["msg"], command_handlers)
        if not command:
            return  # 无匹配指令
        
        # 4. 执行处理函数并生成响应
        handler = command_handlers[command]
        try:
            result = await self._execute_handler(handler, context)
            async for response in self._generate_response(event, result, command):
                yield response
        except Exception as e:
            logger.error(f"执行指令「{command}」失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"执行指令时出错：{str(e)}")

    def _prepare_context(self, event: AstrMessageEvent) -> dict:
        """准备处理消息所需的上下文参数"""
        msg = event.get_message_str().strip()
        user_name = event.get_sender_name()
        user_account = event.get_sender_id()
        
        return {
            "account": user_account,
            "user_name": user_name,
            "msg": msg,
            "path": self.directory,
            "job_manager": self.job_manager,
            "fish_manager": self.fish_manager,
            "game_manager": self.game_manager,
        }

    def _get_command_handlers(self) -> Dict[str, Callable]:
        """获取指令与处理函数的映射"""
        return {
            "小梦菜单": city.xm_main,
            "签到": city.check_in,
            "查询": city.query,
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
            "金币排行": city.gold_rank,
            "魅力排行": city.charm_rank,
            "游戏助手": city.game_menu,
            "游戏绑定": city.bind,
            "更新公告": city.update_notice,
            "逃少代码": city.special_code,
            "​鼠鼠密码": city.delta_special_code,
            "历史事件": city.history_event,
        }

    def _match_command(self, msg: str, command_handlers: Dict[str, Callable]) -> str:
        """匹配用户输入的指令"""
        return next((cmd for cmd in command_handlers if msg.startswith(cmd)), None)

    async def _execute_handler(self, handler: Callable, context: dict):
        """执行处理函数并返回结果"""
        # 获取函数参数签名
        sig = inspect.signature(handler)
        
        # 只提取函数需要的参数
        kwargs = {name: context[name] for name in sig.parameters if name in context}
        
        # 检查是否有缺失的必要参数
        missing_params = [
            name for name in sig.parameters 
            if name not in context and sig.parameters[name].default == inspect.Parameter.empty
        ]
        if missing_params:
            raise ValueError(f"函数 {handler.__name__} 缺少必要参数: {', '.join(missing_params)}")
        
        # 执行函数（同步/异步分离）
        if asyncio.iscoroutinefunction(handler):
            return await handler(**kwargs)
        else:
            return handler(**kwargs)



    async def _generate_response(self, event: AstrMessageEvent, result, command: str):
        """根据处理函数的结果生成响应"""
        if result is None:
            return  # 处理函数可能不需要响应
        
        # 响应类型判断与构造
        if isinstance(result, str):
            # 情况1：返回的是图片 URL（网络地址）
            if result.startswith(("http://", "https://")):
                chain = [
                    Comp.Image.fromURL(result)  # 从网络 URL 加载图片
                ]
                yield event.chain_result(chain)
            # 情况2：返回的是本地图片路径（需验证文件存在）
            elif result.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                # 检查文件是否存在
                image_path = Path(result)
                if image_path.exists():
                    chain = [
                        Comp.Image.fromFileSystem(result)  # 从本地文件加载图片
                    ]
                    yield event.chain_result(chain)
                else:
                    yield event.plain_result(f"⚠️ 图片文件不存在：{result}")
            # 情况3：普通文字响应
            else:
                yield event.plain_result(result)
        # 情况4：非字符串返回值
        else:
            yield event.plain_result(f"⚠️ 无效的返回类型：{type(result)}（仅支持字符串）")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""