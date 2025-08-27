import re
from typing import Optional

import aiohttp
import asyncio
import json

from datetime import datetime
def is_arabic_digit(text: str) -> bool:
    """判断文本是否仅由 0-9 的阿拉伯数字组成"""
    # 空文本直接返回 False
    if len(text) == 0:
        return False
    # 遍历每个字符，检查是否全为 0-9
    for char in text:
        if not ('0' <= char <= '9'):
            return False
    return True

def get_by_qq(content:str):
    """
    解析格式为 'xx yy@zz(qq)' 的字符串。
    目标是提取 yy 和 (qq) 中的 qq。

    :param content: 例如 'xx yy@zz(qq)' 或 'xx yy'
    :return: 元组 (yy, qq)，其中 qq 若无则返回 None；
    """
    parts = content.split(' ', 1)
    if len(parts) < 2:
        return None, None  # 没有空格分隔，格式不对

    # 只处理第二部分：例如 'yy@zz(qq)' \
    s_rest = parts[1]
    if  s_rest.find('@') != -1:
        # yy,qq
        # 先提取 @ 前面的部分，即 yy
        at_split = s_rest.split('@', 1)

        yy = at_split[0]  # @ 前面的部分

        # 剩下的部分是 zz(qq) 或 zz
        after_at = at_split[1]

        # 查找 ( 和 )
        start_paren = after_at.find('(')
        end_paren = after_at.find(')', start_paren)

        if start_paren != -1 and end_paren != -1 and start_paren < end_paren:
            # 找到了有效的 (qq)
            qq = after_at[start_paren + 1:end_paren]  # 去掉括号
            return yy, qq
        else:
            # 没有找到 (qq)，返回 yy 和 None
            return yy, None
    else:
        # yy
        return s_rest, None



def preprocess_date_str(raw_str: str) -> str:
    """
    预处理日期字符串，标准短横线格式直接返回，其他格式转换为 YYYY-MM-DD（补前导零）

    支持的输入格式：
    1. 标准短横线格式（直接返回）：YYYY-MM-DD（如 "2024-08-15" 或 "2023-3-5"）
    2. 中文格式（转换为标准）：YYYY年MM月DD日（如 "2025年12月5日" → "2025-12-05"）
    3. 斜杠格式（转换为标准）：YYYY/MM/DD（如 "2025/12/5" → "2025-12-05"）

    :param raw_str: 原始日期字符串（可能含首尾空格）
    :return: 标准化的日期字符串（标准格式直接返回，其他格式补全前导零）
    """
    # -------------------- 步骤1：去除首尾空格 --------------------
    cleaned = raw_str.strip()
    if not cleaned:
        return ""  # 空字符串直接返回

    # -------------------- 步骤2：优先匹配标准短横线格式 --------------------
    # 标准短横线格式正则（允许月份/日期为1-2位，如 "2024-08-15" 或 "2023-3-5"）
    std_dash_pattern = r'^\d{4}-\d{1,2}-\d{1,2}$'
    if re.fullmatch(std_dash_pattern, cleaned):
        return cleaned  # 标准格式直接返回

    # -------------------- 步骤3：匹配中文格式（YYYY年MM月DD日） --------------------
    cn_pattern = r'^(\d{4})年(\d{1,2})月(\d{1,2})日$'
    cn_match = re.fullmatch(cn_pattern, cleaned)
    if cn_match:
        year = cn_match.group(1)
        month = f"{int(cn_match.group(2)):02d}"  # 补前导零（如 3 → "03"）
        day = f"{int(cn_match.group(3)):02d}"  # 补前导零（如 5 → "05"）
        return f"{year}-{month}-{day}"

    # -------------------- 步骤4：匹配斜杠格式（YYYY/MM/DD） --------------------
    slash_pattern = r'^(\d{4})/(\d{1,2})/(\d{1,2})$'
    slash_match = re.fullmatch(slash_pattern, cleaned)
    if slash_match:
        year = slash_match.group(1)
        month = f"{int(slash_match.group(2)):02d}"  # 补前导零
        day = f"{int(slash_match.group(3)):02d}"  # 补前导零
        return f"{year}-{month}-{day}"

    # -------------------- 步骤5：无匹配格式返回原始字符串（或抛异常） --------------------
    return cleaned  # 或 raise ValueError(f"不支持的日期格式: {raw_str}")


def calculate_delta_days(today_str: str, last_sign_str: str) -> int:
    """
    计算两个日期字符串之间的间隔天数（自然日差）

    :param today_str: 今日日期字符串（格式：YYYY-MM-DD）
    :param last_sign_str: 上次签到日期字符串（格式：YYYY-MM-DD）
    :return: 间隔天数（正数表示上次签到在今日之前，负数表示之后）
    """
    # 定义日期格式（与输入字符串一致）
    date_format = "%Y-%m-%d"

    try:
        # 将字符串转换为 date 对象（自动去除时间部分）
        today_date = datetime.strptime(today_str, date_format).date()
        last_sign_date = datetime.strptime(last_sign_str, date_format).date()
    except ValueError as e:
        raise ValueError(f"日期格式错误或无效: {e}") from e

    # 计算间隔天数（timedelta.days 直接返回自然日差）
    delta_days = (today_date - last_sign_date).days
    return delta_days

