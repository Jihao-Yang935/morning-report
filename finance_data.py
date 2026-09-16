#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时金融数据获取模块
从东方财富、新浪财经等公开API获取真实市场数据
"""

import requests
import json
import time
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    return datetime.now(BEIJING_TZ)

def safe_request(url, params=None, headers=None, timeout=10, retries=2):
    """安全的HTTP请求，带重试"""
    for i in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if i < retries:
                time.sleep(1)
                continue
            print(f"请求失败 {url}: {e}")
            return None

def get_a_share_market_overview():
    """获取A股市场概览：指数涨跌幅、成交额"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取A股市场概览...")
    
    # 东方财富指数API
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": "1.000001,0.399001,0.399006,1.000688",
        "fields": "f2,f3,f4,f12,f14,f6"
    }
    
    data = safe_request(url, params=params)
    result = {}
    
    if data and "data" in data and "diff" in data["data"]:
        for item in data["data"]["diff"]:
            name = item.get("f14", "")
            code = item.get("f12", "")
            price = item.get("f2", 0)
            change_pct = item.get("f3", 0)
            amount = item.get("f6", 0)
            
            if "上证指数" in name or code == "000001":
                result["shanghai"] = {"name": "上证指数", "price": price, "change_pct": change_pct, "amount": amount}
            elif "深证成指" in name or code == "399001":
                result["shenzhen"] = {"name": "深证成指", "price": price, "change_pct": change_pct, "amount": amount}
            elif "创业板指" in name or code == "399006":
                result["chinext"] = {"name": "创业板指", "price": price, "change_pct": change_pct, "amount": amount}
            elif "科创50" in name or code == "000688":
                result["star50"] = {"name": "科创50", "price": price, "change_pct": change_pct, "amount": amount}
    
    # 计算两市成交额
    if "shanghai" in result and "shenzhen" in result:
        total_amount = result["shanghai"].get("amount", 0) + result["shenzhen"].get("amount", 0)
        result["total_amount"] = total_amount
        result["total_amount_yi"] = round(total_amount / 100000000, 0) if total_amount else 0
    
    return result

def get_limit_up_down_data():
    """获取涨停/跌停/炸板数据"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取涨跌停数据...")
    
    result = {
        "limit_up_count": 0,
        "limit_down_count": 0,
        "broken_board_count": 0,
        "broken_board_rate": 0,
        "max_consecutive_boards": 0,
        "max_consecutive_stock": "",
        "consecutive_structure": {}
    }
    
    # 东方财富涨停板API
    url = "https://push2ex.eastmoney.com/getTopicZTPool"
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "200",
        "sort": "fbt:asc",
        "date": get_beijing_time().strftime("%Y%m%d")
    }
    
    data = safe_request(url, params=params)
    
    if data and "data" in data and "pool" in data["data"]:
        pool = data["data"]["pool"]
        result["limit_up_count"] = len(pool)
        
        # 分析连板结构
        consecutive_map = {}
        max_boards = 0
        max_boards_stock = ""
        
        for stock in pool:
            name = stock.get("n", "")
            lbc = stock.get("lbc", 0)  # 连板数
            zbc = stock.get("zbc", 0)  # 炸板数
            
            if lbc > max_boards:
                max_boards = lbc
                max_boards_stock = name
            
            if lbc not in consecutive_map:
                consecutive_map[lbc] = []
            consecutive_map[lbc].append(name)
        
        result["max_consecutive_boards"] = max_boards
        result["max_consecutive_stock"] = max_boards_stock
        result["consecutive_structure"] = {str(k): v for k, v in sorted(consecutive_map.items(), reverse=True)}
    
    # 获取炸板数据
    url2 = "https://push2ex.eastmoney.com/getTopicZBPool"
    data2 = safe_request(url2, params=params)
    
    if data2 and "data" in data2 and "pool" in data2["data"]:
        result["broken_board_count"] = len(data2["data"]["pool"])
    
    # 计算炸板率
    total_attempt = result["limit_up_count"] + result["broken_board_count"]
    if total_attempt > 0:
        result["broken_board_rate"] = round(result["broken_board_count"] / total_attempt * 100, 1)
    
    # 获取跌停数据
    url3 = "https://push2ex.eastmoney.com/getTopicDTPool"
    data3 = safe_request(url3, params=params)
    
    if data3 and "data" in data3 and "pool" in data3["data"]:
        result["limit_down_count"] = len(data3["data"]["pool"])
    
    return result

def get_us_stock_sectors():
    """获取美股11大板块ETF涨跌幅"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取美股板块数据...")
    
    # 标普500 11大板块ETF代码（东方财富格式：105.代码）
    sector_etfs = {
        "XLK": "科技",
        "XLF": "金融",
        "XLE": "能源",
        "XLV": "医疗",
        "XLI": "工业",
        "XLY": "非必需消费",
        "XLC": "通讯",
        "XLP": "必需消费",
        "XLU": "公用事业",
        "XLB": "材料",
        "XLRE": "房地产"
    }
    
    result = []
    
    # 东方财富美股API - 批量获取
    secids = ",".join([f"105.{code}" for code in sector_etfs.keys()])
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": secids,
        "fields": "f2,f3,f4,f12,f14"
    }
    
    data = safe_request(url, params=params, timeout=10)
    
    if data and "data" in data and "diff" in data["data"]:
        for item in data["data"]["diff"]:
            code = item.get("f12", "")
            name_en = item.get("f14", "")
            price = item.get("f2", 0)
            change_pct = item.get("f3", 0)
            
            name = sector_etfs.get(code, name_en)
            result.append({
                "code": code,
                "name": name,
                "price": price,
                "change_pct": change_pct
            })
    
    # 如果东方财富获取失败，补充空数据
    if len(result) < 11:
        existing_codes = {r["code"] for r in result}
        for code, name in sector_etfs.items():
            if code not in existing_codes:
                result.append({"code": code, "name": name, "price": 0, "change_pct": 0})
    
    # 按涨跌幅排序
    result.sort(key=lambda x: x["change_pct"], reverse=True)
    return result

