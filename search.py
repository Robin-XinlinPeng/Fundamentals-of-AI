from camel.toolkits import SearchToolkit
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.loaders import Firecrawl
from typing import List, Dict, Any
from camel.toolkits import FunctionTool
from camel.configs import ChatGPTConfig
from flask import Flask, request, jsonify
import json
import os
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
import jieba
load_dotenv()

api_key = os.getenv("API_KEY")
url = os.getenv('URL')
model_type = os.getenv('MODEL_TYPE')
temperature = float(os.getenv('TEMPERATURE'))
top_p = float(os.getenv('TOP_P'))

# 创建查找图片的tool函数,该函数根据国家名称返回对应的图片URL
country_image_map = {
    "美国": "/static/images/america.png",
    "澳大利亚": "/static/images/australia.png",
    "中国": "/static/images/china.png",
    "英国": "/static/images/england.png", 
    "法国": "/static/images/france.png",
    "德国": "/static/images/germany.png",
    "印度": "/static/images/india.png",
    "日本": "/static/images/japan.png",
    "其他": "/static/images/other.png",
    "新加坡": "/static/images/singapore.png",
    "瑞士": "/static/images/switzerland.png"
}

# 定义一个函数来获取国家对应的图片URL
def get_country_image_url(country: str) -> str:
    return country_image_map.get(country, country_image_map["其他"])

# 定义一个金融概念检索增强的类
class ConceptRetriever:
    def __init__(self, concepts_file="concepts.json"):
        # 加载金融概念库
        current_dir = os.path.dirname(os.path.abspath(__file__))
        concepts_path = os.path.join(current_dir, concepts_file)
        
        with open(concepts_path, 'r', encoding='utf-8') as f:
            concepts_data = json.load(f)
        
        # 准备检索数据
        self.concepts = concepts_data["concepts"]
        self.tokenized_docs = []  # 存储分词后的文档
        
        # 为每个概念创建检索文档并进行中文分词
        for concept in self.concepts:
            # 组合名称、别名和定义作为文档内容
            doc_text = f"{concept['name']} {' '.join(concept['aliases'])} {concept['definition']}"
            # 使用jieba进行中文分词
            tokens = list(jieba.cut(doc_text))
            self.tokenized_docs.append(tokens)
        
        # 初始化BM25检索器
        self.bm25 = BM25Okapi(self.tokenized_docs)
    
    def retrieve_concepts(self, query: str, top_k: int = 3) -> list:
        """
        检索与查询最相关的金融概念
        :param query: 查询文本
        :param top_k: 返回的概念数量
        :return: 相关概念列表
        """
        # 对查询进行中文分词
        tokenized_query = list(jieba.cut(query))
        
        # 执行检索并获取分数
        scores = self.bm25.get_scores(tokenized_query)
        
        # 获取分数最高的top_k个索引
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        # 获取对应的概念对象
        retrieved_concepts = []
        for idx in top_indices:
            concept = self.concepts[idx]
            concept["retrieval_score"] = scores[idx]
            retrieved_concepts.append(concept)
        
        return retrieved_concepts

