import json
import configparser
import math
from pathlib import Path
from difflib import get_close_matches
import random
from typing import Dict, List, Optional, Any, Tuple
import os
import tempfile
from filelock import FileLock
from collections import Counter, OrderedDict

class IniFileReader:
    """
    高效读写INI文件的工具类，支持自动创建节、类型转换、异常处理
    """
    def __init__(
            self,
            project_root: Path,  # 显式传入最终数据目录的绝对路径（如 F:\...\Data）
            subdir_name: str,  # 子目录名（支持斜杠分隔，如 "City/Personal"）
            file_relative_path: str,  # 文件名（如 "Briefly.ini"）
            encoding: str = "utf-8"
    ):
        self.project_root = project_root  # 最终数据目录（如 F:\...\Data）
        self.subdir_name = subdir_name    # 子目录（相对于 project_root）
        self.file_relative_path = file_relative_path  # 文件名（相对于 project_root/subdir_name）
        self.encoding = encoding
        self.file_path = self._get_file_path()  # 完整文件绝对路径
        self.config = self._load_config()     # 初始化时加载配置到内存

    def _get_file_path(self) -> Path:
        """构建INI文件的绝对路径（核心逻辑：project_root + subdir_name + file_relative_path）"""
        # 拼接路径（Path自动处理不同系统的分隔符，如 Windows 反斜杠、Linux 正斜杠）
        return self.project_root / self.subdir_name / self.file_relative_path

    def _load_config(self) -> configparser.ConfigParser:
        """加载INI文件到内存（文件不存在时创建空配置）"""
        config = configparser.ConfigParser()
        if self.file_path.exists():
            try:
                config.read(self.file_path, encoding=self.encoding)
            except Exception as e:
                raise RuntimeError(f"加载INI文件失败: {self.file_path}, 错误: {e}")
        return config  # 文件不存在时返回空配置

    def reload(self) -> None:
        """重新加载配置文件（覆盖内存数据）"""
        self.config = self._load_config()  # 重新加载文件到内存

    def read_all(self) -> Dict[str, Dict[str, Any]]:
        """全量读取配置（返回内存中的最新数据）"""
        return self._parse_config(self.config)

    def read_section(self, section: str, create_if_not_exists: bool = False) -> Dict[str, Any]:
        """
        读取指定节的数据
        :param section: 节名
        :param create_if_not_exists: 节不存在时是否自动创建（默认False）
        :return: 节的键值对字典（节不存在时返回空字典）
        """
        if not self.config.has_section(section):
            if create_if_not_exists:
                self.config.add_section(section)
            return {}
        return self._parse_config(self.config)[section]

    def read_key(self, section: str, key: str, default: Any = None) -> Any:
        """
        读取指定节的键值（支持默认值）

        :param section: 节名（如 "用户信息"）
        :param key: 键名（如 "jail_time"）
        :param default: 键不存在时的默认值（可选，默认为 None）
        :return: 键对应的Python类型值；若键不存在且无默认值，抛出 ValueError
        :raises ValueError: 节或键不存在且未提供默认值时抛出异常
        """
        section_data = self.read_section(section)
        # 检查键是否存在
        if key not in section_data:
            if default is not None:
                return default
            raise ValueError(f"节 [{section}] 中无键 '{key}'")

        return section_data[key]

    def update_key(self, section: str, key: str, value: Any, encoding: Optional[str] = None) -> None:
        """
        更新/新增单个键值对（内存生效，需调用save保存）
        :param section: 节名（不存在则自动创建）
        :param key: 键名（不存在则自动创建）
        :param value: 值（自动转换为INI兼容字符串）
        :param encoding: 写入编码（可选）
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        str_value = self._convert_to_ini_string(value)
        self.config.set(section, key, str_value)

    def update_section_keys(self, section: str, data: Dict[str, Any], encoding: Optional[str] = None) -> None:
        """
        批量更新节中的键值对（内存生效，需调用save保存）
        :param section: 节名（不存在则自动创建）
        :param data: 键值对字典
        :param encoding: 写入编码（可选）
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        # 构建临时字典，减少多次 set 操作
        temp_dict = {key: self._convert_to_ini_string(value) for key, value in data.items()}
        self.config[section].update(temp_dict)

    def save(self, encoding: Optional[str] = None) -> None:
        """
        原子化保存配置到文件（避免并发写入导致数据丢失）
        :param encoding: 写入编码（可选）
        """
        lock = FileLock(f"{self.file_path}.lock")
        with lock:
            write_encoding = encoding or self.encoding
            temp_file = None  # 临时文件句柄

            try:
                # -------------------- 步骤1：创建临时文件 --------------------
                # 在目标文件同目录下生成临时文件（使用相同前缀，避免跨目录问题）
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding=write_encoding,
                    dir=str(self.file_path.parent),  # 与目标文件同目录
                    prefix=f".{self.file_path.name}.tmp.",  # 隐藏临时文件（可选）
                    delete=False  # 手动控制删除（避免异常时残留）
                )

                # -------------------- 步骤2：写入临时文件 --------------------
                self.config.write(temp_file)
                temp_file.flush()  # 强制刷新缓冲区（确保数据写入磁盘）
                os.fsync(temp_file.fileno())  # 同步文件元数据（可选，增强可靠性）

                # -------------------- 步骤3：原子重命名 --------------------
                # 替换原文件（操作系统保证原子性）
                # 注意：Windows 需先关闭临时文件句柄才能重命名
                if os.name == "nt":
                    temp_file.close()  # Windows 必须关闭句柄才能重命名
                    os.replace(temp_file.name, str(self.file_path))
                else:
                    os.replace(temp_file.name, str(self.file_path))  # Unix-like 直接替换

            except Exception as e:
                # -------------------- 异常处理：清理临时文件 --------------------
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)  # 删除残留的临时文件
                    except Exception as cleanup_err:
                        print(f"警告：清理临时文件失败 {temp_file.name}: {cleanup_err}")
                # 抛出原始异常（或包装为自定义异常）
                raise RuntimeError(f"原子化保存INI文件失败: {self.file_path}, 错误: {e}") from e

            finally:
                # 确保临时文件句柄关闭（避免资源泄漏）
                if temp_file and not temp_file.closed:
                    temp_file.close()

    @staticmethod
    def _parse_config(config: configparser.ConfigParser) -> Dict[str, Dict[str, Any]]:
        """将ConfigParser对象解析为嵌套字典（带类型转换）"""
        parsed = {}
        for section in config.sections():
            parsed[section] = {}
            for key, value in config.items(section):
                parsed[section][key] = IniFileReader._convert_value(value)
        return parsed

    @staticmethod
    def _convert_value(value: str) -> Any:
        """将INI字符串转换为Python原生类型（支持int/float/bool/str）"""
        # 尝试转换整数
        try:
            return int(value)
        except ValueError:
            pass
        # 尝试转换浮点数
        try:
            return float(value)
        except ValueError:
            pass
        # 尝试转换布尔值（不区分大小写）
        lower_val = value.strip().lower()
        if lower_val in ("true", "yes", "on"):
            return True
        if lower_val in ("false", "no", "off"):
            return False
        # 其他情况返回去空格的字符串
        return value.strip()

    @staticmethod
    def _convert_to_ini_string(value: Any) -> str:
        """将Python原生类型转换为INI兼容的字符串"""
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return value
        else:
            return str(value)

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f"IniFileReader(file_path={self.file_path}, encoding={self.encoding})"

class BaseJsonFileHandler:
    """
    通用JSON文件读写基类，支持自动创建文件/目录、原子化保存、数据增删改查
    """
    def __init__(
        self,
        project_root: Path,
        subdir_name: str,
        file_relative_path: str,
        encoding: str = "utf-8"
    ):
        self.project_root = project_root
        self.subdir_name = subdir_name
        self.file_relative_path = file_relative_path
        self.encoding = encoding
        self.file_path = self._get_file_path()
        self.data = self._load_data()

    def _get_file_path(self) -> Path:
        return self.project_root / self.subdir_name / self.file_relative_path

    def _load_data(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding=self.encoding) as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return {}
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"加载JSON文件失败: {self.file_path}, 错误: {e}")

    def save(self, encoding: Optional[str] = None) -> None:
        lock = FileLock(f"{self.file_path}.lock")
        with lock:
            save_encoding = encoding if encoding is not None else self.encoding
            try:
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding=save_encoding,
                    dir=str(self.file_path.parent),
                    prefix=f".{self.file_path.name}.tmp.",
                    delete=False
                )
                with temp_file:
                    json.dump(self.data, temp_file, indent=4, ensure_ascii=False)
                os.replace(temp_file.name, str(self.file_path))
            except Exception as e:
                if 'temp_file' in locals() and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as cleanup_err:
                        print(f"警告：清理临时文件失败 {temp_file.name}: {cleanup_err}")
                raise RuntimeError(f"保存JSON文件失败: {self.file_path}, 错误: {e}")

    def update_data(
        self,
        key: str,
        value: Any,
        validate: bool = True,
        expected_type: Optional[type] = None
    ) -> None:
        if not key:
            raise ValueError("键不能为空")
        keys = key.split(".")
        current = self.data
        for i, k in enumerate(keys[:-1]):
            if not isinstance(k, str):
                raise ValueError(f"键包含非字符串部分：{k}")
            if k not in current:
                current[k] = {}
            current = current[k]
            if not isinstance(current, dict):
                raise ValueError(f"键路径 '{'.'.join(keys[:i + 1])}' 指向非字典类型，无法继续更新")
        last_key = keys[-1]
        if validate and expected_type is not None and not isinstance(value, expected_type):
            raise ValueError(f"键 '{last_key}' 的值类型应为 {expected_type.__name__}，当前为 {type(value).__name__}")
        current[last_key] = value

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(file_path={self.file_path}, encoding={self.encoding})"