def get_global_assets():
    """获取全球资产快照：A50、汇率、美元指数、美债、原油、黄金"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取全球资产数据...")
    
    result = {}
    headers = {"Referer": "https://finance.sina.com.cn"}
    
    def calc_change_pct(current, prev_close):
        """计算涨跌幅"""
        if prev_close and prev_close != 0:
            return round((current - prev_close) / prev_close * 100, 2)
        return 0
    
    # 美元指数 DINIW: 时间,当前价,昨收,今开,...
    try:
        url = "https://hq.sinajs.cn/list=DINIW"
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "gbk"
        text = resp.text
        if '"' in text:
            parts = text.split('"')[1].split(",")
            if len(parts) >= 3:
                price = float(parts[1])
                prev_close = float(parts[2])
                result["dxy"] = {
                    "name": "美元指数", 
                    "price": price, 
                    "change_pct": calc_change_pct(price, prev_close)
                }
    except Exception as e:
        print(f"获取美元指数失败: {e}")
    
    # 离岸人民币 fx_susdcnh: 时间,当前价,昨收,...
    try:
        url = "https://hq.sinajs.cn/list=fx_susdcnh"
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "gbk"
        text = resp.text
        if '"' in text:
            parts = text.split('"')[1].split(",")
            if len(parts) >= 3:
                price = float(parts[1])
                prev_close = float(parts[2])
                result["usdcnh"] = {
                    "name": "离岸人民币", 
                    "price": price, 
                    "change_pct": calc_change_pct(price, prev_close)
                }
    except Exception as e:
        print(f"获取离岸人民币失败: {e}")
    
    # WTI原油 hf_CL: 当前价,,买入,卖出,最高,最低,时间,昨收,今开,...
    try:
        url = "https://hq.sinajs.cn/list=hf_CL"
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "gbk"
        text = resp.text
        if '"' in text:
            parts = text.split('"')[1].split(",")
            if len(parts) >= 8:
                price = float(parts[0])
                prev_close = float(parts[7])
                result["wti"] = {
                    "name": "WTI原油", 
                    "price": price, 
                    "change_pct": calc_change_pct(price, prev_close)
                }
    except Exception as e:
        print(f"获取WTI原油失败: {e}")
    
    # COMEX黄金 hf_GC: 格式同WTI
    try:
        url = "https://hq.sinajs.cn/list=hf_GC"
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "gbk"
        text = resp.text
        if '"' in text:
            parts = text.split('"')[1].split(",")
            if len(parts) >= 8:
                price = float(parts[0])
                prev_close = float(parts[7])
                result["gold"] = {
                    "name": "COMEX黄金", 
                    "price": price, 
                    "change_pct": calc_change_pct(price, prev_close)
                }
    except Exception as e:
        print(f"获取黄金失败: {e}")
    
    # 富时A50期指（用东方财富API）
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": "100.CHA50CFD",
            "fields": "f43,f170"
        }
        data = safe_request(url, params=params, timeout=5)
        if data and "data" in data and data["data"]:
            price = data["data"].get("f43", 0) / 100
            change_pct = data["data"].get("f170", 0) / 100
            result["a50"] = {"name": "富时A50期指", "price": price, "change_pct": change_pct}
    except Exception as e:
        print(f"获取A50失败: {e}")
    
    return result

def get_dragon_tiger_list():
    """获取龙虎榜数据（简化版）"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取龙虎榜数据...")
    
    result = {
        "total_stocks": 0,
        "net_buy_top": [],
        "famous_seats": []
    }
    
    # 东方财富龙虎榜API
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "NET_BUY_AMT",
        "sortTypes": "-1",
        "pageSize": "10",
        "pageNumber": "1",
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
        "columns": "ALL",
        "filter": f"(TRADE_DATE='{get_beijing_time().strftime('%Y-%m-%d')}')"
    }
    
    data = safe_request(url, params=params, timeout=10)
    
    if data and "result" in data and data["result"] and "data" in data["result"]:
        stocks = data["result"]["data"]
        result["total_stocks"] = len(stocks)
        
        for stock in stocks[:5]:
            result["net_buy_top"].append({
                "name": stock.get("SECURITY_NAME_ABBR", ""),
                "code": stock.get("SECURITY_CODE", ""),
                "net_buy": stock.get("NET_BUY_AMT", 0),
                "change_pct": stock.get("CHANGE_RATE", 0)
            })
    
    return result