def get_dynamic_rob_ratio(victim_gold: int) -> float:
    if victim_gold <= 200:
        return 0.1   # 10%
    elif victim_gold <= 1000:
        return 0.05   # 5%
    elif victim_gold <= 10000:
        return 0.03   # 3%
    elif victim_gold <= 100000:
        return 0.01   # 1%
    elif victim_gold <= 500000:
        return 0.005   # 0.5%
    else:
        return 0.002  # 0.2%

async def get_qq_nickname(qq_number: str,api_type:int) -> str:
    """
    通过 QQ 号获取昵称（支持多接口类型切换）
    :param qq_number: QQ 号码（如 "3314562947"）
    :param api_type: 接口类型（0-旧版头像接口；1-第三方轻量接口）
    :return: 昵称（成功）或错误提示（失败）
    """

    # 根据接口类型动态配置 URL
    if api_type == 0:
        url = f"http://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={qq_number}"
    elif api_type == 1:
        url = f"https://api.ulq.cc/int/v1/qqname?qq={qq_number}"
    else:
        return "❌ 不支持的接口类型（仅支持 0 或 1）"

    # 模拟浏览器的请求头（避免被简单反爬拦截）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            # 发送异步 GET 请求（设置超时 10 秒）
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                # 检查 HTTP 状态码（非 200 表示请求失败）
                if response.status != 200:
                    return f"❌ {api_type} 接口请求失败（状态码：{response.status}）"

                # 根据接口类型解析响应
                if api_type == 0:
                    # ------------------------------ 旧版头像接口解析 ------------------------------
                    # 读取原始字节内容并手动解码（避免编码错误）
                    raw_content = await response.read()
                    response_text = raw_content.decode("utf-8", errors="replace")

                    # 解析 JSONP 格式（示例："portraitCallBack({...})"）
                    jsonp_prefix = "portraitCallBack("
                    jsonp_suffix = ")"
                    if not (jsonp_prefix in response_text and jsonp_suffix in response_text):
                        return "⚠️ 旧版接口：无效的 JSONP 响应（未找到 portraitCallBack 标记）"

                    # 提取 JSON 部分（去除前后缀）
                    json_str = response_text[len(jsonp_prefix):-len(jsonp_suffix)]

                    # 解析 JSON 数据
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        return f"❌ 旧版接口：JSON 解析失败（错误：{str(e)}，原始数据：{json_str[:50]}...）"

                    # 检查 QQ 号是否存在
                    qq_key = str(qq_number)
                    if qq_key not in data:
                        return f"ℹ️ 旧版接口：未找到 QQ 号 {qq_number} 的昵称信息（接口无数据）"

                    # 提取用户信息数组（接口返回格式：{"QQ号": [头像URL, 好友数, ..., 昵称,...]}）
                    user_info = data[qq_key]
                    if not isinstance(user_info, list):
                        return "❌ 旧版接口：返回数据格式异常（用户信息非数组）"

                    # 动态查找昵称字段（兼容不同版本）
                    possible_nick_indices = [6, 5, 7]  # 常见昵称位置（索引 6 为主）
                    nickname: Optional[str] = None
                    for idx in possible_nick_indices:
                        if idx < len(user_info) and isinstance(user_info[idx], str) and user_info[idx].strip():
                            nickname = user_info[idx].strip()
                            break

                    if not nickname:
                        return f"ℹ️ 旧版接口：无法提取昵称（用户信息数组：{user_info}）"

                elif api_type == 1:
                    # ------------------------------ 第三方轻量接口解析 ------------------------------
                    # 解析 JSON 格式（示例：{"code":200,"msg":"请求成功","qq":2740490583,"name":"๑挽؂๑宝"...}）
                    try:
                        data = await response.json()  # 直接解析 JSON（aiohttp 支持）
                    except json.JSONDecodeError as e:
                        return f"❌ 第三方接口：JSON 解析失败（错误：{str(e)}，原始数据：{await response.text()[:50]}...）"

                    # 检查接口返回状态码（业务层错误码）
                    if data.get("code") != 200:
                        return f"❌ 第三方接口：业务错误（错误码：{data.get('code')}，信息：{data.get('msg')}）"

                    # 提取昵称字段（根据接口文档，昵称在 "name" 字段）
                    nickname = data.get("name")
                    if not nickname or not isinstance(nickname, str):
                        return "ℹ️ 第三方接口：返回数据中未找到有效昵称"

                # 统一返回昵称（两种接口类型均在此处返回）
                return nickname

        except aiohttp.ClientError as e:
            return f"🌐 网络请求异常（错误：{str(e)}）"
        except asyncio.TimeoutError:
            return "⏳ 请求超时（接口响应过慢）"
        except Exception as e:
            return f"❓ 未知错误（错误：{str(e)}）"