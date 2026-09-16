#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日产业情报晨报 V2 - 升级版
功能升级：
1. 实时金融数据源（A股/涨跌停/全球资产）
2. 多模型备份（Coze主用，火山引擎方舟备用）
3. 分层推送（30秒速览 + 完整详情）
4. 事件历史类比数据库
5. 图表可视化（情绪走势图）
6. 反馈优化机制
GitHub Actions 每天 8:30 (北京时间) 自动运行
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timezone, timedelta

# 导入金融数据模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from finance_data import get_all_finance_data, format_finance_data_for_prompt
    FINANCE_DATA_AVAILABLE = True
except ImportError:
    FINANCE_DATA_AVAILABLE = False
    print("警告: finance_data模块未找到，金融数据功能禁用")

# ============ 配置（从 GitHub Secrets 读取） ============
COZE_PAT = os.environ.get("COZE_PAT", "")
COZE_BOT_ID = os.environ.get("COZE_BOT_ID", "")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")
ARK_API_KEY = os.environ.get("ARK_API_KEY", "")  # 火山引擎方舟API Key（备用模型）

COZE_API_BASE = "https://api.coze.cn"
ARK_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
PUSHPLUS_API = "https://www.pushplus.plus/send"

# 北京时间
BEIJING_TZ = timezone(timedelta(hours=8))

# 事件历史数据库文件
EVENT_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_history.json")
# 情绪历史文件
SENTIMENT_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentiment_history.json")


def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


def load_json_file(filepath, default=None):
    """加载JSON文件"""
    if default is None:
        default = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"加载文件失败 {filepath}: {e}")
    return default


