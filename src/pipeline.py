import os
from .llm_handler import LLMClient
from .paper_parser import JSONCleaner
from .planning_agent import PlanningAgent
from .analyzing_agent import AnalyzingAgent
from .coding_agent import CodingAgent
from .utils import ensure_dir_exists, load_json_file, load_text_file # 导入需要的辅助函数
from typing import Optional, Dict, Any
import zipfile # 中文注释: 用于处理ZIP文件
import tempfile # 中文注释: 用于创建临时目录

# 中文注释：定义 Pipeline 类，用于串联整个论文到代码的转换流程。
class Pipeline:
    def __init__(self, paper_name: str, paper_json_path: str, base_output_dir: str, openai_api_key: str, llm_model_name: str = "gpt-4-turbo", latex_zip_path: Optional[str] = None, llm_temperature: float = 0.7, openai_api_base: Optional[str] = None):
        """
        中文注释：Pipeline类的构造函数。
        参数:
            paper_name (str): 论文的名称，用于命名输出文件和目录。
            paper_json_path (str): 经过PDF解析后生成的原始JSON文件的路径。
            base_output_dir (str): 所有输出（包括中间产物和最终代码）的基础存储目录。
            openai_api_key (str): OpenAI API密钥。
            llm_model_name (str): 使用的LLM模型名称。
            latex_zip_path (str, optional): 论文的LaTeX源文件压缩包路径。默认为None。
            llm_temperature (float, optional): LLM的temperature参数。默认为0.7。
            openai_api_base (str, optional): (可选) OpenAI API的基础URL。默认为None，使用OpenAI官方API。
        """
        self.paper_name = paper_name
        self.paper_json_path = paper_json_path # 原始JSON路径
        self.latex_zip_path = latex_zip_path
        self.base_output_dir = base_output_dir
        self.openai_api_key = openai_api_key
        self.llm_model_name = llm_model_name
        self.llm_temperature = llm_temperature
        self.openai_api_base = openai_api_base

        # 中文注释：初始化LLM客户端，传递 api_base
        self.llm_client = LLMClient(
            api_key=self.openai_api_key, 
            model_name=self.llm_model_name, 
            temperature=self.llm_temperature,
            api_base=self.openai_api_base
        )

        # 中文注释：定义各个阶段产物的输出目录
        self.cleaned_json_dir = os.path.join(self.base_output_dir, "0_cleaned_json")
        self.planning_output_dir = os.path.join(self.base_output_dir, "1_planning_artifacts")
        self.analyzing_output_dir = os.path.join(self.base_output_dir, "2_analyzing_artifacts")
        self.coding_artifacts_dir = os.path.join(self.base_output_dir, "3_coding_artifacts")
        self.final_code_dir = os.path.join(self.base_output_dir, "4_output_repository")
        
        # 中文注释：定义清理后的JSON文件路径
        self.cleaned_paper_json_path = os.path.join(self.cleaned_json_dir, f"{self.paper_name}_cleaned.json")

    def _setup_directories(self):
        """中文注释：创建所有需要的输出目录。"""
        ensure_dir_exists(self.base_output_dir)
        ensure_dir_exists(self.cleaned_json_dir)
        ensure_dir_exists(self.planning_output_dir)
        ensure_dir_exists(self.analyzing_output_dir)
        ensure_dir_exists(self.coding_artifacts_dir)
        ensure_dir_exists(self.final_code_dir)
        print(f"Output directories created under: {self.base_output_dir}")

    def run(self):
        """中文注释：执行完整的处理流程。"""
        print(f"Starting pipeline for paper: {self.paper_name}")
        self._setup_directories()

        # --- 0. JSON 清理阶段 ---
        # 中文注释：实例化JSONCleaner并执行清理操作。
        # 假设JSONCleaner的clean方法接收输入和输出路径
        print("\nStage 0: Cleaning JSON...")
        # // 中文注释: 添加详细路径检查日志
        print(f"// 中文注释: [Pipeline.run] 传递给 JSONCleaner 的输入路径: '{self.paper_json_path}'")
        absolute_pipeline_input_path = os.path.abspath(self.paper_json_path)
        print(f"// 中文注释: [Pipeline.run] 绝对路径: '{absolute_pipeline_input_path}'")
        print(f"// 中文注释: [Pipeline.run] 文件是否存在 (os.path.exists): {os.path.exists(absolute_pipeline_input_path)}")

        json_cleaner = JSONCleaner(self.paper_json_path, self.cleaned_paper_json_path)
        json_cleaner.clean_json() # 假设clean_json是其执行方法
        print(f"Cleaned JSON saved to: {self.cleaned_paper_json_path}")
        
        # 中文注释：加载清理后的JSON内容字符串，供PlanningAgent使用
        try:
            cleaned_paper_content_str = load_text_file(self.cleaned_paper_json_path)
        except FileNotFoundError:
            print(f"// 中文注释: 错误 - 清理后的JSON文件 {self.cleaned_paper_json_path} 未找到，无法继续规划。")
            raise # 中文注释：或者采取其他错误处理方式
        except Exception as e:
            print(f"// 中文注释: 错误 - 加载清理后的JSON文件 {self.cleaned_paper_json_path} 时发生未知错误: {e}")
            raise
        
        # 中文注释：处理LaTeX内容 (如果提供了路径)
        latex_content_str: Optional[str] = None
        if self.latex_zip_path and os.path.exists(self.latex_zip_path):
            print(f"// 中文注释: 正在尝试从 {self.latex_zip_path} 加载LaTeX内容...")
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(self.latex_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    tex_files_content = []
                    # 中文注释: 遍历解压后的目录寻找.tex文件
                    for root, _, files in os.walk(temp_dir):
                        for file_name_in_zip in files: # Renamed 'file' to 'file_name_in_zip' to avoid conflict
                            if file_name_in_zip.endswith(".tex"):
                                try:
                                    file_path = os.path.join(root, file_name_in_zip)
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_tex:
                                        tex_content = f_tex.read()
                                        # 中文注释: 简单检查是否可能是主要文件 (包含documentclass)
                                        if "\\documentclass" in tex_content: # Escaped backslash for regex-like interpretation if needed, though simple string check is fine
                                            tex_files_content.insert(0, tex_content) # 优先放入列表头部
                                        else:
                                            tex_files_content.append(tex_content)
                                    print(f"// 中文注释: 已读取LaTeX文件: {file_path}")
                                except Exception as e_read:
                                    print(f"// 中文注释: 读取 .tex 文件 {file_path} 时出错: {e_read}")
                    
                    if tex_files_content:
                        # 中文注释: 合并所有找到的.tex文件内容，优先使用可能的主文件
                        latex_content_str = "\n\n--- (Next .tex File) ---\n\n".join(tex_files_content)
                        print(f"// 中文注释: LaTeX内容加载成功，总长度: {len(latex_content_str)} 字符。")
                    else:
                        print(f"// 中文注释: 警告 - 在 {self.latex_zip_path} 中未找到 .tex 文件。")
            except zipfile.BadZipFile:
                print(f"// 中文注释: 错误 - LaTeX ZIP文件 {self.latex_zip_path} 损坏或格式不正确。")
            except Exception as e_zip:
                print(f"// 中文注释: 处理LaTeX ZIP文件 {self.latex_zip_path} 时发生意外错误: {e_zip}")
        elif self.latex_zip_path: # Only print warning if path was given but not found
            print(f"// 中文注释: 警告 - 提供的LaTeX ZIP路径 {self.latex_zip_path} 不存在。")
        # --- 1. 规划阶段 ---
        # 中文注释：实例化PlanningAgent并执行规划。
        print("\nStage 1: Planning...")
        # 中文注释：更新PlanningAgent的实例化方式
        planning_agent = PlanningAgent(
            llm_client=self.llm_client, # llm_client实例已包含model_name和temperature
            paper_name=self.paper_name,
            planning_output_dir=self.planning_output_dir
        )
        
        # 中文注释：调用PlanningAgent的run方法，传递必要的参数
        try:
            planning_results = planning_agent.run(
                paper_content_full=cleaned_paper_content_str,
                paper_format="JSON", # 假设清理后的内容是JSON字符串格式
                latex_content_full=latex_content_str # 传递处理过的LaTeX内容
            )
        except Exception as e:
            print(f"// 中文注释: PlanningAgent.run() 执行失败: {e}")
            raise # 中文注释：或者采取其他错误处理方式
        
        # 中文注释：从PlanningAgent的返回结果中获取关键文件路径
        config_yaml_path = planning_results.get("config_path")
        planning_trajectories_path = planning_results.get("trajectories_path")
        # 中文注释：直接从 planning_results 中获取已提取的规划内容
        planning_artifacts_content = planning_results.get("artifacts_content", {})
        overall_plan_content = planning_artifacts_content.get("overall_plan", "")
        architecture_design_content = planning_artifacts_content.get("architecture_design", "")
        logic_design_content = planning_artifacts_content.get("logic_design", "") # 这是包含 task_list 的 JSON 字符串

        if not config_yaml_path or not os.path.exists(config_yaml_path):
            print(f"// 中文注释: 错误 - 规划阶段未能生成配置文件或路径无效: {config_yaml_path}")
            # 根据需要决定是否中止流程
            raise FileNotFoundError(f"规划阶段生成的配置文件路径无效: {config_yaml_path}")
        if not planning_trajectories_path or not os.path.exists(planning_trajectories_path):
            print(f"// 中文注释: 错误 - 规划阶段未能生成轨迹文件或路径无效: {planning_trajectories_path}")
            # 根据需要决定是否中止流程
            raise FileNotFoundError(f"规划阶段生成的轨迹文件路径无效: {planning_trajectories_path}")
            
        print(f"Planning artifacts generated in: {self.planning_output_dir}")
        print(f"Config YAML path: {config_yaml_path}")
        print(f"Planning trajectories path: {planning_trajectories_path}")

        # --- 2. 分析阶段 ---
        # 中文注释：实例化AnalyzingAgent并执行分析。
        print("\nStage 2: Analyzing...")
        # 中文注释：更新AnalyzingAgent的实例化方式，传递必要的路径
        analyzing_agent = AnalyzingAgent(
            llm_client=self.llm_client,
            paper_name=self.paper_name,
            config_yaml_path=config_yaml_path, # 来自规划阶段的config文件路径
            planning_trajectories_path=planning_trajectories_path, # 来自规划阶段的轨迹文件路径
            paper_json_path=self.cleaned_paper_json_path, # 清理后的论文JSON路径
            latex_zip_path=self.latex_zip_path, # 原始LaTeX zip路径 (内容由Pipeline的run处理)
            analyzing_artifacts_output_dir=self.analyzing_output_dir, # _simple_analysis.txt等分析产物的保存目录
            paper_base_output_dir=self.base_output_dir # 用于保存分析日志 (_response.json等) 的论文级基础输出目录
        )
        
        # 中文注释：调用AnalyzingAgent的run方法，传递必要的参数
        # cleaned_paper_content_str 和 latex_content_str 已在规划阶段准备好
        try:
            analysis_results = analyzing_agent.run(
                paper_content_full=cleaned_paper_content_str,
                paper_format="JSON", # 与规划阶段一致
                latex_content_full=latex_content_str, # 传递已加载的LaTeX内容
                # 中文注释：传递规划阶段直接提取的文本内容
                planning_overview_content=overall_plan_content,
                architecture_design_content=architecture_design_content,
                logic_design_content=logic_design_content,
                # 中文注释：config_yaml_content 也由 PlanningAgent 生成并保存在 planning_results["artifacts_content"]["config"] 中
                # 但 AnalyzingAgent 的 __init__ 已经接收了 config_yaml_path，并在内部加载，所以这里不需要重复传递 config 内容字符串
            )
            # analysis_results 是一个字典，键是文件名，值是分析文本或None
            # 目前Pipeline不直接使用analysis_results的内容，但可以记录或检查
            if not analysis_results:
                print("// 中文注释: 警告 - AnalyzingAgent.run() 未返回任何结果或返回为空。")
            else:
                # 计算成功分析的文件数量
                successful_analyses = sum(1 for content in analysis_results.values() if content is not None)
                print(f"// 中文注释: 分析阶段完成，成功分析了 {successful_analyses}/{len(analysis_results)} 个文件。")

        except Exception as e:
            print(f"// 中文注释: AnalyzingAgent.run() 执行失败: {e}")
            raise # 中文注释：或者采取其他错误处理方式

        print(f"Analyzing artifacts (_simple_analysis.txt) saved in: {self.analyzing_output_dir}")
        print(f"Analyzing logs (_response.json, _trajectories.json) saved in: {self.base_output_dir}")

        # --- 3. 编码阶段 ---
        # 中文注释：实例化CodingAgent并执行代码生成。
        print("\nStage 3: Coding...")
        # 中文注释：更新CodingAgent的实例化方式，传递必要的路径和目录
        coding_agent = CodingAgent(
            llm_client=self.llm_client,
            paper_name=self.paper_name,
            config_yaml_path=config_yaml_path, # 来自规划阶段的config文件路径
            planning_trajectories_path=planning_trajectories_path, # 来自规划阶段的轨迹文件路径
            paper_json_path=self.cleaned_paper_json_path, # 清理后的论文JSON路径
            latex_zip_path=self.latex_zip_path, # 原始LaTeX zip路径
            analysis_json_logs_dir=self.base_output_dir, # 分析阶段保存 _simple_analysis_response.json 的目录 (即pipeline的base_output_dir)
            output_repo_dir=self.final_code_dir, # 最终代码仓库目录
            coding_artifacts_dir=self.coding_artifacts_dir # 编码阶段原始LLM输出 (_coding.txt) 的保存目录
        )

        # 中文注释：调用CodingAgent的run方法，传递必要的参数
        # cleaned_paper_content_str 和 latex_content_str 已在规划阶段准备好
        try:
            generated_code_map = coding_agent.run(
                paper_content_full=cleaned_paper_content_str,
                paper_format="JSON", # 与规划阶段一致
                latex_content_full=latex_content_str, # 传递已加载的LaTeX内容
                # 中文注释：传递规划阶段直接提取的文本内容
                planning_overview_content=overall_plan_content,
                architecture_design_content=architecture_design_content,
                logic_design_content=logic_design_content
                # 中文注释：同上，CodingAgent 也通过 config_yaml_path 加载配置，无需传递内容字符串
            )
            # generated_code_map 是一个字典，键是文件名，值是生成的代码字符串
            # 可以添加对生成代码的总结性日志
            if not generated_code_map:
                print("// 中文注释: 警告 - CodingAgent.run() 未返回任何代码或返回为空。")
            else:
                generated_files_count = sum(1 for code in generated_code_map.values() if code.strip()) # 计算实际生成了非空代码的文件数量
                print(f"// 中文注释: 编码阶段完成，为 {generated_files_count}/{len(generated_code_map)} 个文件生成了代码。")
        
        except Exception as e:
            print(f"// 中文注释: CodingAgent.run() 执行失败: {e}")
            raise # 中文注释：或者采取其他错误处理方式

        print(f"Final code generated in: {self.final_code_dir}")
        print(f"Coding artifacts (_coding.txt) saved in: {self.coding_artifacts_dir}")

        print("\nPaper2Code pipeline finished.")

# 中文注释：如果直接运行此脚本，可以添加一个简单的命令行接口或测试用例
if __name__ == '__main__':
    # 中文注释：这是一个示例用法，你需要根据实际情况修改路径和API密钥
    # 确保相关的Agent类 (JSONCleaner, PlanningAgent, AnalyzingAgent, CodingAgent, LLMClient) 及其方法已正确实现。
    
    # DUMMY FILES FOR TESTING (You'd have real files)
    EXAMPLE_PAPER_NAME = "example_paper"
    EXAMPLE_BASE_OUTPUT_DIR = "outputs"
    
    # 中文注释：创建虚拟的输入JSON文件，实际使用时应为真实文件路径
    dummy_paper_json_path = os.path.join(EXAMPLE_BASE_OUTPUT_DIR, f"{EXAMPLE_PAPER_NAME}_raw.json")
    ensure_dir_exists(EXAMPLE_BASE_OUTPUT_DIR)
    if not os.path.exists(dummy_paper_json_path):
        with open(dummy_paper_json_path, 'w') as f:
            # 中文注释：JSONCleaner期望移除的键作为示例
            f.write("{\"paper_id\": \"123\", \"metadata\": {}, \"abstract\": [], \"body_text\": []}")

    # 中文注释：从环境变量获取API KEY，或直接填入（不推荐）
    API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
    
    if API_KEY == "your_openai_api_key_here":
        print("警告: 请设置 OPENAI_API_KEY 环境变量或在代码中提供有效的API密钥。")
    else:
        pipeline = Pipeline(
            paper_name=EXAMPLE_PAPER_NAME,
            paper_json_path=dummy_paper_json_path, # 使用虚拟的JSON文件路径
            base_output_dir=os.path.join(EXAMPLE_BASE_OUTPUT_DIR, EXAMPLE_PAPER_NAME + "_output"),
            openai_api_key=API_KEY,
            # latex_zip_path="path/to/your/latex.zip" # 可选
            # openai_api_base="http://localhost:8000/v1" # 可选, 用于兼容接口
        )
        # pipeline.run() # 实际运行时取消注释
        print("Pipeline class defined. To run, create an instance and call .run() method with actual paths and API key.")
        print("Example dummy run is commented out. Ensure all agent classes and their methods are correctly implemented before running.") 