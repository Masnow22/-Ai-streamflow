import feedparser
import os
import json
import requests
import google.generativeai as genai

# --- 安全配置区 ---
# 从 GitHub Secrets 中读取，本地运行时建议在环境变量设置
GEMINI_KEY = os.getenv("GEMINI_KEY")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK")
DB_FILE = "read_papers.json"
TOPIC = "cs.AI" 

def send_to_wechat(content):
    if not WECHAT_WEBHOOK:
        print("未检测到 Webhook，跳过推送（仅在控制台显示）")
        return
    headers = {"Content-Type": "application/json"}
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content}
    }
    try:
        requests.post(WECHAT_WEBHOOK, json=payload, headers=headers)
    except Exception as e:
        print(f"推送微信失败: {e}")

# --- 核心工具函数 ---
def load_read_papers():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except: 
            return [] 
    return []

def save_read_paper(paper_id):
    read_list = load_read_papers()
    if paper_id not in read_list:
        read_list.append(paper_id)
        # 只保留最近 100 条记录
        with open(DB_FILE, 'w') as f:
            json.dump(read_list[-100:], f)

# --- 主逻辑 ---
def fetch_and_summarize():
    # 1. 检查 Key 是否存在
    if not GEMINI_KEY:
        print("错误: 请先配置 GEMINI_KEY 环境变量")
        return

    # 2. 获取数据
    api_url = f"http://export.arxiv.org/api/query?search_query=cat:{TOPIC}&max_results=5&sortBy=submittedDate"
    print(f"正在从 ArXiv 提取 {TOPIC} 方向的最新内容...")
    feed = feedparser.parse(api_url)
    
    if not feed.entries:
        print("暂时没抓到数据。")
        return

    # 3. 配置 AI
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('models/gemini-2.5-flash') 

    # 4. 加载记录
    read_papers = load_read_papers()
    new_paper_count = 0 

    print("-" * 30)
    for entry in feed.entries:
        # 【检查去重】
        if entry.id in read_papers:
            continue 
        
        new_paper_count += 1
        title = entry.title
        summary = entry.summary.replace('\n', ' ') 
        
        prompt = f"""
        你是一个专业的科研领路人。请阅读以下论文：
        标题：{title}
        摘要：{summary}

        请按以下格式输出：
        0. 【原文标题与摘要概括】：先列出原文Title，再用三句话概括这个Abstract。
        1. 【核心贡献】：用一句话说明它解决了什么。
        2. 【大白话启发】：它对我们的世界和本专业的大学生有什么实际意义？
        3. 【名词解释】：挑出文中5个最晦涩的专业术语，用最通俗的语言解释。

        注意：0、1、2总计不超过400字；3大约100字。请使用适合微信阅读的Markdown格式。
        """
        
        try:
            response = model.generate_content(prompt)
            
            # 拼接要发送的内容
            report_content = f"### 📊 AI 论文早报 (#{new_paper_count})\n\n{response.text}\n\n🔗 [查看 ArXiv 原文]({entry.link})"
            
            # 1. 打印到控制台
            print(f"📌 处理中: {title}")
            print(report_content)
            print("-" * 30)
            
            # 2. 推送到微信
            send_to_wechat(report_content)
            
            # 3. 记录已读
            save_read_paper(entry.id)
            
        except Exception as e:
            print(f"AI 总结出错: {e}")

    if new_paper_count == 0:
        print("☕ 今天没有新论文，休息一下吧！")
        # 如果需要没新论文也提醒，可以取消下面这行的注释
        # send_to_wechat("☕ 今天没有新论文更新，可以继续钻研之前的课题。")

if __name__ == "__main__":
    fetch_and_summarize()