def save_json_file(filepath, data):
    """保存JSON文件"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存文件失败 {filepath}: {e}")
        return False


# ============ 1. 实时金融数据 ============
def get_finance_data():
    """获取实时金融数据"""
    if not FINANCE_DATA_AVAILABLE:
        return None, ""
    
    try:
        data = get_all_finance_data()
        prompt_text = format_finance_data_for_prompt(data)
        return data, prompt_text
    except Exception as e:
        print(f"获取金融数据失败: {e}")
        return None, ""


# ============ 2. 多模型备份 ============
def call_coze_api(finance_prompt=""):
    """调用 Coze API 生成晨报（主模型）"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 开始调用 Coze API（主模型）...")

    headers = {
        "Authorization": f"Bearer {COZE_PAT}",
        "Content-Type": "application/json"
    }

    # 构建prompt
    base_prompt = """请生成今日产业情报晨报，包含全部章节：
1. 今日主线一句话（核心矛盾+主线方向）
2. 市场情绪面板（环境定级+建议动作+仓位建议）
3. 昨日预判复盘
4. 今日重点Top3（每条标注星级、性质、定价阶段、传导逻辑、关联标的）
5. 美股隔夜专节（11大板块完整明细+驱动归因）
6. 全球资产快照·A股开盘指引（A50/汇率/美元/美债/原油/黄金+开盘预判）
7. 题材共振检测（含持续性预判）
8. 延续事件跟踪
9. 事件传导分析·打板逻辑链（Top3的完整传导链）
10. 资金面深度专节（龙虎榜/大宗/融资/机构调研）
11. L1-L4分层事件（按星级排序）
12. 昨日盘后公告快报
13. 今日风险清单
14. 事件日历

标记规则：
- 星级：★★★★★全市场级/★★★★☆行业级/★★★☆☆产业链级/★★☆☆☆板块级/★☆☆☆☆一般
- 性质：🔴中长期利好/▼中长期利空/◆一日游
- 定价阶段：○未发酵/◐发酵中/●已定价
- 政策类附加：【规划期/征求意见/正式实施/资金到位】
- 题材类附加：【持续性：1日/3日/周级】
- 每条事件标注"非投资建议"
- 不要来源链接
"""
    
    full_prompt = base_prompt
    if finance_prompt:
        full_prompt = finance_prompt + "\n\n" + base_prompt

    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": "morning-report-bot",
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": full_prompt,
                "content_type": "text"
            }
        ]
    }

    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 创建对话...")
    resp = requests.post(f"{COZE_API_BASE}/v3/chat", headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    chat_data = resp.json()

    chat_info = chat_data.get("data", chat_data)
    conversation_id = chat_info.get("conversation_id", "")
    chat_id = chat_info.get("id", "")
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 对话已创建: conversation_id={conversation_id}, chat_id={chat_id}")
    
    if not conversation_id or not chat_id:
        raise Exception(f"Coze API返回异常: {chat_data}")

    # 轮询状态
    max_wait = 300
    waited = 0
    status = ""

    while waited < max_wait:
        time.sleep(5)
        waited += 5

        retrieve_url = f"{COZE_API_BASE}/v3/chat/retrieve?conversation_id={conversation_id}&chat_id={chat_id}"
        retrieve_resp = requests.get(retrieve_url, headers=headers, timeout=30)
        retrieve_resp.raise_for_status()
        retrieve_data = retrieve_resp.json()

        retrieve_info = retrieve_data.get("data", retrieve_data)
        status = retrieve_info.get("status", "")
        print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 等待中... 状态={status}, 已等{waited}秒")

        if status == "completed":
            break
        elif status in ("failed", "requires_action"):
            raise Exception(f"Coze对话异常: {status}")

    # 获取消息
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取消息内容...")
    msg_url = f"{COZE_API_BASE}/v3/chat/message/list?conversation_id={conversation_id}&chat_id={chat_id}"
    msg_resp = requests.get(msg_url, headers=headers, timeout=30)
    msg_resp.raise_for_status()
    msg_data = msg_resp.json()

    report_content = ""
    messages = msg_data.get("data", [])
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("type") == "answer":
            report_content = msg.get("content", "")
            break

    if not report_content:
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content and len(content) > 100:
                    report_content = content
                    break

    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 晨报生成完成，长度={len(report_content)}字符")
    return report_content


def call_ark_api(finance_prompt=""):
    """调用火山引擎方舟 API 生成晨报（备用模型）"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 开始调用火山引擎方舟 API（备用模型）...")
    
    if not ARK_API_KEY:
        raise Exception("未配置ARK_API_KEY，无法使用备用模型")

    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json"
    }

    base_prompt = """你是一位专业的A股市场投研分析师，请生成今日产业情报晨报。
包含章节：今日主线一句话、市场情绪面板、今日重点Top3、美股隔夜专节（11大板块）、全球资产快照·A股开盘指引、题材共振检测、L1-L4分层事件、今日风险清单、事件日历。
标记规则：星级★★★★★到★☆☆☆☆，性质🔴中长期利好/▼中长期利空/◆一日游，定价阶段○未发酵/◐发酵中/●已定价，每条标注"非投资建议"，不要来源链接。
"""
    
    full_prompt = base_prompt
    if finance_prompt:
        full_prompt = finance_prompt + "\n\n" + base_prompt

    payload = {
        "model": "doubao-pro-32k",
        "messages": [
            {"role": "system", "content": "你是专业的A股投研分析师，擅长产业情报分析和市场情绪研判。"},
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 8000
    }

    resp = requests.post(f"{ARK_API_BASE}/chat/completions", headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    
    report_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 备用模型晨报生成完成，长度={len(report_content)}字符")
    return report_content


def generate_report_with_backup(finance_prompt=""):
    """生成晨报，带多模型备份"""
    # 先尝试主模型 Coze
    try:
        return call_coze_api(finance_prompt), "coze"
    except Exception as e:
        print(f"主模型Coze调用失败: {e}")
        print("切换到备用模型火山引擎方舟...")
    
    # 备用模型 火山引擎方舟
    try:
        return call_ark_api(finance_prompt), "ark"
    except Exception as e:
        print(f"备用模型也失败: {e}")
        raise Exception("所有模型调用失败")


# ============ 3. 分层推送 ============
def extract_quick_summary(report_content):
    """从完整晨报中提取30秒速览"""
    lines = report_content.split("\n")
    summary_lines = []
    in_summary = False
    section_count = 0
    
    for line in lines:
        # 提取关键章节
        if any(keyword in line for keyword in ["今日主线", "市场情绪", "环境定级", "建议动作", "Top1", "Top2", "Top3", "开盘预判", "风险提示"]):
            in_summary = True
            section_count += 1
        
        if in_summary:
            summary_lines.append(line)
            if len(summary_lines) > 50 or section_count > 8:
                break
    
    if not summary_lines:
        # 如果提取失败，取前30行
        summary_lines = lines[:30]
    
    quick_summary = "\n".join(summary_lines)
    
    # 添加头部
    header = f"""⚡ 30秒速览 | {get_beijing_time().strftime('%Y-%m-%d')}
{'='*40}
"""
    footer = f"""
{'='*40}
📖 回复"详情"查看完整晨报
💬 回复"1/2/3"深挖Top3事件
⚠️ 以上内容非投资建议
"""
    
    return header + quick_summary + footer


# ============ 4. 事件历史类比数据库 ============
def update_event_history(report_content):
    """更新事件历史数据库"""
    history = load_json_file(EVENT_HISTORY_FILE, {"events": []})
    
    # 简单提取Top3事件存入历史
    lines = report_content.split("\n")
    today_events = []
    current_event = ""
    
    for line in lines:
        if "Top1" in line or "Top2" in line or "Top3" in line:
            if current_event:
                today_events.append(current_event)
            current_event = line
        elif current_event and len(current_event) < 500:
            current_event += "\n" + line
    
    if current_event:
        today_events.append(current_event)
    
    # 存入历史
    today_str = get_beijing_time().strftime("%Y-%m-%d")
    for event in today_events:
        history["events"].append({
            "date": today_str,
            "content": event[:500],
            "timestamp": get_beijing_time().isoformat()
        })
    
    # 只保留最近90天
    cutoff = (get_beijing_time() - timedelta(days=90)).isoformat()
    history["events"] = [e for e in history["events"] if e.get("timestamp", "") > cutoff]
    
    save_json_file(EVENT_HISTORY_FILE, history)
    print(f"事件历史数据库已更新，当前共{len(history['events'])}条事件")


def get_event_analogy_prompt():
    """获取事件历史类比的prompt"""
    history = load_json_file(EVENT_HISTORY_FILE, {"events": []})
    
    if not history["events"]:
        return ""
    
    # 取最近10条事件作为类比参考
    recent_events = history["events"][-10:]
    analogy_text = "【历史类似事件参考】\n"
    for event in recent_events:
        analogy_text += f"- {event['date']}: {event['content'][:100]}...\n"
    
    return analogy_text + "\n请参考历史类似事件的后续市场表现，对今日事件给出更准确的持续性预判。\n"


# ============ 5. 图表可视化 ============
def generate_sentiment_chart(finance_data=None):
    """生成情绪周期走势图（简化版，用文本表示）"""
    # 加载情绪历史
    sentiment_history = load_json_file(SENTIMENT_HISTORY_FILE, {"history": []})
    
    # 如果有金融数据，更新今日情绪
    if finance_data and "limit_up_down" in finance_data:
        lud = finance_data["limit_up_down"]
        limit_up = lud.get("limit_up_count", 0)
        max_boards = lud.get("max_consecutive_boards", 0)
        broken_rate = lud.get("broken_board_rate", 0)
        
        # 简单定级
        if limit_up < 30 or (max_boards <= 2 and broken_rate > 40):
            sentiment = "冰点"
        elif limit_up < 60 or max_boards == 3:
            sentiment = "修复"
        elif limit_up < 100 or max_boards in (4, 5):
            sentiment = "发酵"
        elif limit_up >= 100 or max_boards >= 6:
            sentiment = "高潮"
        else:
            sentiment = "退潮"
        
        today_str = get_beijing_time().strftime("%Y-%m-%d")
        sentiment_history["history"].append({
            "date": today_str,
            "sentiment": sentiment,
            "limit_up": limit_up,
            "max_boards": max_boards
        })
        
        # 只保留最近30天
        sentiment_history["history"] = sentiment_history["history"][-30:]
        save_json_file(SENTIMENT_HISTORY_FILE, sentiment_history)
    
    # 生成文本图表
    if not sentiment_history["history"]:
        return ""
    
    chart_text = "📊 近5日情绪周期走势\n"
    chart_text += "━" * 30 + "\n"
    
    recent = sentiment_history["history"][-5:]
    for item in recent:
        date_short = item["date"][5:]  # MM-DD
        sentiment = item["sentiment"]
        bar_len = {"冰点": 1, "修复": 2, "发酵": 3, "高潮": 4, "退潮": 2}.get(sentiment, 2)
        bar = "█" * bar_len + "░" * (4 - bar_len)
        chart_text += f"{date_short} {bar} {sentiment}\n"
    
    chart_text += "━" * 30 + "\n"
    
    # 拐点信号
    if len(recent) >= 3:
        sentiments = [item["sentiment"] for item in recent[-3:]]
        if sentiments.count("发酵") >= 3:
            chart_text += "⚠️ 连续3日发酵，警惕高潮/兑现\n"
        elif sentiments[-1] == "高潮" and sentiments[-2] in ("高潮", "发酵"):
            chart_text += "⚠️ 高潮后，警惕退潮\n"
        elif sentiments[-1] == "修复" and sentiments[-2] in ("冰点", "退潮"):
            chart_text += "✅ 冰点/退潮转修复，拐点机会信号\n"
    
    return chart_text


# ============ 6. 反馈优化机制 ============
def add_feedback_links(content):
    """在推送内容中添加反馈链接"""
    feedback_footer = f"""

{'='*40}
📝 反馈优化：
👍 有用 | 👎 无用 | 💡 建议
（回复数字或直接留言，帮助优化晨报质量）
"""
    return content + feedback_footer


# ============ 推送功能 ============
def push_to_wechat(title, content):
    """通过 PushPlus 推送到微信"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 推送到微信: {title}")
    
    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html"
    }
    
    try:
        resp = requests.post(PUSHPLUS_API, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("code") == 200:
            print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 推送成功! message_id={result.get('data', '')}")
            return True
        else:
            print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 推送失败: {result}")
            return False
    except Exception as e:
        print(f"推送异常: {e}")
        return False


# ============ 主函数 ============
def main():
    """主函数"""
    print("=" * 60)
    print(f"每日产业情报晨报 V2 - {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')} 北京时间")
    print("升级功能：实时金融数据 | 多模型备份 | 分层推送 | 事件历史 | 图表可视化 | 反馈优化")
    print("=" * 60)

    # 检查配置
    if not COZE_PAT or not COZE_BOT_ID:
        print("错误: 未设置 COZE_PAT 或 COZE_BOT_ID")
        exit(1)
    if not PUSHPLUS_TOKEN:
        print("错误: 未设置 PUSHPLUS_TOKEN")
        exit(1)

    # 1. 获取实时金融数据
    finance_data, finance_prompt = get_finance_data()
    
    # 2. 获取事件历史类比
    analogy_prompt = get_event_analogy_prompt()
    
    # 合并prompt
    full_prompt = finance_prompt
    if analogy_prompt:
        full_prompt += "\n" + analogy_prompt
    
    # 3. 生成晨报（带多模型备份）
    try:
        report_content, model_used = generate_report_with_backup(full_prompt)
        print(f"使用模型: {model_used}")
    except Exception as e:
        print(f"生成晨报失败: {e}")
        error_msg = f"晨报生成失败，请检查模型API状态。\n\n错误信息: {str(e)}"
        push_to_wechat(f"⚠️ 晨报生成失败 - {get_beijing_time().strftime('%m-%d')}", error_msg)
        exit(1)

    if not report_content or len(report_content) < 50:
        print("错误: 晨报内容为空或过短")
        push_to_wechat(f"⚠️ 晨报内容异常 - {get_beijing_time().strftime('%m-%d')}", "晨报生成内容为空，请检查智能体配置。")
        exit(1)

    # 4. 生成情绪走势图
    sentiment_chart = generate_sentiment_chart(finance_data)
    
    # 5. 提取30秒速览
    quick_summary = extract_quick_summary(report_content)
    if sentiment_chart:
        quick_summary += "\n\n" + sentiment_chart
    
    # 6. 添加反馈链接
    quick_summary = add_feedback_links(quick_summary)
    full_report = add_feedback_links(report_content)
    if sentiment_chart:
        full_report = "\n\n" + sentiment_chart + "\n\n" + full_report

    # 7. 分层推送：先推速览，再推完整
    today_str = get_beijing_time().strftime("%Y-%m-%d")
    
    # 推送30秒速览
    title1 = f"⚡晨报速览 {today_str}"
    success1 = push_to_wechat(title1, quick_summary)
    
    # 推送完整晨报
    time.sleep(2)  # 间隔2秒，避免推送过快
    title2 = f"📊完整晨报 {today_str}"
    success2 = push_to_wechat(title2, full_report)
    
    if not success1 and not success2:
        print("推送全部失败，但晨报已生成")
        print("\n" + "=" * 60)
        print("晨报内容:")
        print(report_content[:2000])
        print("=" * 60)
    
    # 8. 更新事件历史数据库
    update_event_history(report_content)
    
    print("\n✅ 任务完成!")
    print(f"   - 使用模型: {model_used}")
    print(f"   - 金融数据: {'已获取' if finance_data else '未获取'}")
    print(f"   - 速览推送: {'成功' if success1 else '失败'}")
    print(f"   - 完整推送: {'成功' if success2 else '失败'}")


if __name__ == "__main__":
    main()