def get_northbound_flow():
    """获取北向资金数据：净流入/流出 + 买卖TOP5个股"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取北向资金数据...")
    
    result = {
        "net_inflow": 0,
        "sh_net_inflow": 0,
        "sz_net_inflow": 0,
        "top_buy": [],
        "top_sell": []
    }
    
    # 东方财富北向资金实时API
    try:
        url = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
        params = {
            "fields1": "f1,f2,f3,f4",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
            "ut": "b2884a393a59ad64002292a3e90d46a"
        }
        data = safe_request(url, params=params, timeout=10)
        
        if data and "data" in data and data["data"]:
            d = data["data"]
            
            def parse_north_value(val):
                """解析北向资金数值，可能是数组或逗号分隔字符串"""
                if val is None:
                    return 0
                if isinstance(val, (int, float)):
                    return val
                if isinstance(val, list) and len(val) > 0:
                    # 取最后一个非零值
                    for v in reversed(val):
                        if v and v != 0:
                            return v
                    return val[-1] if val else 0
                if isinstance(val, str):
                    # 格式可能是 "时间,数值,..." 或纯数字
                    parts = val.split(",")
                    if len(parts) >= 2:
                        try:
                            return float(parts[1])
                        except:
                            return 0
                    try:
                        return float(val)
                    except:
                        return 0
                return 0
            
            result["net_inflow"] = parse_north_value(d.get("s2n"))
            result["sh_net_inflow"] = parse_north_value(d.get("s2n_sh"))
            result["sz_net_inflow"] = parse_north_value(d.get("s2n_sz"))
    except Exception as e:
        print(f"获取北向资金实时数据失败: {e}")
    
    # 北向资金买卖TOP10个股（东方财富数据中心）
    try:
        url2 = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params2 = {
            "sortColumns": "HOLD_MARKET_CAP",
            "sortTypes": "-1",
            "pageSize": "10",
            "pageNumber": "1",
            "reportName": "RPT_MUTUAL_HOLD_DET",
            "columns": "ALL",
            "filter": f"(TRADE_DATE='{get_beijing_time().strftime('%Y-%m-%d')}')"
        }
        data2 = safe_request(url2, params=params2, timeout=10)
        
        if data2 and "result" in data2 and data2["result"] and "data" in data2["result"]:
            stocks = data2["result"]["data"]
            for stock in stocks[:5]:
                result["top_buy"].append({
                    "name": stock.get("SECURITY_NAME_ABBR", ""),
                    "code": stock.get("SECURITY_CODE", ""),
                    "hold_cap": stock.get("HOLD_MARKET_CAP", 0),
                    "change_pct": stock.get("CHANGE_RATE", 0)
                })
    except Exception as e:
        print(f"获取北向资金个股数据失败: {e}")
    
    return result


def get_margin_trading():
    """获取融资融券数据：融资余额变化 + 融资净买入TOP5行业"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取融资融券数据...")
    
    result = {
        "total_balance": 0,
        "balance_change": 0,
        "balance_change_pct": 0,
        "top_industries": [],
        "top_stocks": []
    }
    
    # 东方财富融资融券API
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "sortColumns": "DATE",
            "sortTypes": "-1",
            "pageSize": "2",
            "pageNumber": "1",
            "reportName": "RPTA_WEB_RZRQ_LSHJ",
            "columns": "ALL"
        }
        data = safe_request(url, params=params, timeout=10)
        
        if data and "result" in data and data["result"] and "data" in data["result"]:
            records = data["result"]["data"]
            if len(records) >= 1:
                result["total_balance"] = records[0].get("RZYE", 0)
            if len(records) >= 2:
                prev_balance = records[1].get("RZYE", 0)
                result["balance_change"] = result["total_balance"] - prev_balance
                if prev_balance > 0:
                    result["balance_change_pct"] = round(result["balance_change"] / prev_balance * 100, 2)
    except Exception as e:
        print(f"获取融资融券总量数据失败: {e}")
    
    # 融资净买入TOP个股
    try:
        url2 = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params2 = {
            "sortColumns": "RZMRE",
            "sortTypes": "-1",
            "pageSize": "5",
            "pageNumber": "1",
            "reportName": "RPTA_WEB_RZRQ_GGMX",
            "columns": "ALL",
            "filter": f"(DATE='{get_beijing_time().strftime('%Y-%m-%d')}')"
        }
        data2 = safe_request(url2, params=params2, timeout=10)
        
        if data2 and "result" in data2 and data2["result"] and "data" in data2["result"]:
            stocks = data2["result"]["data"]
            for stock in stocks:
                result["top_stocks"].append({
                    "name": stock.get("SECURITY_NAME_ABBR", ""),
                    "code": stock.get("SECURITY_CODE", ""),
                    "net_buy": stock.get("RZMRE", 0),
                    "change_pct": stock.get("CHANGE_RATE", 0)
                })
    except Exception as e:
        print(f"获取融资买入个股数据失败: {e}")
    
    return result


