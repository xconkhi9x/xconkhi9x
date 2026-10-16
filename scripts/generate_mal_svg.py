import urllib.request
import re
import base64
from html import unescape, escape

USERNAME = "HaribeatbreX"
USER_URL = f"https://myanimelist.net/profile/{USERNAME}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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
        "updates": updates
    }

def generate_svg(data):
    stats = data
    updates_svg = ""
    y_offset = 125

    for u in stats["updates"]:
        title_disp = escape(u["title"])
        if len(title_disp) > 42:
            title_disp = title_disp[:40] + "..."

        ep_text = escape(f"Ep. {u['episodes']}")
        score_badge = f'<text x="430" y="{y_offset + 32}" font-size="11" fill="#e3b341" text-anchor="end">★ {u["score"]}</text>' if u["score"] != "-" else ""
        
        img_tag = f'<image href="{u["b64_img"]}" x="25" y="{y_offset}" width="32" height="46" preserveAspectRatio="xMidYMid slice" clip-path="url(#poster-clip)"/>' if u["b64_img"] else f'<rect x="25" y="{y_offset}" width="32" height="46" rx="4" fill="#21262d"/>'

        updates_svg += f"""
        <!-- Anime item -->
        <g>
          {img_tag}
          <text x="68" y="{y_offset + 16}" font-size="13" font-weight="600" fill="#58a6ff" class="anime-title">{title_disp}</text>
          <text x="68" y="{y_offset + 34}" font-size="11" fill="#8b949e">{escape(u["status"])} &bull; {ep_text}</text>
          {score_badge}
        </g>
        """
        y_offset += 54

    card_height = y_offset + 10

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{card_height}" viewBox="0 0 480 {card_height}" fill="none">
    <defs>
        <clipPath id="card-clip">
            <rect width="480" height="{card_height}" rx="6"/>
        </clipPath>
        <clipPath id="poster-clip">
            <rect rx="4" width="32" height="46"/>
        </clipPath>
    </defs>
    <style>
        .title {{ font: 600 16px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #58a6ff; }}
        .header-sub {{ font: 400 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
        .stat-label {{ font: 400 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #8b949e; }}
        .stat-value {{ font: 600 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
        .anime-title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
        text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    </style>

    <!-- Background card -->
    <rect width="480" height="{card_height}" rx="6" fill="#0d1117" stroke="#30363d" stroke-width="1"/>

    <!-- Header -->
    <g transform="translate(25, 25)">
        <path d="M0 0h16v16H0z" fill="none"/>
        <!-- MAL Icon representation -->
        <rect x="0" y="0" width="18" height="18" rx="3" fill="#2e51a2"/>
        <text x="2" y="13" font-size="10" font-weight="bold" fill="#ffffff">MAL</text>
        <text x="26" y="14" class="title">MyAnimeList Activity</text>
        <text x="320" y="14" class="header-sub">@{USERNAME}</text>
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

    <!-- Recent updates -->
    {updates_svg}
</svg>"""

    with open("myanimelist.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("Generated myanimelist.svg successfully!")

if __name__ == "__main__":
    d = fetch_data()
    generate_svg(d)
