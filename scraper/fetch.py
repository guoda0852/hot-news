#!/usr/bin/env python3
"""热榜聚合抓取脚本：从各平台拉取热榜数据，写入 data/*.json。

由 GitHub Actions 定时执行。单个源失败不影响其他源；
抓取为空时保留旧数据文件，避免把页面写空。
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

DATA_DIR = "data"
TIMEOUT = 25
BJ = timezone(timedelta(hours=8))

BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def get(url, headers=None):
    h = dict(BROWSER)
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=TIMEOUT).read()


def now_str():
    return datetime.now(BJ).strftime("%Y-%m-%d %H:%M")


def fmt_hot(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


# ---------------- 各平台抓取 ----------------

def fetch_weibo():
    raw = get("https://weibo.com/ajax/side/hotSearch",
              {"Referer": "https://weibo.com/"})
    items = json.loads(raw)["data"]["realtime"]
    out = []
    for it in items:
        word = it.get("word") or it.get("note") or ""
        if not word:
            continue
        url = ("https://s.weibo.com/weibo?q=%23"
               + urllib.parse.quote(word) + "%23")
        out.append({"title": word, "url": url,
                    "hot": fmt_hot(it.get("num"))})
    return out[:50]


def fetch_baidu():
    html = get("https://top.baidu.com/board?tab=realtime",
               {"Accept": "text/html"}).decode("utf-8", "ignore")
    m = re.search(r"<!--s-data:(.*?)-->", html, re.S)
    content = json.loads(m.group(1))["data"]["cards"][0]["content"]
    out = []
    for it in content:
        if not it.get("word"):
            continue
        out.append({"title": it["word"], "url": it.get("url", ""),
                    "hot": fmt_hot(it.get("hotScore"))})
    return out[:30]


def fetch_toutiao():
    raw = get("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc")
    items = json.loads(raw)["data"]
    out = []
    for it in items:
        if not it.get("Title"):
            continue
        out.append({"title": it["Title"], "url": it.get("Url", ""),
                    "hot": fmt_hot(it.get("HotValue"))})
    return out[:50]


def fetch_bilibili():
    raw = get("https://api.bilibili.com/x/web-interface/search/square?limit=20&cid=0")
    items = json.loads(raw)["data"]["trending"]["list"]
    out = []
    for it in items:
        name = it.get("show_name") or it.get("keyword") or ""
        if not name:
            continue
        url = ("https://search.bilibili.com/all?keyword="
               + urllib.parse.quote(name))
        out.append({"title": name, "url": url,
                    "hot": fmt_hot(it.get("heat_score"))})
    return out[:20]


def fetch_v2ex():
    raw = get("https://www.v2ex.com/api/topics/hot.json")
    items = json.loads(raw)
    return [{"title": it["title"],
             "url": f"https://www.v2ex.com/t/{it['id']}",
             "hot": f"{it.get('replies', 0)} 回复"}
            for it in items if it.get("title")][:20]


def fetch_sspai():
    raw = get("https://sspai.com/feed", {"Accept": "application/rss+xml"})
    root = ET.fromstring(raw)
    out = []
    for item in root.findall("./channel/item")[:20]:
        title = item.findtext("title")
        link = item.findtext("link")
        if title and link:
            out.append({"title": title.strip(), "url": link.strip(), "hot": ""})
    return out


def fetch_hackernews():
    raw = get("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30")
    hits = json.loads(raw)["hits"]
    out = []
    for h in hits:
        if not h.get("title"):
            continue
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
        out.append({"title": h["title"], "url": url,
                    "hot": f"{h.get('points', 0)} 分"})
    return out[:30]


SOURCES = [
    ("weibo", "微博热搜", "#e6162d", fetch_weibo),
    ("baidu", "百度热搜", "#2932e1", fetch_baidu),
    ("toutiao", "今日头条", "#f04142", fetch_toutiao),
    ("bilibili", "B站热搜", "#00a1d6", fetch_bilibili),
    ("v2ex", "V2EX", "#334155", fetch_v2ex),
    ("sspai", "少数派", "#d71918", fetch_sspai),
    ("hackernews", "Hacker News", "#ff6600", fetch_hackernews),
]


def main():
    import os
    os.makedirs(DATA_DIR, exist_ok=True)
    meta = {"updated_at": now_str(), "sources": []}
    ok = 0
    for sid, name, color, fn in SOURCES:
        path = os.path.join(DATA_DIR, f"{sid}.json")
        try:
            items = fn()
            if not items:
                raise ValueError("empty result")
            payload = {"id": sid, "name": name, "color": color,
                       "updated_at": now_str(), "items": items}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            meta["sources"].append({"id": sid, "name": name, "color": color,
                                    "updated_at": payload["updated_at"],
                                    "count": len(items), "status": "ok"})
            ok += 1
            print(f"OK   {sid}: {len(items)} items")
        except Exception as e:  # noqa: BLE001
            meta["sources"].append({"id": sid, "name": name, "color": color,
                                    "status": f"error: {type(e).__name__}"})
            print(f"FAIL {sid}: {type(e).__name__}: {str(e)[:120]}",
                  file=sys.stderr)
    with open(os.path.join(DATA_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"done: {ok}/{len(SOURCES)} sources ok")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