def get_leader_stocks_detail(limit_up_data):
    """获取龙头股详细跟踪信息：最高板+次高板的涨停原因、封单、封板时间"""
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 获取龙头股详细信息...")
    
    result = {
        "top_leader": None,
        "second_leader": None,
        "all_leaders": []
    }
    
    if not limit_up_data or "consecutive_structure" not in limit_up_data:
        return result
    
    structure = limit_up_data["consecutive_structure"]
    
    # 从涨停板API获取详细信息
    url = "https://push2ex.eastmoney.com/getTopicZTPool"
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "200",
        "sort": "fbt:asc",
        "date": get_beijing_time().strftime("%Y%m%d")
    }
    
    data = safe_request(url, params=params, timeout=10)
    
    def format_time_str(time_int):
        """将整数时间格式化为HH:MM:SS"""
        if not time_int:
            return ""
        try:
            t = int(time_int)
            h = t // 10000
            m = (t % 10000) // 100
            s = t % 100
            return f"{h:02d}:{m:02d}:{s:02d}"
        except:
            return str(time_int)
    
    stock_details = {}
    if data and "data" in data and "pool" in data["data"]:
        for stock in data["data"]["pool"]:
            name = stock.get("n", "")
            stock_details[name] = {
                "name": name,
                "code": stock.get("c", ""),
                "consecutive_boards": stock.get("lbc", 0),
                "first_limit_time": format_time_str(stock.get("fbt", "")),
                "last_limit_time": format_time_str(stock.get("lbt", "")),
                "limit_amount": stock.get("zbc", 0),
                "seal_amount": stock.get("fund", 0),
                "turnover_rate": stock.get("hs", 0),
                "amount": stock.get("amount", 0),
                "reason": stock.get("hybk", "") or stock.get("zttj", "")
            }
    
    # 提取最高板和次高板龙头
    sorted_boards = sorted(structure.keys(), key=lambda x: int(x), reverse=True)
    
    if len(sorted_boards) >= 1:
        top_board = sorted_boards[0]
        top_stocks = structure[top_board]
        if top_stocks:
            top_name = top_stocks[0]
            result["top_leader"] = stock_details.get(top_name, {"name": top_name, "consecutive_boards": int(top_board)})
            result["all_leaders"].append(result["top_leader"])
    
    if len(sorted_boards) >= 2:
        second_board = sorted_boards[1]
        second_stocks = structure[second_board]
        if second_stocks:
            second_name = second_stocks[0]
            result["second_leader"] = stock_details.get(second_name, {"name": second_name, "consecutive_boards": int(second_board)})
            result["all_leaders"].append(result["second_leader"])
    
    # 再提取3板以上的所有龙头
    for board in sorted_boards:
        if int(board) >= 3:
            for stock_name in structure[board]:
                if stock_name not in [l.get("name") for l in result["all_leaders"]]:
                    detail = stock_details.get(stock_name, {"name": stock_name, "consecutive_boards": int(board)})
                    result["all_leaders"].append(detail)
    
    return result

