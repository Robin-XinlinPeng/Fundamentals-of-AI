import os
import sys
import json
from typing import Optional
from flask import Flask, request, jsonify,Response

from dotenv import load_dotenv
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.agents import ChatAgent

load_dotenv()

api_key = os.getenv('API_KEY')
url = os.getenv('URL')
model_type = os.getenv('MODEL_TYPE')

SYSTEM_PROMPT = """
你是一个财经新闻助手。你的任务是从用户输入中提取财经事件的年份和国家信息，并根据提取结果决定是否需要用户补充信息。

# 输入处理规则
1. **年份提取**：
   - 识别四位数字年份（如2023/2024）
   - 若无年份信息，记为null
   
2. **国家提取**：
   - 识别标准国家名称（如中国/美国/日本）
   - 若包含多个国家，只取第一个
   - 若无国家信息，记为null

3. **need_more_info逻辑**：
   - 当year或area任一为null → true
   - 当year和area均不为null → false

# 输出规则
必须返回严格JSON格式：
{
  "year": 数字|null,
  "area": "国家字符串|null,
  "need_more_info": boolean,
  "response": "动态生成的提示文本"  // 新增规则见下方
}

## response字段生成规则
| 条件                     | response内容                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| 两者齐全时               | "信息在Robin的数据库中查询到啦，正在努力为您生成{year}年{area}财经播报~"     |
| 仅缺年份时               | "Robin还不知道您想获得哪个年份的{area}财经事件呢，请补充年份~"              |
| 仅缺国家时               | "Robin还不知道您想获得哪个国家的{year}年财经事件呢，请补充国家~"            |
| 两者都缺时               | "Robin需要您补充想查询的年份和国家信息哦~"                                  |

**注意**：response字段必须按上表动态生成，不可返回示例中的固定文本

# 处理示例
用户输入："我想了解2023年中国的经济情况"
→ {
    "year": 2023,
    "area": "中国",
    "need_more_info": false,
    "response": "信息在Robin的数据库中查询到啦，正在努力为您生成2023年中国财经播报~"
   }

用户输入："请告诉我去年的美国大事件"
→ {
    "year": null,  // 未明确年份
    "area": "美国",
    "need_more_info": true,
    "response": "Robin还不知道您想获得哪个年份的美国财经事件呢，请补充年份~"
   }

用户输入："2024年有哪些重要事件？"
→ {
    "year": 2024,
    "area": null,
    "need_more_info": true,
    "response": "Robin还不知道您想获得哪个国家的2024年财经事件呢，请补充国家~"
   }

用户输入："给我财经新闻"
→ {
    "year": null,
    "area": null,
    "need_more_info": true,
    "response": "Robin需要您补充想查询的年份和国家信息哦~"
   }
"""


def create_finnews_agent():
    deepseek_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        model_type=model_type,
        api_key=api_key,
        url=url,
        model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
    )

    agent = ChatAgent(
        system_message=SYSTEM_PROMPT,
        model=deepseek_model,
        message_window_size=10,
        output_language='Chinese'
    )
    return agent

finnews_agent = create_finnews_agent()

def get_finnews_info_camel(user_input: str, agent: ChatAgent) -> dict:
    try:
        response = agent.step(user_input)
        # 回到原始状态
        agent.reset()
        if not response or not response.msgs:
            raise ValueError("模型没有返回任何消息")
        json_output = response.msgs[0].content.strip().replace("```json", "").replace("```", "").strip()
        json_output = json.loads(json_output)
        json_output["query"] = user_input
        return json_output
    except json.JSONDecodeError:
        print("Error: 模型返回的不是有效的 JSON 格式。")
        return {
            'year': None,
            'area': None,
            'need_more_info': True,
            'query': user_input,
            'response': None
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            'year': None,
            'area': None,
            'need_more_info': True,
            'query': user_input,
            'response': None
        }
    
