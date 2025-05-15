import argparse
import os
from src.pipeline import Pipeline
from src.utils import ensure_dir_exists
from dotenv import load_dotenv

load_dotenv()

# 中文注释：主函数，用于解析命令行参数并启动处理流程。
def main():
    # 中文注释：在所有其他操作之前，直接打印从环境中获取的 PAPER_JSON_PATH 的值
    print(f"[DEBUG] main.py - os.getenv('PAPER_JSON_PATH') after load_dotenv(): '{os.getenv('PAPER_JSON_PATH')}'")
    # 中文注释：创建命令行参数解析器。
    parser = argparse.ArgumentParser(description="Paper2Code: 将科研论文转换为代码库。")

    # 中文注释：定义命令行参数。
    parser.add_argument(
        "--paper_name",
        # default="Medagents",
        type=str,
        required=False,
        help="论文的名称 (例如：my_awesome_paper)，将用于创建输出子目录和命名文件。",
    )
    parser.add_argument(
        "--paper_json_path",
        # default="./examples/medagents/medagents_pdf.pdf",
        type=str,
        required=False,
        help="从PDF转换得到的原始JSON文件的路径。",
    )
    parser.add_argument(
        "--base_output_dir",
        type=str,
        default="./outputs",
        help="所有输出文件的基础目录。默认为 ./outputs。",
    )
    parser.add_argument(
        "--latex_zip_path",
        # default="./examples/medagents/arXiv-2311.10537v4.tar.gz",
        type=str,
        help="(可选) 论文的LaTeX源文件压缩包路径。",
    )
    parser.add_argument(
        "--openai_api_key",
        # default="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",
        type=str,
        help="(可选) OpenAI API密钥。如果未提供，将尝试从环境变量 OPENAI_API_KEY 读取。",
    )
    parser.add_argument(
        "--openai_api_base",
        # default="https://openrouter.ai/api/v1",
        type=str,
        help="(可选) OpenAI API的基础URL (例如：http://localhost:8000/v1)，用于兼容接口。",
    )
    parser.add_argument(
        "--llm_model_name",
        # default="google/gemini-2.5-flash-preview",
        type=str,
        help="(可选) 使用的LLM模型名称。默认为 gpt-4-turbo。",
    )
    parser.add_argument(
        "--llm_temperature",
        # default=0.7,
        type=float,
        help="(可选) LLM的temperature参数。默认为0.7。",
    )

    # 中文注释：解析命令行参数。
    args = parser.parse_args()

    # 中文注释：获取配置，优先顺序：命令行参数 > 环境变量 (.env) > argparse默认值

    # --- paper_name ---
    # 中文注释：处理 paper_name
    paper_name_cmd = args.paper_name if args.paper_name != parser.get_default("paper_name") else None
    paper_name_env = os.getenv("PAPER_NAME")
    paper_name = paper_name_cmd or paper_name_env or parser.get_default("paper_name")
    # 中文注释：检查 paper_name 是否已提供 (通过命令行或环境变量)
    if not paper_name:
        parser.error("参数 --paper_name (或环境变量 PAPER_NAME) 是必需的。")

    # --- paper_json_path ---
    # 中文注释：处理 paper_json_path
    paper_json_path_cmd = args.paper_json_path if args.paper_json_path != parser.get_default("paper_json_path") else None
    paper_json_path_env = os.getenv("PAPER_JSON_PATH")
    paper_json_path = paper_json_path_cmd or paper_json_path_env or parser.get_default("paper_json_path")
    # 中文注释：检查 paper_json_path 是否已提供
    if not paper_json_path:
        parser.error("参数 --paper_json_path (或环境变量 PAPER_JSON_PATH) 是必需的。")

    # --- base_output_dir ---
    # 中文注释：处理 base_output_dir
    base_output_dir_cmd = args.base_output_dir if args.base_output_dir != parser.get_default("base_output_dir") else None
    base_output_dir_env = os.getenv("BASE_OUTPUT_DIR")
    base_output_dir = base_output_dir_cmd or base_output_dir_env or parser.get_default("base_output_dir")
    
    # --- latex_zip_path ---
    # 中文注释：处理 latex_zip_path
    # 中文注释：原先的逻辑未能正确处理环境变量优先于 argparse 默认值的情况。
    # 中文注释：注意：argparse 定义中 latex_zip_path 有一个默认字符串值。
    latex_zip_path_cmd = args.latex_zip_path if args.latex_zip_path != parser.get_default("latex_zip_path") else None
    latex_zip_path_env = os.getenv("LATEX_ZIP_PATH")
    # 中文注释：如果用户注释掉了 argparse 中的 default，get_default 会返回 None
    latex_zip_path = latex_zip_path_cmd or latex_zip_path_env or parser.get_default("latex_zip_path") 
    
    # API密钥获取逻辑需要调整
    # 1. 命令行参数 (args.openai_api_key)
    # 2. 环境变量 (os.getenv("OPENAI_API_KEY")) - .env 文件会设置这个
    # 3. Argparse 默认值 (不推荐用于敏感信息，但您代码中有)
    
    api_key_cmd = args.openai_api_key if args.openai_api_key != parser.get_default("openai_api_key") else None
    api_key = api_key_cmd or os.getenv("OPENAI_API_KEY") or parser.get_default("openai_api_key")
    
    if not api_key:
        print("错误：未提供OpenAI API密钥。请通过命令行参数、.env 文件或 OPENAI_API_KEY 环境变量提供。")
        return

    # 中文注释：获取 OpenAI API Base URL
    openai_api_base_cmd = args.openai_api_base if args.openai_api_base != parser.get_default("openai_api_base") else None
    openai_api_base_env = os.getenv("OPENAI_API_BASE")
    openai_api_base_default_from_parser = parser.get_default("openai_api_base") #会是None如果用户注释掉了
    openai_api_base = openai_api_base_cmd or openai_api_base_env or openai_api_base_default_from_parser
    # 中文注释：如果解析后 openai_api_base 仍为 None, 应用应用级默认值
    if openai_api_base is None:
        openai_api_base = "https://openrouter.ai/api/v1" # 应用级默认值

    # 中文注释：获取 LLM 模型名称
    llm_model_name_cmd = args.llm_model_name if args.llm_model_name != parser.get_default("llm_model_name") else None
    llm_model_name_env = os.getenv("LLM_MODEL_NAME")
    llm_model_name_default_from_parser = parser.get_default("llm_model_name") #会是None如果用户注释掉了
    llm_model_name = llm_model_name_cmd or llm_model_name_env or llm_model_name_default_from_parser
    # 中文注释：如果解析后 llm_model_name 仍为 None, 应用应用级默认值
    if llm_model_name is None:
        llm_model_name = "google/gemini-2.5-flash-preview" # 应用级默认值

    # 中文注释：获取 LLM Temperature
    llm_temperature_cmd = args.llm_temperature if args.llm_temperature != parser.get_default("llm_temperature") else None
    llm_temperature_str_env = os.getenv("LLM_TEMPERATURE")
    llm_temperature_env = float(llm_temperature_str_env) if llm_temperature_str_env else None
    llm_temperature_default_from_parser = parser.get_default("llm_temperature") #会是None如果用户注释掉了
    llm_temperature = llm_temperature_cmd or llm_temperature_env or llm_temperature_default_from_parser
    # 中文注释：如果解析后 llm_temperature 仍为 None, 应用应用级默认值
    if llm_temperature is None:
        llm_temperature = 0.7 # 应用级默认值
    elif not isinstance(llm_temperature, float):
        llm_temperature = float(llm_temperature) #确保是 float

    # 中文注释：构建针对当前论文的特定输出目录路径。
    # 例如：./outputs/my_awesome_paper_output
    paper_specific_output_dir = os.path.join(
        base_output_dir, f"{paper_name}_output"
    )
    ensure_dir_exists(paper_specific_output_dir)  # 确保基础的论文输出目录存在

    # 中文注释：实例化Pipeline并运行。
    print(f"初始化 Paper2Code Pipeline...")
    print(f"论文名称: {paper_name}")
    print(f"输入JSON路径: {paper_json_path}")
    print(f"输出根目录: {paper_specific_output_dir}")
    if latex_zip_path:
        print(f"LaTeX路径: {latex_zip_path}")
    if openai_api_base:
        print(f"OpenAI API Base URL: {openai_api_base}")
    print(f"LLM 模型: {llm_model_name}")
    print(f"LLM Temperature: {llm_temperature}")

    pipeline = Pipeline(
        paper_name=paper_name,
        paper_json_path=paper_json_path,
        base_output_dir=paper_specific_output_dir,  # 使用为这篇论文创建的特定输出目录
        openai_api_key=api_key,
        llm_model_name=llm_model_name,
        latex_zip_path=latex_zip_path,
        llm_temperature=float(llm_temperature),
        openai_api_base=openai_api_base,
    )

    try:
        # 中文注释：执行整个流程。
        pipeline.run()
        print(f"处理完成！所有输出已保存到: {paper_specific_output_dir}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        # 在实际应用中，这里可能需要更详细的错误处理和日志记录
        import traceback

        traceback.print_exc()


# 中文注释：确保在脚本作为主模块运行时执行main函数。
if __name__ == "__main__":
    main()
