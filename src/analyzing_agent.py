import json
import os
import copy # // 中文注释: 用于深拷贝 trajectories
# // 中文注释: 导入LLMClient用于与LLM交互。
from .llm_handler import LLMClient 
# // 中文注释: 导入typing用于类型提示。
from typing import List, Dict, Any, Tuple, Optional
import re # // 中文注释: 导入re模块，可能在辅助函数中使用
# // 中文注释: 导入辅助函数
from .utils import parse_task_design_from_string # 稍后会将 _parse_task_design 移到 utils.py 并重命名

# // 中文注释: 规划相关的常量，可能需要从 planning_agent 或共享的 constants 文件导入。
# from .planning_agent import PLANNING_ARTIFACTS_PREFIX # Assuming this constant is defined elsewhere
# PLANNING_TRAJECTORIES_FILENAME_SUFFIX = "_planning_trajectories.json" # 由Pipeline直接提供路径
# PLANNING_CONFIG_FILENAME = "_config.yaml" # 由Pipeline直接提供路径

ANALYZING_ARTIFACTS_PREFIX = "analyzing_artifacts" # 此Agent自身输出子目录名
ANALYSIS_FILENAME_SUFFIX = "_simple_analysis.txt"
RESPONSE_JSON_SUFFIX = "_simple_analysis_response.json"
TRAJECTORIES_JSON_SUFFIX = "_simple_analysis_trajectories.json"

