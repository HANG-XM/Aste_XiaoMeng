from typing import List
from astrbot.api import logger

from model import constants
from model.directory import IniFileReader,ShopFileHandler
from model.city_func import get_by_qq

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

def shop(msg, path) -> str:

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
        total_pages = (total_items +  constants.SHOP_ITEMS_PER_PAGE - 1) //  constants.SHOP_ITEMS_PER_PAGE
        return (
            f"📦 小梦商店总览\n"
            f"总商品数：{total_items} 件\n"
            f"总页数：{total_pages} 页\n"
            f"每页显示 {constants.SHOP_ITEMS_PER_PAGE} 件\n"
            f"类别：游戏/礼物/鱼竿/鱼饵/体力/经验\n"
            f"指令：'商店 X' X为类别/页数\n"
            f"其他指令：购买/查商品/背包/使用"
        )

    # ====================== 模式二：分页查询 ======================
    if param.isdigit():
        page = int(param)
        total_items = len(shop_handler.data)
        total_pages = (total_items +  constants.SHOP_ITEMS_PER_PAGE - 1) //  constants.SHOP_ITEMS_PER_PAGE

        # 页码有效性检查
        if page < 1:
            return "❌ 页码错误：页码不能小于1"
        if page > total_pages:
            return f"❌ 页码错误：当前只有 {total_pages} 页"

        # 计算分页数据
        start = (page - 1) *  constants.SHOP_ITEMS_PER_PAGE
        end = start +  constants.SHOP_ITEMS_PER_PAGE
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
        return "想要购买什么呢？发送[商店]查看心仪的商品吧！\n购买格式示例：购买 小心心"

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
        hint += "\n发送[商店]查看所有商品"
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
    }.get(goods_category, f"购买成功！该{goods_name}已经放入[背包]，发送'使用 {goods_name}'即可使用！")

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
        footer = "\n提示：发送「使用 X」使用物品"
        return f"{header}\n" + "\n".join(items_list) + footer
    else:
        return "你的购物篮里暂时没有可用物品～快去商店看看吧！🛍️"

def check_goods( msg:str, path):
    """
    查询商品详细信息（优化版，增强健壮性与用户体验）

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
        return f"{user_name} 使用方法：使用 物品。各项物品可前往[商店]查看"

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
        except Exception as e:
            logger.error(f"初始化用于钓鱼系统数据错误：{str(e)}")
            return "系统繁忙，请稍后重试"

        if good_category == "fishing_rod":
            fish_manager.update_key(section=account,key="current_rod",value=good_name)
        elif good_category == "fishing_bait":
            fish_manager.update_key(section=account, key="current_bait", value=good_name)
        fish_manager.save(encoding="utf-8")
        return "使用成功！"
    else:
        return "意外的商品！无法使用！"