import urllib.request
import urllib.parse
import re
import base64
from html import unescape, escape

USERNAME = "HaribeatbreX"
USER_URL = f"https://myanimelist.net/profile/{USERNAME}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_title_from_url(path):
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        slug = parts[2]
        title = urllib.parse.unquote(slug).replace("_", " ")
        return title
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
    total = extract(r"Total Entries</span><span[^>]*>([\d,]+)", "0")
    episodes = extract(r"Episodes</span><span[^>]*>([\d,]+)", "0")

    # 1. Watching This Season posters (grid)
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
                print(f"Error fetching season poster {img_url}: {e}")
            season_items.append({
                "title": title,
                "b64_img": b64_img,
                "url": f"https://myanimelist.net{link}" if link.startswith("/") else link
            })

    # 2. Last Anime Updates
    anime_sec = page_html.split('class="updates anime"')[1].split('class="updates manga"')[0] if 'class="updates anime"' in page_html else ""
    blocks = re.findall(r'<div class="statistics-updates di-b w100 mb8">(.*?)</div>\s*</div>\s*</div>', anime_sec, re.DOTALL)

    updates = []
    for b in blocks[:3]:
        img_m = re.search(r'data-src="([^"]+)"', b)
        title_m = re.search(r'<a href="https://myanimelist\.net/anime/\d+/[^"]+">([^<]+)</a>', b)
        status_m = re.search(r'<div class="fn-grey2">\s*([A-Za-z]+)', b)
        eps_m = re.search(r'<span class="text anime [^"]+">(\d+)</span>/(\d+|\?)', b)
        score_m = re.search(r'Scored\s*<span[^>]*>(\d+)</span>', b)

        title = unescape(title_m.group(1)) if title_m else "Unknown"
        img_url = img_m.group(1) if img_m else None
        status = status_m.group(1) if status_m else "Watching"
        curr_ep = eps_m.group(1) if eps_m else "?"
        tot_ep = eps_m.group(2) if eps_m else "?"
        score = score_m.group(1) if score_m else "-"

        b64_img = ""
        if img_url:
            try:
                ireq = urllib.request.Request(img_url, headers=HEADERS)
                with urllib.request.urlopen(ireq, timeout=8) as iresp:
                    b64_img = "data:image/jpeg;base64," + base64.b64encode(iresp.read()).decode("utf-8")
            except Exception as e:
                print(f"Could not load image {img_url}: {e}")

        updates.append({
            "title": title,
            "b64_img": b64_img,
            "status": status,
            "episodes": f"{curr_ep}/{tot_ep}",
            "score": score
        })

    return {
        "days": days,
        "mean": mean,
        "watching": watching,
        "completed": completed,
        "dropped": dropped,
        "plantowatch": plantowatch,
        "total": total,
        "episodes": episodes,
        "season_items": season_items,
        "updates": updates
    }