class FinGenerater:
    def __init__(self, year: int, area: str):
        
        #定义地点和时间，设置默认值
        self.year = year
        self.area = area
        self.res = None        
        self.concept_retriever = ConceptRetriever()

        # 初始化模型和智能体
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type=model_type,
            url=url,
            api_key=api_key,
            model_config_dict=ChatGPTConfig(temperature=temperature,stream=True,max_tokens=8192,top_p=top_p).as_dict(),
        )



        # 新闻搜索和重排序agent
        self.news_agent = ChatAgent(
            system_message="你是一个财经新闻筛选专家，要找出和{year}年{area}财经新闻最相关的2条结果，保存他们的标题、内容，严格以json格式输出",
            model=self.model,
            output_language='中文'
        )
        
        # 修改金融知识点提取agent的系统提示
        self.knowledge_agent = ChatAgent(
            system_message=(
                "你是一个金融经济专家，要根据财经新闻内容{content}提取出3个金融经济知识点，并做简单解释。"
                "系统会提供一些相关概念供参考，但请确保你至少找到了一个知识点，解释准确且符合上下文。"
                "严格以json格式输出"
            ),
            model=self.model,
            output_language='中文'
        )
    def extract_json_from_response(self, response_content: str) -> List[Dict[str, Any]]:
        """从LLM响应中提取JSON内容"""
        try:
            # 尝试直接解析整个响应内容
            try:
                parsed = json.loads(response_content)
                if isinstance(parsed, dict):
                    print(f"直接解析的JSON内容: {parsed}")
                    return [parsed]
                elif isinstance(parsed, list):
                    print(f"直接解析的JSON列表内容: {parsed}")
                    return parsed
            except json.JSONDecodeError:
                pass
            
            # 如果直接解析失败，尝试查找代码块
            start = response_content.find('```json\n') + 8
            if start == 7:  # 没找到的情况
                start = response_content.find('```') + 3
                if start == 2:  # 还是没找到
                    print("未找到JSON内容的标记")
                    return []
            
            end = response_content.find('\n```', start)
            if end == -1:
                end = response_content.find('```', start)
                if end == -1:
                    print("未找到JSON内容的结束标记")
                    return []
            
            json_str = response_content[start:end].strip()
            print(f"提取的JSON字符串: {json_str}")
            
            # 解析 JSON 字符串
            parsed = json.loads(json_str)
            
            if isinstance(parsed, dict):
                return [parsed]
            elif isinstance(parsed, list):
                return parsed
            else:
                print("未找到预期的JSON结构")
                return []
            
        except json.JSONDecodeError as e:
            print(f"解析JSON失败: {str(e)}")
            print(f"原始内容: {response_content}")
            return []
        except Exception as e:
            print(f"发生错误: {str(e)}")
            return []
        
    def get_area_image_url(self, area: str) -> Dict[str, Any]:
        """直接获取指定国家的图片URL"""
        try:
            return get_country_image_url(area)
            
        except Exception as e:
            print(f"获取地区图片失败: {str(e)}")
            return country_image_map["其他"]
            
        
    def search_finance_news(self) -> Dict[str, Any]:
        """搜索财经新闻并提取关键信息"""
        try:
            
            prompt = f"""
            请筛选出最相关的2条{self.year}年{self.area}财经新闻，
            每条新闻包含标题、简要内容：
            
            【输出格式要求】
            {{
                "news": [
                    {{
                        "title": "新闻标题",
                        "content": "新闻简要内容",
                    
                    }}
                ]
            }}
            """
            
            response = self.news_agent.step(prompt)
            news_data = self.extract_json_from_response(response.msgs[0].content)
            
            return news_data[0] if news_data else {"news": []}
            
        except Exception as e:
            print(f"财经新闻搜索失败: {str(e)}")
            return {"news": []}

    def extract_finance_knowledge(self, content: str) -> Dict[str, str]:
        """从新闻内容中提取金融经济知识点（增强版）"""
        try:
            # 第一步：检索相关概念
            related_concepts = self.concept_retriever.retrieve_concepts(content, top_k=5)
            
            # 格式化相关概念信息
            concept_references = "\n".join(
                [f"- {concept['name']}: {concept['definition']}" 
                 for concept in related_concepts]
            )
            
            # 构建增强提示
            prompt = f"""
            从以下财经新闻内容中提取最重要的2-4个金融经济知识点，并做简单解释。至少有一个概念解释！！不能没有知识点！！：
            {content}
            
            【系统提供的相关概念参考】
            {concept_references}
            
            【输出格式要求】
            {{
                "knowledge": [
                    {{
                        "concept": "金融经济概念名称",
                        "explanation": "概念解释说明"
                    }},
                    {{
                        "concept": "金融经济概念名称",
                        "explanation": "概念解释说明"
                    }}
                ]
            }}
            """
            
            response = self.knowledge_agent.step(prompt)
            knowledge_data = self.extract_json_from_response(response.msgs[0].content)
            
            return knowledge_data[0] if knowledge_data else {"knowledge": {"concept": "", "explanation": ""}}
            
        except Exception as e:
            print(f"金融知识点提取失败: {str(e)}")
            return {"knowledge": {"concept": "", "explanation": ""}}

    def generate_finance_report(self) -> Dict[str, Any]:
        """生成完整的财经报告"""
        # 获取地区图片URL
        area_image_url = self.get_area_image_url("{}".format(self.area))
        
        # 搜索财经新闻
        news_result = self.search_finance_news()
        news_list = news_result.get("news", [])
        
        # 为每条新闻提取金融知识点
        processed_news = []
        for news in news_list:
            knowledge = self.extract_finance_knowledge(news["content"])
            processed_news.append({
                "title": news["title"],
                "content": news["content"],
                "knowledge": knowledge["knowledge"]
            })
        
        # 构建最终结果
        result = {
            "year": self.year,
            "area": self.area,
            "area_image": area_image_url,
            "finance_news": processed_news
        }
        
        # 保存结果到JSON文件
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(current_dir, "storage")
            os.makedirs(storage_dir, exist_ok=True)
            
            filename = os.path.join(storage_dir, f"{self.year}_{self.area}_财经新闻.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
            print(f"财经新闻报告已保存到文件：{filename}")
        except Exception as e:
            print(f"保存JSON文件时出错: {str(e)}")
        
        return result



