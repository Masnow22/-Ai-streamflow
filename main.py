import feedparser
import os
import json
import requests
import google.generativeai as genai
import datetime
import time  # 必须引入时间库

# --- 安全配置区 ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK")
DB_FILE = "read_papers.json"
TOPIC = "cs.AI" 

def send_to_wechat(content):
    if not WECHAT_WEBHOOK:
        print("未检测到 Webhook，跳过推送")
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
        with open(DB_FILE, 'w') as f:
            json.dump(read_list[-100:], f)

# --- 主逻辑 ---
def fetch_and_summarize():
    if not GEMINI_KEY:
        print("错误: 请先配置 GEMINI_KEY 环境变量")
        return

    # 1. 获取数据
    api_url = f"http://export.arxiv.org/api/query?search_query=cat:{TOPIC}&max_results=10&sortBy=submittedDate"
    print(f"正在抓取 {TOPIC} 的最新内容...")
    feed = feedparser.parse(api_url)
    
    if not feed.entries:
        print("暂时没抓到数据。")
        return

    # 2. 确定当前推送类型 (北京时间)
    now_bj = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    report_type = "🌅 AI 论文早报" if 6 <= now_bj.hour <= 15 else "🌙 AI 论文晚报"

    # 3. 配置 AI
    genai.configure(api_key=GEMINI_KEY)
    # 单 Key 用户建议死守 gemini-1.5-flash，它的免费限额最慷慨
    model = genai.GenerativeModel('gemini-1.5-flash') 

    # 4. 加载记录
    read_papers = load_read_papers()
    new_paper_count = 0 

    print("-" * 30)
    for entry in feed.entries:
        if entry.id in read_papers:
            continue 
        
        new_paper_count += 1
        
        # --- 【单 Key 核心保护逻辑】 ---
        # 哪怕只有一篇新论文，我们也先等 20 秒，给 API 留出喘息空间
        print(f"⏳ 准备总结第 {new_paper_count} 篇... 正在执行 10 秒安全冷却...")
        time.sleep(10) 

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
            report_content = f"### {report_type} (#{new_paper_count})\n\n{response.text}\n\n🔗 [查看 ArXiv 原文]({entry.link})"
            
            print(f"📌 处理中: {title}")
            send_to_wechat(report_content)
            
            save_read_paper(entry.id)
            print(f"✅ 推送成功")
            print("-" * 30)
            
        except Exception as e:
            # 针对 429 报错的特殊处理
            if "429" in str(e):
                print("⚠️ 警告：单个 Key 已达限制，跳过剩余任务以保护账号。")
                break
            print(f"AI 总结出错: {e}")

    if new_paper_count == 0:
        print(f"☕ {report_type}: 今天没有新出的论文。")

if __name__ == "__main__":
    fetch_and_summarize()
