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
from collections import Counter

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

class JobFileHandler:
    """
    高效读写JSON文件的工具类，支持自动创建文件/目录、数据增删改查、层级信息提取
    （适配JSON中字符串类型的职位ID）
    """
    def __init__(
            self,
            project_root: Path,  # 显式传入最终数据目录的绝对路径（如 F:\...\Data）
            subdir_name: str,  # 子目录名（支持斜杠分隔，如 "City/Personal"）
            file_relative_path: str,  # 文件名（如 "jobs.json"）
            encoding: str = "utf-8"
    ):
        """
        初始化JSON文件处理器

        :param project_root: 最终数据目录的绝对路径（如 F:\Tool\...\Data）
        :param subdir_name: JSON文件所在的子目录名（相对于 project_root，支持斜杠分隔）
        :param file_relative_path: JSON文件名（相对于 project_root/subdir_name）
        :param encoding: 文件编码（默认utf-8）
        """
        self.project_root = project_root  # 最终数据目录（如 F:\...\Data）
        self.subdir_name = subdir_name    # 子目录（相对于 project_root）
        self.file_relative_path = file_relative_path  # 文件名（相对于 project_root/subdir_name）
        self.encoding = encoding
        self.file_path = self._get_file_path()  # 完整文件绝对路径
        self.data = self._load_data()         # 初始化时加载数据到内存

    def _get_file_path(self) -> Path:
        """构建JSON文件的绝对路径（核心逻辑：project_root + subdir_name + file_relative_path）"""
        # 拼接路径（Path自动处理不同系统的分隔符，如 Windows 反斜杠、Linux 正斜杠）
        return self.project_root / self.subdir_name / self.file_relative_path

    def _load_data(self) -> Dict[str, Any]:
        """加载JSON文件数据到内存（文件不存在时创建空文件和空数据）"""
        # 若文件不存在，创建父目录并初始化空数据
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding=self.encoding) as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return {}

        # 文件存在时加载数据
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"加载JSON文件失败: {self.file_path}, 错误: {e}")

    def save(self) -> None:
        """将内存中的数据保存回JSON文件（原子化保存，避免写入过程中损坏文件）"""
        lock = FileLock(f"{self.file_path}.lock")
        with lock:
            try:
                # 原子化保存：先写入临时文件，再替换原文件
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding=self.encoding,
                    dir=str(self.file_path.parent),
                    prefix=f".{self.file_path.name}.tmp.",
                    delete=False
                )
                with temp_file:
                    json.dump(self.data, temp_file, indent=4, ensure_ascii=False)

                # 替换原文件（操作系统保证原子性）
                os.replace(temp_file.name, str(self.file_path))
            except Exception as e:
                # 清理临时文件
                if 'temp_file' in locals() and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as cleanup_err:
                        print(f"警告：清理临时文件失败 {temp_file.name}: {cleanup_err}")
                raise RuntimeError(f"保存JSON文件失败: {self.file_path}, 错误: {e}")

    def update_data(self, key: str, value: Any) -> None:
        if "." not in key:
            raise ValueError("Key must contain at least one '.' separator")
        keys = key.split(".")
        current = self.data
        for i, k in enumerate(keys[:-1]):
            if k not in current:
                current[k] = {}
            if not isinstance(current[k], dict):  # 新增类型检查
                raise ValueError(f"中间键 '{k}' 的值必须为字典类型")
            current = current[k]
        current[keys[-1]] = value

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
    def __getitem__(self, key: str) -> Any:
        """支持通过[]直接访问数据（如handler["10"]）"""
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """支持通过[]直接修改数据（如handler["10"] = new_data）"""
        self.data[key] = value

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f"JobFileHandler(file_path={self.file_path}, encoding={self.encoding})"

