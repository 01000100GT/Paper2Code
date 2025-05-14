import json
import os
import copy # // 中文注释: 用于深拷贝 trajectories
import re   # // 中文注释: 用于从LLM响应中提取代码
# // 中文注释: 导入LLMClient用于与LLM交互。
from .llm_handler import LLMClient
# // 中文注释: 导入typing用于类型提示。
from typing import List, Dict, Any, Tuple, Optional
# // 中文注释: 导入辅助函数
from .utils import parse_task_design_from_string # 稍后会将 _parse_task_design 移到 utils.py 并重命名

# // 中文注释: 来自分析阶段和规划阶段的文件名常量。
# from .analyzing_agent import RESPONSE_JSON_SUFFIX as ANALYSIS_RESPONSE_JSON_SUFFIX # 现在直接从路径构造
# from .planning_agent import PLANNING_TRAJECTORIES_FILENAME_SUFFIX, PLANNING_CONFIG_FILENAME # Pipeline直接提供路径

ANALYSIS_RESPONSE_JSON_SUFFIX = "_simple_analysis_response.json" # 定义常量以供内部使用

CODING_ARTIFACTS_PREFIX = "coding_artifacts"
CODING_FILENAME_SUFFIX = "_coding.txt" # For raw LLM output during coding

class CodingAgent:
    """
    // 中文注释: CodingAgent 类负责根据规划和分析阶段的输出来生成实际的代码文件。
    """
    # 中文注释：修改构造函数以接收明确的路径和输出目录
    def __init__(self, 
                 llm_client: LLMClient, 
                 paper_name: str, 
                 config_yaml_path: str, 
                 planning_trajectories_path: str, 
                 paper_json_path: str, # 清理后的论文JSON路径
                 latex_zip_path: Optional[str], # LaTeX压缩包路径（内容由Pipeline传入run）
                 # planning_artifacts_dir: str, # 规划产物目录 (md文件等，如果需要直接加载)
                 analysis_json_logs_dir: str, # 分析阶段保存 _simple_analysis_response.json 的目录
                 output_repo_dir: str, # 最终代码仓库目录
                 coding_artifacts_dir: str # 本阶段编码产物 (_coding.txt) 的保存目录
                 ):
        """
        // 中文注释: 初始化 CodingAgent。
        // llm_client: LLMClient的实例。
        // paper_name: 当前处理的论文名称。
        // config_yaml_path: _config.yaml文件的路径。
        // planning_trajectories_path: 规划阶段轨迹文件的路径。
        // paper_json_path: 清理后的论文JSON文件路径。
        // latex_zip_path: (可选) LaTeX源文件压缩包路径。
        // analysis_json_logs_dir: 分析阶段保存 _simple_analysis_response.json 文件的目录。
        // output_repo_dir: 生成的最终代码仓库的输出目录。
        // coding_artifacts_dir: 保存本阶段原始LLM输出 (_coding.txt) 的目录。
        """
        self.llm_client = llm_client
        self.paper_name = paper_name
        self.config_yaml_path = config_yaml_path
        self.planning_trajectories_path = planning_trajectories_path
        self.paper_json_path = paper_json_path
        self.latex_zip_path = latex_zip_path # 内容由Pipeline处理并传入run
        
        # self.planning_artifacts_dir = planning_artifacts_dir # 如果需要加载 .md 文件等，则取消注释
        self.analysis_json_logs_dir = analysis_json_logs_dir
        self.output_repo_dir = output_repo_dir
        self.coding_artifacts_dir = coding_artifacts_dir
        
        os.makedirs(self.coding_artifacts_dir, exist_ok=True)
        os.makedirs(self.output_repo_dir, exist_ok=True)
        
        self.done_file_code_map: Dict[str, str] = {}
        self.detailed_logic_analyses_map: Dict[str, str] = {}

    # 中文注释：重构 _load_coding_inputs 以使用传入的路径和规划内容
    def _prepare_inputs_for_coding(self, 
                                   planning_overview_content: str, 
                                   architecture_design_content: str, 
                                   logic_design_content: str
                                   ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], List[str]]:
        """
        // 中文注释: 加载编码阶段所需的所有输入。
        // planning_overview_content: 规划总览的文本内容。
        // architecture_design_content: 架构设计的文本内容 (JSON字符串)。
        // logic_design_content: 逻辑与任务设计的文本内容 (JSON字符串, 包含task_list)。
        // 返回: (config_yaml_content, plan_overview, arch_design, task_design_str, todo_files)
        """
        config_yaml_content: Optional[str] = None
        todo_files: List[str] = []

        try:
            with open(self.config_yaml_path, 'r', encoding='utf-8') as f:
                config_yaml_content = f.read()
        except FileNotFoundError:
            print(f"// 中文注释: 错误 - 编码阶段：规划配置文件 {self.config_yaml_path} 未找到。")
            return None, None, None, None, []
        except Exception as e:
            print(f"// 中文注释: 错误 - 编码阶段：加载规划配置文件失败: {e}")
            return None, None, None, None, []

        # // 中文注释: 直接使用传入的规划内容
        plan_overview = planning_overview_content
        arch_design = architecture_design_content
        task_design_str = logic_design_content # logic_design_content 是原始的 task_design_str

        # // 中文注释: 从 task_design_str (即 logic_design_content) 中解析出 todo_file_list
        parsed_task_info = parse_task_design_from_string(task_design_str) # 使用导入的函数
        if parsed_task_info and "todo_file_list" in parsed_task_info:
            todo_files = parsed_task_info["todo_file_list"]
        else:
            print(f"// 中文注释: 警告 - 编码阶段：未能从任务设计中解析出待办文件列表。内容: {task_design_str[:200]}")

        self.detailed_logic_analyses_map.clear()
        for file_name in todo_files:
            if file_name.lower() == "_config.yaml" or file_name.lower() == "config.yaml": continue
            
            analysis_file_key = file_name.replace("/", "_") 
            # 中文注释：从 self.analysis_json_logs_dir 加载分析响应日志
            analysis_response_path = os.path.join(self.analysis_json_logs_dir, f"{analysis_file_key}{ANALYSIS_RESPONSE_JSON_SUFFIX}")
            try:
                with open(analysis_response_path, 'r', encoding='utf-8') as f:
                    analysis_response_data_list = json.load(f)
                if analysis_response_data_list and isinstance(analysis_response_data_list, list) and analysis_response_data_list[0]:
                    # 假设第一个响应的第一个choice的消息内容是分析文本
                    analysis_message = analysis_response_data_list[0].get('choices', [{}])[0].get('message', {})
                    self.detailed_logic_analyses_map[file_name] = analysis_message.get('content', "")
                else:
                    self.detailed_logic_analyses_map[file_name] = ""
                    print(f"// 中文注释: 警告 - 编码阶段：分析响应JSON {analysis_response_path} 结构不符或为空。")
            except FileNotFoundError:
                print(f"// 中文注释: 警告 - 编码阶段：文件 {file_name} 的分析响应JSON {analysis_response_path} 未找到。将使用空分析。")
                self.detailed_logic_analyses_map[file_name] = ""
            except Exception as e:
                print(f"// 中文注释: 错误 - 编码阶段：加载文件 {file_name} 的分析响应时出错: {e}")
                self.detailed_logic_analyses_map[file_name] = ""
        
        return config_yaml_content, plan_overview, arch_design, task_design_str, todo_files

    # 中文注释：更新 _prepare_coding_prompt_messages 以接受 latex_content_full
    def _prepare_coding_prompt_messages(self, current_file_name: str, 
                                        paper_content_full: str, paper_format_str: str, 
                                        plan_overview: str, arch_design: str, task_design_str: str, 
                                        config_yaml_content: str,
                                        latex_content_full: Optional[str] = None) -> List[Dict[str, str]]:
        """
        // 中文注释: 准备用于为单个文件生成代码的LLM提示消息。
        """
        system_message = f"""You are an expert researcher and software engineer with a deep understanding of experimental design and reproducibility in scientific research.
You will receive a research paper in {paper_format_str} format. {"Also provided is the LaTeX source if available." if latex_content_full else ""}
An overview of the plan, a Design in JSON format consisting of \"Implementation approach\", \"File list\", \"Data structures and interfaces\", and \"Program call flow\".
Followed by a Task in JSON format that includes \"Required packages\", \"Required other language third-party packages\", \"Logic Analysis\", and \"Task list\".
Along with a configuration file named \"_config.yaml\". 
Your task is to write code to reproduce the experiments and methodologies described in the paper. 

The code you write must be elegant, modular, and maintainable, adhering to Google-style guidelines. 
The code must strictly align with the paper's methodology, experimental setup, and evaluation metrics. 
Write code with triple quoto."""

        coded_files_context_str = ""
        if self.done_file_code_map:
            for done_file_name, done_file_code in self.done_file_code_map.items():
                if done_file_name.lower().endswith((".yaml", ".yml")): continue
                coded_files_context_str += f"""## Code: {done_file_name}
```python
{done_file_code}
```

"""
        if not coded_files_context_str.strip():
            coded_files_context_str = "No other code files have been generated yet."

        detailed_logic_analysis_for_file = self.detailed_logic_analyses_map.get(current_file_name, "No detailed logic analysis provided for this file.")
        
        done_files_list_str_display = list(self.done_file_code_map.keys())
        if not done_files_list_str_display: 
            done_files_list_str_display.append("_config.yaml") 
        else: 
            if "_config.yaml" not in done_files_list_str_display:
                 done_files_list_str_display.insert(0, "_config.yaml")

        user_message_content = f"""# Context
## Paper ({paper_format_str} format)
{paper_content_full}
{f'''
## LaTeX Source
{latex_content_full}
''' if latex_content_full else ''}

-----

## Overview of the plan
{plan_overview}

-----

## Design (JSON format)
{arch_design}

-----

## Task (JSON format)
{task_design_str}

-----

## Configuration file (_config.yaml)
```yaml
{config_yaml_content}
```
-----

## Code Files Generated So Far
{coded_files_context_str}
-----

# Format example
## Code: {current_file_name}
```python
## {current_file_name}
# Your Python code for {current_file_name} here
```

-----

# Instruction
Based on the paper, plan, design, task, and configuration file (_config.yaml) specified previously, and considering the code files already generated (if any), please follow the \"Format example\" to write the Python code for the target file.

We have already processed or generated the following files: {str(done_files_list_str_display)}.
Your current task is to write **ONLY** the code for the file: \"{current_file_name}\".

Key guidelines for generating the code for \"{current_file_name}\":
1.  **Single File Focus**: Implement **ONLY THIS ONE FILE** (`{current_file_name}`). Do not generate code for other files.
2.  **Complete and Reliable Code**: Ensure the code is complete, reliable, and reusable as part of the larger project.
3.  **Default Values and Typing**: If there are any settings or parameters, ALWAYS provide a sensible default value. Use strong typing and explicit variable declarations. Actively AVOID circular imports.
4.  **Adhere to Design**: You MUST strictly follow the \"Data structures and interfaces\" provided in the ## Design section. DO NOT change any part of the given design. Do not use public member functions that are not part of the specified design.
5.  **Completeness Check**: Carefully verify that you have not missed any necessary classes, functions, or methods that should be in THIS FILE according to the plan and design.
6.  **Imports**: Before using any external variable, module, or a class/function from another file in this project, ensure you import it correctly at the beginning of the file.
7.  **No TODOs**: Write out EVERY code detail. DO NOT leave any TODO comments or placeholders.
8.  **Use Configuration**: You MUST use configuration values from the `_config.yaml` provided in the ## Configuration file section. DO NOT fabricate or hardcode any configuration values that are expected to come from this file.

Here is the detailed logic analysis for \"{current_file_name}\" to guide your implementation:
{detailed_logic_analysis_for_file}

## Code: {current_file_name}
"""
        
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message_content}
        ]

    def _extract_code_from_llm_response(self, llm_response_content: str, target_filename: str) -> str:
        """
        // 中文注释: 从LLM的响应中提取纯代码块。
        """
        pattern_with_filename = rf"^## Code: {re.escape(target_filename)}\s*```(?:python)?\s*(.*?)\s*```"
        match = re.search(pattern_with_filename, llm_response_content, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        pattern_generic = r"```(?:python)?\s*(.*?)\s*```"
        match_generic = re.search(pattern_generic, llm_response_content, re.DOTALL)
        if match_generic:
            return match_generic.group(1).strip()
        
        if not ("```" in llm_response_content and "## Code:" in llm_response_content):
             print(f"// 中文注释: 警告 - 未能在LLM响应中为文件 {target_filename} 找到标准代码块标记。将尝试使用原始响应内容。响应预览: {llm_response_content[:200]}...")
             return llm_response_content.strip()
        
        print(f"// 中文注释: 警告 - 未能为文件 {target_filename} 提取代码，即使检测到标记。返回空字符串。响应预览: {llm_response_content[:200]}...")
        return ""

    # 中文注释：修改 generate_code_for_single_file 以接受 latex_content_full
    def generate_code_for_single_file(self, current_file_name: str, 
                                        paper_content_full: str, paper_format_str: str, 
                                        plan_overview: str, arch_design: str, task_design_str: str, 
                                        config_yaml_content: str, gpt_version_str: str,
                                        latex_content_full: Optional[str] = None) -> Optional[str]:
        """
        // 中文注释: 为单个文件生成代码，调用LLM，提取代码并保存。
        // 返回生成的代码字符串，如果失败则返回None。
        """
        print(f"// 中文注释: [编码阶段] 开始为文件生成代码: {current_file_name}")
        
        messages = self._prepare_coding_prompt_messages(
            current_file_name, paper_content_full, paper_format_str,
            plan_overview, arch_design, task_design_str, config_yaml_content,
            latex_content_full
        )

        try:
            additional_params = {}
            if "o3-mini" in gpt_version_str:
                additional_params["reasoning_effort"] = "high"
            completion = self.llm_client.call_llm(
                messages=messages, 
                model_version=gpt_version_str,
                **additional_params
            )
            llm_raw_output = completion.choices[0].message.content
        except Exception as e:
            print(f"// 中文注释: LLM调用在为文件 {current_file_name} 生成代码时失败: {e}")
            self.done_file_code_map[current_file_name] = "" # Mark as attempted but failed
            return None # Indicate failure

        safe_artifact_filename = current_file_name.replace("/", "_")
        artifact_file_path = os.path.join(self.coding_artifacts_dir, f"{safe_artifact_filename}{CODING_FILENAME_SUFFIX}")
        try:
            with open(artifact_file_path, 'w', encoding='utf-8') as f:
                f.write(llm_raw_output)
            print(f"// 中文注释: [编码产物原始输出已保存] {artifact_file_path}")
        except IOError as e:
            print(f"// 中文注释: 错误 - 无法写入编码产物文件 {artifact_file_path}: {e}")

        generated_code = self._extract_code_from_llm_response(llm_raw_output, current_file_name)
        if not generated_code.strip():
            print(f"// 中文注释: 警告 - 为文件 {current_file_name} 提取的代码为空。将跳过保存到代码仓库。")
            self.done_file_code_map[current_file_name] = "" 
            return "" 

        target_code_path = os.path.join(self.output_repo_dir, current_file_name)
        target_dir = os.path.dirname(target_code_path)
        if target_dir and not os.path.exists(target_dir): # Ensure directory exists if filename includes path
            os.makedirs(target_dir, exist_ok=True)
        
        try:
            with open(target_code_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            print(f"// 中文注释: [代码已生成并保存] {target_code_path}")
        except IOError as e:
            print(f"// 中文注释: 错误 - 无法写入生成的代码文件 {target_code_path}: {e}")
            # Even if save fails, code is generated; consider how to handle this error for overall success

        self.done_file_code_map[current_file_name] = generated_code
        
        print(f"// 中文注释: [编码阶段] 完成文件代码生成: {current_file_name}")
        return generated_code

    # 中文注释：修改 execute_coding_stage 以接受 paper_content_full 和 latex_content_full 及规划内容
    def execute_coding_stage(self, 
                             paper_content_full: str, 
                             paper_format_str: str, 
                             gpt_version_str: str, 
                             planning_overview_content: str,
                             architecture_design_content: str,
                             logic_design_content: str,
                             latex_content_full: Optional[str] = None
                             ) -> Dict[str, str]:
        """
        // 中文注释: 执行完整的编码阶段，遍历所有待编码文件。
        // 返回一个字典，键是文件名，值是生成的代码字符串。
        """
        loaded_data = self._prepare_inputs_for_coding(
            planning_overview_content=planning_overview_content,
            architecture_design_content=architecture_design_content,
            logic_design_content=logic_design_content
        )
        config_yaml_content, plan_overview, arch_design, task_design_str, todo_files = loaded_data

        if config_yaml_content is None or plan_overview is None or task_design_str is None: # task_design_str is needed for prompt
            print("// 中文注释: 错误 - 编码阶段因缺少必要的规划产物而无法继续。")
            self.done_file_code_map.clear()
            return self.done_file_code_map
        
        self.done_file_code_map.clear()

        for file_name_to_code in todo_files:
            if file_name_to_code.lower() == "_config.yaml" or file_name_to_code.lower() == "config.yaml":
                print(f"// 中文注释: [编码阶段] 跳过配置文件生成: {file_name_to_code}")
                continue
            
            self.generate_code_for_single_file(
                current_file_name=file_name_to_code,
                paper_content_full=paper_content_full,
                paper_format_str=paper_format_str,
                plan_overview=plan_overview,
                arch_design=arch_design,
                task_design_str=task_design_str,
                config_yaml_content=config_yaml_content,
                gpt_version_str=gpt_version_str,
                latex_content_full=latex_content_full
            )

        print("// 中文注释: 编码阶段完成。所有指定文件已尝试生成代码。")
        return self.done_file_code_map

    # 中文注释：添加 run 方法作为 Pipeline 的主调用入口
    def run(self, 
            paper_content_full: str, 
            paper_format: str, 
            planning_overview_content: str,
            architecture_design_content: str,
            logic_design_content: str,
            latex_content_full: Optional[str] = None
            ) -> Dict[str, str]:
        """
        // 中文注释: 执行编码流程的主入口点。
        // paper_content_full: 论文的完整内容 (例如，JSON字符串)。
        // paper_format: 论文内容的格式 (例如，"JSON")。
        // planning_overview_content: 规划总览的文本内容。
        // architecture_design_content: 架构设计的文本内容。
        // logic_design_content: 逻辑与任务设计的文本内容。
        // latex_content_full: (可选) LaTeX的完整内容字符串。
        // 返回: 一个字典，包含已生成代码的文件名和其内容。
        """
        print(f"// 中文注释: [CodingAgent] 开始执行编码，论文: {self.paper_name}")
        
        gpt_version = self.llm_client.model_name

        results = self.execute_coding_stage(
            paper_content_full=paper_content_full,
            paper_format_str=paper_format,
            gpt_version_str=gpt_version,
            planning_overview_content=planning_overview_content,
            architecture_design_content=architecture_design_content,
            logic_design_content=logic_design_content,
            latex_content_full=latex_content_full
        )
        
        print(f"// 中文注释: [CodingAgent] 编码完成。代码仓库位于: {self.output_repo_dir}")
        return results

# // 中文注释: 示例用法。
if __name__ == '__main__':
    # ... (示例代码保持不变，但需要更新以匹配新的 __init__ 和 run 签名)
    pass

    # // 中文注释: 此示例需要正确设置 OPENAI_API_KEY 环境变量，
    # // 并且在指定的 output_dir_base_paper 中已存在规划和分析阶段的输出。
    # try:
    #     llm_client = LLMClient() 
        
    #     paper_name_example = "Transformer_Code_Test"
    #     base_output_dir = f"../outputs/{paper_name_example}"
    #     final_repo_dir = f"../outputs/{paper_name_example}_repo"
        
    #     # // 确保基础输出目录和其中的必要输入文件存在
    #     os.makedirs(base_output_dir, exist_ok=True)
    #     os.makedirs(final_repo_dir, exist_ok=True)
    #     os.makedirs(os.path.join(base_output_dir, CODING_ARTIFACTS_PREFIX), exist_ok=True)
        
    #     # // [模拟] 创建一些编码阶段所需的输入文件 (通常由规划和分析阶段生成)
    #     # 1. config.yaml
    #     mock_config_content = "model:\n  name: TestModel\nlearning_rate: 0.001\n" 
    #     with open(os.path.join(base_output_dir, PLANNING_CONFIG_FILENAME), 'w') as f:
    #         f.write(mock_config_content)
        
    #     # 2. planning_trajectories.json (简化版，包含可解析的plan, arch, task)
    #     mock_plan = "This is the overall plan."
    #     mock_arch = "{\"File list\": [\"main.py\", \"utils.py\"]}" # 简化，实际更复杂
    #     mock_task = "{\"Task list\": [\"main.py\", \"utils.py\"], \"Logic Analysis\": [[\"main.py\", \"Entry point\"], [\"utils.py\", \"Helper functions\"]]}"
    #     mock_planning_traj = [
    #         {}, {}, {"role": "assistant", "content": f"[CONTENT]{mock_plan}[/CONTENT]"},
    #         {}, {"role": "assistant", "content": f"[CONTENT]{mock_arch}[/CONTENT]"},
    #         {}, {"role": "assistant", "content": f"[CONTENT]{mock_task}[/CONTENT]"}
    #     ]
    #     with open(os.path.join(base_output_dir, f"{paper_name_example}{PLANNING_TRAJECTORIES_FILENAME_SUFFIX}"), 'w') as f:
    #         json.dump(mock_planning_traj, f)

    #     # 3. _simple_analysis_response.json for each file in task list
    #     #    (main.py, utils.py from mock_task)
    #     mock_main_analysis = "Detailed analysis for main.py: create main function, parse args."
    #     mock_utils_analysis = "Detailed analysis for utils.py: implement helper_function."
    #     main_analysis_resp = [{
    #         "choices": [{"message": {"content": mock_main_analysis, "role": "assistant"}}]
    #     }]
    #     utils_analysis_resp = [{
    #         "choices": [{"message": {"content": mock_utils_analysis, "role": "assistant"}}]
    #     }]
    #     with open(os.path.join(base_output_dir, f"main.py{ANALYSIS_RESPONSE_JSON_SUFFIX}"), 'w') as f:
    #         json.dump(main_analysis_resp, f)
    #     with open(os.path.join(base_output_dir, f"utils.py{ANALYSIS_RESPONSE_JSON_SUFFIX}"), 'w') as f:
    #         json.dump(utils_analysis_resp, f)
        
    #     # // 初始化 CodingAgent
    #     coder = CodingAgent(llm_client=llm_client, 
    #                         output_dir_base_paper=base_output_dir, 
    #                         output_repo_dir=final_repo_dir, 
    #                         paper_name=paper_name_example)
        
    #     # // 模拟论文内容
    #     example_paper_content = "{\"title\": \"Attention Is All You Need - Coding Test\"}" 
    #     example_paper_format = "JSON"
    #     example_gpt_version = "gpt-3.5-turbo"

    #     print(f"\n// 中文注释: 开始为论文 '{paper_name_example}' 执行编码阶段...")
    #     generated_code_map = coder.execute_coding_stage(
    #         paper_content_full=example_paper_content,
    #         paper_format_str=example_paper_format,
    #         gpt_version_str=example_gpt_version
    #     )

    #     print("\n// 中文注释: 编码阶段完成。生成的代码文件:")
    #     if generated_code_map:
    #         for file_name, code_content in generated_code_map.items():
    #             print(f"--- {file_name} ---")
    #             if code_content:
    #                 print(code_content[:200].strip() + "...")
    #             else:
    #                 print("(代码为空或生成失败)")
    #             print("------\n")
    #     else:
    #         print("// 中文注释: 未生成任何代码或编码阶段提前终止。")
        
    #     print(f"// 中文注释: 最终生成的代码仓库位于: {coder.output_repo_dir}")
    #     print(f"// 中文注释: 编码过程中的原始LLM输出保存在: {coder.artifacts_dir}")

    # except ValueError as ve: 
    #     print(f"// 中文注释: 初始化或配置错误: {ve}")
    # except Exception as e:
    #     print(f"// 中文注释: 执行编码阶段示例时发生错误: {e}")
    #     import traceback
    #     traceback.print_exc()
    pass 