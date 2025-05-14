import os
import json # 导入json模块，方便后续进行json文件的读写
from typing import Dict, Any, Optional, List # 中文注释: 增加 List

# 中文注释：确保指定的目录路径存在，如果不存在则创建它。
def ensure_dir_exists(path: str):
    """
    Ensures that the directory at the given path exists. If not, it creates it.
    Args:
        path (str): The directory path.
    """
    os.makedirs(path, exist_ok=True)

# 中文注释：从JSON文件中加载内容。
def load_json_file(file_path: str) -> dict:
    """
    Loads content from a JSON file.
    Args:
        file_path (str): The path to the JSON file.
    Returns:
        dict: The content loaded from the JSON file.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 中文注释：将字典内容保存到JSON文件。
def save_json_file(data: dict, file_path: str):
    """
    Saves dictionary content to a JSON file.
    Args:
        data (dict): The dictionary to save.
        file_path (str): The path to the JSON file.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 中文注释：从文本文件中加载内容。
def load_text_file(file_path: str) -> str:
    """
    Loads content from a text file.
    Args:
        file_path (str): The path to the text file.
    Returns:
        str: The content loaded from the text file.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# 中文注释：将文本内容保存到文件。
def save_text_file(text: str, file_path: str):
    """
    Saves text content to a file.
    Args:
        text (str): The text to save.
        file_path (str): The path to the text file.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

# 中文注释: 将 _parse_task_design 方法添加到 utils.py 并重命名为 parse_task_design_from_string。
def parse_task_design_from_string(task_design_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    // 中文注释: 从任务设计字符串 (JSON格式) 中解析出文件列表和逻辑分析映射等。
    // task_design_str: 包含任务设计信息的JSON字符串。
    // 返回: 一个包含解析后信息的字典，例如 {"todo_file_list": [...], "logic_analysis_map": {...}}，如果解析失败则返回None。
    """
    if not task_design_str or not task_design_str.strip():
        print("// 中文注释: 警告 - 任务设计字符串为空，无法解析。")
        return None
    try:
        task_data = json.loads(task_design_str)
        result = {}
        
        # // 中文注释: 解析 "Task list" (兼容多种键名)
        key_variants_task_list = ['Task list', 'task_list', 'task list']
        found_task_list = None
        for key in key_variants_task_list:
            if key in task_data:
                found_task_list = task_data[key]
                break
        result["todo_file_list"] = found_task_list if isinstance(found_task_list, list) else []
        if not found_task_list:
                print(f"// 中文注释: 警告 - 未在任务设计数据中找到有效的 'Task list'。Keys found: {list(task_data.keys())}")

        # // 中文注释: 解析 "Logic Analysis" (兼容多种键名)
        key_variants_logic_analysis = ['Logic Analysis', 'logic_analysis', 'logic analysis']
        logic_analysis_raw = None
        for key in key_variants_logic_analysis:
            if key in task_data:
                logic_analysis_raw = task_data[key]
                break
        
        logic_map = {}
        if isinstance(logic_analysis_raw, list):
            for item in logic_analysis_raw:
                if isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], str):
                    logic_map[item[0]] = item[1]
                # // 中文注释: 也处理另一种可能的格式 ["filename", "description", "status", ...]
                elif isinstance(item, list) and len(item) > 1 and isinstance(item[0], str) and isinstance(item[1], str):
                    logic_map[item[0]] = item[1] # 取前两个作为文件名和描述
                else:
                    print(f"// 中文注释: 警告 - Logic Analysis中的项目格式不正确或不完整: {item}")
        result["logic_analysis_map"] = logic_map
        if not logic_analysis_raw and result["todo_file_list"]: # 如果有todo list但没有logic analysis，也发出警告
            print(f"// 中文注释: 警告 - 未在任务设计数据中找到有效的 'Logic Analysis'。Keys found: {list(task_data.keys())}")
            
        return result
    except json.JSONDecodeError as e:
        print(f"// 中文注释: 错误 - 解析任务设计字符串为JSON失败: {e}. 内容预览: {task_design_str[:200]}...")
        return None
    except Exception as e:
        print(f"// 中文注释: 解析任务设计时发生未知错误: {e}")
        return None

# 后续可以根据需要添加更多辅助函数
# 例如：读取PDF内容的函数、处理LaTeX文件的函数等。 