# 热榜聚合 🔥

各平台热搜一页看完：微博、百度、今日头条、B站、V2EX、少数派、Hacker News。

## 原理

纯静态站 + GitHub Actions 定时抓取，无需服务器：

- `scraper/fetch.py` — 每 30 分钟抓取各平台热榜，写入 `data/*.json`
- `.github/workflows/update.yml` — 定时任务，抓完自动 commit
- `index.html` / `app.js` / `style.css` — 纯前端，读取本地 JSON 渲染

GitHub Pages 直接托管即可，零成本。

## 本地运行

```bash
python3 scraper/fetch.py   # 抓取一次，写入 data/
python3 -m http.server      # 浏览器打开 http://localhost:8000
```