class ShopFileHandler:
    """
    高效读写JSON文件的工具类、数据增删改查、层级信息提取
    """

    def __init__(
            self,
            project_root: Path,  # 显式传入最终数据目录的绝对路径（如 F:\...\Data）
            subdir_name: str,  # 子目录名（支持斜杠分隔，如 "City/Personal"）
            file_relative_path: str,  # 文件名（如 "jobs.json"）
            encoding: str = "utf-8"
    ):
        """
        初始化JSON文件处理器

        :param project_root: 最终数据目录的绝对路径（如 F:\Tool\...\Data）
        :param subdir_name: JSON文件所在的子目录名（相对于 project_root，支持斜杠分隔）
        :param file_relative_path: JSON文件名（相对于 project_root/subdir_name）
        :param encoding: 文件编码（默认utf-8）
        """
        self.project_root = project_root  # 最终数据目录（如 F:\...\Data）
        self.subdir_name = subdir_name    # 子目录（相对于 project_root）
        self.file_relative_path = file_relative_path  # 文件名（相对于 project_root/subdir_name）
        self.encoding = encoding
        self.file_path = self._get_file_path()  # 完整文件绝对路径
        self.data = self._load_data()         # 初始化时加载数据到内存

    def _get_file_path(self) -> Path:
        """构建JSON文件的绝对路径（核心逻辑：project_root + subdir_name + file_relative_path）"""
        # 拼接路径（Path自动处理不同系统的分隔符，如 Windows 反斜杠、Linux 正斜杠）
        return self.project_root / self.subdir_name / self.file_relative_path

    def _load_data(self) -> Dict[str, Any]:
        """加载JSON文件数据到内存（文件不存在时创建空文件和空数据）"""
        # 若文件不存在，创建父目录并初始化空数据
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding=self.encoding) as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return {}

        # 文件存在时加载数据
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"加载JSON文件失败: {self.file_path}, 错误: {e}")

    def save(self, encoding: Optional[str] = None) -> None:
        """
        将内存中的数据保存回JSON文件（原子化保存，避免写入过程中损坏文件）

        Args:
            encoding: 可选参数，指定保存文件的编码。若未传入，则使用类初始化时的 `self.encoding`（默认"utf-8"）
        """
        lock = FileLock(f"{self.file_path}.lock")
        with lock:
            # 确定最终使用的编码（优先使用方法参数，否则用类属性）
            save_encoding = encoding if encoding is not None else self.encoding

            try:
                # 原子化保存：先写入临时文件，再替换原文件
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding=save_encoding,  # 使用最终确定的编码
                    dir=str(self.file_path.parent),
                    prefix=f".{self.file_path.name}.tmp.",
                    delete=False
                )
                with temp_file:
                    json.dump(self.data, temp_file, indent=4, ensure_ascii=False)

                # 替换原文件（操作系统保证原子性）
                os.replace(temp_file.name, str(self.file_path))
            except Exception as e:
                # 清理临时文件
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
            validate: bool = True,  # 新增：是否启用数据验证
            expected_type: Optional[type] = None  # 新增：期望的值类型（可选）
    ) -> None:
        """
        安全更新内存中的数据（支持嵌套键），可选数据验证

        :param key: 要更新的键（支持嵌套键，如"quantity"或"20.00.jobName"）
        :param value: 要设置的新值
        :param validate: 是否启用数据验证（默认启用）
        :param expected_type: 期望的值类型（如int、str，可选）
        :raises ValueError: 数据验证失败时抛出
        """
        if not key:
            raise ValueError("键不能为空")

        keys = key.split(".")
        current = self.data

        # 遍历嵌套键，逐层创建或更新字典
        for i, k in enumerate(keys[:-1]):
            if not isinstance(k, str):
                raise ValueError(f"键包含非字符串部分：{k}")
            if k not in current:
                current[k] = {}  # 自动创建缺失的嵌套字典
            current = current[k]
            if not isinstance(current, dict):
                # 防止覆盖非字典类型的中间节点（如误将列表当字典更新）
                raise ValueError(f"键路径 '{'.'.join(keys[:i + 1])}' 指向非字典类型，无法继续更新")

        # 最终键的赋值
        last_key = keys[-1]
        if validate:
            # 数据验证逻辑（根据业务需求扩展）
            if expected_type is not None and not isinstance(value, expected_type):
                raise ValueError(f"键 '{last_key}' 的值类型应为 {expected_type.__name__}，当前为 {type(value).__name__}")

        current[last_key] = value

    def __getitem__(self, key: str) -> Any:
        """支持通过[]直接访问数据（如handler["10"]）"""
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """支持通过[]直接修改数据（如handler["10"] = new_data）"""
        self.data[key] = value

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f"JobFileHandler(file_path={self.file_path}, encoding={self.encoding})"

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