def generate_svg(data):
    stats = data
    card_width = 480
    
    # Season section
    season_svg = ""
    y_cursor = 120
    if stats["season_items"]:
        season_svg += f"""
        <!-- Watching This Season Section -->
        <g transform="translate(25, {y_cursor})">
            <text x="0" y="0" font-size="12" font-weight="600" fill="#f0883e">WATCHING THIS SEASON</text>
        </g>
        """
        y_cursor += 12
        poster_w = 64
        poster_h = 92
        gap = 9
        start_x = 25
        for i, item in enumerate(stats["season_items"]):
            px = start_x + i * (poster_w + gap)
            img_tag = f'<image href="{item["b64_img"]}" x="{px}" y="{y_cursor}" width="{poster_w}" height="{poster_h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#season-clip)"/>' if item["b64_img"] else f'<rect x="{px}" y="{y_cursor}" width="{poster_w}" height="{poster_h}" rx="5" fill="#21262d"/>'
            
            title_clean = escape(item["title"])
            if len(title_clean) > 11:
                title_clean = title_clean[:10] + ".."

            season_svg += f"""
            <g>
                {img_tag}
                <text x="{px + poster_w // 2}" y="{y_cursor + poster_h + 14}" font-size="10" fill="#8b949e" text-anchor="middle">{title_clean}</text>
            </g>
            """
        y_cursor += poster_h + 26
        season_svg += f'<line x1="25" y1="{y_cursor}" x2="455" y2="{y_cursor}" stroke="#21262d" stroke-width="1"/>'
        y_cursor += 18

    # Recent updates section
    updates_svg = ""
    if stats["updates"]:
        updates_svg += f"""
        <g transform="translate(25, {y_cursor})">
            <text x="0" y="0" font-size="12" font-weight="600" fill="#58a6ff">LATEST UPDATES</text>
        </g>
        """
        y_cursor += 12
        for u in stats["updates"]:
            title_disp = escape(u["title"])
            if len(title_disp) > 42:
                title_disp = title_disp[:40] + "..."

            ep_text = escape(f"Ep. {u['episodes']}")
            score_badge = f'<text x="455" y="{y_cursor + 28}" font-size="11" font-weight="600" fill="#e3b341" text-anchor="end">★ {u["score"]}</text>' if u["score"] != "-" else ""
            
            img_tag = f'<image href="{u["b64_img"]}" x="25" y="{y_cursor}" width="30" height="42" preserveAspectRatio="xMidYMid slice" clip-path="url(#update-clip)"/>' if u["b64_img"] else f'<rect x="25" y="{y_cursor}" width="30" height="42" rx="4" fill="#21262d"/>'

            updates_svg += f"""
            <g>
              {img_tag}
              <text x="65" y="{y_cursor + 15}" font-size="13" font-weight="600" fill="#c9d1d9">{title_disp}</text>
              <text x="65" y="{y_cursor + 32}" font-size="11" fill="#8b949e">{escape(u["status"])} • {ep_text}</text>
              {score_badge}
            </g>
            """
            y_cursor += 50

    card_height = y_cursor + 10

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}" fill="none">
    <defs>
        <clipPath id="season-clip">
            <rect rx="5" width="64" height="92"/>
        </clipPath>
        <clipPath id="update-clip">
            <rect rx="4" width="30" height="42"/>
        </clipPath>
    </defs>
    <style>
        .title {{ font: 600 15px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #58a6ff; }}
        .header-sub {{ font: 400 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
        .stat-label {{ font: 400 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
        .stat-value {{ font: 600 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
        text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    </style>

    <!-- Background card -->
    <rect width="{card_width}" height="{card_height}" rx="6" fill="#0d1117" stroke="#30363d" stroke-width="1"/>

    <!-- Header -->
    <g transform="translate(25, 25)">
        <rect x="0" y="0" width="18" height="18" rx="3" fill="#2e51a2"/>
        <text x="2" y="13" font-size="10" font-weight="bold" fill="#ffffff">MAL</text>
        <text x="26" y="14" class="title">MyAnimeList Activity</text>
        <text x="430" y="14" class="header-sub" text-anchor="end">@{USERNAME}</text>
    </g>

    <!-- Divider -->
    <line x1="25" y1="52" x2="455" y2="52" stroke="#21262d" stroke-width="1"/>

    <!-- Stats grid row 1 -->
    <g transform="translate(25, 70)">
        <text x="0" y="0" class="stat-label">Days Watched:</text>
        <text x="85" y="0" class="stat-value">{stats["days"]}</text>

        <text x="145" y="0" class="stat-label">Mean Score:</text>
        <text x="220" y="0" class="stat-value">{stats["mean"]}</text>

        <text x="280" y="0" class="stat-label">Episodes:</text>
        <text x="340" y="0" class="stat-value">{stats["episodes"]}</text>
    </g>

    <!-- Stats grid row 2 -->
    <g transform="translate(25, 92)">
        <text x="0" y="0" class="stat-label">Watching: <tspan class="stat-value">{stats["watching"]}</tspan></text>
        <text x="100" y="0" class="stat-label">Completed: <tspan class="stat-value">{stats["completed"]}</tspan></text>
        <text x="210" y="0" class="stat-label">Dropped: <tspan class="stat-value">{stats["dropped"]}</tspan></text>
        <text x="290" y="0" class="stat-label">Planned: <tspan class="stat-value">{stats["plantowatch"]}</tspan></text>
    </g>

    <!-- Divider -->
    <line x1="25" y1="108" x2="455" y2="108" stroke="#21262d" stroke-width="1"/>

    <!-- Watching this season grid -->
    {season_svg}

    <!-- Recent updates -->
    {updates_svg}
</svg>"""

    with open("myanimelist.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated myanimelist.svg ({card_width}x{card_height}) successfully!")

if __name__ == "__main__":
    d = fetch_data()
    generate_svg(d)
