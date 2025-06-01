import os
import json
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from user import get_finnews_info_camel, finnews_agent
from search import FinGenerater
from user_preferences import user_prefs

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'storage'
def generate_html_report(report_data: dict) -> str:
    """从报告数据生成专业HTML内容，增强健壮性处理"""
    try:
        # 安全获取数据字段，提供默认值
        year = report_data.get('year', '未知年份')
        area = report_data.get('area', '未知地区')
        
        # 处理图片
        image_url = report_data.get('area_image', '/static/images/other.png') 
        
        # 处理新闻数据
        finance_news = report_data.get('finance_news', [])
        if not isinstance(finance_news, list):
            finance_news = []

        # 构建HTML结构
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{year}年{area}财经事件</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{
            background-color: #f8f9fa; /* 浅灰色背景 */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
        }}
        .report-header {{
            background: linear-gradient(135deg, #1a3a5f, #2c5282); /* 深蓝渐变 */
            color: #fff; /* 白色文字 */
            border-radius: 0;
            padding: 2.5rem 0;
            margin-bottom: 2rem;
        }}
        .flag-container {{
            width: 120px;
            height: 80px;
            margin: 0 auto 1rem;
            border: 1px solid #e0e6ed; /* 浅灰色边框 */
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #fff;
        }}
        .flag-container img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
        .news-card {{
            transition: transform 0.3s, box-shadow 0.3s;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 1.5rem;
            border: 1px solid #e0e6ed; /* 浅灰色边框 */
            background-color: #fff;
        }}
        .news-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
        }}
        .knowledge-badge {{
            background-color: #edf2f7; /* 浅灰色背景 */
            color: #2d3748; /* 深灰色文字 */
            border-radius: 4px;
            padding: 5px 12px;
            margin: 5px 5px 5px 0;
            display: inline-block;
            font-size: 0.85rem;
            border-left: 3px solid #3182ce; /* 左侧蓝色装饰线 */
        }}
        .footer {{
            background-color: #1a202c; /* 深灰色背景 */
            color: #cbd5e0; /* 浅灰色文字 */
            padding: 2rem 0;
            margin-top: 3rem;
        }}
        .timestamp {{
            font-size: 0.85rem;
            color: #718096;
            text-align: right;
            margin-top: 2rem;
        }}
        .report-content {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
            border: 1px solid #e2e8f0;
        }}
        .knowledge-section {{
            background-color: #f7fafc; /* 非常浅的灰色背景 */
            border-radius: 8px;
            padding: 1.25rem;
            margin-top: 1.25rem;
            border: 1px solid #e2e8f0;
        }}
        .news-title {{
            border-bottom: 1px solid #e2e8f0; /* 浅灰色下划线 */
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            color: #2b6cb0; /* 蓝色标题 */
            font-weight: 600;
        }}
        .card-header {{
            background-color: #ebf4ff !important; /* 浅蓝色背景 */
            color: #2b6cb0 !important; /* 蓝色文字 */
            border-bottom: 1px solid #c3dafe;
            font-weight: 600;
        }}
        .section-divider {{
            height: 1px;
            background: linear-gradient(to right, rgba(0,0,0,0), #e2e8f0, rgba(0,0,0,0));
            margin: 2rem 0;
        }}
    </style>
</head>
<body>
    <div class="report-header text-center">
        <div class="container">
            <h1 class="display-5 fw-bold mb-3"><i class="fas fa-chart-line me-2"></i>{year}年{area}财经事件</h1>
            <div class="flag-container">
                {f'<img src="{image_url}" alt="{area}图片">' if image_url else '<i class="fas fa-flag fa-3x" style="color:#a0aec0;"></i>'}
            </div>
            <p class="lead mt-2">财经事件 · 鉴往知来</p>
        </div>
    </div>
    
    <div class="container">
        <div class="row">
            <div class="col-lg-10 mx-auto">
                <div class="report-content">
        """
        
        # 添加新闻条目
        for idx, news in enumerate(finance_news, 1):
            title = news.get('title', f'财经新闻 #{idx}')
            content = news.get('content', '暂无详细内容')
            knowledge_points = news.get('knowledge', [])
            
            html += f"""
            <div class="card news-card">
                <div class="card-header">
                    <h3 class="h5 mb-0"><i class="fas fa-newspaper me-2"></i>{title}</h3>
                </div>
                <div class="card-body">
                    <p class="card-text">{content}</p>
                    
                    <div class="knowledge-section">
                        <h4 class="news-title"><i class="fas fa-lightbulb me-2"></i>金融知识点分析</h4>
                        <div class="d-flex flex-wrap mt-3">
            """
            
            # 添加知识点
            if knowledge_points and isinstance(knowledge_points, list):
                for point in knowledge_points:
                    concept = point.get('concept', '金融概念')
                    explanation = point.get('explanation', '暂无解释')
                    html += f"""
                    <div class="knowledge-badge">
                        <strong>{concept}:</strong> {explanation}
                    </div>
                    """
            else:
                html += """
                <div class="alert alert-light w-100">
                    暂无相关金融知识点分析
                </div>
                """
            
            html += """
                        </div>
                    </div>
                </div>
            </div>
            """

        # 添加页脚
        html += f"""
                </div>
            </div>
        </div>
        
        <div class="timestamp">
            报告生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    
    <div class="footer">
        <div class="container text-center">
            <p class="mb-0">© {time.strftime('%Y')} ROBIN财经新闻 | DeepSeek-V3 API</p>
            <p class="mb-0">数据来源: 全球财经报道聚合</p>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        """
        
        return html
    
    except Exception as e:
        # 生成错误报告页面
        error_html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>报告生成错误</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container py-5">
                <div class="alert alert-danger">
                    <h2>报告生成失败</h2>
                    <p>错误信息: {str(e)}</p>
                    <p>请检查输入数据格式是否正确</p>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html

@app.route('/')
def index():
    """渲染前端页面"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_input():
    """处理用户输入并生成报告"""
    user_input = request.json.get('input', '').strip()
    
    if not user_input:
        return jsonify({
            "status": "error",
            "message": "请输入查询内容"
        })
    
    # 步骤1: 提取关键信息
    info = get_finnews_info_camel(user_input, finnews_agent)
    
    # 步骤2: 检查信息完整性
    if info.get('need_more_info', True):
        return jsonify({
            "status": "need_more_info",
            "response": info.get('response', '请补充年份和国家信息')
        })
    
    # 步骤3: 生成财经报告
    try:
        year = int(info['year'])
        area = info['area']
        
        # 更新用户偏好
        user_prefs.update_area_preference(area)
        user_prefs.update_year_preference(year)

        # 创建报告生成器
        generator = FinGenerater(year=year, area=area)
        report_data = generator.generate_finance_report()
        
        # 生成HTML内容
        html_content = generate_html_report(report_data)
        
        # 保存HTML文件
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = f"{year}_{area}_财经报告_{int(time.time())}.html"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return jsonify({
            "status": "success",
            "preview": info.get('response', '报告生成成功'),
            "report_url": f"/reports/{filename}"
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"报告生成失败: {str(e)}"
        })

@app.route('/reports/<filename>')
def serve_report(filename):
    """提供生成的报告文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # 确保存储目录存在
    os.makedirs('storage', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)