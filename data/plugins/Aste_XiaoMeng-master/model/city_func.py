import re
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

async def get_qq_nickname(qq_number: str) -> str:
    """
    通过 QQ 号获取昵称（基于你提供的接口格式）
    :param qq_number: QQ 号码（如 "3314562947"）
    :return: 昵称或错误信息
    """

    # portraitCallBack({"3314562947":["http://qlogo4.store.qq.com/qzone/3314562947/3314562947/100",2564,-1,0,0,0,"HG",0]})
    # 假设的第三方接口 URL（需替换为真实接口）
    url = f"http://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={qq_number}"

    # 请求头（模拟浏览器，避免被拦截）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                # 检查 HTTP 状态码（非 200 表示请求失败）
                if response.status != 200:
                    return f"HTTP 请求失败，状态码：{response.status}"

                # 读取响应文本（JSONP 格式）
                response_text = await response.text()

                # 解析 JSONP：提取括号内的 JSON 数据
                # 示例响应文本："portraitCallBack({...})"
                jsonp_prefix = "portraitCallBack("
                jsonp_suffix = ")"
                if not (jsonp_prefix in response_text and jsonp_suffix in response_text):
                    return "无效的 JSONP 响应格式（未找到 portraitCallBack 标记）"

                # 提取并解析 JSON
                json_str = response_text[len(jsonp_prefix):-len(jsonp_suffix)]
                data = json.loads(json_str)

                # 检查 QQ 号是否存在于响应中
                qq_key = str(qq_number)
                if qq_key not in data:
                    return f"未找到 QQ 号 {qq_number} 的相关信息"

                # 提取昵称（数组的第6个元素，索引6）
                user_info = data[qq_key]
                if len(user_info) < 7:  # 确保数组长度足够（至少7个元素）
                    return "接口返回数据不完整，无法提取昵称"

                nickname = user_info[6]  # 索引6 是昵称（如 "HG"）
                return nickname

        except aiohttp.ClientError as e:
            return f"网络请求异常：{str(e)}"
        except json.JSONDecodeError:
            return "解析 JSON 失败，响应格式错误"
        except IndexError:
            return "接口返回数组长度不足，无法提取昵称"
        except Exception as e:
            return f"未知错误：{str(e)}"