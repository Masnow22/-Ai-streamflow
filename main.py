import urllib.parse
import feedparser
import os
import json
import requests
import google.generativeai as genai
import datetime
import time
import openai
from openai import OpenAI

# --- 安全配置区 ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK")
DB_FILE = "read_papers.json"
TOPIC = "(cat:cs.AI OR cat:cs.CV OR cat:cs.LG)"

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

def get_ai_summary(title, summary):
    prompt = f"""
    你是一个专业的科研领路人。请阅读以下论文并进行筛选：
    标题：{title}
    摘要：{summary}

    筛选准则：
    1. 优先总结具有创新性、突破性，或来自知名机构（如 OpenAI, Google, Meta, DeepMind, 斯坦福等）的论文。
    2. 如果论文属于普通的增量研究、综述或质量平平，请仅回复“SKIP”四个字母。

    总结格式：
    0. 【原文标题与摘要概括】
    1. 【核心贡献】
    2. 【大白话启发】
    3. 【名词解释】
    注意：0-2不超过400字。
    """

    # --- 统一返回格式：(内容, 模型名) ---
    try:
        print(f"🤖 Gemini 正在评估: {title[:30]}...")
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('models/gemma-3-27b-it')
        response = model.generate_content(prompt)
        return response.text.strip(), "Gemma-3-27b"
    except Exception as e:
        print(f"⚠️ Gemini 报错: {e}，尝试切换 DeepSeek...")
        
        if DEEPSEEK_KEY:
            try:
                client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的学术论文评审助手。"},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content.strip(), "DeepSeek-V3"
            except Exception as ds_e:
                print(f"❌ 全部 AI 失败: {ds_e}")
                return "ERROR", "None"
        return "ERROR", "None"

def fetch_and_summarize():
    if not GEMINI_KEY:
        print("错误: 请先配置环境变量")
        return

    # 1. 获取数据
    
    encoded_topic = urllib.parse.quote(TOPIC)
    api_url = f"http://export.arxiv.org/api/query?search_query={encoded_topic}&max_results=15&sortBy=submittedDate&sortOrder=descending"
    print(f"正在抓取 {TOPIC} 的最新内容...")
    feed = feedparser.parse(api_url)
    
    if not feed.entries:
        print("暂时没抓到数据。")
        return

    # 2. 确定时间
    now_bj = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    report_type = "🌅 AI 论文早报" if 6 <= now_bj.hour <= 15 else "🌙 AI 论文晚报"

    # 3. 处理论文
    read_papers = load_read_papers()
    new_paper_count = 0 
    processed_count = 0

    print("-" * 30)
    for entry in feed.entries:
        if entry.id in read_papers:
            continue 
        
        processed_count += 1
        if processed_count > 1:
            print(f"⏳ 冷却 10 秒...")
            time.sleep(10)

        # 【核心修正】：一次调用，同时获取结果和模型名
        result, model_name = get_ai_summary(entry.title, entry.summary.replace('\n', ' '))
        
        if result == "SKIP":
            print(f"🍃 跳过低相关性论文: {entry.title[:30]}...")
            save_read_paper(entry.id)
            continue
        
        if result == "ERROR":
            print(f"❌ 处理失败，跳过")
            continue

        # 4. 推送
        new_paper_count += 1
        # 修正变量名 rfooter -> footer
        footer = f"\n\n---\n> 🤖 **AI 署名**：本文由 {model_name} 自动总结生成"
        report_content = f"### {report_type} (#{new_paper_count})\n\n{result}{footer}\n\n🔗 [查看 ArXiv 原文]({entry.link})"
        
        send_to_wechat(report_content)
        save_read_paper(entry.id)
        print(f"✅ 已推送: {entry.title[:30]}")
        print("-" * 30)

    if new_paper_count == 0:
        print(f"☕ {report_type}: 暂时没有符合筛选标准的新论文。")

if __name__ == "__main__":
    fetch_and_summarize()
