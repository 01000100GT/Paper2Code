import json
import os
# // 中文注释: 导入LLMClient用于与LLM交互。
from .llm_handler import LLMClient 
# // 中文注释: 导入typing用于类型提示。
from typing import List, Dict, Any, Tuple, Optional # // 中文注释: 导入 Optional
import re # // 中文注释: 导入 re 模块

# // 中文注释: 规划阶段产生的文件的基础名称。
PLANNING_ARTIFACTS_PREFIX = "planning"

class PlanningAgent:
    """
    // 中文注释: PlanningAgent 类负责论文复现的规划阶段。
    // 它与LLM交互以生成总体计划、架构设计、逻辑设计和配置文件。
    """
    def __init__(self, llm_client: LLMClient, paper_name: str, planning_output_dir: str):
        """
        // 中文注释: 初始化 PlanningAgent。
        // llm_client: LLMClient的实例。
        // paper_name: 当前处理的论文名称，用于构建输出路径。
        // planning_output_dir: 保存所有规划产物 (artifacts 和 trajectories) 的统一输出目录。
        """
        self.llm_client = llm_client
        self.paper_name = paper_name
        # 中文注释：使用 planning_output_dir 作为所有规划产物的根目录
        self.planning_output_dir = planning_output_dir
        # // 中文注释: 确保规划产物目录存在。
        os.makedirs(self.planning_output_dir, exist_ok=True)
        # // 中文注释: 对话历史，用于多轮对话。
        self.trajectories: List[Dict[str, str]] = [] 

    def _get_prompts(self, paper_content: str, paper_format: str, latex_content: Optional[str] = None) -> List[List[Dict[str, str]]]:
        """
        // 中文注释: 定义并返回规划各个阶段的提示(prompts)。
        // paper_content: 论文的文本内容 (JSON字符串或Markdown等)。
        // paper_format: 论文的格式 (例如 "JSON" 或 "LaTeX")。
        // latex_content: (可选) LaTeX原始内容字符串。
        // 返回: 一个包含各阶段提示列表的列表。
        """
        # // 中文注释: 根据是否有 LaTeX 内容，调整 paper_content 或提示
        # // 当前提示模板主要针对 paper_content。如果需要同时使用 JSON 和 LaTeX，提示需要修改。
        # // 为简单起见，此处暂时不直接在提示中合并 LaTeX，仅作参数传递。
        
        plan_msg_system_content = f"""You are an expert researcher and strategic planner with a deep understanding of experimental design and reproducibility in scientific research. 
You will receive a research paper in {paper_format} format. {"Also provided is the LaTeX source if available." if latex_content else ""}
Your task is to create a detailed and efficient plan to reproduce the experiments and methodologies described in the paper.
This plan should align precisely with the paper's methodology, experimental setup, and evaluation metrics. 

Instructions:

1. Align with the Paper: Your plan must strictly follow the methods, datasets, model configurations, hyperparameters, and experimental setups described in the paper.
2. Be Clear and Structured: Present the plan in a well-organized and easy-to-follow format, breaking it down into actionable steps.
3. Prioritize Efficiency: Optimize the plan for clarity and practical implementation while ensuring fidelity to the original experiments."""
        
        plan_msg_user_content = f"""## Paper ({paper_format} format)
{paper_content}
{f'''
## LaTeX Source
{latex_content}
''' if latex_content else ''}

## Task
1. We want to reproduce the method described in the attached paper. 
2. The authors did not release any official code, so we have to plan our own implementation.
3. Before writing any Python code, please outline a comprehensive plan that covers:
   - Key details from the paper's **Methodology**.
   - Important aspects of **Experiments**, including dataset requirements, experimental settings, hyperparameters, or evaluation metrics.
4. The plan should be as **detailed and informative** as possible to help us write the final code later.

## Requirements
- You don't need to provide the actual code yet; focus on a **thorough, clear strategy**.
- If something is unclear from the paper, mention it explicitly.

## Instruction
The response should give us a strong roadmap, making it easier to write the code later."""
        
        plan_msg = [
            {'role': "system", "content": plan_msg_system_content},
            {'role': "user", "content" : plan_msg_user_content}
        ]

        file_list_msg = [
            {'role': "user", "content": """Your goal is to create a concise, usable, and complete software system design for reproducing the paper's method. Use appropriate open-source libraries and keep the overall architecture simple.
             
Based on the plan for reproducing the paper's main method, please design a concise, usable, and complete software system. 
Keep the architecture simple and make effective use of open-source libraries.

-----

## Format Example
[CONTENT]
{
    "Implementation approach": "We will ...",
    "File list": [
        "main.py",  
        "dataset_loader.py", 
        "model.py",  
        "trainer.py",
        "evaluation.py" 
    ],
    "Data structures and interfaces": "\nclassDiagram\n    class Main {\n        +__init__()\n        +run_experiment()\n    }\n    class DatasetLoader {\n        +__init__(config: dict)\n        +load_data() -> Any\n    }\n    class Model {\n        +__init__(params: dict)\n        +forward(x: Tensor) -> Tensor\n    }\n    class Trainer {\n        +__init__(model: Model, data: Any)\n        +train() -> None\n    }\n    class Evaluation {\n        +__init__(model: Model, data: Any)\n        +evaluate() -> dict\n    }\n    Main --> DatasetLoader\n    Main --> Trainer\n    Main --> Evaluation\n    Trainer --> Model\n",
    "Program call flow": "\nsequenceDiagram\n    participant M as Main\n    participant DL as DatasetLoader\n    participant MD as Model\n    participant TR as Trainer\n    participant EV as Evaluation\n    M->>DL: load_data()\n    DL-->>M: return dataset\n    M->>MD: initialize model()\n    M->>TR: train(model, dataset)\n    TR->>MD: forward(x)\n    MD-->>TR: predictions\n    TR-->>M: training complete\n    M->>EV: evaluate(model, dataset)\n    EV->>MD: forward(x)\n    MD-->>EV: predictions\n    EV-->>M: metrics\n",
    "Anything UNCLEAR": "Need clarification on the exact dataset format and any specialized hyperparameters."
}
[/CONTENT]

## Nodes: \"<node>: <type>  # <instruction>\"
- Implementation approach: <class 'str'>  # Summarize the chosen solution strategy.
- File list: typing.List[str]  # Only need relative paths. ALWAYS write a main.py or app.py here.
- Data structures and interfaces: typing.Optional[str]  # Use mermaid classDiagram code syntax, including classes, method(__init__ etc.) and functions with type annotations, CLEARLY MARK the RELATIONSHIPS between classes, and comply with PEP8 standards. The data structures SHOULD BE VERY DETAILED and the API should be comprehensive with a complete design.
- Program call flow: typing.Optional[str] # Use sequenceDiagram code syntax, COMPLETE and VERY DETAILED, using CLASSES AND API DEFINED ABOVE accurately, covering the CRUD AND INIT of each object, SYNTAX MUST BE CORRECT.
- Anything UNCLEAR: <class 'str'>  # Mention ambiguities and ask for clarifications.

## Constraint
Format: output wrapped inside [CONTENT][/CONTENT] like the format example, nothing else.

## Action
Follow the instructions for the nodes, generate the output, and ensure it follows the format example."""}
        ]

        task_list_msg = [
            {'role': 'user', 'content': """Your goal is break down tasks according to PRD/technical design, generate a task list, and analyze task dependencies. 
You will break down tasks, analyze dependencies.
             
You outline a clear PRD/technical design for reproducing the paper's method and experiments. 

Now, let's break down tasks according to PRD/technical design, generate a task list, and analyze task dependencies.
The Logic Analysis should not only consider the dependencies between files but also provide detailed descriptions to assist in writing the code needed to reproduce the paper.

-----

## Format Example
[CONTENT]
{
    "Required packages": [
        "numpy==1.21.0",
        "torch==1.9.0"  
    ],
    "Required Other language third-party packages": [
        "No third-party dependencies required"
    ],
    "Logic Analysis": [
        [
            "data_preprocessing.py",
            "DataPreprocessing class ........"
        ],
        [
            "trainer.py",
            "Trainer ....... "
        ],
        [
            "dataset_loader.py",
            "Handles loading and ........"
        ],
        [
            "model.py",
            "Defines the model ......."
        ],
        [
            "evaluation.py",
            "Evaluation class ........ "
        ],
        [
            "main.py",
            "Entry point  ......."
        ]
    ],
    "Task list": [
        "dataset_loader.py", 
        "model.py",  
        "trainer.py", 
        "evaluation.py",
        "main.py"  
    ],
    "Full API spec": "openapi: 3.0.0 ...",
    "Shared Knowledge": "Both data_preprocessing.py and trainer.py share ........",
    "Anything UNCLEAR": "Clarification needed on recommended hardware configuration for large-scale experiments."
}

[/CONTENT]

## Nodes: \"<node>: <type>  # <instruction>\"
- Required packages: typing.Optional[typing.List[str]]  # Provide required third-party packages in requirements.txt format.(e.g., 'numpy==1.21.0').
- Required Other language third-party packages: typing.List[str]  # List down packages required for non-Python languages. If none, specify "No third-party dependencies required".
- Logic Analysis: typing.List[typing.List[str]]  # Provide a list of files with the classes/methods/functions to be implemented, including dependency analysis and imports. Include as much detailed description as possible.
- Task list: typing.List[str]  # Break down the tasks into a list of filenames, prioritized based on dependency order. The task list must include the previously generated file list.
- Full API spec: <class 'str'>  # Describe all APIs using OpenAPI 3.0 spec that may be used by both frontend and backend. If front-end and back-end communication is not required, leave it blank.
- Shared Knowledge: <class 'str'>  # Detail any shared knowledge, like common utility functions or configuration variables.
- Anything UNCLEAR: <class 'str'>  # Mention any unresolved questions or clarifications needed from the paper or project scope.

## Constraint
Format: output wrapped inside [CONTENT][/CONTENT] like the format example, nothing else.

## Action
Follow the node instructions above, generate your output accordingly, and ensure it follows the given format example."""}]
        
        # 中文注释：确保LLM被明确指示生成_config.yaml，以便后续步骤能找到它。
        config_msg_user_content = """You write elegant, modular, and maintainable code. Adhere to Google-style guidelines.

Based on the paper, plan, design specified previously, follow the "Format Example" and generate the code. 
Extract the training details from the above paper (e.g., learning rate, batch size, epochs, etc.), follow the "Format example" and generate the code. 
DO NOT FABRICATE DETAILS — only use what the paper provides.

You must write `_config.yaml`.

ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. Your output format must follow the example below exactly.

-----

# Format Example
## Code: _config.yaml
```yaml
## _config.yaml
training:
  learning_rate: ...
  batch_size: ...
  epochs: ...
...
```

-----

## Code: _config.yaml 
""" # Important: Prompt ends here, LLM starts with content of _config.yaml
        config_msg = [
            {'role': 'user', 'content': config_msg_user_content}
        ]
        return [plan_msg, file_list_msg, task_list_msg, config_msg]

    def _extract_content_from_response(self, response_content: str, is_yaml: bool = False) -> str:
        """
        // 中文注释: 从LLM的响应中提取核心内容。
        // 某些响应可能包含特定的标记（如 [CONTENT]...[/CONTENT] 或 ```yaml...```）。
        // response_content: LLM返回的原始字符串。
        // is_yaml: 指示内容是否为YAML，需要特殊处理。
        // 返回: 提取后的核心内容字符串。
        """
        if is_yaml:
            # // 中文注释: 提取YAML块，专门寻找 _config.yaml 的标记
            match = re.search(r"## Code: _config\.yaml\s*```yaml\s*(.*?)\s*```", response_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            # // 中文注释: 如果上述特定标记未找到，尝试更通用的YAML块提取
            match_generic_yaml = re.search(r"```yaml\s*(.*?)\s*```", response_content, re.DOTALL | re.IGNORECASE)
            if match_generic_yaml:
                return match_generic_yaml.group(1).strip()
            # // 中文注释: 作为最后的手段，如果根本没有 ``` 标记，则返回原始内容（可能LLM未按预期格式化）
            if "```" not in response_content:
                return response_content.strip()
            # // 中文注释: 如果有 ``` 但未匹配，可能格式错误，返回空字符串或记录警告
            print(f"// 中文注释: 警告 - 在YAML响应中找到 \`\`\` 但无法提取内容: {response_content[:200]}...")
            return "" # 或者抛出错误，取决于严格程度

        # // 中文注释: 提取被 [CONTENT] 包裹的内容。
        if "[CONTENT]" in response_content and "[/CONTENT]" in response_content:
            # // 中文注释: 使用正则表达式以处理内容标签大小写不敏感和前后空格问题
            match = re.search(r"\[CONTENT\](.*?)\[/CONTENT\]", response_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # // 中文注释: 如果没有特定标记，则返回原始剥离空格后的内容。
        return response_content.strip()

    def _save_artifact(self, content: str, filename_key: str) -> str:
        """
        // 中文注释: 将规划产物保存到文件。
        // content: 要保存的内容。
        // filename_key: 产物的键名 (例如 "overall_plan", "config")，用于生成标准文件名。
        // 返回: 保存文件的绝对路径。
        """
        if filename_key == "config":
            actual_filename = "_config.yaml" # // 中文注释：确保配置文件名为 _config.yaml
        else:
            actual_filename = f"{self.paper_name}_{PLANNING_ARTIFACTS_PREFIX}_{filename_key}.md"
        
        filepath = os.path.join(self.planning_output_dir, actual_filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"// 中文注释: [规划产物已保存] {filepath}")
            return filepath
        except IOError as e:
            print(f"// 中文注释: 错误：无法写入规划产物文件 {filepath}。错误: {e}")
            raise

    def _save_trajectories(self) -> str:
        """
        // 中文注释: 保存完整的对话历史到 trajectories.json 文件。
        // 返回: 保存文件的绝对路径。
        """
        trajectories_filename = f"{self.paper_name}_{PLANNING_ARTIFACTS_PREFIX}_trajectories.json"
        trajectories_path = os.path.join(self.planning_output_dir, trajectories_filename)
        try:
            with open(trajectories_path, 'w', encoding='utf-8') as f:
                json.dump(self.trajectories, f, indent=4, ensure_ascii=False)
            print(f"// 中文注释: [对话历史已保存] {trajectories_path}")
            return trajectories_path
        except IOError as e:
            print(f"// 中文注释: 错误：无法写入对话历史文件 {trajectories_path}。错误: {e}")
            raise
        except TypeError as e:
            print(f"// 中文注释: 错误：序列化对话历史到JSON时失败。错误: {e}")
            raise

    def execute_planning_stage(self, paper_content_full: str, paper_format: str, gpt_version: str, latex_content_full: Optional[str] = None) -> Dict[str, Any]:
        """
        // 中文注释: 执行完整的规划阶段，包括所有子步骤。
        // paper_content_full: 完整的论文内容字符串。
        // paper_format: 论文的格式 ("JSON" 或 "LaTeX")。
        // gpt_version: 使用的GPT模型版本。
        // latex_content_full: (可选) 完整的LaTeX原始内容字符串。
        // 返回: 一个字典，包含 'config_path', 'trajectories_path', 'artifacts_content' (内容映射), 和 'artifact_paths' (路径映射)。
        """
        all_prompts = self._get_prompts(paper_content_full, paper_format, latex_content_full)
        stage_names = ["overall_plan", "architecture_design", "logic_design", "config"]
        
        # // 中文注释: 重置对话历史以备新的规划会话。
        self.trajectories = [] 
        generated_artifacts_content = {}
        saved_artifact_paths = {} # // 中文注释: 用于存储各产物的路径

        for idx, (instruction_msg_template, stage_name) in enumerate(zip(all_prompts, stage_names)):
            current_stage_log_name = f"[Planning] {stage_name.replace('_', ' ').title()}"
            print(f"// 中文注释: 开始规划阶段: {current_stage_log_name}")

            messages_to_send = list(self.trajectories) 
            if not messages_to_send: 
                messages_to_send.extend(instruction_msg_template)
            else: 
                # // 中文注释: 对于后续轮次，通常只添加新的 user message。
                # // instruction_msg_template 对于后续阶段可能只包含一个 user message。
                user_message_parts = [msg for msg in instruction_msg_template if msg['role'] == 'user']
                if len(user_message_parts) == 1:
                    messages_to_send.append(user_message_parts[0])
                else: # // 如果模板结构非预期，则按原样添加全部，或采取其他错误处理
                    print(f"// 中文注释: 警告 - {stage_name} 的指令模板结构非预期，将添加所有消息部分。")
                    messages_to_send.extend(instruction_msg_template)           
            try:
                additional_params = {}
                # // 中文注释: 为 o3-mini 添加 reasoning_effort="high" (如果适用)。
                # // gpt_version 来自 self.llm_client.model_name, temperature 来自 self.llm_client.temperature
                if "o3-mini" in gpt_version: 
                     additional_params["reasoning_effort"] = "high"
                
                completion = self.llm_client.call_llm(
                    messages=messages_to_send, 
                    model_version=gpt_version, # 使用传入的 gpt_version (来自llm_client.model_name)
                    # temperature 将由 llm_client 自动从 self.llm_client.temperature 获取
                    **additional_params
                )
                response_content = completion.choices[0].message.content
            except Exception as e:
                print(f"// 中文注释: LLM调用在 {current_stage_log_name} 阶段失败: {e}")
                raise # // 中文注释: 发生错误时抛出异常，以便上层处理

            is_yaml_output = (stage_name == "config")
            extracted_content = self._extract_content_from_response(response_content, is_yaml=is_yaml_output)
            
            # // 中文注释: 保存当前阶段的产物并获取路径。
            artifact_path = self._save_artifact(extracted_content, stage_name)
            saved_artifact_paths[stage_name] = artifact_path # // 中文注释: 存储路径
            generated_artifacts_content[stage_name] = extracted_content # // 中文注释: 存储内容
            
            # // 中文注释: 更新对话历史，加入LLM的响应。
            # // 首先添加本轮的用户/系统提示 (如果尚未完全在self.trajectories中)
            if not self.trajectories: # // 第一轮, instruction_msg_template 是完整的 (system, user)
                 self.trajectories.extend(instruction_msg_template)
            else: # // 后续轮, 只添加user message部分到历史记录 (因为system提示已在开头)
                 user_message_parts_for_history = [msg for msg in instruction_msg_template if msg['role'] == 'user']
                 if user_message_parts_for_history: # 确保确实有user message再添加
                    self.trajectories.extend(user_message_parts_for_history)
                 # else: system message only, do not add to history again.

            self.trajectories.append({'role': 'assistant', 'content': response_content}) # // 使用原始回复加入历史记录

            print(f"// 中文注释: 完成规划阶段: {current_stage_log_name}")
        
        # // 中文注释: 在所有阶段完成后，保存完整的对话历史。
        trajectories_file_path = self._save_trajectories()

        return {
            "config_path": saved_artifact_paths.get("config", None), # // 中文注释: 返回config文件的路径 (_config.yaml)
            "trajectories_path": trajectories_file_path, # // 中文注释: 返回轨迹文件的路径
            "artifacts_content": generated_artifacts_content, # // 中文注释: 返回所有提取的产物内容
            "artifact_paths": saved_artifact_paths # // 中文注释: 返回所有保存的产物文件路径 (字典)
        }

    # 中文注释：添加 run 方法作为 Pipeline 的主调用入口
    def run(self, paper_content_full: str, paper_format: str, latex_content_full: Optional[str] = None) -> Dict[str, Any]:
        """
        // 中文注释: 执行规划流程的主入口点。
        // paper_content_full: 论文的完整内容 (例如，JSON字符串)。
        // paper_format: 论文内容的格式 (例如，"JSON")。
        // latex_content_full: (可选) LaTeX的完整内容字符串。
        // 返回: 一个字典，包含config_path, trajectories_path, artifacts_content, artifact_paths。
        """
        print(f"// 中文注释: [PlanningAgent] 开始执行规划，论文: {self.paper_name}")
        
        # // 中文注释: LLMClient实例自身已包含model_name和temperature，call_llm会使用它们
        results = self.execute_planning_stage(
            paper_content_full=paper_content_full,
            paper_format=paper_format,
            gpt_version=self.llm_client.model_name, # // 中文注释: 从llm_client获取默认模型名称
            latex_content_full=latex_content_full
        )
        
        config_p = results.get('config_path')
        traj_p = results.get('trajectories_path')
        print(f"// 中文注释: [PlanningAgent] 规划完成。配置文件: {config_p}, 轨迹文件: {traj_p}")
        return results

# // 中文注释: 示例用法 (通常此类会由更高级别的流程管理器实例化和调用)。
if __name__ == '__main__':
    # // 中文注释: 这是一个示例，需要正确设置OPENAI_API_KEY环境变量和输入。
    # import tempfile # // 中文注释: 用于创建临时目录进行测试
    # temp_output_dir = tempfile.mkdtemp()
    # print(f"// 中文注释: 测试输出将保存到临时目录: {temp_output_dir}")

    # try:
    #     # // 中文注释: llm_client 现在从 __init__ 接收 model_name 和 temperature
    #     llm_client_instance = LLMClient(model_name="gpt-3.5-turbo", temperature=0.5) 
        
    #     paper_name_example = "TestPaper123"
        
    #     # // 中文注释: 创建 PlanningAgent 实例。
    #     planner = PlanningAgent(
    #         llm_client=llm_client_instance, 
    #         paper_name=paper_name_example,
    #         planning_output_dir=os.path.join(temp_output_dir, paper_name_example, "1_planning_artifacts") # // 中文注释: 模拟Pipeline中的路径结构
    #     )
    #     example_paper_json_content = json.dumps({"title": "Attention Is All You Need", "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks..."})
    #     example_paper_format = "JSON"
    #     example_latex_content = "\\\\documentclass{article}\\n\\\\begin{document}\\nThis is a test LaTeX document.\\n\\\\end{document}\""

    #     print(f"// 中文注释: 正在为论文 '{paper_name_example}' 执行规划阶段 (run method)...")
    #     # // 中文注释: 调用新的 run 方法
    #     planning_outputs = planner.run(
    #         paper_content_full=example_paper_json_content, 
    #         paper_format=example_paper_format,
    #         latex_content_full=example_latex_content
    #     )

    #     print("\n// 中文注释: PlanningAgent.run() 返回的输出:")
    #     print(f"  Config Path: {planning_outputs.get('config_path')}")
    #     print(f"  Trajectories Path: {planning_outputs.get('trajectories_path')}")
    #     if planning_outputs.get('config_path') and os.path.exists(planning_outputs.get('config_path')):
    #         with open(planning_outputs.get('config_path'), 'r') as f_conf:
    #             print(f"  Config Content Preview: {f_conf.read(100)}...")
        
    #     # // 中文注释: 清理临时目录 (可选)
    #     # import shutil
    #     #     # shutil.rmtree(temp_output_dir)
    #     #     # print(f"// 中文注释: 已清理临时目录: {temp_output_dir}")
    # except ValueError as ve: # // 中文注释: 来自LLMClient的初始化错误
    #     print(f"// 中文注释: 初始化错误: {ve}")
    # except Exception as e:
    #     print(f"// 中文注释: 执行示例时发生错误: {e}")
    #     import traceback
    #     traceback.print_exc()
    pass 