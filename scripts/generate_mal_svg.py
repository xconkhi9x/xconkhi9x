import urllib.request
import urllib.parse
import re
import base64
from html import escape

USERNAME = "HaribeatbreX"
USER_URL = f"https://myanimelist.net/profile/{USERNAME}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_title_from_url(path):
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        slug = parts[2]
        return urllib.parse.unquote(slug).replace("_", " ")
    return "Anime"

def fetch_data():
    req = urllib.request.Request(USER_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        page_html = resp.read().decode("utf-8", errors="ignore")

    def extract(pattern, default="0"):
        m = re.search(pattern, page_html)
        return m.group(1).strip() if m else default

    days = extract(r"Days:\s*</span>([\d\.]+)", "0")
    mean = extract(r"Mean Score:\s*</span>\s*<span[^>]*>([\d\.]+)", "0")
    watching = extract(r'animelist/' + USERNAME + r'\?status=1\"[^>]*>Watching</a><span[^>]*>([\d,]+)', "0")
    completed = extract(r'animelist/' + USERNAME + r'\?status=2\"[^>]*>Completed</a><span[^>]*>([\d,]+)', "0")
    dropped = extract(r'animelist/' + USERNAME + r'\?status=4\"[^>]*>Dropped</a><span[^>]*>([\d,]+)', "0")
    plantowatch = extract(r'animelist/' + USERNAME + r'\?status=6\"[^>]*>Plan to Watch</a><span[^>]*>([\d,]+)', "0")
    episodes = extract(r"Episodes</span><span[^>]*>([\d,]+)", "0")

    # Watching this season
    season_items = []
    idx_season = page_html.find("Watching this season")
    end_season = page_html.find("Last completed anime")
    if idx_season != -1 and end_season != -1:
        sec = page_html[idx_season:end_season]
        matches = re.findall(r'<li class="l-listitem-list-item">\s*<a href="([^"]+)">\s*<img src="([^"]+)"', sec)
        for link, img_url in matches[:6]:
            title = clean_title_from_url(link)
            b64_img = ""
            try:
                ireq = urllib.request.Request(img_url, headers=HEADERS)
                with urllib.request.urlopen(ireq, timeout=8) as iresp:
                    b64_img = "data:image/jpeg;base64," + base64.b64encode(iresp.read()).decode("utf-8")
            except Exception as e:
                print(f"Error img: {e}")
            season_items.append({
                "title": title,
                "b64_img": b64_img,
                "url": f"https://myanimelist.net{link}"
            })

    # Last anime updates
    anime_sec = page_html.split('class="updates anime"')[1].split('class="updates manga"')[0] if 'class="updates anime"' in page_html else ""
    blocks = re.findall(r'<div class="statistics-updates di-b w100 mb8">(.*?)</div>\s*</div>\s*</div>', anime_sec, re.DOTALL)

    updates = []
    for b in blocks[:2]:
        img_m = re.search(r'data-src="([^"]+)"', b)
        title_m = re.search(r'<a href="https://myanimelist\.net/anime/\d+/[^"]+">([^<]+)</a>', b)
        eps_m = re.search(r'<span class="text anime [^"]+">(\d+)</span>/(\d+|\?)', b)
        score_m = re.search(r'Scored\s*<span[^>]*>(\d+)</span>', b)

        title = title_m.group(1).strip() if title_m else "Unknown"
        img_url = img_m.group(1) if img_m else None
        curr_ep = eps_m.group(1) if eps_m else "?"
        tot_ep = eps_m.group(2) if eps_m else "?"
        score = score_m.group(1) if score_m else None

        b64_img = ""
        if img_url:
            try:
                ireq = urllib.request.Request(img_url, headers=HEADERS)
                with urllib.request.urlopen(ireq, timeout=8) as iresp:
                    b64_img = "data:image/jpeg;base64," + base64.b64encode(iresp.read()).decode("utf-8")
            except Exception as e:
                print(f"Error img: {e}")

        updates.append({
            "title": title,
            "b64_img": b64_img,
            "progress": f"{curr_ep}/{tot_ep}",
            "score": score
        })

    return {
        "days": days,
        "mean": mean,
        "watching": watching,
        "completed": completed,
        "dropped": dropped,
        "plantowatch": plantowatch,
        "episodes": episodes,
        "season_items": season_items,
        "updates": updates
    }

def render_svg(data):
    # exact CSS styles and layout from lowlighter/metrics classic template
    season_html = ""
    for item in data["season_items"]:
        title_disp = escape(item["title"])
        if len(title_disp) > 13:
            title_disp = title_disp[:12] + "…"
        season_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center; width:64px; margin:0 4px;">
            <img src="{item['b64_img']}" width="60" height="85" style="border-radius:6px; object-fit:cover; box-shadow:0 2px 6px rgba(0,0,0,0.4);" alt="" />
            <span style="font-size:10px; color:#8b949e; margin-top:5px; text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; width:64px;">{title_disp}</span>
        </div>
        """

    updates_html = ""
    for u in data["updates"]:
        score_span = f'<span style="color:#e3b341; margin-left:12px; font-weight:600;">★ {u["score"]}</span>' if u["score"] else ""
        updates_html += f"""
        <div class="media" style="display:flex; align-items:center; margin-bottom:10px; width:450px;">
            <img src="{u['b64_img']}" width="38" height="54" style="border-radius:6px; object-fit:cover; margin-right:12px;" alt="" />
            <div class="about" style="flex-grow:1; min-width:0;">
                <div class="name" style="font-size:13px; font-weight:600; color:#58a6ff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:390px;">{escape(u['title'])}</div>
                <div class="infos" style="font-size:12px; color:#8b949e; margin-top:3px; display:flex; align-items:center;">
                    <span>Watching • Episode {escape(u['progress'])}</span>
                    {score_span}
                </div>
            </div>
        </div>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="385" class="">
    <defs>
        <style/>
    </defs>
    <style>
        svg {{
            font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif, Apple Color Emoji, Segoe UI Emoji;
            font-size: 14px;
            color: #777;
        }}
        h2 {{
            margin: 8px 0 6px;
            padding: 0;
            color: #0366d6;
            font-weight: 400;
            font-size: 16px;
        }}
        h2 svg {{
            fill: currentColor;
        }}
        .field {{
            display: flex;
            align-items: center;
            margin-bottom: 2px;
            white-space: nowrap;
        }}
        .field svg {{
            margin: 0 8px;
            fill: #959da5;
            flex-shrink: 0;
        }}
        .row {{
            display: flex;
            flex-wrap: wrap;
        }}
        .row section {{
            flex: 1 1 0;
        }}
        .fill-width {{
            width: 100%;
        }}
        .anilist {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            margin-left: 28px;
            margin-top: 4px;
        }}
        :root {{
            --color-text-primary: #58a6ff;
            --color-text-secondary: #8b949e;
        }}
    </style>
    <foreignObject x="0" y="0" width="100%" height="100%">
        <div xmlns="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink" class="items-wrapper">
            <section>
                <h2 class="field">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                        <path fill-rule="evenodd" d="M4.75 2.5a.25.25 0 00-.25.25v9.91l3.023-2.489a.75.75 0 01.954 0l3.023 2.49V2.75a.25.25 0 00-.25-.25h-6.5zM3 2.75C3 1.784 3.784 1 4.75 1h6.5c.966 0 1.75.784 1.75 1.75v11.5a.75.75 0 01-1.227.579L8 11.722l-3.773 3.107A.75.75 0 013 14.25V2.75z"/>
                    </svg>
                    MyAnimeList
                </h2>
                <div class="row fill-width">
                    <section>
                        <div class="field">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                                <path fill-rule="evenodd" d="M1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0zM8 0a8 8 0 100 16A8 8 0 008 0zm.5 4.75a.75.75 0 00-1.5 0v3.5a.75.75 0 00.37.65l2.5 1.5a.75.75 0 00.76-1.3L8.5 7.96V4.75z"/>
                            </svg>
                            {data['days']} days watched ({data['episodes']} episodes)
                        </div>
                        <div class="field">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                                <path d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
                            </svg>
                            {data['mean']} mean score
                        </div>
                    </section>
                    <section>
                        <div class="field">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                                <path fill-rule="evenodd" d="M16 3.75a.75.75 0 00-1.136-.643L11 5.425V4.75A1.75 1.75 0 009.25 3h-7.5A1.75 1.75 0 000 4.75v6.5C0 12.216.784 13 1.75 13h7.5A1.75 1.75 0 0011 11.25v-.675l3.864 2.318A.75.75 0 0016 12.25v-8.5z"/>
                            </svg>
                            {data['watching']} watching, {data['completed']} completed
                        </div>
                        <div class="field">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                                <path fill-rule="evenodd" d="M0 2.75C0 1.784.784 1 1.75 1h12.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0114.25 15H1.75A1.75 1.75 0 010 13.25V2.75zm1.75-.25a.25.25 0 00-.25.25v10.5c0 .138.112.25.25.25h12.5a.25.25 0 00.25-.25V2.75a.25.25 0 00-.25-.25H1.75zM4 4.5a.75.75 0 01.75.75v5.5a.75.75 0 01-1.5 0v-5.5A.75.75 0 014 4.5zm4 0a.75.75 0 01.75.75v5.5a.75.75 0 01-1.5 0v-5.5A.75.75 0 018 4.5zm4 0a.75.75 0 01.75.75v5.5a.75.75 0 01-1.5 0v-5.5a.75.75 0 01.75-.75z"/>
                            </svg>
                            {data['plantowatch']} plan to watch, {data['dropped']} dropped
                        </div>
                    </section>
                </div>
            </section>
            <section style="margin-top:14px;">
                <h2 class="field">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                        <path fill-rule="evenodd" d="M1.5 3A1.5 1.5 0 000 4.5v7A1.5 1.5 0 001.5 13h13a1.5 1.5 0 001.5-1.5v-7A1.5 1.5 0 0014.5 3h-13zm0 1.5h13a.5.5 0 01.5.5v7a.5.5 0 01-.5.5h-13a.5.5 0 01-.5-.5v-7a.5.5 0 01.5-.5z"/>
                    </svg>
                    Watching this season
                </h2>
                <div style="display:flex; justify-content:space-between; margin:8px 0 12px 14px; width:450px;">
                    {season_html}
                </div>
            </section>
            <section style="margin-top:8px;">
                <h2 class="field">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                        <path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z"/>
                    </svg>
                    Recent updates
                </h2>
                <div class="anilist" style="margin-left:14px; margin-top:6px;">
                    {updates_html}
                </div>
            </section>
        </div>
        <div xmlns="http://www.w3.org/1999/xhtml" id="metrics-end"></div>
    </foreignObject>
</svg>"""

    with open("myanimelist.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Rendered exact lowlighter/metrics style SVG successfully!")

if __name__ == "__main__":
    d = fetch_data()
    render_svg(d)
