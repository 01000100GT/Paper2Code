import json
import os # // 中文注释: 确保导入os模块

class JSONCleaner:
    """
    // 中文注释: 此类用于清理从PDF转换的JSON文件中不必要的字段。
    """
    def __init__(self, input_json_path: str, output_json_path: str):
        # // 中文注释: 定义需要从JSON中移除的键列表。
        self.keys_to_remove = [
            "cite_spans", "ref_spans", "eq_spans", "authors", "bib_entries",
            "year", "venue", "identifiers", "_pdf_hash", "header"
        ]
        # 中文注释：存储输入和输出文件路径
        self.input_json_path = input_json_path
        self.output_json_path = output_json_path

    def _remove_spans_recursive(self, data):
        """
        // 中文注释: 递归地移除数据中的指定键。
        // data: 要处理的字典或列表。
        // 返回: 清理后的数据。
        """
        if isinstance(data, dict):
            for key in self.keys_to_remove:
                data.pop(key, None)
            for key, value in data.items():
                data[key] = self._remove_spans_recursive(value)
        elif isinstance(data, list):
            return [self._remove_spans_recursive(item) for item in data]
        return data

    def clean_json_file(self, input_json_path: str, output_json_path: str):
        """
        // 中文注释: 加载、清理并保存JSON文件。
        // input_json_path: 输入JSON文件的路径。
        // output_json_path: 清理后JSON文件的保存路径。
        """
        # // 中文注释: 添加详细路径检查日志
        print(f"// 中文注释: [JSONCleaner.clean_json_file] 尝试打开输入文件: '{input_json_path}'")
        absolute_input_path = os.path.abspath(input_json_path)
        print(f"// 中文注释: [JSONCleaner.clean_json_file] 绝对路径: '{absolute_input_path}'")
        print(f"// 中文注释: [JSONCleaner.clean_json_file] 文件是否存在 (os.path.exists): {os.path.exists(absolute_input_path)}")
        print(f"// 中文注释: [JSONCleaner.clean_json_file] 是否为文件 (os.path.isfile): {os.path.isfile(absolute_input_path)}")

        try:
            with open(input_json_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"// 中文注释: 错误：输入文件 {input_json_path} 未找到。")
            return
        except json.JSONDecodeError:
            print(f"// 中文注释: 错误：无法解码 {input_json_path} 中的JSON。")
            return

        cleaned_data = self._remove_spans_recursive(data)

        try:
            with open(output_json_path, 'w') as f:
                json.dump(cleaned_data, f, indent=4) # // 中文注释: 添加indent使输出更易读
            print(f"// 中文注释: [已保存] 清理后的JSON文件到 {output_json_path}")
        except IOError:
            print(f"// 中文注释: 错误：无法写入到输出文件 {output_json_path}。")

    # 中文注释：添加 clean_json 方法，该方法调用 clean_json_file 并使用存储的路径
    def clean_json(self):
        """
        // 中文注释: 使用存储在实例中的路径清理JSON文件。
        """
        print(f"// 中文注释: [JSONCleaner] 开始清理文件 {self.input_json_path} -> {self.output_json_path}")
        self.clean_json_file(self.input_json_path, self.output_json_path)

if __name__ == '__main__':
    # // 中文注释: 这是一个示例用法，实际调用会由主流程控制。
    # // import argparse
    # // parser = argparse.ArgumentParser(description="Clean a JSON file by removing specified spans.")
    # // parser.add_argument("--input_json_path", type=str, required=True, help="Path to the input JSON file.")
    # // parser.add_argument("--output_json_path", type=str, required=True, help="Path to save the cleaned JSON file.")
    # // args = parser.parse_args()
    
    # // 中文注释: 示例：实例化并调用新的 clean_json 方法
    # // cleaner = JSONCleaner(input_json_path=args.input_json_path, output_json_path=args.output_json_path)
    # // cleaner.clean_json()
    
    # // 中文注释: 示例：或者直接调用 clean_json_file 方法
    # // direct_cleaner = JSONCleaner(input_json_path="dummy_input.json", output_json_path="dummy_output.json") # __init__仍然需要路径参数
    # // direct_cleaner.clean_json_file(args.input_json_path, args.output_json_path)
    pass 