import argparse
import os
from src.pipeline import Pipeline
from src.utils import ensure_dir_exists


# 中文注释：主函数，用于解析命令行参数并启动处理流程。
def main():
    # 中文注释：创建命令行参数解析器。
    parser = argparse.ArgumentParser(description="Paper2Code: 将科研论文转换为代码库。")

    # 中文注释：定义命令行参数。
    parser.add_argument(
        "--paper_name",
        default="Medagents",
        type=str,
        required=False,
        help="论文的名称 (例如：my_awesome_paper)，将用于创建输出子目录和命名文件。",
    )
    parser.add_argument(
        "--paper_json_path",
        default="./examples/medagents/medagents_pdf.pdf",
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
        default="./examples/medagents/arXiv-2311.10537v4.tar.gz",
        type=str,
        help="(可选) 论文的LaTeX源文件压缩包路径。",
    )
    parser.add_argument(
        "--openai_api_key",
        default="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",
        type=str,
        help="(可选) OpenAI API密钥。如果未提供，将尝试从环境变量 OPENAI_API_KEY 读取。",
    )
    parser.add_argument(
        "--openai_api_base",
        default="https://openrouter.ai/api/v1",
        type=str,
        help="(可选) OpenAI API的基础URL (例如：http://localhost:8000/v1)，用于兼容接口。",
    )
    parser.add_argument(
        "--llm_model_name",
        default="google/gemini-2.5-flash-preview",
        type=str,
        help="(可选) 使用的LLM模型名称。默认为 gpt-4-turbo。",
    )
    parser.add_argument(
        "--llm_temperature",
        default=0.7,
        type=float,
        help="(可选) LLM的temperature参数。默认为0.7。",
    )

    # 中文注释：解析命令行参数。
    args = parser.parse_args()

    # 中文注释：获取OpenAI API密钥，优先从命令行参数获取，其次从环境变量获取。
    api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "错误：未提供OpenAI API密钥。请通过 --openai_api_key 参数或 OPENAI_API_KEY 环境变量提供。"
        )
        return

    # 中文注释：构建针对当前论文的特定输出目录路径。
    # 例如：./outputs/my_awesome_paper_output
    paper_specific_output_dir = os.path.join(
        args.base_output_dir, f"{args.paper_name}_output"
    )
    ensure_dir_exists(paper_specific_output_dir)  # 确保基础的论文输出目录存在

    # 中文注释：实例化Pipeline并运行。
    print(f"初始化 Paper2Code Pipeline...")
    print(f"论文名称: {args.paper_name}")
    print(f"输入JSON路径: {args.paper_json_path}")
    print(f"输出根目录: {paper_specific_output_dir}")
    if args.latex_zip_path:
        print(f"LaTeX路径: {args.latex_zip_path}")
    if args.openai_api_base:
        print(f"OpenAI API Base URL: {args.openai_api_base}")
    print(f"LLM 模型: {args.llm_model_name}")
    print(f"LLM Temperature: {args.llm_temperature}")

    pipeline = Pipeline(
        paper_name=args.paper_name,
        paper_json_path=args.paper_json_path,
        base_output_dir=paper_specific_output_dir,  # 使用为这篇论文创建的特定输出目录
        openai_api_key=api_key,
        llm_model_name=args.llm_model_name,
        latex_zip_path=args.latex_zip_path,
        llm_temperature=args.llm_temperature,
        openai_api_base=args.openai_api_base,
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