class AnalyzingAgent:
    """
    // 中文注释: AnalyzingAgent 类负责对规划阶段输出的每个文件进行详细的逻辑分析。
    """
    # 中文注释：修改构造函数以接收明确的路径和输出目录
    def __init__(self, 
                 llm_client: LLMClient, 
                 paper_name: str, 
                 config_yaml_path: str, 
                 planning_trajectories_path: str, 
                 paper_json_path: str, # 清理后的论文JSON路径
                 latex_zip_path: Optional[str], # LaTeX压缩包路径，内容处理由Pipeline完成并传入run方法
                 analyzing_artifacts_output_dir: str, # 分析产物 (_simple_analysis.txt) 的输出目录
                 paper_base_output_dir: str # 用于保存分析日志 (_response.json, _trajectories.json) 的论文级基础输出目录
                 ):
        """
        // 中文注释: 初始化 AnalyzingAgent。
        // llm_client: LLMClient的实例。
        // paper_name: 当前处理的论文名称。
        // config_yaml_path: planning_config.yaml文件的路径。
        // planning_trajectories_path: 规划阶段轨迹文件的路径。
        // paper_json_path: 清理后的论文JSON文件路径。
        // latex_zip_path: (可选) LaTeX源文件压缩包路径。
        // analyzing_artifacts_output_dir: 保存本阶段主要产物 (_simple_analysis.txt) 的目录。
        // paper_base_output_dir: 保存本阶段日志文件 (_response.json, _trajectories.json) 的目录。
        """
        self.llm_client = llm_client
        self.paper_name = paper_name
        self.config_yaml_path = config_yaml_path
        self.planning_trajectories_path = planning_trajectories_path
        self.paper_json_path = paper_json_path 
        self.latex_zip_path = latex_zip_path # 主要用于信息传递，内容由Pipeline的run方法处理并传入
        
        # 中文注释：用于保存 _simple_analysis.txt 文件
        self.analyzing_artifacts_output_dir = analyzing_artifacts_output_dir
        os.makedirs(self.analyzing_artifacts_output_dir, exist_ok=True)
        
        # 中文注释：用于保存 _simple_analysis_response.json 和 _simple_analysis_trajectories.json
        self.paper_base_output_dir = paper_base_output_dir 
        # 这个目录应该由Pipeline创建，这里不再重复创建，假设它已存在

    # 中文注释：重构 _load_planning_outputs 为 _prepare_inputs_from_planning，使用传入的路径
    def _prepare_inputs_from_planning(self, 
                                      planning_overview_content: str, 
                                      architecture_design_content: str, 
                                      logic_design_content: str
                                      ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], List[str], Dict[str, str]]:
        """
        // 中文注释: 使用在构造函数中提供的路径加载配置文件，并使用直接传入的规划内容。
        // planning_overview_content: 规划总览的文本内容。
        // architecture_design_content: 架构设计的文本内容 (JSON字符串)。
        // logic_design_content: 逻辑与任务设计的文本内容 (JSON字符串, 包含task_list)。
        // 返回: (config_yaml_content, planning_overview, architecture_design_str, task_design_str, todo_file_list, logic_analysis_map)。
        """
        config_yaml_content: Optional[str] = None
        todo_file_list: List[str] = []
        logic_analysis_map: Dict[str, str] = {}

        try:
            with open(self.config_yaml_path, 'r', encoding='utf-8') as f:
                config_yaml_content = f.read()
        except FileNotFoundError:
            print(f"// 中文注释: 错误 - 规划配置文件 {self.config_yaml_path} 未找到。")
            return None, None, None, None, [], {}
        except Exception as e:
            print(f"// 中文注释: 错误 - 加载规划配置文件 {self.config_yaml_path} 失败: {e}")
            return None, None, None, None, [], {}
        
        # // 中文注释: 直接使用传入的规划内容
        planning_overview = planning_overview_content
        architecture_design_str = architecture_design_content
        task_design_str = logic_design_content # logic_design_content 是原始的 task_design_str

        # // 中文注释: 从 task_design_str (即 logic_design_content) 中提取 todo_file_list 和 logic_analysis_map
        # // _parse_task_design 将会被 utils.parse_task_design_from_string 替代
        parsed_task_design = parse_task_design_from_string(task_design_str) # 使用导入的函数
        if parsed_task_design:
            todo_file_list = parsed_task_design.get("todo_file_list", [])
            logic_analysis_map = parsed_task_design.get("logic_analysis_map", {})
        
        if not todo_file_list:
            print(f"// 中文注释: 警告 - 未能从规划产物中提取到任务文件列表 (todo_file_list)。 内容: {task_design_str[:200]}")

        return config_yaml_content, planning_overview, architecture_design_str, task_design_str, todo_file_list, logic_analysis_map

    def _prepare_analysis_prompt_messages(self, current_file_name: str, current_file_description: str, 
                                          paper_content_full: str, paper_format_str: str, 
                                          planning_overview: str, architecture_design_str: str, 
                                          task_design_str: str, config_yaml_content: str,
                                          latex_content_full: Optional[str] = None) -> List[Dict[str, str]]: # Add latex_content_full
        """
        // 中文注释: 准备用于分析单个文件的LLM提示消息。
        """
        system_message = f"""You are an expert researcher, strategic analyzer and software engineer with a deep understanding of experimental design and reproducibility in scientific research.
You will receive a research paper in {paper_format_str} format. {"Also provided is the LaTeX source if available." if latex_content_full else ""}
An overview of the plan, a design in JSON format consisting of \"Implementation approach\", \"File list\", \"Data structures and interfaces\", and \"Program call flow\".
Followed by a task in JSON format that includes \"Required packages\", \"Required other language third-party packages\", \"Logic Analysis\", and \"Task list\".
Along with a configuration file named \"_config.yaml\". 

Your task is to conduct a comprehensive logic analysis to accurately reproduce the experiments and methodologies described in the research paper. 
This analysis must align precisely with the paper's methodology, experimental setup, and evaluation criteria.

1. Align with the Paper: Your analysis must strictly follow the methods, datasets, model configurations, hyperparameters, and experimental setups described in the paper.
2. Be Clear and Structured: Present your analysis in a logical, well-organized, and actionable format that is easy to follow and implement.
3. Prioritize Efficiency: Optimize the analysis for clarity and practical implementation while ensuring fidelity to the original experiments.
4. Follow design: YOU MUST FOLLOW \"Data structures and interfaces\". DONT CHANGE ANY DESIGN. Do not use public member functions that do not exist in your design.
5. REFER TO CONFIGURATION: Always reference settings from the _config.yaml file. Do not invent or assume any values—only use configurations explicitly provided.
"""
        
        draft_desc = f"Write the logic analysis in '{current_file_name}', which is intended for '{current_file_description}'."
        if not current_file_description or len(current_file_description.strip()) == 0:
            draft_desc = f"Write the logic analysis in '{current_file_name}'."

        user_message_content = f"""## Paper ({paper_format_str} format)
{paper_content_full}
{f'''
## LaTeX Source
{latex_content_full}
''' if latex_content_full else ''}

-----

## Overview of the plan
{planning_overview}

-----

## Design (JSON format)
{architecture_design_str}

-----

## Task (JSON format)
{task_design_str}

-----

## Configuration file (_config.yaml)
```yaml
{config_yaml_content}
```
-----

## Instruction
Conduct a Logic Analysis to assist in writing the code, based on the paper, the plan, the design, the task and the previously specified configuration file (_config.yaml). 
You DON'T need to provide the actual code yet; focus on a thorough, clear analysis.

{draft_desc}

-----

## Logic Analysis for: {current_file_name}"""
        
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message_content}
        ]

    def execute_single_file_analysis(self, 
                                     current_file_name: str, current_file_description: str,
                                     paper_content_full: str, paper_format_str: str,
                                     planning_overview: str, architecture_design_str: str,
                                     task_design_str: str, config_yaml_content: str,
                                     gpt_version_str: str,
                                     latex_content_full: Optional[str] = None) -> Optional[str]: # Add latex_content_full
        """
        // 中文注释: 对单个文件执行逻辑分析，调用LLM并保存结果。
        // 返回分析文本，如果失败则返回None。
        """
        print(f"// 中文注释: [分析阶段] 开始分析文件: {current_file_name}")
        
        messages = self._prepare_analysis_prompt_messages(
            current_file_name, current_file_description, 
            paper_content_full, paper_format_str,
            planning_overview, architecture_design_str, 
            task_design_str, config_yaml_content,
            latex_content_full # Pass latex content
        )
        
        trajectories_for_this_file = list(messages) 
        raw_responses_for_this_file = []

        try:
            additional_params = {}
            if "o3-mini" in gpt_version_str:
                 additional_params["reasoning_effort"] = "high"

            completion = self.llm_client.call_llm(
                messages=messages, 
                model_version=gpt_version_str,
                **additional_params
            )
            analysis_content = completion.choices[0].message.content
            # 中文注释：确保 completion.model_dump_json() 存在并且可以序列化
            try:
                raw_responses_for_this_file.append(json.loads(completion.model_dump_json()))
            except AttributeError:
                 print(f"// 中文注释: 警告 - completion对象缺少model_dump_json方法。将尝试直接使用字典表示。")
                 # 尝试直接构造一个类似结构的字典，如果可能的话
                 raw_responses_for_this_file.append({
                     'id': completion.id,
                     'model': completion.model,
                     'choices': [{'message': {'role': completion.choices[0].message.role, 'content': analysis_content}}],
                     'usage': completion.usage.model_dump() if hasattr(completion.usage, 'model_dump') else str(completion.usage)
                 } if hasattr(completion, 'id') else {"error": "Could not serialize full completion object"})
            except Exception as ser_e:
                print(f"// 中文注释: 警告 - 序列化LLM原始响应失败: {ser_e}")
                raw_responses_for_this_file.append({"error": f"Serialization failed: {ser_e}"})

            trajectories_for_this_file.append({'role': completion.choices[0].message.role, 'content': analysis_content})

        except Exception as e:
            print(f"// 中文注释: LLM调用在分析文件 {current_file_name} 时失败: {e}")
            return None

        analysis_file_path = os.path.join(self.analyzing_artifacts_output_dir, f"{current_file_name.replace('/', '_')}{ANALYSIS_FILENAME_SUFFIX}")
        try:
            with open(analysis_file_path, 'w', encoding='utf-8') as f:
                f.write(analysis_content)
            print(f"// 中文注释: [分析产物已保存] {analysis_file_path}")
        except IOError as e:
            print(f"// 中文注释: 错误 - 无法写入分析文件 {analysis_file_path}: {e}")
            
        safe_filename_part = current_file_name.replace("/", "_")
        # 中文注释：使用 self.paper_base_output_dir 保存日志文件
        response_json_path = os.path.join(self.paper_base_output_dir, f"{safe_filename_part}{RESPONSE_JSON_SUFFIX}")
        trajectories_json_path = os.path.join(self.paper_base_output_dir, f"{safe_filename_part}{TRAJECTORIES_JSON_SUFFIX}")
        try:
            with open(response_json_path, 'w', encoding='utf-8') as f:
                json.dump(raw_responses_for_this_file, f, indent=4, ensure_ascii=False)
            with open(trajectories_json_path, 'w', encoding='utf-8') as f:
                json.dump(trajectories_for_this_file, f, indent=4, ensure_ascii=False)
            print(f"// 中文注释: 分析日志已保存到: {response_json_path} 和 {trajectories_json_path}")
        except IOError as e:
            print(f"// 中文注释: 错误 - 无法写入分析阶段的响应/轨迹JSON文件: {e}")
        except TypeError as e:
            print(f"// 中文注释: 错误 - 序列化分析阶段的响应/轨迹为JSON时失败: {e}")
            
        print(f"// 中文注释: [分析阶段] 完成分析文件: {current_file_name}")
        return analysis_content

    # 中文注释：修改 execute_analysis_stage 以接受 paper_content_full 和 latex_content_full 及规划内容
    def execute_analysis_stage(self, 
                               paper_content_full: str, 
                               paper_format_str: str, 
                               gpt_version_str: str, 
                               planning_overview_content: str,
                               architecture_design_content: str,
                               logic_design_content: str,
                               latex_content_full: Optional[str] = None
                               ) -> Dict[str, Optional[str]]:
        """
        // 中文注释: 执行完整的分析阶段，遍历所有待分析文件。
        // 返回一个字典，键是文件名，值是分析文本 (如果成功) 或 None (如果失败)。
        """
        loaded_data = self._prepare_inputs_from_planning(
            planning_overview_content=planning_overview_content,
            architecture_design_content=architecture_design_content,
            logic_design_content=logic_design_content
        )
        config_yaml_content, planning_overview, architecture_design_str, task_design_str, todo_file_list, logic_analysis_map = loaded_data

        if config_yaml_content is None or planning_overview is None or task_design_str is None or not todo_file_list:
            print("// 中文注释: 错误 - 分析阶段因缺少必要的规划产物而无法继续。请检查之前的日志。")
            return {}
        
        analyzed_files_content: Dict[str, Optional[str]] = {}

        for file_name in todo_file_list: 
            if file_name.lower() == "_config.yaml" or file_name.lower() == "config.yaml": 
                print(f"// 中文注释: [分析阶段] 跳过配置文件: {file_name}")
                continue
            
            file_description = logic_analysis_map.get(file_name, "")
            
            analysis_result = self.execute_single_file_analysis(
                current_file_name=file_name,
                current_file_description=file_description,
                paper_content_full=paper_content_full, # 从run方法传入
                paper_format_str=paper_format_str, # 从run方法传入
                planning_overview=planning_overview,
                architecture_design_str=architecture_design_str,
                task_design_str=task_design_str,
                config_yaml_content=config_yaml_content,
                gpt_version_str=gpt_version_str, # 从run方法传入 (即llm_client.model_name)
                latex_content_full=latex_content_full # 从run方法传入
            )
            analyzed_files_content[file_name] = analysis_result
        
        print("// 中文注释: 分析阶段完成。")
        return analyzed_files_content

    # 中文注释：添加 run 方法作为 Pipeline 的主调用入口
    def run(self, 
            paper_content_full: str, 
            paper_format: str, 
            planning_overview_content: str,
            architecture_design_content: str,
            logic_design_content: str,
            latex_content_full: Optional[str] = None
            ) -> Dict[str, Optional[str]]:
        """
        // 中文注释: 执行分析流程的主入口点。
        // paper_content_full: 论文的完整内容 (例如，JSON字符串)。
        // paper_format: 论文内容的格式 (例如，"JSON")。
        // planning_overview_content: 规划总览的文本内容。
        // architecture_design_content: 架构设计的文本内容。
        // logic_design_content: 逻辑与任务设计的文本内容。
        // latex_content_full: (可选) LaTeX的完整内容字符串。
        // 返回: 分析结果字典。
        """
        print(f"// 中文注释: [AnalyzingAgent] 开始执行分析，论文: {self.paper_name}")

        # // 中文注释: paper_content_full 和 latex_content_full 从方法参数获取
        # // paper_json_path 和 latex_zip_path 存储在self中，但这里直接用传入的内容字符串
        
        # // 中文注释: 从 self.llm_client 获取模型名称
        gpt_version = self.llm_client.model_name

        results = self.execute_analysis_stage(
            paper_content_full=paper_content_full,
            paper_format_str=paper_format, # paper_format_str -> paper_format
            gpt_version_str=gpt_version,
            planning_overview_content=planning_overview_content,
            architecture_design_content=architecture_design_content,
            logic_design_content=logic_design_content,
            latex_content_full=latex_content_full
        )
        
        print(f"// 中文注释: [AnalyzingAgent] 分析完成。分析产物保存在: {self.analyzing_artifacts_output_dir}")
        return results