def get_all_finance_data():
    """获取所有金融数据，汇总返回"""
    print("=" * 60)
    print("开始获取实时金融数据...")
    print("=" * 60)
    
    # 先获取涨跌停数据（龙头股跟踪需要）
    limit_up_down = get_limit_up_down_data()
    
    result = {
        "fetch_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
        "a_share": get_a_share_market_overview(),
        "limit_up_down": limit_up_down,
        "us_sectors": get_us_stock_sectors(),
        "global_assets": get_global_assets(),
        "dragon_tiger": get_dragon_tiger_list(),
        "northbound": get_northbound_flow(),
        "margin_trading": get_margin_trading(),
        "leader_stocks": get_leader_stocks_detail(limit_up_down)
    }
    
    print("=" * 60)
    print("金融数据获取完成!")
    print("=" * 60)
    
    return result

def format_finance_data_for_prompt(data):
    """将金融数据格式化为prompt文本，传给智能体"""
    lines = []
    lines.append("【实时金融数据（已验证）】")
    lines.append("")
    
    # A股市场
    if "a_share" in data and data["a_share"]:
        a = data["a_share"]
        lines.append("一、A股市场概览（昨日收盘）:")
        for key in ["shanghai", "shenzhen", "chinext", "star50"]:
            if key in a:
                idx = a[key]
                lines.append(f"  {idx['name']}: {idx['price']}点, 涨跌幅{idx['change_pct']}%")
        if "total_amount_yi" in a:
            lines.append(f"  两市成交额: {a['total_amount_yi']}亿元")
        lines.append("")
    
    # 涨跌停数据
    if "limit_up_down" in data and data["limit_up_down"]:
        l = data["limit_up_down"]
        lines.append("二、涨跌停数据:")
        lines.append(f"  涨停家数: {l.get('limit_up_count', 0)}家")
        lines.append(f"  跌停家数: {l.get('limit_down_count', 0)}家")
        lines.append(f"  炸板家数: {l.get('broken_board_count', 0)}家")
        lines.append(f"  炸板率: {l.get('broken_board_rate', 0)}%")
        lines.append(f"  最高连板: {l.get('max_consecutive_boards', 0)}板 ({l.get('max_consecutive_stock', '')})")
        
        if l.get("consecutive_structure"):
            lines.append("  连板梯队:")
            for boards, stocks in l["consecutive_structure"].items():
                lines.append(f"    {boards}板: {', '.join(stocks[:3])}{'...' if len(stocks) > 3 else ''}")
        lines.append("")
    
    # 美股板块
    if "us_sectors" in data and data["us_sectors"]:
        lines.append("三、美股11大板块涨跌幅（隔夜收盘）:")
        for sector in data["us_sectors"]:
            arrow = "↑" if sector["change_pct"] > 0 else "↓" if sector["change_pct"] < 0 else "→"
            lines.append(f"  {sector['name']}({sector['code']}): {arrow}{abs(sector['change_pct'])}%")
        lines.append("")
    
    # 全球资产
    if "global_assets" in data and data["global_assets"]:
        lines.append("四、全球资产快照:")
        for key, asset in data["global_assets"].items():
            arrow = "↑" if asset["change_pct"] > 0 else "↓" if asset["change_pct"] < 0 else "→"
            lines.append(f"  {asset['name']}: {asset['price']}, {arrow}{abs(asset['change_pct'])}%")
        lines.append("")
    
    # 龙虎榜
    if "dragon_tiger" in data and data["dragon_tiger"] and data["dragon_tiger"].get("net_buy_top"):
        lines.append("五、龙虎榜净买入TOP5:")
        for stock in data["dragon_tiger"]["net_buy_top"]:
            net_buy_yi = round(stock["net_buy"] / 100000000, 2) if stock["net_buy"] else 0
            lines.append(f"  {stock['name']}({stock['code']}): 净买入{net_buy_yi}亿, 涨跌幅{stock['change_pct']}%")
        lines.append("")
    
    # 北向资金
    if "northbound" in data and data["northbound"]:
        nb = data["northbound"]
        lines.append("六、北向资金:")
        
        def safe_to_yi(val):
            """安全转换为亿元"""
            if val is None:
                return 0
            if isinstance(val, (int, float)):
                return round(val / 100000000, 2)
            return 0
        
        net_inflow_yi = safe_to_yi(nb.get("net_inflow", 0))
        arrow = "↑" if net_inflow_yi > 0 else "↓" if net_inflow_yi < 0 else "→"
        lines.append(f"  北向资金净流入: {arrow}{abs(net_inflow_yi)}亿")
        sh_yi = safe_to_yi(nb.get("sh_net_inflow", 0))
        sz_yi = safe_to_yi(nb.get("sz_net_inflow", 0))
        lines.append(f"  沪股通: {sh_yi}亿, 深股通: {sz_yi}亿")
        if nb.get("top_buy"):
            lines.append("  北向持股市值TOP5:")
            for stock in nb["top_buy"][:5]:
                hold_yi = safe_to_yi(stock.get("hold_cap", 0))
                lines.append(f"    {stock['name']}({stock['code']}): 持股市值{hold_yi}亿")
        lines.append("")
    
    # 融资融券
    if "margin_trading" in data and data["margin_trading"]:
        mt = data["margin_trading"]
        lines.append("七、融资融券:")
        total_yi = round(mt.get("total_balance", 0) / 100000000, 2) if mt.get("total_balance") else 0
        change_yi = round(mt.get("balance_change", 0) / 100000000, 2) if mt.get("balance_change") else 0
        arrow = "↑" if change_yi > 0 else "↓" if change_yi < 0 else "→"
        lines.append(f"  融资余额: {total_yi}亿, 较前日{arrow}{abs(change_yi)}亿({mt.get('balance_change_pct', 0)}%)")
        if mt.get("top_stocks"):
            lines.append("  融资净买入TOP5:")
            for stock in mt["top_stocks"][:5]:
                net_buy_yi = round(stock.get("net_buy", 0) / 100000000, 2) if stock.get("net_buy") else 0
                lines.append(f"    {stock['name']}({stock['code']}): 净买入{net_buy_yi}亿, 涨跌幅{stock.get('change_pct', 0)}%")
        lines.append("")
    
    # 龙头股跟踪
    if "leader_stocks" in data and data["leader_stocks"] and data["leader_stocks"].get("all_leaders"):
        ls = data["leader_stocks"]
        lines.append("八、龙头股跟踪（3板以上）:")
        for leader in ls["all_leaders"]:
            boards = leader.get("consecutive_boards", 0)
            name = leader.get("name", "")
            code = leader.get("code", "")
            first_time = leader.get("first_limit_time", "")
            seal_amount = leader.get("seal_amount", 0)
            seal_yi = round(seal_amount / 100000000, 2) if seal_amount else 0
            reason = leader.get("reason", "")
            lines.append(f"  {boards}板 {name}({code}): 首封{first_time}, 封单{seal_yi}亿, 题材:{reason}")
        lines.append("")
    
    lines.append("【请基于以上真实数据生成晨报，不要编造数据】")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    data = get_all_finance_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)
    print("格式化后的prompt:")
    print("=" * 60)
    print(format_finance_data_for_prompt(data))
