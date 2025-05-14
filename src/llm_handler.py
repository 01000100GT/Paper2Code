import os
from openai import OpenAI
# // 中文注释: 导入 typing 用于类型提示。
from typing import List, Dict, Any, Optional

# // 中文注释: 未来可以从 utils 或 config 中加载成本数据。
# from .utils import load_accumulated_cost, save_accumulated_cost, print_log_cost

class LLMClient:
    """
    // 中文注释: LLMClient 类封装了与LLM API交互的逻辑。
    // 支持 OpenAI API，并可以扩展以支持其他LLM提供商。
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo", temperature: float = 0.7, api_base: Optional[str] = None):
        """
        // 中文注释: 初始化LLMClient。
        // api_key: OpenAI API密钥。如果为None，则尝试从环境变量OPENAI_API_KEY读取。
        // model_name: 默认使用的模型名称。
        // temperature: 默认使用的temperature。
        // api_base: (可选) API的基础URL，用于兼容OpenAI的接口。
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("// 中文注释: API密钥未提供。请通过构造函数参数或OPENAI_API_KEY环境变量设置。")
        
        self.model_name = model_name
        self.temperature = temperature
        self.api_base = api_base # // 中文注释: 存储api_base

        # // 中文注释: 在构造函数中初始化OpenAI客户端，以便正确设置api_base
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base # // 中文注释: 如果api_base为None，则openai库会使用默认的OpenAI URL
            )
        except Exception as e:
            raise ValueError(f"// 中文注释: 初始化OpenAI客户端失败: {e}")

    def call_llm(self, messages: List[Dict[str, str]], model_version: Optional[str] = None, **kwargs) -> Any:
        """
        // 中文注释: 调用LLM API。
        // messages: 发送给LLM的消息列表。
        // model_version: (可选) 要使用的特定模型版本，如果为None，则使用实例的默认model_name。
        // kwargs: 其他传递给OpenAI API的参数 (例如 temperature, max_tokens)。
        // 返回: LLM的响应对象。
        """
        model_to_use = model_version if model_version else self.model_name
        
        # // 中文注释: 从kwargs获取temperature，如果未提供，则使用实例的默认temperature
        current_temperature = kwargs.pop('temperature', self.temperature)

        try:
            # // 中文注释: 使用 self.client 进行API调用
            completion = self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=current_temperature,
                **kwargs
            )
            return completion
        except openai.APIConnectionError as e:
            print(f"// 中文注释: OpenAI API请求失败：无法连接到服务器。URL: {self.api_base or '默认OpenAI URL'}。错误: {e}")
            raise
        except openai.RateLimitError as e:
            print(f"// 中文注释: OpenAI API请求超过速率限制。错误: {e}")
            raise
        except openai.APIStatusError as e:
            print(f"// 中文注释: OpenAI API返回了非200的状态码。状态码: {e.status_code}。响应: {e.response}")
            raise
        except Exception as e:
            print(f"// 中文注释: 调用LLM API时发生未知错误: {e}")
            raise

# // 中文注释: 示例用法（用于测试）
if __name__ == '__main__':
    # // 中文注释: 运行此示例前，请确保设置了OPENAI_API_KEY环境变量，或者在下面提供api_key。
    # // 如果要测试自定义api_base，请取消注释并设置正确的URL。
    # custom_api_base = "http://localhost:8000/v1" # 例如，本地vLLM或Llama.cpp服务器的地址
    
    try:
        print("// 中文注释: 尝试使用默认OpenAI设置初始化LLMClient...")
        # // 中文注释: 如果您没有OPENAI_API_KEY环境变量，请直接在此处提供: api_key="sk-yourkey"
        client_default = LLMClient(model_name="gpt-3.5-turbo") 
        # client_default = LLMClient(model_name="gpt-3.5-turbo", api_base=custom_api_base) # 测试自定义api_base
        
        example_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        print(f"// 中文注释: 使用模型 {client_default.model_name} 和 temperature {client_default.temperature} 调用LLM...")
        # response = client_default.call_llm(example_messages, temperature=0.5) # 可以在调用时覆盖temperature
        # print("// 中文注释: LLM响应:", response.choices[0].message.content)
        print("// 中文注释: 示例代码已注释掉，以防意外调用。取消注释以进行测试。")

    except ValueError as ve:
        print(f"// 中文注释: 初始化LLMClient时出错: {ve}")
    except Exception as e:
        print(f"// 中文注释: 示例执行期间发生错误: {e}")

    # // 中文注释: 示例用法（通常不会在这里直接运行）。
    # if __name__ == '__main__':
    #     # // 中文注释: 请确保设置了 OPENAI_API_KEY 环境变量。
    #     # try:
    #     #     llm_client = LLMClient(model_name="gpt-3.5-turbo", temperature=0.5) # // 中文注释: 示例中传递参数
    #     #     example_messages = [
    #     #         {"role": "system", "content": "You are a helpful assistant."},
    #     #         {"role": "user", "content": "Hello!"}
    #     #     ]
    #     #     # // 中文注释: 调用时不指定 model_version 和 temperature，将使用实例上存储的值
    #     #     response = llm_client.call_llm(example_messages) 
    #     #     print("// 中文注释: LLM 响应 (使用实例默认值):")
    #     #     print(response.choices[0].message.content)

    #     #     # // 中文注释: 调用时指定 model_version 和 temperature，将覆盖实例默认值
    #     #     response_override = llm_client.call_llm(example_messages, model_version="gpt-4", temperature=0.9)
    #     #     print("\n// 中文注释: LLM 响应 (使用调用时指定的值):")
    #     #     print(response_override.choices[0].message.content)

    #     # except ValueError as ve:
    #     #     print(ve)
    #     # except Exception as ex:
    #     #     print(f"// 中文注释: 发生错误: {ex}")
    pass 