class FishFileHandler:
    """
    高效读写JSON文件的工具类、数据增删改查、层级信息提取
    """

    def __init__(
            self,
            project_root: Path,  # 显式传入最终数据目录的绝对路径（如 F:\...\Data）
            subdir_name: str,  # 子目录名（支持斜杠分隔，如 "City/Personal"）
            file_relative_path: str,  # 文件名（如 "jobs.json"）
            encoding: str = "utf-8"
    ):
        """
        初始化JSON文件处理器

        :param project_root: 最终数据目录的绝对路径（如 F:\Tool\...\Data）
        :param subdir_name: JSON文件所在的子目录名（相对于 project_root，支持斜杠分隔）
        :param file_relative_path: JSON文件名（相对于 project_root/subdir_name）
        :param encoding: 文件编码（默认utf-8）
        """
        self.project_root = project_root  # 最终数据目录（如 F:\...\Data）
        self.subdir_name = subdir_name    # 子目录（相对于 project_root）
        self.file_relative_path = file_relative_path  # 文件名（相对于 project_root/subdir_name）
        self.encoding = encoding
        self.file_path = self._get_file_path()  # 完整文件绝对路径
        self.data = self._load_data()         # 初始化时加载数据到内存

    def _get_file_path(self) -> Path:
        """构建JSON文件的绝对路径（核心逻辑：project_root + subdir_name + file_relative_path）"""
        # 拼接路径（Path自动处理不同系统的分隔符，如 Windows 反斜杠、Linux 正斜杠）
        return self.project_root / self.subdir_name / self.file_relative_path

    def _load_data(self) -> Dict[str, Any]:
        """加载JSON文件数据到内存（文件不存在时创建空文件和空数据）"""
        # 若文件不存在，创建父目录并初始化空数据
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding=self.encoding) as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return {}

        # 文件存在时加载数据
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"加载JSON文件失败: {self.file_path}, 错误: {e}")

    def save(self, encoding: Optional[str] = None) -> None:
        """
        将内存中的数据保存回JSON文件（原子化保存，避免写入过程中损坏文件）

        Args:
            encoding: 可选参数，指定保存文件的编码。若未传入，则使用类初始化时的 `self.encoding`（默认"utf-8"）
        """
        lock = FileLock(f"{self.file_path}.lock")
        with lock:
            # 确定最终使用的编码（优先使用方法参数，否则用类属性）
            save_encoding = encoding if encoding is not None else self.encoding

            try:
                # 原子化保存：先写入临时文件，再替换原文件
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding=save_encoding,  # 使用最终确定的编码
                    dir=str(self.file_path.parent),
                    prefix=f".{self.file_path.name}.tmp.",
                    delete=False
                )
                with temp_file:
                    json.dump(self.data, temp_file, indent=4, ensure_ascii=False)

                # 替换原文件（操作系统保证原子性）
                os.replace(temp_file.name, str(self.file_path))
            except Exception as e:
                # 清理临时文件
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
            validate: bool = True,  # 新增：是否启用数据验证
            expected_type: Optional[type] = None  # 新增：期望的值类型（可选）
    ) -> None:
        """
        安全更新内存中的数据（支持嵌套键），可选数据验证

        :param key: 要更新的键（支持嵌套键，如"quantity"或"20.00.jobName"）
        :param value: 要设置的新值
        :param validate: 是否启用数据验证（默认启用）
        :param expected_type: 期望的值类型（如int、str，可选）
        :raises ValueError: 数据验证失败时抛出
        """
        if not key:
            raise ValueError("键不能为空")

        keys = key.split(".")
        current = self.data

        # 遍历嵌套键，逐层创建或更新字典
        for i, k in enumerate(keys[:-1]):
            if not isinstance(k, str):
                raise ValueError(f"键包含非字符串部分：{k}")
            if k not in current:
                current[k] = {}  # 自动创建缺失的嵌套字典
            current = current[k]
            if not isinstance(current, dict):
                # 防止覆盖非字典类型的中间节点（如误将列表当字典更新）
                raise ValueError(f"键路径 '{'.'.join(keys[:i + 1])}' 指向非字典类型，无法继续更新")

        # 最终键的赋值
        last_key = keys[-1]
        if validate:
            # 数据验证逻辑（根据业务需求扩展）
            if expected_type is not None and not isinstance(value, expected_type):
                raise ValueError(f"键 '{last_key}' 的值类型应为 {expected_type.__name__}，当前为 {type(value).__name__}")

        current[last_key] = value

    def __getitem__(self, key: str) -> Any:
        """支持通过[]直接访问数据（如handler["10"]）"""
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """支持通过[]直接修改数据（如handler["10"] = new_data）"""
        self.data[key] = value

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f"JobFileHandler(file_path={self.file_path}, encoding={self.encoding})"

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