from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
from astrbot.api import logger
import asyncio
from PIL import Image, ImageDraw, ImageFont

from model.directory import IniFileReader
from model.city_func import get_qq_nickname,get_system_font


# ------------------------------ 核心排行榜函数 ------------------------------
async def generate_rank(
    account: str,
    user_name: str,
    path: Path,
    sort_key: str,
    title: str  # 示例：title="金币" 或 "魅力"
) -> Optional[str]:
    """图文版排行榜（含用户当前排名、前三名颜色区分）"""
    try:
        # -------------------- 数据读取 --------------------
        user_handler = IniFileReader(
            project_root=path,
            subdir_name="City/Personal",
            file_relative_path="Briefly.info",
            encoding="utf-8"
        )
        user_data = user_handler.read_all() or {}
    except Exception as e:
        logger.error(f"读取用户数据失败：{str(e)}")
        error_path = await _save_error_image("读取数据失败", get_system_font(24))
        return error_path

    if not user_data:
        error_path = await _save_error_image("无用户数据", get_system_font(24))
        return error_path

    # -------------------- 数据预处理 --------------------
    # 过滤有效用户并按数值降序排序
    valid_users = [(acc, info.get(sort_key, 0)) for acc, info in user_data.items() if info.get(sort_key) is not None]
    if not valid_users:
        error_path = await _save_error_image(f"无{title}数据", get_system_font(24))
        return error_path

    sorted_users = sorted(valid_users, key=lambda x: x[1], reverse=True)
    top_n = min(10, len(sorted_users))  # 最多显示前10名
    rank_mapping = {acc: idx+1 for idx, (acc, _) in enumerate(sorted_users)}  # 排名映射

    # -------------------- 异步获取昵称（最多前10名） --------------------
    target_accounts = [u[0] for u in sorted_users[:top_n]]
    nickname_tasks = [get_qq_nickname(acc, 2) for acc in target_accounts]  # 假设get_qq_nickname是异步获取昵称的函数
    nicknames = await asyncio.gather(*nickname_tasks, return_exceptions=True)

    # -------------------- 初始化画布（动态计算尺寸） --------------------
    # 基础参数
    img_width = 1000  # 画布宽度（固定）
    padding = 20  # 全局边距
    title_font_size = 42  # 标题字体大小
    rank_font_size = 34  # 排名字体大小
    name_font_size = 32  # 昵称字体大小
    value_font_size = 32  # 数值字体大小
    user_info_font_size = 36  # 用户信息字体大小（加粗）
    line_spacing = 18  # 行间距

    # 动态计算标题高度
    title_font = get_system_font(title_font_size)
    title_text = f"🏆 {title} 排行榜"  # 标题格式：奖杯图标+Title+排行榜
    title_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), title_text, font=title_font)
    title_h = int(title_bbox[3] - title_bbox[1]) + 2 * padding  # 标题高度（含上下边距）

    # 动态计算列表项高度（根据字体大小和行间距）
    item_font = get_system_font(max(rank_font_size, name_font_size, value_font_size))
    item_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), "测试", font=item_font)
    item_h = int(item_bbox[3] - item_bbox[1]) + line_spacing  # 单个列表项高度

    # 用户信息区域高度（固定或动态）
    user_info_h = int(item_font.size * 1.8) + 2 * padding  # 用户信息行高（加粗字体）

    # 总高度计算（标题+列表+用户信息+页脚）
    list_total_h = item_h * top_n
    footer_h = 40  # 页脚高度
    total_h = title_h + list_total_h + user_info_h + footer_h + padding * 3  # 总高度（含全局边距）

    # 创建画布
    img = Image.new("RGB", (img_width, total_h), "#F8F9FA")  # 背景色
    draw = ImageDraw.Draw(img)

    # -------------------- 绘制标题栏 --------------------
    # 标题背景（渐变或纯色）
    title_bg_color = (245, 245, 245)  # 浅灰色背景（比列表略深）
    draw.rounded_rectangle(
        (padding, padding, img_width - padding, title_h - padding),
        radius=18,  # 圆角略大
        fill=title_bg_color,
        outline="#D0D0D0",  # 边框略深
        width=2
    )

    # 标题文本（居中显示，加粗）
    title_x = (img_width - (title_bbox[2] - title_bbox[0])) // 2
    title_y = padding + (title_h - (title_bbox[3] - title_bbox[1])) // 2
    draw.text(
        (title_x, title_y),
        title_text,
        fill="#2D3436",  # 深灰色标题（比之前略深）
        font=title_font
    )

    # -------------------- 绘制列表区域 --------------------
    list_start_y = title_h + padding * 2  # 列表起始Y坐标（增加顶部间距）
    list_bg_color = "white"  # 列表背景色
    draw.rounded_rectangle(
        (padding, list_start_y, img_width - padding, list_start_y + list_total_h),
        radius=18,  # 圆角与标题一致
        fill=list_bg_color,
        outline="#E8E8E8",  # 边框略深
        width=2
    )

    # 定义颜色规则（前三名不同颜色，其他统一）
    rank_colors = [
        ("#FF6B6B", "#FF8E8E"),  # 第1名：红色系（主色+浅色）
        ("#FFA94D", "#FFC19A"),  # 第2名：橙色系
        ("#FFD43B", "#FFE082"),  # 第3名：金色系
        ("#6C757D", "#868E96")   # 第4名及以后：深灰色系
    ]

    # 遍历绘制每个排名项（前10名）
    for rank_idx in range(top_n):
        # 当前用户数据
        acc, value = sorted_users[rank_idx]
        nickname = nicknames[rank_idx] if not isinstance(nicknames[rank_idx], Exception) else f"用户{acc[-4:]}"
        if len(nickname) > 15:  # 昵称过长截断（保留12字符+...）
            nickname = nickname[:12] + "..."

        # 当前项Y坐标
        item_y = list_start_y + rank_idx * item_h

        # -------------------- 绘制排名序号（带背景色块） --------------------
        rank_text = f"{rank_idx + 1}"  # 排名文本（1、2、3...）
        rank_font = get_system_font(rank_font_size)
        rank_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), rank_text, font=rank_font)
        rank_w = int(rank_bbox[2] - rank_bbox[0])
        rank_h = int(rank_bbox[3] - rank_bbox[1])

        # 排名背景色块（宽度=排名文本宽度+20px，高度=排名文本高度+10px）
        bg_padding = 10
        rank_bg_x = padding + 5
        rank_bg_y = item_y + (item_h - (rank_h + 2*bg_padding)) // 2
        rank_bg_w = rank_w + 2*bg_padding
        rank_bg_h = rank_h + 2*bg_padding

        # 填充色（前三名用主色，其他用浅灰）
        fill_color = rank_colors[rank_idx][1] if rank_idx < 3 else "#E9ECEF"
        draw.rounded_rectangle(
            (rank_bg_x, rank_bg_y, rank_bg_x + rank_bg_w, rank_bg_y + rank_bg_h),
            radius=8,
            fill=fill_color,  # 填充色
            outline=fill_color  # 边框色与填充色一致（无外边框）
        )

        # 排名文本（居中显示在背景色块中）
        draw.text(
            (rank_bg_x + (rank_bg_w - rank_w) // 2, rank_bg_y + (rank_bg_h - rank_h) // 2),
            rank_text,
            fill=rank_colors[rank_idx][0] if rank_idx < 3 else "#495057",  # 前三名用主色，其他用深灰
            font=rank_font
        )

        # -------------------- 绘制昵称（居中显示） --------------------
        name_font = get_system_font(name_font_size)
        name_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), nickname, font=name_font)
        name_w = int(name_bbox[2] - name_bbox[0])
        name_h = int(name_bbox[3] - name_bbox[1])
        name_x = rank_bg_x + rank_bg_w + 30  # 排名背景右侧间距30px
        name_y = item_y + (item_h - name_h) // 2  # 垂直居中
        draw.text(
            (name_x, name_y),
            nickname,
            fill="#2D3436",  # 昵称颜色（深灰）
            font=name_font
        )

        # -------------------- 绘制数值+Title（右对齐） --------------------
        value_text = f"{int(value)} {title}"  # 数值+Title（如"1000 金币"）
        value_font = get_system_font(value_font_size)
        value_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), value_text, font=value_font)
        value_w = int(value_bbox[2] - value_bbox[0])
        value_h = int(value_bbox[3] - value_bbox[1])

        # 数值右侧边距（预留20px）
        max_value_x = img_width - padding - 20
        value_x = max_value_x - value_w  # 右对齐
        value_x = max(value_x, name_x + name_w + 40)  # 确保数值在昵称右侧至少40px

        # 数值文本（垂直居中）
        value_y = item_y + (item_h - value_h) // 2
        draw.text(
            (value_x, value_y),
            value_text,
            fill=rank_colors[rank_idx][0] if rank_idx < 3 else "#495057",  # 前三名用主色，其他用深灰
            font=value_font
        )

    # -------------------- 绘制用户当前排名信息（底部突出显示） --------------------
    user_rank = rank_mapping.get(account, 0)  # 获取用户当前排名
    if user_rank > 0:  # 仅当用户有排名时显示
        # 用户信息背景色（浅金色/浅蓝色，突出显示）
        user_info_bg_color = "#FFF3CD" if user_rank <= 3 else "#E3F2FD"
        draw.rounded_rectangle(
            (padding, list_start_y + list_total_h + padding, img_width - padding,
             list_start_y + list_total_h + padding + user_info_h),
            radius=15,
            fill=user_info_bg_color,
            outline="#FFEEBA" if user_rank <= 3 else "#BBDEFB",  # 边框与背景呼应
            width=2
        )

        # 用户信息文本（加粗，左对齐）
        user_info_font = ImageFont.truetype("simhei.ttf", user_info_font_size)
        user_nick = user_name if len(user_name) <= 15 else f"{user_name[:12]}..."  # 昵称截断
        value_display = int(value) if isinstance(value, (int, float)) else "N/A"
        user_info_text = (
            f"当前第{user_rank}名 · {user_nick} · {value_display} {title}"
        )
        user_info_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), user_info_text, font=user_info_font)
        user_info_w = int(user_info_bbox[2] - user_info_bbox[0])
        user_info_x = padding + 10  # 左侧边距10px
        user_info_y = list_start_y + list_total_h + padding + (user_info_h - user_info_bbox[3] + user_info_bbox[1]) // 2
        draw.text(
            (user_info_x, user_info_y),
            user_info_text,
            fill="#856404" if user_rank == 1 else "#DC3545" if user_rank == 2 else "#FF9800" if user_rank <=3 else "#2D3436",
            font=user_info_font
        )

    # -------------------- 绘制页脚（数据更新时间） --------------------
    footer_font = get_system_font(24)
    footer_text = f"数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    footer_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), footer_text, font=footer_font)
    footer_w = int(footer_bbox[2] - footer_bbox[0])
    footer_x = img_width - padding - footer_w
    footer_y = total_h - padding - 10  # 页脚Y坐标（底部边距10px）
    draw.text(
        (footer_x, footer_y),
        footer_text,
        fill="#7F8C8D",  # 页脚颜色（深灰）
        font=footer_font
    )

    # -------------------- 保存图片 --------------------
    try:
        cache_dir = path / "Cache"
        cache_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"rank_{sort_key}_{timestamp}_{uuid.uuid4().hex[:8]}.png"
        save_path = cache_dir / filename
        img.save(save_path, "PNG")
        return str(save_path.resolve())
    except Exception as e:
        logger.error(f"保存排行榜图片失败：{str(e)}")
        error_path = await _save_error_image("生成图片失败", get_system_font(24))
        return error_path

# ------------------------------ 错误提示函数 ------------------------------
async def _save_error_image(text: str, font: ImageFont.FreeTypeFont) -> str:
    """生成错误提示图片（示例）"""
    img = Image.new("RGB", (600, 300), "#F8F9FA")
    draw = ImageDraw.Draw(img)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = text_bbox[2]-text_bbox[0], text_bbox[3]-text_bbox[1]
    draw.text(
        ((600 - text_w) // 2, (300 - text_h) // 2),
        text,
        fill="#6C757D",
        font=font
    )
    error_path = Path("error.png")
    img.save(error_path, "PNG")
    return str(error_path)


# -------------------- 原调用函数 ------------------------------
async def gold_rank(account: str, user_name: str, path: Path) -> Optional[str]:
    return await generate_rank(
        account=account,
        user_name=user_name,
        path=path,
        sort_key="coin",
        title="金币"
    )


async def charm_rank(account: str, user_name: str, path: Path) -> Optional[str]:
    return await generate_rank(
        account=account,
        user_name=user_name,
        path=path,
        sort_key="charm",
        title="魅力"
    )