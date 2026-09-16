#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日产业情报晨报 - Coze API 调用 + PushPlus 微信推送
GitHub Actions 每天 8:30 (北京时间) 自动运行
"""

import os
import time
import json
import requests
from datetime import datetime, timezone, timedelta

# ============ 配置（从 GitHub Secrets 读取） ============
COZE_PAT = os.environ.get("COZE_PAT", "")          # Coze 个人访问令牌
COZE_BOT_ID = os.environ.get("COZE_BOT_ID", "")    # 智能体 Bot ID
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")  # PushPlus token

COZE_API_BASE = "https://api.coze.cn"
PUSHPLUS_API = "https://www.pushplus.plus/send"

# 北京时间
BEIJING_TZ = timezone(timedelta(hours=8))


def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


def call_coze_api():
    """调用 Coze API 生成晨报"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 开始调用 Coze API...")

    # 1. 创建对话
    headers = {
        "Authorization": f"Bearer {COZE_PAT}",
        "Content-Type": "application/json"
    }

    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": "morning-report-bot",
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": "请生成今日产业情报晨报，包含全部章节：今日主线一句话、市场情绪面板、今日重点Top3、美股隔夜专节（11大板块完整明细）、全球资产快照·A股开盘指引、题材共振检测、L1-L4分层事件、今日风险清单、事件日历。每条事件标注星级、性质（🔴中长期利好/▼中长期利空/◆一日游）、定价阶段（○未发酵/◐发酵中/●已定价）、传导逻辑、关联板块/标的。标注'非投资建议'。不要来源链接。",
                "content_type": "text"
            }
        ]
    }

    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 创建对话...")
    resp = requests.post(f"{COZE_API_BASE}/v3/chat", headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    chat_data = resp.json()

    # Coze API v3 返回的数据在 data 字段中
    chat_info = chat_data.get("data", chat_data)
    conversation_id = chat_info.get("conversation_id", "")
    chat_id = chat_info.get("id", "")
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 对话已创建: conversation_id={conversation_id}, chat_id={chat_id}")
    if not conversation_id or not chat_id:
        print(f"[{get_beijing_time().strftime('%H:%M:%S')}] API返回完整数据: {chat_data}")

    # 2. 轮询对话状态
    max_wait = 300  # 最多等5分钟
    waited = 0
    status = ""

    while waited < max_wait:
        time.sleep(5)
        waited += 5

        retrieve_url = f"{COZE_API_BASE}/v3/chat/retrieve?conversation_id={conversation_id}&chat_id={chat_id}"
        retrieve_resp = requests.get(retrieve_url, headers=headers, timeout=30)
        retrieve_resp.raise_for_status()
        retrieve_data = retrieve_resp.json()

        # Coze API v3 返回的数据在 data 字段中
        retrieve_info = retrieve_data.get("data", retrieve_data)
        status = retrieve_info.get("status", "")
        print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 等待中... 状态={status}, 已等{waited}秒")

        if status == "completed":
            break
        elif status in ("failed", "requires_action"):
            print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 对话异常: {status}")
            break

    # 3. 获取消息列表
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取消息内容...")
    msg_url = f"{COZE_API_BASE}/v3/chat/message/list?conversation_id={conversation_id}&chat_id={chat_id}"
    msg_resp = requests.get(msg_url, headers=headers, timeout=30)
    msg_resp.raise_for_status()
    msg_data = msg_resp.json()

    # 提取 assistant 的回复内容
    report_content = ""
    messages = msg_data.get("data", [])
    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("type") == "answer":
            report_content = msg.get("content", "")
            break

    if not report_content:
        # 尝试从其他类型的消息中提取
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content and len(content) > 100:
                    report_content = content
                    break

    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 晨报生成完成，长度={len(report_content)}字符")
    return report_content


def push_to_wechat(title, content):
    """通过 PushPlus 推送到微信"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 推送到微信...")

    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html"
    }

    resp = requests.post(PUSHPLUS_API, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") == 200:
        print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 推送成功! message_id={result.get('data', '')}")
        return True
    else:
        print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 推送失败: {result}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print(f"每日产业情报晨报 - {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')} 北京时间")
    print("=" * 60)

    # 检查配置
    if not COZE_PAT:
        print("错误: 未设置 COZE_PAT 环境变量")
        exit(1)
    if not COZE_BOT_ID:
        print("错误: 未设置 COZE_BOT_ID 环境变量")
        exit(1)
    if not PUSHPLUS_TOKEN:
        print("错误: 未设置 PUSHPLUS_TOKEN 环境变量")
        exit(1)

    # 生成晨报
    try:
        report_content = call_coze_api()
    except Exception as e:
        print(f"生成晨报失败: {e}")
        # 推送错误通知
        error_msg = f"晨报生成失败，请检查 Coze 智能体状态和 API 配置。\n\n错误信息: {str(e)}"
        push_to_wechat(f"⚠️ 晨报生成失败 - {get_beijing_time().strftime('%m-%d')}", error_msg)
        exit(1)

    if not report_content or len(report_content) < 50:
        print("错误: 晨报内容为空或过短")
        push_to_wechat(f"⚠️ 晨报内容异常 - {get_beijing_time().strftime('%m-%d')}", "晨报生成内容为空，请检查智能体提示词和插件配置。")
        exit(1)

    # 推送到微信
    title = f"📊 产业情报晨报 {get_beijing_time().strftime('%Y-%m-%d')}"
    try:
        success = push_to_wechat(title, report_content)
        if not success:
            print("推送失败，但晨报已生成")
            # 打印晨报内容到日志
            print("\n" + "=" * 60)
            print("晨报内容:")
            print(report_content[:2000])
            print("=" * 60)
    except Exception as e:
        print(f"推送异常: {e}")

    print("\n✅ 任务完成!")


if __name__ == "__main__":
    main()