# // 中文注释: 示例用法。
if __name__ == '__main__':
    # // 中文注释: 此示例需要正确设置 OPENAI_API_KEY 环境变量，
    # // 并且在指定的 output_dir_base_paper 中已存在规划阶段的输出。
    # try:
    #     # llm_client_instance = LLMClient()
    #     # paper_name_example = "TestPaperAnalysis"
    #     # base_output_for_paper = f"../outputs/{paper_name_example}"
    #     # Path to a dummy _config.yaml (normally from planning)
    #     # dummy_config_path = os.path.join(base_output_for_paper, "1_planning_artifacts", "_config.yaml") 
    #     # Path to a dummy planning_trajectories.json (normally from planning)
    #     # dummy_traj_path = os.path.join(base_output_for_paper, "1_planning_artifacts", f"{paper_name_example}_planning_trajectories.json")
    #     # Path to a dummy cleaned paper json
    #     # dummy_paper_json = os.path.join(base_output_for_paper, "0_cleaned_json", f"{paper_name_example}_cleaned.json")
        
    #     # Ensure dummy files and dirs exist for test
    #     # os.makedirs(os.path.join(base_output_for_paper, "0_cleaned_json"), exist_ok=True)
    #     # os.makedirs(os.path.join(base_output_for_paper, "1_planning_artifacts"), exist_ok=True)
    #     # os.makedirs(os.path.join(base_output_for_paper, "2_analyzing_artifacts"), exist_ok=True)
        
    #     # with open(dummy_paper_json, 'w') as f: f.write(json.dumps({"title": "Test Paper for Analysis"}))
    #     # with open(dummy_config_path, 'w') as f: f.write("test_param: true")
    #     # dummy_traj_data = [{"role": "assistant", "content": "[CONTENT]Plan overview content[/CONTENT]"}, # Plan
    #     #                    {"role": "assistant", "content": "[CONTENT]{\"File list\": [\"main.py\"]}[/CONTENT]"}, # Arch
    #     #                    {"role": "assistant", "content": "[CONTENT]{\"Task list\": [\"main.py\"], \"Logic Analysis\": [[\"main.py\", \"main logic\"]]}[/CONTENT]"}] # Task
    #     # with open(dummy_traj_path, 'w') as f: json.dump(dummy_traj_data, f)

    #     # analyzer = AnalyzingAgent(
    #     #     llm_client=llm_client_instance,
    #     #     paper_name=paper_name_example,
    #     #     config_yaml_path=dummy_config_path,
    #     #     planning_trajectories_path=dummy_traj_path,
    #     #     paper_json_path=dummy_paper_json,
    #     #     latex_zip_path=None,
    #     #     analyzing_artifacts_output_dir=os.path.join(base_output_for_paper, "2_analyzing_artifacts"),
    #     #     paper_base_output_dir=base_output_for_paper
    #     # )
        
    #     # example_paper_content_str = json.dumps({"title": "Test Paper for Analysis", "body_text": "Content of the paper..."}) 
    #     # example_paper_format_str = "JSON"

    #     # print(f"\n// 中文注释: 开始为论文 '{paper_name_example}' 执行分析阶段 (run method)...")
    #     # analysis_results = analyzer.run(
    #     #     paper_content_full=example_paper_content_str,
    #     #     paper_format=example_paper_format_str,
    #     #     latex_content_full=None # Optional
    #     # )

    #     # print("\n// 中文注释: 分析阶段产物:")
    #     # if analysis_results:
    #     #     for file_name_key, content_preview in analysis_results.items():
    #     #         if content_preview:
    #     #             print(f"  - {file_name_key}: {content_preview[:100].replace('\n', ' ')}...")
    #     #         else:
    #     #             print(f"  - {file_name_key}: 分析失败或无内容")
    #     # else:
    #     #     print("// 中文注释: 未生成分析产物或分析阶段提前终止。")

    # except ValueError as ve: 
    #     print(f"// 中文注释: 初始化错误: {ve}")
    # except Exception as e:
    #     print(f"// 中文注释: 执行分析阶段示例时发生错误: {e}")
    #     import traceback
    #     traceback.print_exc()
    pass 