class JobFileHandler(BaseJsonFileHandler):
    """
    高效读写JSON文件的工具类、数据增删改查、层级信息提取
    """

    def get_last_n_job_ids(self, job_id: str) -> List[str]:
        """
        获取该大类中按顺序排列后的最后N个职位ID列表，数量由该大类职位总数决定：
        总职位数除以3，向上取整（不足3个不算）

        :param job_id: 当前职位ID（如"1000"）
        :return: 最后N个职位ID列表（如["1005","1006","1007"]）
        """
        # 验证job_id有效性
        if not isinstance(job_id, str) or len(job_id) != 4:
            return []

        # 获取所属专业系列ID（如"10"）
        major_id = job_id[:2]
        major_jobs = self.data.get(major_id, {})

        # 提取所有职位ID并按数值排序
        job_ids = sorted(major_jobs.keys(), key=lambda x: int(x))
        n = len(job_ids)

        # 计算需要取的职位数量（总数量除以3，向上取整）
        if n == 0:
            return []
        m = math.ceil(n / 3)

        # 返回最后m个职位ID
        return job_ids[-m:]

    def get_all_info(self) -> Dict[str, Any]:
        """获取所有职位系列数据（如 {"10": {...}, "20": {...}}）"""
        return self.data

    def get_all_jobs_and_companies(self) -> List[Dict[str, str]]:
        """
        获取所有职位的名称和对应的公司信息
        :return: 包含所有职位名称和公司的列表，每个元素为字典格式 {"jobName": "职位名称", "company": "公司名称"}
                 无有效数据时返回空列表
        """
        all_jobs = []
        for major_series in self.data.values():
            if not isinstance(major_series, dict):
                continue
            for job_info in major_series.values():
                if not isinstance(job_info, dict):
                    continue
                job_name = job_info.get("jobName")
                company = job_info.get("company")
                if job_name and company:  # 提前合并判断
                    all_jobs.append({"jobName": job_name.strip(), "company": company.strip()})
        return all_jobs

    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        """
        根据job_id（如"2000"）直接获取完整职位信息
        :param job_id: 职位ID（四位字符串，如"2000"）
        :return: 职位详细信息字典，如未获取返回{}字典
        """
        if not isinstance(job_id, str) or len(job_id) != 4:
            return {}
        major_id = job_id[:2]
        return self.data.get(major_id, {}).get(job_id, {})

    def get_job_info_ex(self, job_name: str) -> List[Dict[str, Any]]:
        """
        根据职位名称模糊匹配相关职位信息（支持多关键词、精准排序）

        :param job_name: 职位名称关键词（支持空格分隔多关键词，如"软件 后端 工程师"）
        :return: 匹配的职位信息列表（按匹配度从高到低排序）；
                 无匹配或参数非法时返回空列表 []
        """
        # 输入校验：非字符串直接返回空列表

        # 清洗输入：去除首尾空格，分割多关键词（支持空格分隔）
        raw_keywords = job_name.strip().split()
        if not raw_keywords:  # 空输入返回空列表
            return []

        # 预处理关键词：统一转小写，过滤空关键词
        keywords = [kw.lower() for kw in raw_keywords if kw.strip()]
        if not keywords:
            return []

        # 获取职位数据（兼容旧数据结构）
        job_series = self.data

        # 遍历所有职位，收集匹配信息及匹配度得分
        matched_jobs = []
        for major_id, jobs in job_series.items():
            if not isinstance(jobs, dict):
                continue
            for job_id, job_info in jobs.items():
                if not isinstance(job_info, dict):
                    continue

                # 提取职位名称（兼容不同字段名）
                job_name_full = job_info.get("jobName", "").strip().lower()
                if not job_name_full:
                    continue  # 无职位名称的记录跳过

                # 计算匹配度得分（关键逻辑）
                score = self._calculate_match_score(job_name_full, keywords)
                if score > 0:  # 仅保留有匹配的职位
                    matched_jobs.append({
                        "job_info": job_info,
                        "score": score,
                        "matched_keywords": [kw for kw in keywords if kw in job_name_full]
                    })

        # 按匹配度降序排序（得分相同则按关键词覆盖数量降序，再按职位名称长度升序）
        matched_jobs.sort(
            key=lambda x: (
                -x["score"],
                -len(x["matched_keywords"]),
                len(x["job_info"]["jobName"])
            )
        )

        # 提取最终结果（仅保留职位信息）
        return [item["job_info"] for item in matched_jobs]

    def _calculate_match_score(self, job_name: str, keywords: List[str]) -> int:
        """
        计算职位名称与关键词的匹配度得分（自定义算法）

        :param job_name: 职位全称（小写）
        :param keywords: 关键词列表（小写）
        :return: 匹配度得分（越高越相关，范围 0-1000）
        """
        score = 0
        # 计算关键词总长度（用于归一化，避免长关键词主导得分）
        max_possible = sum(len(kw) for kw in keywords)
        if max_possible == 0:  # 防御空关键词列表
            return 0

        # 规则1：完全匹配关键词（按出现次数加权，并归一化）
        keyword_counts = Counter(keywords)
        for kw, count in keyword_counts.items():
            if kw in job_name:
                # 匹配贡献 = （出现次数 × 关键词长度） / 关键词总长度 × 100
                # （总贡献上限为 100，避免单个长关键词过度影响）
                match_contribution = (job_name.count(kw) * len(kw)) / max_possible * 100
                score += min(match_contribution, 100)  # 单规则上限100

        # 规则2：连续关键词匹配（严格顺序匹配，强化高价值匹配）
        combined_kw = "".join(keywords)
        if combined_kw in job_name:
            # 连续匹配贡献 = 300（固定高权重，但不超过剩余分数空间）
            score += min(300, 1000 - score)  # 总得分不超过1000

        # 规则3：首词匹配（严格开头匹配，补充基础分）
        if keywords and keywords[0] == job_name[:len(keywords[0])]:
            # 首词匹配贡献 = 200（固定中等权重）
            score += min(200, 1000 - score)  # 总得分不超过1000

        return min(score, 1000)  # 最终得分封顶1000

    def get_promote_num(self, job_id: str) -> int:
        """
        获取当前职位可晋升的更高阶职位数量
        :param job_id: 当前职位ID（如"2000"）
        :return: 可晋升的职位数量
        """
        major_id = job_id[:2]
        major_jobs = self.data.get(major_id, {})
        return sum(1 for job_key in major_jobs if job_key > job_id)

    def get_promote_chain(self, job_id: str) -> List[str]:
        """
        生成晋升链：当前职位及同组中更高阶的职位名称列表（按职位等级升序排列）
        :param job_id: 当前职位ID（如"2000"）
        :return: 晋升链职位名称列表（如 ["初级工程师", "中级工程师", "高级工程师"]）
        """
        if not isinstance(job_id, str) or len(job_id) != 4:
            return []
        major_id = job_id[:2]
        # 安全获取当前major下的职位字典，若不存在则为空
        major_jobs = self.data.get(major_id, {})
        # 将职位键转换为整数并排序，确保按等级升序处理
        sorted_job_ids = sorted(major_jobs.keys(), key=lambda x: int(x))
        promote_chain = []
        for job_key in sorted_job_ids:
            if job_key > job_id:  # 若需排除当前职位，改为 job_key > job_id
                promote_chain.append(major_jobs[job_key]["jobName"])
        return promote_chain

    def get_next_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        根据当前职位 ID 返回下一个相邻职位的信息（按 ID 顺序）
        :param job_id: 当前职位 ID（如"1000"）
        :return: 下一个职位的完整信息字典；若当前 ID 不存在或已是最后一个，返回 None
        """

        # 获取所有职位系列（如 "10"/"20" 等大类）
        job_series = self.data

        # 遍历每个职位系列，查找当前 job_id 所在的系列
        for major_id, jobs in job_series.items():
            if not isinstance(jobs, dict):
                continue  # 跳过非字典类型的子节点

            # 将当前系列的职位按 ID 排序（确保顺序正确）
            sorted_jobs = sorted(jobs.items(), key=lambda x: int(x[0]))  # 按 ID 数值排序（如 "1000" < "1001"）

            # 提取排序后的 ID 列表和对应的职位信息
            job_ids = [jid for jid, _ in sorted_jobs]
            job_info_list = [info for _, info in sorted_jobs]

            # 检查当前 job_id 是否在该系列中
            if job_id in job_ids:
                current_index = job_ids.index(job_id)
                # 若存在下一个职位（非最后一个）
                if current_index + 1 < len(job_ids):
                    return job_info_list[current_index + 1]  # 返回下一个职位的完整信息
                else:
                    return None  # 当前是该系列最后一个职位

        # 若遍历完所有系列仍未找到当前 job_id
        return None

class ShopFileHandler(BaseJsonFileHandler):
    """
    高效读写JSON文件的工具类、数据增删改查、层级信息提取
    """
    def get_item_info(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        根据商品名精确查找商品信息

        :param item_name: 商品名称（如"小心心"、"木鱼竿"）
        :return: 匹配的商品信息字典，若未找到返回None
        """
        return self.data.get(item_name)

    def get_similar_items(
            self,
            item_name: str,
            similarity_threshold: float = 0.6,  # 名称相似度阈值（0-1，越高越严格）
            top_n_name: int = 3,  # 名称相似最多返回数量
            top_n_price: int = 0  # 价格相邻最多返回数量（前后各取top_n_price个）
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        综合名称相似性和价格相邻性的商品推荐（返回包含数量信息的相似商品列表）

        :param item_name: 目标商品名称（如"小心心"）
        :param similarity_threshold: 名称相似度阈值（0-1，建议0.5-0.7）
        :param top_n_name: 名称相似最多返回的商品数量
        :param top_n_price: 价格相邻时，前后各取最多top_n_price个商品（总数量≤2*top_n_price）
        :return: 相似商品列表，格式为[(商品名, 商品详情), ...]，商品详情包含数量等信息
        """
        # -------------------- 基础校验 --------------------
        if not isinstance(item_name, str) or len(item_name.strip()) == 0:
            return []  # 无效商品名

        # 目标商品不存在于商店数据中
        if item_name not in self.data:
            return []

        # -------------------- 步骤1：获取名称相似的商品 --------------------
        # 提取所有商品名称和详情
        all_items = list(self.data.items())  # 格式：[(商品名, 商品详情), ...]
        all_names = [name for name, _ in all_items]

        # 使用difflib计算名称相似度（按相似度从高到低排序）
        similar_names = get_close_matches(
            word=item_name,
            possibilities=all_names,
            n=top_n_name,  # 最多取前top_n_name个
            cutoff=similarity_threshold  # 相似度阈值
        )

        # 整理名称相似的商品（排除自身，补充数量信息）
        name_similar_items = []
        for name in similar_names:
            if name == item_name:
                continue  # 跳过目标商品自身
            item_detail = self.data[name].copy()  # 复制详情避免修改原始数据
            item_detail["quantity"] = item_detail.get("quantity", 0)  # 确保数量字段存在
            name_similar_items.append((name, item_detail))

        # -------------------- 步骤2：获取价格相邻的商品 --------------------
        # 按价格升序排序（价格相同则按原顺序稳定排序）
        sorted_by_price = sorted(
            all_items,
            key=lambda x: (x[1]["price"], all_items.index((x[0], x[1])))
        )

        # 查找目标商品在价格排序中的索引
        target_price_idx = next(
            (idx for idx, (name, _) in enumerate(sorted_by_price) if name == item_name),
            -1
        )
        if target_price_idx == -1:
            return []  # 理论上不会触发（已校验目标商品存在）

        # 计算价格相邻的候选索引（前后各取top_n_price个）
        price_candidates = []
        # 向前取（价格更低的商品）
        for i in range(1, top_n_price + 1):
            prev_idx = target_price_idx - i
            if prev_idx >= 0:
                price_candidates.append(prev_idx)
        # 向后取（价格更高的商品）
        for i in range(1, top_n_price + 1):
            next_idx = target_price_idx + i
            if next_idx < len(sorted_by_price):
                price_candidates.append(next_idx)

        # 整理价格相邻的商品（排除自身，补充数量信息）
        price_adjacent_items = []
        for idx in price_candidates:
            name, detail = sorted_by_price[idx]
            if name == item_name:
                continue  # 跳过目标商品自身
            detail = detail.copy()
            detail["quantity"] = detail.get("quantity", 0)
            price_adjacent_items.append((name, detail))

        # -------------------- 步骤3：合并去重并按优先级排序 --------------------
        # 合并名称相似和价格相邻的商品（去重）
        combined = {}
        for name, detail in name_similar_items + price_adjacent_items:
            if name not in combined:
                combined[name] = detail  # 以名称为唯一标识去重

        # 转换为列表并按优先级排序（名称相似优先，其次价格接近）
        sorted_result = sorted(
            combined.items(),
            key=lambda x: (
                -1 if x[0] in [n for n, _ in name_similar_items] else 0,  # 名称相似的排前面
                abs(self.data[x[0]]["price"] - self.data[item_name]["price"])  # 价格差小的排前面
            )
        )

        # 提取最终结果（格式：[(商品名, 商品详情), ...]）
        return [(name, detail) for name, detail in sorted_result]

class FishFileHandler(BaseJsonFileHandler):
    """
    高效读写JSON文件的工具类、数据增删改查、层级信息提取
    """

    def get_item_info(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        根据商品名精确查找商品信息

        :param item_name: 鱼名称
        :return: 匹配鱼字典，若未找到返回None
        """
        return self.data.get(item_name)

    def get_random_fish_by_bait(self, bait: str) -> Optional[Dict[str, Any]]:
        """
        根据指定鱼饵随机返回一条匹配的鱼信息

        :param bait: 鱼饵名称（如"蚯蚓"、"活虾"）
        :return: 匹配的鱼信息字典，若无匹配项返回None
        """
        matching_fishes = []
        for fish_name, fish_info in self.data.items():
            if bait in fish_info.get("bait", []):
                matching_fishes.append({fish_name: fish_info})

        if not matching_fishes:
            return None

        return random.choice(matching_fishes)

class UnifiedCreelManager:
    def __init__(
        self,
        save_dir: Path,
        *,
        subdir: Optional[str] = None,          # 新增：次级目录（可选）
        data_filename: str = "AllCreels.json"  # 新增：自定义数据文件名（默认不变）
    ):
        """
        初始化统一渔获数据管理器（支持自定义目录和文件名）

        :param save_dir: 数据保存根目录（如 Path("City/Record")）
        :param subdir: 次级目录（可选，如 "fish_records"，会在 save_dir 下创建该子目录）
        :param data_filename: 数据文件名（默认 "AllCreels.json"，自定义如 "my_fish.json"）
        """
        self.save_dir = save_dir
        # 构建实际保存目录（根目录 + 次级目录）
        self.actual_save_dir = self.save_dir / subdir if subdir else self.save_dir
        # 自定义文件锁路径（与数据文件同目录）
        self.lock_path = self.actual_save_dir / ".unified_creel.lock"
        # 自定义数据文件路径
        self.data_file = self.actual_save_dir / data_filename
        # 创建目录（含次级目录）
        self.actual_save_dir.mkdir(parents=True, exist_ok=True)

    def _load_data(self) -> Dict[str, Dict]:
        """加载统一文件数据（顶层为字典：{account: user_data}）"""
        if not self.data_file.exists():
            return {}  # 默认空字典（无用户数据）
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON解析失败（文件: {self.data_file}）: {e.msg}", e.doc, e.pos) from e
        except Exception as e:
            raise RuntimeError(f"读取数据文件失败（文件: {self.data_file}）: {str(e)}") from e

    def _save_data(self, data: Dict[str, Dict]) -> bool:
        """原子化保存统一文件数据（顶层为字典：{account: user_data}）"""
        lock = FileLock(self.lock_path, timeout=5)
        with lock:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        return True

    def add_fish_weight(
            self,
            account: str,
            fish_name: str,
            weight: float,
    ) -> bool:
        """
        新增鱼的重量数据（自动处理用户记录创建/更新）

        :param account: 用户账号（如 "user123"）
        :param fish_name: 鱼名（如 "鲫鱼"）
        :param weight: 新增重量（必须为正数）
        :return: 操作是否成功
        :raises ValueError: 重量参数无效时抛出
        """
        # 参数校验
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError(f"无效重量值：{weight}（必须为正数）")

        # 加载现有数据（顶层字典）
        data = self._load_data()

        # 获取或初始化用户数据（直接通过账号键访问）
        user_data = data.get(account)
        if not user_data:
            user_data = {"fish_records": []}
            data[account] = user_data  # 新增用户到字典

        # 查找或创建鱼记录
        fish_record = next(
            (fr for fr in user_data["fish_records"] if fr["fish_name"] == fish_name),
            None
        )
        if not fish_record:
            # 新增鱼记录（移除 unit 字段）
            user_data["fish_records"].append({
                "fish_name": fish_name,
                "weights": [weight]
            })
        else:
            # 追加重量
            fish_record["weights"].append(weight)

        # 保存数据（可能抛出异常）
        self._save_data(data)
        return True

    def get_fish_records(self, account: str, fish_name: str) -> List[Dict]:
        """获取指定鱼的完整记录（仅保留重量）"""
        data = self._load_data()
        user_data = data.get(account)
        if not user_data:
            return []  # 用户不存在时返回空列表

        records = []
        for record in user_data["fish_records"]:
            if record["fish_name"] == fish_name:
                records.append({
                    "fish_name": record["fish_name"],
                    "weights": record["weights"],
                    "count": len(record["weights"]),
                    "total_weight": sum(record["weights"])
                })
        return records

    def get_user_summary(self, account: str) -> Dict:
        """获取用户渔获概览（含每种鱼的总重量统计）

        :param account: 用户账号（如 "user123"）
        :return: 字典，包含以下字段：
            - account: 用户账号
            - total_catches: 总捕获次数（所有鱼的重量记录数之和）
            - total_weight: 总重量（所有鱼的重量之和，单位：重量单位）
            - fish_types: 鱼的种类数（不同鱼名的数量）
            - fish_weights: 每种鱼的总重量（键：鱼名，值：该鱼总重量，单位：重量单位）
        :raises ValueError: 用户不存在时抛出
        """
        data = self._load_data()
        user_data = data.get(account)
        if not user_data:
            raise ValueError(f"用户 {account} 不存在")

        # 初始化概览字典（新增 fish_weights 字段）
        summary = {
            "total_catches": 0,
            "total_weight": 0.0,
            "fish_types": len(user_data["fish_records"]),
            "fish_weights": {}  # 新增：每种鱼的总重量（键：鱼名，值：总重量）
        }

        # 遍历每条鱼记录，累加统计值
        for record in user_data["fish_records"]:
            fish_name = record["fish_name"]
            weights = record["weights"]
            fish_total = sum(weights)  # 当前鱼的总重量

            # 累加全局统计
            summary["total_catches"] += len(weights)
            summary["total_weight"] += fish_total

            # 记录当前鱼的总重量（若已存在则累加，否则初始化）
            if fish_name in summary["fish_weights"]:
                summary["fish_weights"][fish_name] += fish_total
            else:
                summary["fish_weights"][fish_name] = fish_total

        return summary

    def calculate_total_amount(
            self,
            account: str,
            fish_name: str,
            average_price: int,  # 平均价格（元/重量单位）
            average_weight: float  # 平均重量（重量单位，如kg）
    ) -> int:
        """
        计算指定用户某条鱼的总金额（公式：总金额 =（总重量 ÷ 平均重量）× 平均价格，最终取整）

        :param account: 用户账号（如 "user123"）
        :param fish_name: 鱼名（如 "鲫鱼"）
        :param average_price: 该鱼的平均价格（如 15 元/kg）
        :param average_weight: 该鱼的平均重量（如 2.5 kg）
        :return: 总金额（元，取整后）
        :raises ValueError: 用户/鱼不存在、平均重量无效或无重量数据时抛出
        """
        # 加载用户数据
        data = self._load_data()
        user_data = data.get(account)
        if not user_data:
            raise ValueError(f"用户 {account} 不存在")

        # 查找鱼记录
        fish_record = next(
            (fr for fr in user_data["fish_records"] if fr["fish_name"] == fish_name),
            None
        )
        if not fish_record:
            raise ValueError(f"用户 {account} 不存在鱼 {fish_name}")

        # 获取该鱼的所有重量数据
        fish_weights = fish_record["weights"]
        if not fish_weights:
            raise ValueError(f"用户 {account} 的 {fish_name} 无重量记录")

        # 计算总重量
        total_weight = sum(fish_weights)

        # 避免除以0（平均重量为0时无意义）
        if average_weight <= 0:
            raise ValueError(f"平均重量 {average_weight} 不能为0或负数")

        # 计算数量（总重量 ÷ 平均重量）
        quantity = total_weight / average_weight

        # 计算总金额（数量 × 平均价格）
        total_amount = quantity * average_price

        # 取整（四舍五入到整数）
        return round(total_amount)

    def delete_fish(
            self,
            account: str,
            fish_name: str
    ) -> bool:
        """
        删除指定用户下的某条鱼记录

        :param account: 用户账号（如 "user123"）
        :param fish_name: 鱼名（如 "鲫鱼"）
        :return: 是否删除成功
        :raises ValueError: 用户/鱼不存在时抛出
        """
        data = self._load_data()
        user_data = data.get(account)
        if not user_data:
            raise ValueError(f"用户 {account} 不存在")

        # 查找并删除鱼记录
        fish_index = next(
            (i for i, fr in enumerate(user_data["fish_records"]) if fr["fish_name"] == fish_name),
            -1
        )
        if fish_index == -1:
            raise ValueError(f"用户 {account} 不存在鱼 {fish_name}")

        # 执行删除
        del user_data["fish_records"][fish_index]

        # 保存修改（可能抛出异常）
        self._save_data(data)
        return True
    
class GameUpdateManager:
    def __init__(self):
        self.updates = OrderedDict([
            ("250731", {
                "content": """
七周年庆版本重磅更新，狂欢来袭！七待与你共赴一场蟠桃盛宴~
【玩法更新-天宫大乱斗】
3大变身角色，9大变身流派，成为失忆者·齐天大圣、劲铠·二郎真君、小学妹·玉兔公主，与大boss炼丹炉体验一场场酣畅淋漓的神仙打架！
【全新武器卡-喷火枪】
"三昧真火"降临DMM世界，草丛老六是时候露露脸了~现开启全服火力值挑战，少年们快来试试这把能燃烧一切的喷火枪将打出怎样不可思议的操作，点燃火热的对局场面吧！
【周年活动福利管饱】
1. 瑶池盛宴：呼朋唤友，瑶池相会~活动期间少年们可以做任务收集美味食盒，宴请宾客炫饭，收获好评并获取奖励！还可以一起奏乐起舞，互动拍照哦~
2. 天书绘卷：徐徐展开的画卷，承载着玩家少年们共创的优质内容，带来惊喜，一同庆生！
3. 天宫之路：全新勇者任务归来，让你更自由、更简单地解锁缤纷大奖！
4. 周年回顾：一路走来，你与DMM承载了多少旅途上的回忆？选择你心爱的小福神，和它一起追忆往昔，与其他小伙伴们一起放飞天灯，收获一份专属周年礼吧~
5. 周年幸运大转盘抽奖，精美时装等你拿！
【商店上新-缤纷一夏】
新一期幻想造物、浮光之梦、缤纷城：能量剑星耀皮肤、龙小侠凌渊套装、巡逻犬哮日神犬、女特工年度特惠等陆续上线~
                            """
            }),
            ("250626", {
                "content": """
暑期大版本重磅更新，全新大闹天宫主题，各路神仙热闹非凡~~
【SS30赛季-大闹天宫】
劲凯·天目神君、魔术师·仙鼎小妖、小梦魇·炼丹童子、侦察眼·照妖仙镜等赛季主题皮肤上新
【新角色-小师姐雾柒柒】
来自雾影山的全新角色雾柒柒登场！本次新角色会同步上线4182及金库攻防玩法。在不同玩法下，少年们将会体验到独特技能的新角色打法，快来挖掘小师姐的更多招式吧！还有还有，小师姐的多个表情和语音彩蛋等着少年们去探索哦~
【道具重构-腕炮升级】
能量腕炮的不可越墙直线弹道改造成了抛物线弹道。没错，它能穿墙啦！参与活动任务还能收集道具碎片，助力腕炮升级，少年们快来试试吧~
【活动多多福利满满】
1、天宫绘卷：活动期间少年们可以通过天宫盗宝解开法宝封印，获得老神仙的法宝；还能在殿前演武中，自由选择玉兔、杨戬、大圣的皮影小人物进行比武，获得积分领取更多福利！
2、新一期浮光织梦、寻迹极光、缤纷城：失忆者大圣套装、小学妹玉兔公主套、幽妍人鱼公主套装、滑板筋斗云等陆续上线
3、全新回流系统：新版回流活动开启，欢迎少年们回家！一键掌握最新资讯、漂流瓶寻找逃搭搭、奖励升级福利加码等体验升级，期待每位回归的少年们收获满满~
                            """
            }),
            ("250522", {
                "content": """
亲爱的少年：
春季来临，万物复苏，你是否会对神秘的森林深处充满向往呢？进入DMM世界，与朋友一起遇见各种各样的生物精灵、共同破解未知挑战、在冒险中收获勇气与智慧的成长吧！
【SS29 森灵奇境】
"小骇客·风花之灵、小狮子·森之勇者、灵膳子·密林语者、蹦嘣枪·蕊华风语、战术捣弹·自然绽放、飞爪·蔓痕握"等超多主题外观惊喜上线！
【新4V1上自建房 】
新4v1模式已加入自建房，少年们可单机，可组队，随意任玩，并不受段位限制~
【道具卡重构-弹簧板】
双阵营道具卡：跳跳杆超进化后，集趣味性和实用性于一身！划重点！！追捕使用它也能跳啦！
【活动多多 福利多多】
1、七日登录 ：登录七天，可领取气泡·嘻嘻喔~
2、初夏挑战：活动期间，每日解锁1个任务，完成任务将获得对应奖励，完成所有任务将获得单件：小狐狸·奶油莓莓头饰！
3、气球收集 ：活动期间，参与经典4v1、8v2以及大乱斗，在对局中能够获得气球礼盒，拾取礼盒即可随机获得道具，集齐不同数量道具可兑换活动奖励！
                            """
            }),
            ("250417", {
                "content": """
亲爱的少年：
春季来临，万物复苏，你是否会对神秘的森林深处充满向往呢？进入DMM世界，与朋友一起遇见各种各样的生物精灵、共同破解未知挑战、在冒险中收获勇气与智慧的成长吧！
【SS29 森灵奇境】
"小骇客·风花之灵、小狮子·森之勇者、灵膳子·密林语者、蹦嘣枪·蕊华风语、战术捣弹·自然绽放、飞爪·蔓痕握"等超多主题外观惊喜上线！
【荣耀热斗S2】
1、赛季战报震撼上线！
2、总榜前100名的玩家可获得一周的"荣耀之证头像框"，还有道具卡皮肤等超多福利等你拿！
【道具卡重构-弹簧板】
双阵营道具卡：跳跳杆超进化后，集趣味性和实用性于一身！划重点！！追捕使用它也能跳啦！
【活动多多 福利多多】
1、林中觅宝 ：完成任务可收集各种奖励，还有机会抽取赛季胶卷、微光之种和灵感胶囊！累计游玩一定圈数，还可获得大奖"吼吼号·林间龙语"喔。
2、七日签到：登录可得点券、道具卡碎片等奖励，还可获得酷酷的表情气泡"气泡·眉头一皱"。
3、魔药炼制 ：帮团子找到魔药炼制的正确顺序，赢得奖励！首日即可抱走紫皮"手榴弹·喷火菇菇"，随着关卡逐步解锁，还可获得涂鸦·头要炸了，气泡·尼诺哭哭，气泡·双击666"等奖励喔
                            """
            }),
            ("250116", {
                "content": """
亲爱的少年：
    在航天精神的引领下，DMM星球的星际小队也要去太空遨游啦！快叫上小伙伴们一起乘坐飞船探索宇宙的奇幻吧~
【新联动-航天文创CASCI】
完成任务即可获得"失忆者·太空漫步套装"、"头像框·航天之志"！
还有道具卡皮肤"魔法墙·铭记一刻"、"治疗球·逐梦号"等你带回家喔~
【太空8v2】
焕然一新的太空场景，身处巨大的"追梦者"号太空游轮内，星河环绕~
还有往来穿梭的浮空艇、更具代入视角的射击体验、失重的房间、能自由跑酷的墙面、以及可破坏场景的道具、还有机会临时体验新武器喔~
【太空大乱斗】
每局游戏开始时会随机一个事件，不同机制不同体验喔！
局内还可通过开启宝箱、抽奖等方式收集货币，货币可以用来参与抽奖以及购买地图上随机刷新的"魔猿机甲"、"月球车"、"多种无人机"供少年们使用喔~
【全新道具卡—裂地锤】
这是一把兼具位移能力与近身爆发输出的强力近战武器；可以用其跨障追击、还可以更方便地完成飞车切入等操作喔~
【荣耀热斗S1，震撼返场】
局前BP、乱斗等级系统来袭！结算大更新，游戏实力一览无余！快来查看你的专属雷达图和玩法称号吧！
                            """
            }),
            ("231121", {
                "content": """
亲爱的少年：
SS27“繁星入夜”全新赛季开启，快和小伙伴们来一场唯美、神秘的命运占卜之旅吧~
【航海8v2加入自建房】
大海战~可自定义的航海8v2加入自建房啦，少年们可单机，可组队，随意任玩；
除了原本少年们熟悉的追逃参数外，少年们还可以自定义“战船数量”、“渔船数量”、“钓鱼数量”、甚至是“螃蟹数量”；
【金库攻防新角色】
全新高机动+连招型刺客角色——茶气郎登场；茶气郎的输出依赖近距离的气功推掌，所以有效利用茶气突进和奶茶追击接近敌人是发挥其实力的关键喔~
【活动多多 福利多多】
1、星阵塔罗：活动期间，少年每日登录游戏、进行对局可获得占卜次数，每日共可占卜3次；每次占卜将获得能量值以及点券等随机奖励，累计能量值获得气泡·目瞪口呆、紫卡包*5、动作·扇面舞以及道具卡皮肤侦查眼·命运视角；
2、命运星途：活动期间，完成任务获得“勇者的证明”，累计可兑换皮肤、动作等各类奖励~
3、冒险指南：同期金库攻防将上线全新的段位机制以及新英雄茶气郎，少年们观看视频并完成对应任务可获得“勇者的证明”；
4、七日签到：活动期间，登录将获得点券、道具卡碎片等奖励，累计登录7天还将获得永久头像框。
                            """
            }),
            ("231101", {
                "content": """
这是哪？怎么有雪人、还有麋鹿？” 泷惊讶地问道。
洛杰：“就等你们了，版本更新、地图玩法都更新了，快来打雪仗！”
【版本重点内容】
1.8v2冰雪世界：打雪仗放肆玩
来全新冰雪地图，听踩雪声超解压！
变身雪人！可伪装or侦察or攻击，隐藏玩法超多！
多人滚雪球，看谁滚的大？碰撞爆炸，还能冻人！
禁闭室下面竟然有鱼！试试能不能钓出来…
2.新限时道具卡：飞天麋鹿
超强超远跨墙位移，还能跑路、救人、守门...这个好搭档必须拥有！
【重点活动预告】
1.赛季宝藏
新赛季“雪境极光”来袭，【蹦嘣枪 暖晶蓄能枪】、【影之忍者·极地霜华套装】、【小骇客·极地融雪套装】和【水之忍者·极地晶流套装】多重福利等你开启！
2.周周有好运
限定皮肤【治疗球·企鹅康康】免费抽！完成“连星探秘”“深海掘金”任务就能参与抽奖，还有耀金卡包、气泡等超值奖励拿不停！
3.寻迹极光
寰宇光域活动开启！洛杰带着他的星耀时装【失忆者·光域领主套装】、【生命护盾·光域守护】和【飞爪·晶能捕捉器】来和大家见面啦~
【版本贴心优化】
平衡性调整：
1、霸天斧：通过高度带来的伤害变化由从95/108调整为99/99。
2、团子：主动技能冷却时间由满级后的23s调整为28s；
被动天赋美食伙伴移速10%调整为15%，护盾值33调整为40；
增益持续时间由3s-6s调整为5s-8s；
以上就是更新的重点内容啦！少年们，锁定11月冰雪新版本，和好友们来场痛快刺激的雪仗吧！
                            """
            }),
            ("231101", {
                "content": """
这是哪？怎么有雪人、还有麋鹿？” 泷惊讶地问道。
洛杰：“就等你们了，版本更新、地图玩法都更新了，快来打雪仗！”
【版本重点内容】
1.8v2冰雪世界：打雪仗放肆玩
来全新冰雪地图，听踩雪声超解压！
变身雪人！可伪装or侦察or攻击，隐藏玩法超多！
多人滚雪球，看谁滚的大？碰撞爆炸，还能冻人！
禁闭室下面竟然有鱼！试试能不能钓出来…
2.新限时道具卡：飞天麋鹿
超强超远跨墙位移，还能跑路、救人、守门...这个好搭档必须拥有！
【重点活动预告】
1.赛季宝藏
新赛季“雪境极光”来袭，【蹦嘣枪 暖晶蓄能枪】、【影之忍者·极地霜华套装】、【小骇客·极地融雪套装】和【水之忍者·极地晶流套装】多重福利等你开启！
2.周周有好运
限定皮肤【治疗球·企鹅康康】免费抽！完成“连星探秘”“深海掘金”任务就能参与抽奖，还有耀金卡包、气泡等超值奖励拿不停！
3.寻迹极光
寰宇光域活动开启！洛杰带着他的星耀时装【失忆者·光域领主套装】、【生命护盾·光域守护】和【飞爪·晶能捕捉器】来和大家见面啦~
【版本贴心优化】
平衡性调整：
1、霸天斧：通过高度带来的伤害变化由从95/108调整为99/99。
2、团子：主动技能冷却时间由满级后的23s调整为28s；
被动天赋美食伙伴移速10%调整为15%，护盾值33调整为40；
增益持续时间由3s-6s调整为5s-8s；
以上就是更新的重点内容啦！少年们，锁定11月冰雪新版本，和好友们来场痛快刺激的雪仗吧！
                            """
            }),
            ("230920", {
                "content": """
春困、夏乏、秋打盹儿？
不对！秋高气爽品美食！DMM一年一度的美食节来咯~一起来游戏中摆地摊，大乱炖，嗨玩美食节吧！
【版本重点内容】
1.大乱斗厨王版：玩法大乱炖，下饭大乱斗！
乱炖出什么，这把乱斗玩什么！大乱斗厨王版来袭！听说找到团子进行神秘烹饪，就可随机乱炖出花式道具卡噢~运气爆棚的话还可收获小跟班+N，这次龙人、史莱姆、蘑菇怪都听你差遣！
2.团子超进化：这波我能1救8！
团子的背包升级啦！这波slay全场！升级后的团子抛出自己的背包，会投掷出随机食物，吃到食物的队友们可获得救援，此外，团子还能化身移动救援站，用飞车、滑板等载起自己的背包，队友在哪都能救！
3.2张新限时道具卡：玩个锤子？or小罐开喷
· 动能锤：少年，玩个锤子不？挥舞锤子砸下，敌人都变纸片人啦！
· 喷射小罐：开喷吧小罐！向敌人释放1瓶摇满气泡的阔乐，敌人被阔乐瓶创飞啦~
【版本贴心优化】
1.关系系统
好友关系系统上线咯！互相关注成为好友后，就会显示好友亲密度啦！想和谁成为最佳亲密好友，就快和TA一起开黑、互相点赞、互送礼物提升亲密度吧~
【时装/皮肤/活动预告】
灵膳子时装免费送！！
2023.9.20，一起来参与DMM星球一年一度的美食摆摊节吧，参与游戏赚取金币，即可获得【灵膳子·私房小当家】套装和【灵膳子·金牌料理人】上衣噢~
                            """
            }),
            ("230802", {
                "content": """
我重生了，重生在2023年8月2日，上一世因阴差阳错，我未能好好体验《逃跑吧！少年》的五周年庆典：这一次限时道具卡、限定免费时装、全新乱斗地图、奇妙8v2以及关于五周年的一切，我将全部体验一遍，阅读后续内容，细听我重生计划！
【版本重点内容】 
1.4张限时道具卡：满级免费get，一次玩个爽！
· 飘飘翼：你飞了，还是他飘了？原来是神奇飘飘翼！利用它的飞盘连接各种奇怪物体，直接把你拖拽飞上天！
· 缩小隧道：穿过奇妙的隧道，化身迷你的小人儿，鞋盒大小的皮卡也可以载上7个队友飞驰~
· 放大镜：想要化身巨人么！快使用放大镜，让敌人体验直击灵魂的压迫感，微微一击把敌人弹飞到天空！
· 任意网：可以将任意单位抓起来丢向目标点，玩的就是一个搞怪捣蛋！
2.4张新乱斗地图：主打一个互坑
全新玩法来袭！4张地图，全新体验，单局2-3分钟，随时随地，打开即玩！这把战斗无压力，乱斗地图玩出了八百个心眼子！一起穿越游戏世界，在疯狂决斗场、滚木圆台中戏耍敌人，坑哭队友吧！休闲时刻再来一把欢乐吃币人~输赢都走开，这把比比谁坑的更特别！
3.热斗赛：争霸电玩游戏王 参与送道具卡皮肤
少年永远热血，竞技永不停歇！荣耀热斗赛，谁才是真正的电玩游戏王？快来报名参与热斗赛，获取荣耀之证；努力进阶争夺全省全服最强称号吧！另外，多人组队事半功倍，热斗赛最多可邀8人开黑，自己菜别怕，好友带飞共享荣誉！
4.奇妙8v2娱乐赛：来开随机地图盲盒
是真的！海滩地图与丛林地图回归啦！本次8v2娱乐赛，除了地图回归，还混入了一些奇妙的规则~失重、滑行、体型变化等机制将会和地图一起随机混合出现，多达48种组合！那么下一把，又将开出什么新鲜体验呢？
【时装/皮肤/活动预告】
1.魔术师·电玩主理人套装免费送
里奥有什么坏心思呢？只是想给大家送五周年第一份贺礼罢了！2023.08.02上线当天即得免费魔术师·电玩主理人套装~
2.通关宝藏之路：9件永久外观免费得
什么？通关游戏，有神秘大奖？2023.08.02-2023.09.19，收集电玩骰子，一起探寻宝藏之路吧！通关后可免费获得【毒液·像素污染皮肤】、气泡表情、角色动作噢~还有【小骇客·像素源码套装】、【雇佣兵·街头摇滚套装】、【小狮子·淘气船员套装】免费三选一！
3.开启周年回忆
2023.08.03-2023.09.19，在游戏内开启专属自己的五周年回顾之旅，领取五周年限定头像框、气泡框和2018个随机白卡碎片吧！
4.周年庆大转盘
2023.08.02-2023.08.13，五周年大转盘火热开启，本次大转盘将会分8月2日10:00和20:30、8月3日 13:30和20:30、8月4日 13:30和20:30，六个时段补充内容，再也不用担心抢不到可爱的实物周边了！
5.赛季宝藏
2023.08.02-2023.10.31
全新赛季“电玩之星”上架，本次带来了【火箭筒·手柄像素袍】、【飞爪·充能插头】、传说【失忆者·成就之星者套装】、史诗【小狐狸·音律之星套装】和史诗【小梦魇·梦游之星套装】等超多电玩风格新时装和皮肤噢~
好啦，以上就本次8.02版本我的重点计划啦~这一次，邀请少年们共赴五周年电玩盛典，不留遗憾！
                            """
            }),
            ("230705", {
                "content": """
哈喽少年们~ 《逃跑吧！少年》与电视动画《一拳超人》联动版本更新啦~快来游戏内领取免费埼玉时装，打败波罗斯吧！
【版本重点内容】
1.限时联动乱斗玩法： 驾驭英雄能力 开局战力拉满
7月5日至8月2日，全新大乱斗联动地图登场， 驭电吞噬者、无敌葱击菇，万吨毁灭龙，波罗斯...怪人们来势汹汹，将在地图上横行霸道，肆虐全场！击败他们，即可掌握他们的专属能力，还可获得大量道具卡的补充！快和你的好友一起组队，进入对局，不断升级，赢得胜利吧！
2.人气角色时装：埼玉时装免费领
7月5日至8月4日完成英雄试炼任务，即可免费获得【茶气郎·埼玉时装】。除此之外，还有杰诺斯、战栗的龙卷、饿狼，音速的索尼克等更多与电视动画《一拳超人》联动的限定系列时装等着少年们获取！
3.全新逃生角色茶气郎
别追啦，茶气郎苏乐请你先整口奶茶！作为逃生阵营新添的猛将，苏乐的招式集刚柔并济于一身，少年们既可使用苏乐正面刚，以一段技能高速冲刺命中击飞敌人；又可以退为进，在任意招式命中敌方后触发被动恢复自身生命值，溢出转化为护盾。进可攻，退可守！少年们快来使用苏乐秀把6到飞起的连招操作吧~
【版本贴心优化】
1. 道具卡系统改造
（1）道具卡界面加入了分类和排序，可以帮助少年们更方便地找到需要的道具卡，再也不会出现卡就在眼前，却看不到它的场面啦！
（2）单张道具卡展示方式调整，少年们是不是经常出现换了皮肤后找不到道具卡的情况呢？
现在可以直接在道具卡界面看到道具卡的名字啦！
（3）新增道具卡拖动功能，反复“点击”、“使用”是不是有些麻烦呢？现在可以直接拖动道具卡来调整装备了！想卸下还是换位都可以！不过要注意，选中的卡可以直接拖动，未选中的卡需要长按一会儿才能拖动噢~
（4）道具卡信息界面细分为三个板块咯，教学视频，道具卡属性一目了然。
（5）道具卡一键升级功能来啦！想要升级的时候再也不用一直点点点了。勾选后会有二次确认弹窗，不用担心手滑哦~
2. 玩法入口优化
（1）新增页签功能，点击可以直接定位到对应玩法页。
（2）优化了页面视觉效果，所有玩法入口大换新。
（3）新增版本新类目，当前版本的新玩法会在版本新类目统一呈现。
（4）整理了娱乐玩法排序，进化之战和水乐园模式从更多玩法之中移到一级页面显示。
（5）训练场、单人模式和大神资格证合入了训练模式里，同时新手教程收进大神资格证之内少年们不要找错了噢~
【时装/皮肤/活动预告】
1.幻想造物霰弹枪
2023.07.21-2023.09.30，莹莹辉光闪烁，新一期幻想造物开启！【霰弹枪·陨落辉光】和【毒液·荧荧星河】、【肾上腺素·碎裂星穹】、【自走球·光影漫步】等道具卡皮肤来和大家见面啦！快来体验辉光之力给道具卡带来的炫酷效果吧~
2.狂热鼓点-女特工年度特惠
2023.07.14-2023.08.31，一年一度的年度特惠活动来袭！【女特工·狂热鼓手套装】惊喜骨折价，购买礼包全额返钻！
另外！游戏系统正在持续优化中，随时欢迎少年们在任何渠道对游戏不足提出意见~
那么约定好了~带上好友一起开启热血战斗吧~
                            """
            }),
            ("230610", {
                "content": """
哈喽少年们~5月31日，全新赛季来咯！
听说这一次DMM星球的少年们来到了神奇之海，开启了一场奇妙的蔚蓝之旅~
【版本重点更新】
新追捕角色-可露
抓到你了，别想逃跑！淘气云·可露来报到咯~她是一位拥有全新淘汰手段的追捕者，要小心她的云朵哟！倒地的逃生者将会被其自动转移至禁闭室内进行淘汰~同时可露还拥有超强的守门能力噢~
【重点时装/皮肤/活动预告】
1.玩家共创冠军时装-小狐狸·玖儿-翩翩琉璃
2023.06.22-2023.07.23，玩家共创大赛第一名埋埋设计的时装【琉璃】上线啦！一起体验小狐狸穿上新衣，踩着落花翩翩而来，使用赠送【动作·翩翩】，在落花中优雅起舞的感觉吧~
2.战斗少女·艾可-星耀时装
2023.06.16-2023.09.27，猛虎袭来~战斗少女·艾可穿上帅气星耀时装【守护者：白虎套装】，并携带【传送门·白虎跃空】、【飞爪·白虎之守】等道具卡皮肤来和大家见面啦！
另外！游戏系统正在持续优化中，随时欢迎少年们在任何渠道对游戏不足提出意见~
那么约定好了~5月31日，一起开启蔚蓝之旅吧~
版本 8.16.1 2023-05-31
哈喽少年们~5月31日，全新赛季来咯！
听说这一次DMM星球的少年们来到了神奇之海，开启了一场奇妙的蔚蓝之旅~
【版本重点更新】
新追捕角色-可露
抓到你了，别想逃跑！淘气云·可露来报到咯~她是一位拥有全新淘汰手段的追捕者，要小心她的云朵哟！倒地的逃生者将会被其自动转移至禁闭室内进行淘汰~同时可露还拥有超强的守门能力噢~
【重点时装/皮肤/活动预告】
1.玩家共创冠军时装-小狐狸·玖儿-翩翩琉璃
2023.06.22-2023.07.23，玩家共创大赛第一名埋埋设计的时装【琉璃】上线啦！一起体验小狐狸穿上新衣，踩着落花翩翩而来，使用赠送【动作·翩翩】，在落花中优雅起舞的感觉吧~
2.战斗少女·艾可-星耀时装
2023.06.16-2023.09.27，猛虎袭来~战斗少女·艾可穿上帅气星耀时装【守护者：白虎套装】，并携带【传送门·白虎跃空】、【飞爪·白虎之守】等道具卡皮肤来和大家见面啦！
另外！游戏系统正在持续优化中，随时欢迎少年们在任何渠道对游戏不足提出意见~
那么约定好了~5月31日，一起开启蔚蓝之旅吧~
                            """
            }),
            ("230426", {
                "content": """
哈喽少年们~4月26日，版本更新咯！
【版本重点更新】
1.全新训练场
还在为不知如何练习技术而苦恼嘛？全新训练场，TA来啦！无限金币？无敌模式？你想要的都能满足，快进入训练场，一飞冲天，成为大神吧！哦对了！还可以邀请小伙伴一起练习噢!
2.全新武器卡-聚合弓
秒了！秒了！1箭99！来试试攻击远&伤害高的全新武器卡聚合弓吧！体验拉弓时间越长，打击面越小，但伤害越高，射程越远的独特设计！
【版本福利预告】
1.DIY艾可时装免费送
设计师艾可的灵感闹脾气离家出走啦~发布紧急求助！2023.4.28-2023.05.21少年们完成对局任务即可获取灵感，DIY专属艾可时装，制作完成后即可免费获取~
【版本贴心优化】
1..平衡性调整
（1）命石者-衡
· 技能冷却时间上调为35|32|30|28；技能消耗调整为0金币；
· 强力抱摔技能新增0.25秒前摇时间，飞行与击飞敌方的距离下调为3.5格|1.5格，技能释放时间减少20%；并取消该状态下的额外护盾。
（2）小狐狸-玖儿-甜心锁链技能调整
· 冷却调为35|32|29|25秒；技能消耗调为0金币；
· 瞄准距离下调为4.5格，断开距离上调为7格；
· 断开链接调为0.75秒后会断开链接，链接命中速度提升33%；
· 链接倒地队友后，新增1.5秒的准备时间，才可拉取倒地队友。
                            """
            }),
            ("230322", {
                "content": """
哈喽少年们~3月22日，全新版本上线啦！
超多新内容，一起来看吧~
【版本重点更新】
1.新逃生角色——夜翎·利芙
灵活走位，戏耍追捕，刺客利芙加入逃生阵营！她的飞刃，一开一合，敌人尽在掌握！同时，她也拥有着进可攻退可守的自保能力，攻击后的冲刺让她灵活穿梭战场！另外大声通知：新角色上线期间（2023.03.22-2023.04.11）完成任务可免费拿头像框，气泡框等好礼噢~
2.新赛季主题-荣光之誓
全新赛季主题“荣光之誓”上线啦~全新主题大厅背景更新，更有角色时装、道具卡皮肤、单件等好礼上线，无论是行走在白昼还是奔袭于黑夜，我们都一起为守护荣光城奋力战斗！
【版本福利预告】
1.免费皮肤——唤风镖10/13级皮肤
道具卡唤风镖10级皮肤量子动能，和13级皮肤神铸之刃将在本次版本更新同步上线，少年们快来升级手中的唤风镖体验这狂风吧！
2.七日登录领福利
2023.3.31-2023.4.16七日登录领福利，参与对局任务，更有机会免费获取小灰机全新道具卡皮肤青空远航哦~
【版本贴心优化】
1.组队大乱斗功能优化
（1）增加了队友倒地后的箭头指示，少年们能够清晰的在人群中锁定队友啦~
（2）增加了选择出生位置界面，正在等待的少年们可以get更多信息。
（3）进行了结算评分标准优化。
                            """
            }),
            ("230222", {
                "content": """
哈喽少年们~2月22日我们将进行新年后的第一次版本更新啦！新的一年我们增加了新的玩法内容，并对游戏体验进行了优化~ 快来一起看看吧~
【版本重点更新】
1.全新道具卡——车轮滚滚
全新道具卡车轮滚滚上线啦！一起再体验一次童年最爱的碰碰车吧！在使用它时，少年们可以主动撞向敌人，同时也可以让自己获得“duang duang”的反弹快感噢~
2.抢金币玩法开启
还在为能量晶体不够而苦恼？变形金刚角色来帮忙啦！2.24抢金币玩法开启，少年们可以选择和心仪的变形金刚角色并肩作战~这一次，我们共同战斗！
【贴心优化】
本次我们针对游戏系统进行了相关优化，优化仍在持续进行中，欢迎少年们在任何渠道随时对游戏不足提出意见与反馈~
1.角色、道具卡平衡性调整
2.新信誉分系统上线
3.结算规则优化
4.角色时装/道具皮肤局内试玩功能优化
5.角色购买界面优化
【重点时装预告】
星粉活动·璀璨音途
“2023.03.10-2023.06.11”，虚拟歌姬小狐狸将带着她的星耀时装【小狐狸·璀璨星途套装】、【医疗箱·疗愈音箱】、【小灰机·巡回音浪】等道具卡皮肤和大家见面！
                            """
            }),
            ("230111", {
                "content": """
在很久以前，由于星球爆炸，一颗能量晶体掉落到DMM星球上，
依托于能量晶体的能量，机械城应然而生......
随着机械城的发展，能量晶体散发出的波动，吸引了塞伯坦的变形金刚纷纷前往机械城......
欢迎来到，机械纪元！
----------更新内容-----------------
【大乱斗重磅更新】
大乱斗将迎来科技感满满的新地图啦！擎天柱、威震天、大黄蜂、红蜘蛛、热破、声波变形金刚也将强势加入大乱斗！少年们快与变形金刚进入有趣爽快的对局，一同制霸战场，绝地反击！
【变形金刚集结！】
近来，擎天柱与威震天所代表的两个阵营，对于能量碎片的归属和使用方式产生分歧，分析激化矛盾，大战一触即发！在DMM星球内，少年们可以选择支持的阵营加入，未来掌握在你们手中！
【新追捕阿治】
全新追捕者劲铠·阿治具有强大的正面淘汰能力。手臂上的臂铠能提供动能，让他打出难以躲避的升龙拳，阿治坚信：胜负，即将分晓！我的肩铠说的！
【新春贺礼送不停】
请查收这份新春贺礼！小骇客免费时装、红蜘蛛/大黄蜂主题时装3日体验让你焕然一新过春节~更有拜年祝福和整点红包等你来查收噢~游戏内更多好礼，陪你过新春！
【SS18赛季-机械纪元】
想沉浸式体验机械纪元？那可不要错过SS18赛季！ 失忆者·威震天主题时装、机械之心·代号：磁电、迫击炮·机龙咆哮，肾上腺素·动能胶囊等时装&道具卡皮肤，机能风拉满~ 
                            """
            }),
            ("221123", {
                "content": """
“哐哐哐哐~”
“够啦！”
在我一千零一次敲打在策划大哥的办公桌上时，他终于忍不住了......
“你究竟要干嘛！”（抓狂.jpg）策划大哥顶着两个黑眼圈，快哭了。
“哥~求更新！”我眨巴着眼睛无辜地看着他~
2000 hours later......
“哐哐哐哐~”
“更了！更了！”策划大哥掩面而泣，“真的更新了~别敲了呜呜呜~”
嘿嘿，家人们11月23日《逃跑吧！少年》版本更新，快来玩吧！
----------更新内容-----------------
【影之忍者——超进化】
想要尝尝影子的威力吗？影之忍者喜提超进化！全新的影之忍者，将释放影之威力——位移之影灵动飘逸，影之分身虚实难辨。真亦可逐，影不可捕——忍者之刃寒气来袭！
【新道具卡——互拉圈】
嘿！想要和朋友来一场极致的拉扯吗~全新道具卡互拉圈上线！作为贴贴敌人和队友的最佳道具卡，你可以使用它以在场全部玩家为目标投掷。即刻组队开黑，和大家亲密接触吧！
【追捕加入娱乐玩法】
追捕有脚不能跳？NO！现在起，大家可以选择自己心爱的追捕角色在大乱斗、竞速之战等娱乐玩法畅快地游玩了！ 一起来加入战斗吧！
【多重福利送不停】
双十一青龙潜影返场，双十二合集大礼包，更有冬季礼盒等海量福利，快来收福利吧！欸~福利太多，真的要收不下啦~
                            """
            }),
            ("221019", {
                "content": """
【新逃生角色-幽妍】
指绘师幽妍为追寻画中色彩，她来到了DMM星球，一瞬间温暖的情绪袭来，幽妍的画作自此充满色彩......
【新赛季SS17幻梦绘本】
为了感谢少年们传递的温暖情绪，使得自己的画作拥有色彩与生机，幽妍策划了一场画中世界的旅行，邀请少年们进入她的画中开启一场奇妙的冒险，并且郑重其事地将此次行程命名为幻梦绘本。
【金库攻防重磅更新】
金库攻防再添一员，软萌的团子来啦！在此次更新中团子将在对方发起进攻的时候，使用粽子护盾为队友承担爆发伤害，化解危机。
【竞速之战玩法再启】
10月19日，火热的竞速之战将再次开启！这一次，所有恐龙均可畅玩，所有属性全部满级，畅快的道具对决，极致的乱斗体验，等你来战！
【福利活动】
11月04日-11月22日，登录游戏签到领好礼，并有机会获得经验翻倍、限时时装、半价点券等奖励噢！快来开黑吧！
                            """
            }),
            ("220907", {
                "content": """
【竞速之战-玩法升级】
人气玩法竞速之战升级啦！新增小幽灵道具卡，它可对敌人造成伤害和减速效果噢~此外还有新道具卡群体护盾，可在激战中保护自己与队友的安危并解除Debuff，快用新道具卡和队友来一场刺激跑酷吧！
【正版授权-奥特曼联动第二弹】
9月30日奥特曼联动开启第二弹！泽塔奥特曼、泽塔奥特曼·德尔塔天爪，赛文加等将陆续登场~更有精彩系列活动等你探索！
【双阵营武器“唤风镖”】
双阵营武器“唤风镖”强势来袭！唤风镖能够卷起无视地形的狂风，对路径上的造成穿透伤害！接到飞回的唤风镖将给予下一次狂风更强的力量。
【龙币大放送】
抢龙币玩法上线，击败对手收集龙币兑换限定角色时装！
【活跃活动合集】
活跃活动，福利多多！签到送好礼，海量返场折扣礼包。大转盘重磅上新，参与就有机会获得命石者和小骇客赛车主题时装哟！
                            """
            }),
            ("220803", {
                "content": """
【大黄蜂登场】
变形金刚正版授权皮肤-大黄蜂已上线，飙车、变形、酷玩、舞蹈....大黄蜂就是你的最佳选择！完成任务收集恐龙，即可解锁联动皮肤！！
【全新赛季-龙之星乐园】
如果让我选一件夏天最酷的事情...那就是去龙之星乐园！这里有爱喝肥宅快乐水的翼龙、喜欢亮晶晶水果的迅猛龙、爱吃日料的沧龙...性格各异的恐龙等你领养，还能带着它们去参加跑酷噢！
【新角色-机械之心奥博】
首个双形态追捕角色燃擎登场！双形态自由切换的追捕者来啦~变车时的突然冲刺，变人后的战斗形态，再配合上道具卡，强大的控制加上输出会让逃生者们十分头疼噢~
【全新地图-竞速之战】
重磅道具跑酷竞速玩法来袭！3人组队一共9人在充满各种机关和障碍的赛道上比拼！同时抢夺道具卡！和队友配合一起给敌人制造麻烦吧！扭转局势就靠你啦~
【新道具卡-噗噗蛋】
全新道具卡噗噗蛋闪亮登场！它的主要能力是牵制和封锁哦~重点是...噗噗蛋受到任何攻击都会打破变成一条小龙，一口咬住范围内最近的敌人，将其禁锢！这绝对是你最忠实的小保镖！
【生日福利大放送】
4周年乐园狂欢！入园即领专属龙宝，还有更多精彩好礼等你发现~
                            """
            }),
            ("220706", {
                "content": """
【全新升级BOSS战-进化之战】
6名逃生者进行匹配，随机一人当BOSS。少年们可选择不同的能力升级并互相组合，每一局都是精彩独特的体验~成为BOSS或者打倒BOSS吧！
【新道具卡-吼吼号出击】
变身吧~少年！全新道具卡吼吼号已上线，变身吼吼号获得护盾，背上队友不受到伤害，安全感拉满~主动技能-向前发射电磁脉冲，命中敌人并造成眩晕~你们准备好了吗？一起加入战斗吧！
【生日庆典筹备中】
4周年庆典筹备计划开启！每日打卡、周年涂鸦，玩家设计皮肤......还有万众期待的周年版本重磅预告！每一个都是惊喜，每一个都不容错过~少年快来参加吧！
                            """
            }),
            ("220525", {
                "content": """
滴滴-滴-滴滴报告队长！本次的目的地是...星际！
【SS15赛季揽星起航】
DMM宇宙管理局正在筹备向星际发起探索，尼诺带领的DMM机动队的成员组成了新的小队，此次的行动名称为“揽星计划”....
【全新角色】
新逃生者灵膳子-团子前来报到！据说他有个“神奇背包”，能将能量转化为随机的变身食物，吃了团子的食物还能获得特殊能力噢~至于吃到的是粽子还是蛋黄酥？还得看团子的心情了。
【角色升级】
追捕老将-机器人超进化啦！强大的侦察技能能够让他探测到敌方的方位；手部的强磁体可以交互地面物体并自动吸起附近倒地的敌人。小提示：搭配能量腕炮效果更佳！
【自建房大更新】
自建房新增四种娱乐玩法：金库攻防、夺宝奇兵、红包大作战和组队大乱斗，快叫上好友尽情开黑！
【更多活动】
本次代言DMM大陆知名‘时代洋流’主题时装的模特是...这身衣服可真是为她量身打造呢！时尚弄潮儿们，赶紧来游戏内体验最新款吧！
                            """
            }),
            ("220420", {
                "content": """
【角色升级-发明家】
【发明家-尼诺】和他的发明【禁锢空间】已全面升级！尼诺能够创造一个永久持续且拥有淘汰敌人能力的禁锢空间，能够快速将敌人传送到禁锢空间的同时，当尼诺受到伤害时禁锢空间还能释放能量波噢~
【全新道具卡-霰弹枪】
霰弹枪能向前方扇形区域开火，发射伤害随距离减弱，快来尝尝近距离刚枪的快感吧！
【娱乐玩法更新】
本次更新中，小骇客·琪琪加入了【金库攻防&夺宝奇兵】哦~小骇客的定位是刺客，她能够使用武器正面消耗或隐身切入战场，配合幻影手连续爆发收割！
【组队功能优化】
少年们在综合频道中，可以点击头像，使用新增的【邀请组队】按钮，直接发起对应模式的组队邀请~尚未结识的少年也可以邀请哦！
【SS14西游主题赛季】
失忆者与衡一行人前往DMM宇宙管理局，不料偶遇穿梭能量波动，穿梭到了西游世界...全新赛季火焰山主题赛季进行中，看失忆者化身孙悟空玩转花式道具！
【更多活动】
嘿嘿~小学妹的小卖铺开张啦！（叉腰.jpg）不定时给少年们带来折扣噢！至于卖什么嘛....嘻嘻快去游戏中寻找兔兔的踪影吧！
                            """
            }),
            ("220316", {
                "content": """
火焰山之旅启程~
【SS14西游主题赛季】
失忆者与衡一行人前往DMM宇宙管理局，不料偶遇穿梭能量波动，穿梭到了西游世界...全新赛季火焰山主题登场，看失忆者化身孙悟空玩转花式道具！
【全新角色】
新逃生者-小骇客·琪琪上线啦！不仅可以在指定区域持续隐蔽踪迹，还能够利用手臂力量远程交互物体噢~“代码从不说谎，但是眼睛可不一定。”
【全新玩法】
新玩法-夺宝奇兵登场，本次新玩法的目标是-争夺宝物！10名玩家分2支队伍将对方基地中的宝物带回己方的基地获得积分，分高的队伍将取得胜利。
【组队功能优化】
游戏新增招募功能，房主可以通过房间内邀请列表下方的招募按钮，向招募页签发送招募邀请信息。一键组队，欢乐上分。
【更多活动】
DMM大陆知名‘时代洋流’主题时装正在紧锣密鼓筹备中，更有一波愚人节好礼即将搞怪来袭。
                            """
            }),
            ("220216", {
                "content": """
奥特曼超燃现身，光与暗的战斗一触即发！
【正版授权】
ss13奇迹之光赛季进行中，赛罗、贝利亚、格丽乔...多个奥特曼时装、道具卡皮肤等你开启。
【大作战玩法-新体验】
玩家组队一起争夺光之结晶，将石化的迪迦唤醒成为不同的形态，让奥特曼同少年们一起去战斗吧！
【角色升级】
小狐狸·玖儿升级进化！叮铃铃——治愈灵波已连接，人气辅助小狐狸将拥有更加强大的技能来保护队友打出配合啦，快来领一只回家吧～
【金库攻防-角色武器更新】
玩家可选择命石者·衡加入战场！远程持续输出快速收割，搭配全新道具卡‘火力支援’和武器‘突击步枪’制霸全场，咱就是说轻松成为全场mvp！
【海量福利】
开春啦～一大波节日限定惊喜来袭！全新时装和道具卡皮肤即将陆续登场。等等？怎么还有小学妹的试卷出没？！
                            """
            }),
            ("220119", {
                "content": """
奥特曼超燃现身，光与暗的战斗一触即发！
【正版授权】ss13奇迹之光赛季启动，赛罗、贝利亚、格丽乔...多个奥特曼时装、道具卡皮肤等你开启。
【玩法升级】古兰特王入侵DMM星球！乱斗大升级，每位少年都能化身成光，去击败怪兽，去做救世主！
【全新角色】新逃生者 命石者-衡加入战斗，能飞天能抱摔，战场新霸主降临！
【全新道具卡】全新道具卡能量腕炮登场，体验在空中"biubiubiu"的快感！
【海量福利】登录游戏即可领永久胜利队时装！每日打卡可再获赛罗冲锋枪皮肤！
【全新活动】还原经典ip，奥特曼卡牌大收集！还有迪迦奥特曼时装、皮肤、动作等你获取！
                            """
            }),
            ("211231", {
                "content": """
一、又萌又凶全新追捕“小狮子-巴库”来袭
二、“金库攻防”玩法正式上线
三、幻想造物2期—星聚之地闪耀登场
四、“幸运抽奖”第二期开启
五、BUG修复&游戏调整
                            """
            }),
            ("211201", {
                "content": """
一、全新追捕小狮子来袭
小狮子巴库是一个拥有超强追击能力和超强对抗能力的追捕，跨地形快速移动能力和全图视野让巴库在追击的时候有着超强的优势！
还能依靠独特的输出转化生命值的机制让它在后期对抗阶段更加坚挺~
二、“金库攻防”正式上线
金库攻防又又又又又带着全新内容来啦！在本次更新中，新增助攻机制，在助攻时获得击杀一半的金币!
更有【战绩】数据界面的新增，统计每个玩家K/D/A、输出、承伤、治疗数据带给玩家们更好的体验优化~
三、大乱斗、抢红包玩法更新
在本次玩法更新中，战斗体验大升级~武器霰弹枪加入战场！
还有道具卡-生物炸弹，它能够对爆炸范围内的友军缓慢回复血量和加速，并对敌军产生持续扣血和减速效果，发明家看了都直呼好用！
                            """
            }),
            ("211027", {
                "content": """
一、SS12全新赛季雾影密钥神秘开启
DMM大陆最近发生了很多奇怪的事，为了破解谜团，此次赛季中莉安娜将化身为魅影怪盗，小狐狸和女特工变身为见习法医和雾都探长！带领玩家们拨开迷雾，一同探寻事件真相！
二、全新道具卡“时光机”上线
“时光机”是尼诺的时间机器原型，因为技术尚不成熟，它只能实现短暂的时间穿越。
在玩家救援队友，对抗敌人的过程中可以利用强大的时间回溯能力快速脱离战场和恢复血量健康以保证自己安全撤出战场，快来游戏内用时间戏耍敌人吧~
三、角色升级-水之忍者进化归来！
伴随着神秘时光机降临DMM，泷受到了时光机光芒的照耀，身体机能大幅度提升，
水之忍者得到了全新的力量，实现超进化！进化后的水之忍者在保留原逃生能力的基础上把水龙术改造为更具进攻性与灵活性，使其牵制能力和灵活性达到S级！
四、金库攻防四期
金库攻防四期又带着全新内容来啦！在本次更新中，星辰圣女·莉安娜和黎明盾卫·谢尔德也加入了金库攻防~花式玩法对抗敌人！
                            """
            }),
            ("210915", {
                "content": """
一、全新角色黎明盾卫登场~
谢尔德是首位具有双主动技能的逃生者，既可以长时间的牵制敌人的行动，又能在合适的时机举起手中的盾牌，抵挡海量的伤害。
二、玩法“金库攻防”三期
在本期金库攻防中，战斗少女艾可的卡组搭配和武器进行了全新升级，另外魔术师的武器和小狐狸专属道具卡也进行了全新升级。战力提升，趣味加倍，就等你来探索!
三、卡组推荐功能
道具卡界面新增了便捷组卡功能，便于大家更好配置适合自己的道具卡。不会给角色组卡？没关系，卡组推荐里有官方总结的实用卡组等你来选！
四、角色碎片系统
全新角色碎片系统开启！获取角色的难度将会下降了哦~大家可以通过每日签到和商城推荐等地方免费获取角色碎片，获取相应的碎片数量即可兑换想要的角色哟~
                            """
            }),
            ("210818", {
                "content": """
一、新道具卡“小灰机”酷炫出动
作为“首个飞行道具卡”的小灰机，兼具优秀的操控性和跨地形移动能力，让空中飞行的感觉无比顺畅，给少年们带来超丰富的博弈体验！
二、SS11赛季“玩具之城”强势登场
众人穿越进孩子的玩具箱，化身为各种小玩具~憨憨的纸板小恐龙、正义感爆棚的武士手办、插上了发条的公主玩偶，快来解锁更多童趣时光！
三、玩法“金库攻防”二期惊喜来袭
在本期金库攻防玩法中，小狐狸玖儿的卡组搭配得到了优化，将拥有自己的专属武器和道具卡，战力提升，趣味加倍，就等你来体验！
四、回流活动
许久未登录的少年们将可能收到来自DMM大陆的挑战书，达成挑战将获得随机生成的奖励哦~
五、开学季系列活动
就快要开学啦~少年们准备好新学期的冲击了嘛？新的学期也要支棱起来！
                            """
            }),
            ("210714", {
                "content": """
一、新角色“星辰圣女-莉安娜”闪亮登场
莉安娜是首位携带“专属武器”的逃生者，快来感受颜值与实力的暴击吧！
二、新玩法“金库攻防”火热开战
3V3激烈对抗！随机角色、无限弹药，还有杀伤力极强的萌犬混入！一起摧毁敌方的金库！
三、3周年庆典来袭
《逃跑吧！少年》3岁啦！少年们快来参加精心准备的生日派对吧！超多有趣的内容等着大家哦~
四、七夕专属活动
新时装、新礼物~ 超多福利过七夕！
                            """
            }),
            ("210609", {
                "content": """
一、新角色“影之忍者”帅气登场
风一般的女子——实力派忍者·缈来袭！来感受影子的威力吧！
（来自小学妹的情报——缈配上新衣服简直颜值暴击！）
二、赛季宝藏SS10“航海奇缘”开启
一起成为海上冒险家，与人鱼公主开启一段航海奇缘吧！
三、夏季新主界面场景上线！
阳光！沙滩！椰树！大海！ 夏天来啦！
四、商城打折活动开启
欢迎来到小学妹的魔法茶会！超低折扣等你来~
五、幻想造物功能优化
抽奖的展现形式做了颠覆性的创新！只想为少年们带来更好的抽奖体验~
六、体验优化与问题修复
1.部分玩法平衡调整
2.修复了震荡波偶尔无法进行第二段效果释放的BUG
3.修复了在单局内变成小的变身道具可以卡到保险柜里，不会受到火箭筒的攻击的BUG
4.修复了部分显示异常BUG
                            """
            }),
            ("210428", {
                "content": """
一、更新了一张超级帅气的新道具卡“震荡波”
简简单单就可以做出帅气的操作，Boom！就要掷地有声的炸裂！
二、五一欢乐活动开启！
幸运大转盘、每日登录领奖、集字任务得免费时装~
三、新道具卡皮肤抽奖·幻想造物开启！
各种新皮肤特效超炫酷！带上这把星耀能量剑，少年你所向披靡！
四、各种新活动陆续上线
520时空主题活动、六一儿童节活动等等
五、体验优化与问题修复
1.部分玩法平衡调整
2.部分显示异常BUG修复
3.修复了小学妹在兔子状态下被小梦魇气泡命中，使用针、药包解除后无法跳高的BUG
BUG少了~游戏也更加顺畅了~
                            """
            }),
            ("210331", {
                "content": """
1. 新道具卡【追踪雷】全新上架
· 探测布防好帮手，放置后隐身，敌人靠近时主动出击并造成减速
· 新卡活动开启，完成任务免费领取，并能获得限定皮肤、炫光奖励
2. SS9赛季宝藏【甜蜜轰炸】幸福开启
· 草莓小学妹、蓝莓女特工、还有糖果机器人，甜到爆炸糖果主题赛季闪亮登场~~
· 美食之旅中随手完成任务、解锁海量奖励，一同开启总价值超过2000元的赛季宝藏
3. 更多玩法限时开启
· 红包大作战、丛林8v2加入【更多玩法】，等你来战！
4. 主界面更新为春季主题啦~
5. 玩法平衡性调整
                            """
            }),
            ("210310", {
                "content": """
1. 新角色“水之忍者泷”登场
- “泷”掌握着水之忍法，可以在复杂的战场环境中踏浪穿行
- 新角色活动全新改版推出：活动期间只需低价点券即可获得“水之忍者泷”
2. 星粉祈愿第三期「游戏世界」重磅推出！
- 全新三套炫酷电玩主题时装，还记得你儿时痴迷的电玩世界吗？这次我们让你做最炫目的电玩崽~
- 幸运值不再清零！希望你每期都能幸运满满~
- 在商城每日折扣道具区域，有几率刷新限时折扣水晶，助攻你的星粉之愿
3. 赛季返场功能
- 还在为自己错过以往的赛季而羡慕不已吗？这份缺憾现在弥补你！以往的赛季时装开始返场啦~
4. 白色情人节活动
- 活动期间疾跑·心之痕皮肤，炫光·甜蜜浪潮限时限定折扣开启
- 累计签到3天，即可领取永久涂鸦和“666”礼物奖励
5. 商城推出新外观，猜猜有没有你期待的外观呢？
6. BUG修复&道具卡平衡性调整
                            """
            }),
            ("210127", {
                "content": """
一、新道具卡“蹦嘣枪”
·“蹦嘣枪”可以让你在各种角度发起进攻，只要能规划好弹射轨迹，这将是把无所不能的武器
· 新卡活动开启，完成任务新卡免费得！更有限定皮肤、炫光等你领取
二、SS8赛季仙侠幻想盛大拉开帷幕
· 梨花舞剑，白衣胜雪，目若星辰，这场仙侠之旅你想要谁伴你同行？
· 仙侠之旅中随手完成任务、解锁海量奖励，一同开启总价值超过2000元的赛季宝藏
三、喜气洋洋的新春狂欢
· 经验翻倍、开箱半价以及限时新春主题时装掉落等三重福利限时开启，你可以穿上喜气洋洋的新春限定时装，与小伙伴们一起在躲猫猫世界共度美好佳节！
· 春节签到7天可领永久失忆者·潮流国风套装
四、甜蜜满满的情人节献礼
· 送出情人节专属礼物“恋爱木马”分别可领限定头像框奖励
· 英伦风情人节限定套装、涂鸦来袭，收集小爱心即可兑换
五、圆圆满满的元宵节Party
· 欢乐的你追我赶之余，收集元宵活动道具，可兑换新春定制的雇佣兵新年主题套装
                            """
            }),
            ("201223", {
                "content": """
一、新道具卡“战术捣弹”
·“战术捣弹”使后会变身为一枚导弹，可爆炸，速度越快造成伤害值越高
·轻松完成任务，即可免费领取“战术捣弹””
二、星粉祈愿第二期「炫音霞光」推出
·“DMM最炸街的酷炫风格套装”，推出了失忆者、雇佣兵、女特工三套时装
·它拥有：街头风造型、反光镜面效果的镭射布料、独一无二的对局内拖尾特效、动作和语音
三、圣诞元旦缤纷双旦活动
圣诞限定外观、丰富活动，欢乐过双旦！
·圣诞大转盘：失忆者、小学妹等限定圣诞时装
·圣诞祝福：赠送或收到新礼物“暖心姜饼人”可领取圣诞限定头像框
·圣诞返利：送肾上腺素皮肤
·元旦点灯：完成任务兑换限定皮肤、涂鸦
四、其他优化&新外观
五、玩法调整
                            """
            }),
            ("201125", {
                "content": """
一、新追捕者“小梦魇·小眠”
· 拥有梦魇之力的强力追捕者“小梦魇”全新登场！小身板，超强力！
· 新角色活动全新改版推出：活动期间只需低价点券即可获得新角色！
二、赛季宝藏SS7“睡衣派对”
· 汪汪狗发明家、嗷嗷龙魔术师、喵喵猫战斗少女，你会邀请谁一起开趴？
· 开启宝藏，总价值超过2000元的礼包即可带回家
三、全新“星耀”武器皮肤横空出世
·“DMM神秘偷偷开发最尖端的科技”，推出火箭筒、自走球、阻挡箱的星耀品质皮肤
·“星耀武器皮肤”它拥有：
①“酷炫造型”——科技感十足的外形和配色
②“酷炫特效”——对局内独一无二的子弹特效
四、其他活动&新外观
五、玩法调整&BUG修复
                            """
            }),
            ("201028", {
                "content": """
1.老玩法新体验！
·改版后的新·BOSS战模式重磅回归，熟悉的配方，更好的乐趣体验~
·大乱斗模式加入新道具卡，这会给整个对局带来什么样的策略选择变化呢？
2.全新“星耀”品质时装横空出世
·全新的超稀有布料材质，特有的拖尾特效，华丽的出场动画和独一无二的软萌配音
3.商城优化
·界面更美观，操作更便捷
·内容新增：全新立体绘图、每日免费奖励等，每天快乐多一点点~
4.玩法调整
·4V1、8V2模式加快游戏节奏、调整经济平衡
·速度数值平衡调整
5.体验优化和BUG修复
                            """
            }),
            ("200923", {
                "content": """
1、全新武器卡“能量剑”上线
·  首款近战武器，超高的爆发伤害在正面对抗中绝对能占据上风
·  新卡活动开启，完成任务新卡免费得！更有限定皮肤、炫光等你领取
2、SS6赛季“古堡舞会”震撼开场
·  华美的舞会礼服、奇幻的魔法道具，这场“古堡舞会”怎能缺少你的身影？
·  游玩中随手完成任务、解锁海量奖励，一同开启总价值超过2000元得赛季宝藏
3、国庆中秋双节狂欢
·  角色经验翻倍、宝箱随机掉落限定熊猫系列T恤时装等三重福利限时开启
·  中秋限定道具皮肤、涂鸦来袭，收集月饼即可兑换！
4、玩法调整
·  部分道具卡的数值优化
·  新增治疗球道具卡10级、13级皮肤
5、体验优化和BUG修复
                            """
            }),
            ("200819", {
                "content": """
一、新道具卡上线，“新卡活动”同步开启
1、新道具卡“充气垫”上线
·你可以用它连贯地翻越地形，快速地转移位置，将跑酷一般的追逃体验发挥到极致
2、“充气垫”新卡活动
·升级领奖活动新增传说限定炫光·跃动之星
二、全新皮肤·引力场 华丽登场
1、引力场10级皮肤·飓风之力
2、引力场13级皮肤·魔能沙
三、体验优化与问题修复
1、修复在游戏内看到别人使用跳高攻击时越跳越高的BUG
2、体验优化：
·主界面场景优化
·公告位置的转移
3、部分显示异常BUG修复
                            """
            }),
            ("200722", {
                "content": """
1.新角色上线与相关活动限时开启
· 新角色——小狐狸玖儿上线
· “小狐狸登场”新角色活动限时开启
2.2周年派对大狂欢 10大活动嗨不停
· 所有角色限时免费体验
· 其他三重UP福利活动，将享有角色经验翻倍、宝箱随机掉落限定奖励等福利
3.SS5赛季宝藏【夏恋花火】震撼开场  
· 主界面场景全新夏日祭典烟花之夜主题
· 数十款夏日祭和风主题角色时装等奖励
· 开启宝藏获得的总价值超过2000元
4.体验优化
· 角色天赋初始拥有三个技能
· 道具卡和平衡性调优
5.新增“邀请好友共享好礼”系统
· 邀请好友加入躲猫猫世界，共同领取丰富奖励
6.修复了部分bug
                            """
            }),
            ("200624", {
                "content": """
1、道具卡“生命上限”超进化为“生命护盾”
· 集解除控制、增加护盾、提升生命上限于一身
2、道具卡超进化活动开启
· 免费领卡、技巧详解、升级领奖、助力升级四大活动限时畅享
3、治疗球、自走球、滑板道具卡功能优化
4、滑板和魔法墙的13级皮肤全新上线
5、单局时间缩短、断线重连等机制优化
6、新增屏蔽语音、限制他人观战等个性化设置
7、部分BUG修复
                            """
            }),
            ("200525", {
                "content": """
1.修复赛季宝藏时装展示问题
2.低灵敏度操作手感问题优化
3.发明家持枪动作优化
4.修复断线重连的部分BUG
5.核心玩法优化
· 优化了8v2随机锁地图的布局和资源刷新规则
· 道具卡平衡性调整等其他优化
                            """
            }),
            ("200520", {
                "content": """
1. 全新道具卡【治疗球】上架
· 投掷类道具，可召唤1个球形的治疗机器人，自动搜救周围的友方角色
2. 新卡登场活动开启
· 新增彩虹卡包，开启必定获得新卡
· 新卡直购、升级领奖、免费领卡、助力升级四大活动限时畅享
3. SS4赛季宝藏【纯白花嫁】浪漫开启
· 数十款角色时装、道具皮肤、涂鸦、动作等你来拿
· 总价值超过2000元！
4. 核心玩法优化
· 优化了8v2随机锁地图的布局和资源刷新规则
· 道具卡平衡性调整等其他优化
5. BUG修复
                            """
            }),
            ("200423", {
                "content": """
3分钟即可体验到的惊险刺激的【逃生】之旅，收获一场4v1躲猫猫的休闲竞技盛宴
1、新玩法【组队大乱斗】开放测试、支持2名玩家“组队吃鸡”
2、【家族战】限时开放测试、支持家族战10v10匹配
3、全新道具卡【引力场】上架、投掷类道具，可生成一个小型引力场，持续牵引被命中的敌人，并造成一定伤害
4、新卡登场活动开启、新增彩虹卡包，开启必定获得新卡、新卡直购、升级领奖、免费领卡、助力升级四大活动限时畅享
5、Bug修复&网络优化
                            """
            }),
            ("200415", {
                "content": """
3分钟即可体验到的惊险刺激的【逃生】之旅 收获一场4v1躲猫猫的休闲竞技盛宴
1. 全新道具卡【引力场】上架  投掷类道具，可生成一个小型引力场，持续牵引被命中的敌人，并造成一定伤害
2. 新卡登场活动开启   新增彩虹卡包，开启必定获得新卡  新卡直购、升级领奖、免费领卡、助力升级四大活动限时畅享
3. 竞技狂欢节来袭  角色经验翻倍、开启宝箱点券消耗减半、开启宝箱有概率获取限定竞技时装
4. 核心玩法优化（具体内容请参见游戏内公告）
5. 新手体验优化
6. Bug修复；网络优化
                            """
            }),
            ("200410", {
                "content": """
1、新道具卡上架&新卡配套活动优化
道具卡【引力场】上架，控制类投掷道具，丢出后可以将一定范围内的对手吸向圆心位置，像一个炸开的泡泡糖把大家拉回来，具有较强的趣味性和实用性，能够极大地丰富游戏的策略体验。
新卡上架活动改版，原本限时活动【新卡直购】、【升级领奖励】、【超值卡包】将会再度升级，帮助玩家更好地理解新卡的使用乐趣以及使用场景，建立起对新卡的追求，再辅以配套的运营、付费活动，以深挖新道具卡上架期间的活跃和付费指标。
2、家族战系统开放测试
家族战系统推出，玩家可以以家族为单位，组建10人小队，在指定活动时间内与其他竞技水平相近的家族进行匹配，并争夺榜单排名，赢得荣誉。
筛选出的战队将有机会参与后续直播赛段的比赛，通过虎牙直播进行面向全部玩家的赛事表演，并有专业的解说人员进行讲解演绎
家族战将以赛季的形式长期开放，营造游戏内的竞技氛围，帮助玩家对竞技荣誉形成追求，从而更好地了解游戏乐趣和技巧，提升活跃。
测试阶段，家族战将先在王者家族进行试点开放测试
3、新手&AI局体验优化
对当前的新手AI局进行了重构升级，让新手玩家进入游戏后能获得愉快的游戏体验，通过合理设计AI的能力表现，让AI队友能够将一些基础的操作技巧和游戏乐趣在单局中“演示”给新手玩家，让玩家在观察和模仿中不知不觉地上手。
调整了“阻挡箱”道具的投放段位，让新手玩家能够更早接触到“阻挡箱”在众多使用场景中的有效性和趣味性，以及和其他道具联动时出乎意料的效果。
道具栏的初始开放栏位从6个下调到4个，减少新手玩家对于“道具轮换”的理解难度，先对道具卡的形成概念，后续再逐步进行“道具轮换”的策略体验深度展开。
可能会在新手阶段加入半AI、半真人的对局模式，帮助玩家获得更好的初期游戏体验。
4、生存大乱斗玩法优化
玩家千呼万唤的战队匹配是否将会在这个版本与大家见面呢？我们拭目以待。
5、竞技周主题运营活动
四大活动带你融入这场竞技狂欢！
                            """
            }),
            ("200318", {
                "content": """
1、SS3赛季宝藏【电音狂潮】盛大开场 · 数十款电音主题角色时装、道具皮肤、动作炫光等奖励，开启宝藏就有，总价值超过2000元！ · 积分商店神秘揭晓，收集宝藏币兑换顶级奖品
2、道具卡调整 · 对冲锋枪、毒液、巡逻犬的效果进行了“大胆的改动” · 降低了滑板的速度和持续时间
3、生存大乱斗玩法优化 · 新增回复类道具（医疗箱、肾上腺素）的专属栏位，以释放更多的道具卡槽位 · 新增玩家之间淘汰信息的实时公告 · 巡逻犬道具卡加入生存大乱斗模式
4、竞技狂欢节4月10日开启 · 专属时装免费领、经验加倍乐翻天
5、网络优化及bug修复
                            """
            }),
            ("200226", {
                "content": """
3分钟即可体验到的惊险刺激的【逃生】之旅
收获一场4v1躲猫猫的休闲竞技盛宴
1、全新道具卡推出 · 滑板：花式跑酷、载人扫射 · 魔法墙：拦敌减速，己方加速、抵挡子弹攻击
2、多张道具卡玩法及升级效果调整优化
3、赛季宝藏系统优化并修复了部分bug
4、生存大乱斗性能优化并修复了部分bug
                            """
            }),
            ("200115", {
                "content": """
3分钟即可体验到的惊险刺激的【逃生】之旅 收获一场4v1躲猫猫的休闲竞技盛宴
1、全新追捕者登场——发明家·尼诺
2、新玩法【生存大乱斗】在“更多玩法”开放测试
· 20人混战，各自为阵；紧张缩圈，淘汰对手！
3、赛季宝藏【SS2-奇幻狂欢】将于1月22日全新启程
· 任务系统优化，赛季奖励提升
4、新春福利活动即将开启
5、玩法优化
· 新增单人训练场模式，支持与电脑进行4v1对抗
· 优化了匹配规则，避免段位差距过大的选手匹配，可能匹配时间增长
                            """
            }),
            ("191225", {
                "content": """
1、冬季限定特惠礼包——阻挡箱·冰河世纪上架
2、赛季宝藏任务优化 · 平衡了任务难度，优化了单局内任务界面
3、圣诞送礼活动、元旦集字活动即将开启 · 限定头像框、涂鸦等奖励等你来拿
4、观战功能优化，支持多种方式查看战斗画面和数据，同时自建房支持创建裁判房间
5、梦幻水乐园开园时间调整为8:00-22:00
6、性能优化
7、实名认证功能优化
                            """
            }),
            ("191218", {
                "content": """
、冬季限定特惠礼包——阻挡箱·冰河世纪上架
2、赛季宝藏任务优化
· 平衡了任务难度，优化了单局内任务界面
3、圣诞送礼活动、元旦集字活动即将开启
· 限定头像框、涂鸦等奖励等你来拿
4、梦幻水乐园开园时间调整为8:00-22:00
5、性能优化
                            """
            }),
            ("191129", {
                "content": """
1、赛季宝藏系统全新上线——冰雪派对盛大开启
· 开启赛季宝藏，达成活跃任务，赢取冰雪限定人物时装、道具皮肤、涂鸦，还有更多奖励等着您，总价值超过2000元！
· 新赛季将持续8周，后续每个赛季都有新主题和新惊喜等你哦~
2、主界面【冰雪世界】场景更新
3、艾可模型品质提升，给你更美的视觉体验
4、保险柜随机开放玩法自建房上线测试
5、新增道具卡槽锁定功能
6、玩法优化
                            """
            }),
            ("191031", {
                "content": """
3分钟即可体验到的惊险刺激的【逃生】之旅 收获一场4v1躲猫猫的休闲竞技盛宴
1、全新地图——梦幻水乐园 盛大开园 · 马戏团主题禁闭室、趣味喷泉、凶险海盗船、欢乐足球场等多个主题场景同步上线 · 全套美术资源、新奇道具，更多交互开关、双禁闭室玩法尝试给你好玩
2、全新系统——大神资格证发布 · 完成关卡考核，领取大神认证，获取永久涂鸦和卡包奖励 · 初阶新星、进阶高手考核关卡现已开放挑战
3、万圣节活动将于10.31开启，可兑换永久限定涂鸦
4、道具卡系统升级 · 新增卡组一键复制功能，大神卡组轻松copy · 新增道具卡满级预览功能
                            """
            }),
            ("190927", {
                "content": """
1、商城系统升级 · 动作、涂鸦和道具皮肤可在商城购买限时体验
2、超值首充活动来袭 · 幻影流星跑车皮肤、篮球少年套装、炫光·星星舞台，累充12元即领永久！
3、新增操作界面的个性化设置 · 支持自定义键位、自瞄开关及摇杆感应调整
4、优化世界聊天封号规则、空间相册检测机制，举报和反馈机制更加完善快捷
5、新地图测试版已于自建房上线，同时更新了至少10个有趣的bug，欢迎探索！
6、国庆节活动预告——新时装和转盘活动敬请期待"
                            """
            }),
            ("190828", {
                "content": """
1、礼物系统温情上线
· 不仅能送礼物，还能抢礼物
· 新增礼物榜，周榜排名前三可领取限定奖励
2、新增关注和粉丝功能，粉丝数量无上限
· 互相关注后支持私聊及观战功能
3、新增访客功能，方便回访互动
4、艾可新时装上架
5、秋季首充更新，将于9月1日上架
6、部分平衡性改动及bug修复
                            """
            }),
            ("190731", {
                "content": """
1. 周年派对大狂欢 八大福利嗨不停
· 福利一 全新逃生者登场——战斗少女·艾可
幸运许愿抢先拥有新角色，还可收集新角色限定动作、涂鸦和艾可柴郡猫套装
做任务领限定头像框和气泡框
艾可柴郡猫套装商城同步上架
新角色将于活动结束后于商城售卖
· 福利二 周年分享
全服共迎周年庆，每日点赞祝福来领周年庆限定气泡框
全服祝福值达到不同阶段会有不同奖励给每一个参与者
· 福利三 周年特别版幸运大转盘
兑换奖励大更新！梦境派对主题CP时装、猫鼠大战限定头套、全新官方周边礼品应有尽有~
· 福利四 周末福利来袭
活动时间：8月2日-8月25日每周五至周日全天
玩游戏角色成长值翻倍！结算宝箱半价点券开启，且有极高概率掉落限定猫鼠大战头套！
· 福利五 集字换涂鸦 
游戏中拾取【周年礼盒】，打开礼盒即可获得道具，集齐道具可兑换永久1周年蛋糕涂鸦
· 福利六 周年庆特惠礼包 
超低折扣入手限定头像框、猫鼠大战永久头套
· 福利七 蛋糕兑换
做任务得蛋糕，可兑换角色周年动作
· 福利八 充值返利
累计充值得限定狂欢礼花涂鸦、酒桶·烟花筒皮肤
2. 优化角色展示页面 
· 原【角色】功能入口拆分为【角色】和【个性】，方便玩家更快捷的进行个性搭配
· 新角色页面补充了更详细的角色信息、背景故事、时装展示
· 新个性页面增加了全套时装的一键更换功能，增加了3套时装搭配存储，可自由切换
· 现在组队时也能便捷的更换时装和表情啦！
3. 平衡性调整和Bug修复
· 冲锋枪——增加对墙上敌人的击退力度，减少攻击时的减速效果
· 毒液——增加伤害判定频率
· 尝试修复非正常途径携带道具卡及皮肤的Bug
· 尝试修复在逃生门未开时卡进逃生区域的Bug
4. 新增道具卡10级皮肤
· 冲锋枪——激光 
· 毒液——蜘蛛粘液
                            """
            }),
            ("190703", {
                "content": """
1. 全新道具卡
· 冲锋枪——超快射速，密集火力 · 毒液——范围减速，持续伤害
2. 全新道具卡活动
· 升级道具卡可领取永久涂鸦、限定个性框等超值奖励
· 新卡定向礼包、超值道具卡折扣礼包限时上架
3. 商城界面优化
· 新增热门商品推荐、每日超值礼盒
4. 家族系统优化
· 新增家族内捐卡排行和捐卡动态
5. 角色天赋平衡性调整
· 调整了部分角色的天赋效果及金币消耗
                            """
            })
        ])
        self.history = {
            "2024.09.13": "9月13日更新：金库攻防-克隆模式玩法开放；全新中秋活动上线，参与活动即可免费获得全新时装；龙龙商场返场好物；梦幻寄语活动更新战斗少女、发明家限定时装，附赠配套动作",
            "2024.08.01": "8月1日更新：6周年更新，海岛新玩法上新，金库挑战赛开启，2024夏季追风杯更新等",
            "2024.07.30": "将于8月1日更新：6周年更新，海岛新玩法上新，金库挑战赛开启，2024夏季追风杯更新等，当天具体几点待定",
            "2024.07.11": "7月11日更新：猪猪侠联动开启，猪猪侠套装、超级棒棒糖皮肤免费得",
            "2024.07.06": "将于7月11日更新：猪猪侠联动开启，猪猪侠套装、超级棒棒糖皮肤免费得，具体时间待定",
            "2024.04.22": "4月24日更新：「蜡笔小新」联动开启，小灰机皮肤免费送！",
            "2024.03.28": "3月28日更新：「金库攻防」全新升级，新角色利芙带聚合弓加入战场，猪猪类型调整",
            "2024.01.31": "1月31日更新：《熊出没》联动开启，光头强皮卡免费领",
            "2024.01.01": "将于1月31日更新：《熊出没》联动开启，光头强皮卡免费领，当天具体几点待定",
            "2023.12.21": "12月22日更新：双旦合集活动开启，冬日奇妙夜来临，幸运大转盘上线",
            "2023.12.15": "12月15日更新：周末签到、双周体验活动开启，版本预告、双旦预告活动上线",
            "2023.12.08": "12月8日更新：6元皮肤售卖-捣蛋、主题包抽奖更新、龙龙商店售卖更新",
            "2023.12.01": "12月1日更新：双周活跃体验活动更新",
            "2023.11.24": "11月24日更新：龙龙商店售卖开启，连星探秘1期更新",
            "2023.11.17": "11月17日更新：双周版本开启，【连星探秘】开启、风尚谷-紫装直售",
            "2023.11.10": "11月10日更新：【小学妹·雪道飞兔】皮肤直售、时空商城上新",
            "2023.11.01": "11月1日更新：S22全新赛季雪境极光开启、冰雪世界地图上线",
            "2023.10.31": "将于11月1日上午9点更新：S22全新赛季雪境极光开启、冰雪世界地图上线",
            "2023.10.27": "10月27日更新：万圣节合集活动更新",
            "2023.10.20": "10月20日更新：万圣节系列活动开启，参与对局任务可领取多重奖励和全新命石者",
            "2023.10.13": "10月13日更新：美食大亨的秋天系列活动开启",
            "2023.09.29": "9月29日更新：双节福利活动开启，七日签到、三重福利等内容上线",
            "2023.09.20": "9月20日更新：DMM美食季开启，灵膳子·团子超进化",
            "2023.09.16": "将于9月20日上午9点停服更新：DMM美食季开启，灵膳子·团子超进化",
            "2023.09.15": "9月15日更新：新橙装-发明家登场",
            "2023.09.08": "9月8日更新：【机器人的赠礼】活动开启",
            "2023.09.07": "将于9月8日更新：【机器人的赠礼】活动开启，具体时间待定",
            "2023.09.01": "9月1日更新：【校园进行时】活动开启",
            "2023.08.25": "8月25日更新：10钻月礼包、新季度礼包上线",
            "2023.08.18": "8月18日更新：【电玩盛典】开启，缤纷城时装上新",
            "2023.08.17": "将于8月18日更新：【电玩盛典】开启，缤纷城时装上新，具体时间待定",
            "2023.08.11": "8月11日更新：周年庆-8V2娱乐赛上线",
            "2023.08.02": "8月2日更新：5周年版本，4张新地图、新乱斗等",
            "2023.07.28": "7月28日更新：五周年电玩盛典开启；将于8月2日上午9点更新：5周年版本，4张新地图、新乱斗等",
            "2023.07.24": "将于8月2日上午9点更新：5周年版本，4张新地图、新乱斗等",
            "2023.07.21": "将于8月2日更新：5周年新版本上线，具体更新内容可持续关注快爆最新消息",
            "2023.07.21": "7月21日更新：新一期幻想造物来袭",
            "2023.07.14": "7月14日更新：女特工年度特惠开启！",
            "2023.07.05": "7月5日更新：一拳超人联动版本来袭，限时联动乱斗玩法上线",
            "2023.06.26": "将于7月5日更新：一拳超人联动版本上线，具体时间待定",
            "2023.06.22": "6月22日更新：端午活动来袭，玩家设计大赛开启；将于7月5日更新：一拳超人联动版本上线",
            "2023.06.22": "6月22日更新：端午活动来袭，玩家设计大赛开启",
            "2023.05.31": "5月31日更新：全新赛季开启，新追捕角色-淘气云·可露登场",
            "2023.05.28": "5月31日上午9点更新：全新赛季开启，新追捕角色-淘气云·可露登场",
            "2023.05.10": "5月10日更新：新皮肤酒桶-骑士团登场",
            "2023.04.26": "4月26日更新：新模式训练场来袭，新武器卡聚合弓登场",
            "2023.04.21": "4月21日更新：幻想造物（6期）开启；将于4月26日上午9点更新：新模式训练场来袭，新武器卡聚合弓登场",
            "2023.04.17": "将于4月26日上午9点更新：新模式训练场来袭，新武器卡聚合弓登场",
            "2023.04.07": "4月7日更新：角色折扣活动开启",
            "2023.03.22": "3月22日上午10点更新：全新角色夜翎·利芙登场，SS19赛季开启",
            "2023.03.10": "将于3月22日上午9点停服更新：全新角色夜翎·利芙登场，SS19赛季开启",
            "2023.03.10": "3月10日更新：小狐狸·玖儿【璀璨星途】星耀时装上线",
            "2023.02.22": "2月22日更新：新道具卡车轮滚滚登场",
            "2023.02.13": "将于2月22日更新：新道具卡车轮滚滚登场，具体时间待定",
            "2023.02.10": "2月10日更新：情人节活动开启",
            "2023.01.19": "1月19日更新：春节活动开启",
            "2023.01.11": "1月11日上午10点更新：寒假变形金刚联动版本，新角色-劲铠·阿治登场",
            "2023.01.11": "1月11日上午9点~9点30分更新，维护时间已延后，寒假变形金刚联动版本，新角色-劲铠·阿治将登场",
            "2023.01.05": "将于1月11日上午9点~11点更新寒假变形金刚联动版本，新角色-劲铠·阿治将登场",
            "2023.01.02": "将于1月11日上午上午9点~11点更新寒假大版本，新角色-劲铠·阿治将登场",
            "2022.12.16": "将于1月11日更新寒假大版本，具体更新内容以及时间待定",
            "2022.12.09": "12月9日更新：寻迹极光星粉活动开启！",
            "2022.11.23": "11月23日更新：影之忍者忍法升级、全新道具卡「互拉圈」上线",
            "2022.11.15": "将于11月23日上午9点更新：影之忍者忍法升级、全新道具卡「互拉圈」上线",
            "2022.11.04": "11月4日更新：「悠然假日」双十一活动上线",
            "2022.10.19": "10月19日更新：新赛季SS17开启，新角色「幽妍」上线",
            "2022.10.06": "将于10月19日上午9点更新：新赛季SS17开启，新角色「幽妍」上线，预计上午11点开服",
            "2022.09.30": "9月30日更新：奥特曼联动第二弹开启，光之历练上线等",
            "2022.09.09": "9月7日更新：全新武器道具卡·唤风镖、限时玩法龙币争夺战等。",
            "2022.08.03": "8月3日更新：4周年新版本，全新角色·机械之心奥博、全新道具卡·噗噗蛋、新地图和新玩法等",
            "2022.08.03": "8月3日更新：4周年新版本，全新角色·机械之心奥博、全新道具卡·噗噗蛋、新地图和新玩法等，预计11点开服",
            "2022.07.26": "将于8月3日上午9点更新：4周年新版本，全新角色·机械之心奥博、全新道具卡·噗噗蛋、新地图和新玩法等，预计11点开服",
            "2022.07.12": "将于8月3日更新：4周年新版本上线，具体更新内容可持续关注快爆最新消息",
            "2022.07.06": "7月6日更新：全新载具吼吼号上线，BOSS战升级归来，夏日活动开启等",
            "2022.05.25": "5月25日更新：SS15赛季，全新角色·灵膳子上线、机器人超进化等",
            "2022.05.25": "5月25日更新：SS15赛季，全新角色·灵膳子上线、机器人超进化等，预计11点开服",
            "2022.05.24": "将于5月25日上午9点~11点更新：全新角色·灵膳子上线、新角色登场活动开启、机器人超进化等",
            "2022.04.20": "4月20更新：发明家升级进化和新道具卡霰弹枪登场",
            "2022.04.18": "将于4月20早上9点~11点更新：发明家升级进化和新道具卡霰弹枪登场",
            "2022.03.16": "3月16日更新：S14西游记赛季，新角色小骇客-琪琪、新玩法争夺宝物",
            "2022.03.02": "S14西游记赛季将于3月16日上午9点更新：新角色小骇客-琪琪、新玩法争夺宝物",
            "2022.02.16": "2月16日更新：光能大作战玩法、小狐狸升级进化、步步高升开学新活动等",
            "2022.02.16": "原定于9点30分更新完毕，因官方原因延迟开服，具体开服时间待定",
            "2022.02.11": "将于2月16日上午9点更新：大作战玩法，新春全新时装、道具卡皮肤",
            "2022.01.19": "1月19日更新：开启与奥特曼联动，ss13奇迹之光赛季、联动大乱斗玩法、全新角色新逃生者命石者-衡等",
            "2022.01.11": "将于1月19日上午9点开启与奥特曼联动",
            "2022.01.07": "将于2022年1月19日上午11点更新寒假大版本",
            "2021.12.31": "将于2022年1月19日更新寒假大版本",
            "2021.12.01": "12月1日更新：全新追捕小狮子来袭、'金库攻防正式上线'",
            "2021.09.15": "9月15日更新：全新角色黎明盾卫登场",
            "2021.08.18": "8月18日更新：SS11赛季'玩具之城'登场",
            "2021.03.31": "3月31日更新：S9赛季甜蜜轰炸开启",
            "2021.03.10": "3月10日更新：新角色水之忍者泷登场！",
            "2021.01.27": "1月27日更新：SS8赛季仙侠幻想开启！",
            "2020.12.23": "12月23日更新：圣诞元旦缤纷活动开启！",
            "2020.11.25": "11月25日更新：新角色活[小梦魇·小眠]上线！",
            "2020.10.28": "10月28日更新：新·BOSS战模式重磅回归！",
            "2020.09.23": "9月23日更新：新武器卡上线，SS6赛季开启！",
            "2020.08.19": "8月19日更新： 新道具卡上线，'新卡活动'同步开启！",
            "2020.07.22": "7月22日更新： 两周年庆，新角色-小狐狸登场！",
            "2020.05.20": "5月20日更新：SS4赛季【纯白花嫁】盛大开启！",
            "2020.04.10": "4月10日更新：家族战系统开测！",
            "2020.03.18": "3月18日更新：S3赛季 【电音狂潮】盛大开场！",
            "2020.01.15": "1月15日更新：全新追捕者尼诺登场，新玩法【生存大乱斗】开启！",
            "2019.10.31": "10月31日更新，新地图梦幻水乐园上线",
            "2019.07.31": "7月31日更新，一周年全新版本重磅来袭",
            "2019.01.18": "1月18日更新，新玩法：全新BOSS战重磅开启",
            "2018.08.31": "8月31日更新，新角色：魔术师与机器人登场！",
            "2018.08.03": "已于8月3日上午10点正式上线",
            "2018.08.02": "预下载已开启，游戏将于8月3日上午10点正式上线",
            "2018.07.24": "将于8月3日上午10点正式上线(正式上线时间确定)",
            "2018.07.20": "将于8月3日正式上线(正式上线时间曝光)",
            "2018.07.16": "删档测试已于7月16日中午12点结束(删档测试结束)",
            "2018.07.06": "测试服已于7月6日上午10点开启，删档测试进行中(删档测试开启)",
            "2018.07.02": "将于7月6日上午10点开启删档测试(测试时间确定)",
            "2018.05.28": "预计于7月6日开启不删档测试"
        }

    def get_update_by_date(self, date):
        """根据日期获取更新公告"""
        update = self.updates.get(date)
        if update:
            return update['content']
        return "未找到该日期的更新公告"
    def get_all_update_ids(self):
        """获取所有更新公告的ID列表"""
        return list(self.updates.keys())
    def get_all_history_dates(self):
        """获取所有历史记录的日期列表"""
        return list(self.history.keys())