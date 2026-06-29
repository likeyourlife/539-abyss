"""数据抓取 - 从多个源获取开奖数据

数据源优先级：
1. i539.tw 主页（近20期，最可靠）
2. lottolyzer（全量历史，50页/页）
3. lottery.timetable.tw（3267期全量）
"""

import re
import json
from datetime import date, datetime
from typing import List, Optional
from .models import Draw

try:
    import httpx
    _USE_HTTPX = True
except ImportError:
    import urllib.request
    _USE_HTTPX = False

try:
    from bs4 import BeautifulSoup
    _USE_BS4 = True
except ImportError:
    _USE_BS4 = False


def _fetch_url(url: str) -> str:
    """获取URL内容"""
    if _USE_HTTPX:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")


def _parse_html_smart(html: str) -> str:
    """用BeautifulSoup解析HTML，返回结构化文本"""
    if _USE_BS4:
        soup = BeautifulSoup(html, "html.parser")
        # 提取所有文本内容，保留结构信息
        return soup.get_text(separator="\n")
    else:
        # 去除HTML标签
        return re.sub(r'<[^>]+>', '\n', html)


def fetch_i539_recent() -> List[Draw]:
    """从i539.tw主页抓取近20期数据

    页面结构：
    <table class="lau-history">
      <tr>
        <td class="lau-td-date">2026/06/27 (六)</td>
        <td class="lau-td-numbers">
          <span class="lau-mini-ball">04</span>
          <span class="lau-mini-ball">14</span>
          ...
        </td>
      </tr>
    </table>
    """
    url = "https://i539.tw/"

    try:
        html = _fetch_url(url)
    except Exception as e:
        print(f"i539.tw 抓取失败: {e}")
        return []

    draws = []

    if _USE_BS4:
        soup = BeautifulSoup(html, "html.parser")
        # 找到历史数据表格
        history_table = soup.find("table", class_=re.compile("lau-history"))
        if history_table:
            for tr in history_table.find_all("tr"):
                date_td = tr.find("td", class_=re.compile("lau-td-date"))
                nums_td = tr.find("td", class_=re.compile("lau-td-numbers"))

                if date_td and nums_td:
                    try:
                        # 提取日期
                        date_text = date_td.get_text(strip=True)
                        # 格式: "2026/06/27 (六)"
                        date_str = re.match(r'(\d{4}/\d{2}/\d{2})', date_text).group(1)
                        draw_date = datetime.strptime(date_str, "%Y/%m/%d").date()

                        # 提取号码球
                        balls = nums_td.find_all("span", class_=re.compile("lau-mini-ball|lau-ball"))
                        numbers = [int(b.get_text(strip=True)) for b in balls
                                   if b.get_text(strip=True).isdigit() and 1 <= int(b.get_text(strip=True)) <= 39]

                        if len(numbers) == 5:
                            draw_id = f"i539_{draw_date.isoformat()}"
                            draws.append(Draw(
                                draw_id=draw_id,
                                draw_date=draw_date,
                                numbers=sorted(numbers),
                                source="i539",
                            ))
                    except Exception:
                        continue
    else:
        # 正则解析（无BS4）
        # 匹配: lau-td-date + lau-mini-ball 模式
        row_pattern = re.compile(
            r'lau-td-date[^>]*>\s*(\d{4}/\d{2}/\d{2})[^<]*<.*?'
            r'lau-td-numbers[^>]*>(.*?)</td>',
            re.DOTALL
        )
        ball_pattern = re.compile(r'lau-mini-ball[^>]*>\s*(\d{1,2})\s*<')

        for match in row_pattern.finditer(html):
            try:
                date_str = match.group(1)
                draw_date = datetime.strptime(date_str, "%Y/%m/%d").date()
                nums_html = match.group(2)
                numbers = [int(b) for b in ball_pattern.findall(nums_html)
                           if 1 <= int(b) <= 39]

                if len(numbers) == 5:
                    draw_id = f"i539_{draw_date.isoformat()}"
                    draws.append(Draw(
                        draw_id=draw_id,
                        draw_date=draw_date,
                        numbers=sorted(numbers),
                        source="i539",
                    ))
            except Exception:
                continue

    draws.sort(key=lambda d: d.draw_date)
    return draws


def fetch_lottolyzer_page(page: int = 1, per_page: int = 50) -> List[Draw]:
    """从lottolyzer抓取单页数据

    正确URL格式: cn.lottolyzer.com/history/taiwan/daily-cash-539/page/{page}/per-page/{per_page}/number-view
    """
    url = f"https://cn.lottolyzer.com/history/taiwan/daily-cash-539/page/{page}/per-page/{per_page}/number-view"

    try:
        html = _fetch_url(url)
    except Exception as e:
        print(f"lottolyzer 第{page}页抓取失败: {e}")
        return []

    if _USE_BS4:
        soup = BeautifulSoup(html, "html.parser")
        draws = _parse_lottolyzer_bs4(soup)
    else:
        draws = _parse_lottolyzer_regex(html)

    return draws


def _parse_lottolyzer_bs4(soup) -> List[Draw]:
    """用BeautifulSoup解析lottolyzer页面

    页面结构：
    - 期号: <div>第115000156期</div>
    - 日期: <div class="date">2026年06月27日</div>
    - 号码球: <img class="ball" src="//cdn.lottolyzer.com/images/ball04.gif" alt="4" title="4">
    """
    draws = []

    # 找所有号码球img元素
    ball_imgs = soup.find_all("img", class_="ball")

    # 找所有期号和日期
    # 期号在普通div中，日期在 class="date" 的div中
    period_divs = soup.find_all("div", string=re.compile(r'第\d+期'))
    date_divs = soup.find_all("div", class_=re.compile(r'date'))

    # 每期有5个球，50期=250个球
    expected_periods = len(ball_imgs) // 5

    if expected_periods > 0 and len(period_divs) >= expected_periods and len(date_divs) >= expected_periods:
        for i in range(expected_periods):
            try:
                # 提取期号
                period_text = period_divs[i].get_text(strip=True)
                draw_id_match = re.search(r'(\d+)', period_text)
                draw_id = draw_id_match.group(1) if draw_id_match else f"lotto_{i}"

                # 提取日期
                date_text = date_divs[i].get_text(strip=True)
                date_match = re.search(r'(\d{4})年(\d{2})月(\d{2})日', date_text)
                if date_match:
                    y, m, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                    draw_date = date(y, m, d)
                else:
                    continue

                # 提取号码
                start_idx = i * 5
                end_idx = start_idx + 5
                if end_idx > len(ball_imgs):
                    break

                numbers = []
                for img in ball_imgs[start_idx:end_idx]:
                    # 从alt或title属性获取号码
                    alt = img.get("alt", "")
                    title = img.get("title", "")
                    # 也从src提取（ball04.gif → 4）
                    src = img.get("src", "")
                    src_match = re.search(r'ball(\d{1,2})\.gif', src)

                    n = None
                    if alt.isdigit():
                        n = int(alt)
                    elif title.isdigit():
                        n = int(title)
                    elif src_match:
                        n = int(src_match.group(1))

                    if n and 1 <= n <= 39:
                        numbers.append(n)

                if len(numbers) == 5:
                    draws.append(Draw(
                        draw_id=draw_id,
                        draw_date=draw_date,
                        numbers=sorted(numbers),
                        source="lottolyzer",
                    ))
            except Exception:
                continue

    return draws


def _parse_lottolyzer_regex(html: str) -> List[Draw]:
    """纯正则解析lottolyzer页面（无BeautifulSoup时）

    格式：
    期号: 第115000156期</div>
    日期: <div class="...date">2026年06月27日</div>
    球: <img class="ball" src="...ball04.gif" alt="4" title="4">
    """
    draws = []

    # 提取所有期号
    period_matches = list(re.finditer(r'第(\d+)期', html))
    # 提取所有日期
    date_matches = list(re.finditer(r'(\d{4})年(\d{2})月(\d{2})日', html))
    # 提取所有号码球（从img src或alt/title）
    ball_pattern = re.compile(r'class="ball"[^>]*src="[^"]*ball(\d{1,2})\.gif[^"]*"[^>]*(?:alt="(\d{1,2})"[^>]*title="(\d{1,2})")?')
    balls_raw = []
    for m in ball_pattern.finditer(html):
        # 优先用alt/title，回退到src中的数字
        n = None
        for g in [m.group(2), m.group(3), m.group(1)]:
            if g and g.isdigit():
                n = int(g)
                break
        if n and 1 <= n <= 39:
            balls_raw.append(n)

    # 如果alt/title模式不匹配，用更宽松的匹配
    if not balls_raw:
        ball_pattern2 = re.compile(r'class="ball"[^>]*alt="(\d{1,2})"')
        balls_raw = [int(m.group(1)) for m in ball_pattern2.finditer(html)
                     if m.group(1).isdigit() and 1 <= int(m.group(1)) <= 39]

    if not balls_raw:
        ball_pattern3 = re.compile(r'ball(\d{1,2})\.gif')
        balls_raw = [int(m.group(1)) for m in ball_pattern3.finditer(html)
                     if 1 <= int(m.group(1)) <= 39]

    expected_periods = len(balls_raw) // 5

    if expected_periods > 0 and len(period_matches) >= expected_periods and len(date_matches) >= expected_periods:
        for i in range(expected_periods):
            try:
                draw_id = period_matches[i].group(1)
                y, m, d = int(date_matches[i].group(1)), int(date_matches[i].group(2)), int(date_matches[i].group(3))
                draw_date = date(y, m, d)

                start_idx = i * 5
                numbers = balls_raw[start_idx:start_idx + 5]

                if len(numbers) == 5 and all(1 <= n <= 39 for n in numbers):
                    draws.append(Draw(
                        draw_id=draw_id,
                        draw_date=draw_date,
                        numbers=sorted(numbers),
                        source="lottolyzer",
                    ))
            except Exception:
                continue

    return draws


def fetch_lottolyzer_all(max_pages: int = 20) -> List[Draw]:
    """从lottolyzer抓取多页数据（获取更多历史）

    Args:
        max_pages: 最大页数（每页50期，20页=1000期）
    """
    all_draws = []
    for page in range(1, max_pages + 1):
        page_draws = fetch_lottolyzer_page(page)
        if not page_draws:
            print(f"lottolyzer 第{page}页无数据，停止翻页")
            break
        all_draws.extend(page_draws)
        print(f"lottolyzer 第{page}页: {len(page_draws)}期")

    # 去重和排序
    seen = set()
    unique = []
    for d in all_draws:
        key = d.draw_date.isoformat()
        if key not in seen:
            seen.add(key)
            unique.append(d)

    unique.sort(key=lambda d: d.draw_date)
    return unique


def fetch_timetable() -> List[Draw]:
    """从lottery.timetable.tw抓取全量数据（3267期）

    URL: https://lottery.timetable.tw/draws/jin-cai-539
    """
    url = "https://lottery.timetable.tw/draws/jin-cai-539"

    try:
        html = _fetch_url(url)
    except Exception as e:
        print(f"timetable 抓取失败: {e}")
        return []

    if _USE_BS4:
        soup = BeautifulSoup(html, "html.parser")
        draws = _parse_timetable_bs4(soup)
    else:
        draws = _parse_timetable_regex(html)

    return draws


def _parse_timetable_bs4(soup) -> List[Draw]:
    """解析timetable页面"""
    draws = []

    # 查找表格行
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 3:
                texts = [td.get_text(strip=True) for td in tds]
                draw = _try_parse_draw_row(texts)
                if draw:
                    draws.append(draw)

    # 也查找非表格格式的数据
    text = soup.get_text(separator="\n")

    # 匹配日期 + 号码模式
    pattern = re.compile(
        r'(\d{4}[/-]\d{2}[/-]\d{2})\s+'
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})'
    )
    for match in pattern.finditer(text):
        try:
            date_str = match.group(1)
            numbers = [int(match.group(i)) for i in range(2, 7)]
            if all(1 <= n <= 39 for n in numbers):
                draw_date = datetime.strptime(date_str.replace("/", "-"), "%Y-%m-%d").date()
                draws.append(Draw(
                    draw_id=f"tt_{draw_date.isoformat()}",
                    draw_date=draw_date,
                    numbers=sorted(numbers),
                    source="timetable",
                ))
        except Exception:
            continue

    draws.sort(key=lambda d: d.draw_date)
    return draws


def _parse_timetable_regex(html: str) -> List[Draw]:
    """纯正则解析timetable页面"""
    draws = []
    text = re.sub(r'<[^>]+>', ' ', html)

    pattern = re.compile(
        r'(\d{4}[/-]\d{2}[/-]\d{2})\s+'
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})'
    )
    for match in pattern.finditer(text):
        try:
            date_str = match.group(1)
            numbers = [int(match.group(i)) for i in range(2, 7)]
            if all(1 <= n <= 39 for n in numbers):
                draw_date = datetime.strptime(date_str.replace("/", "-"), "%Y-%m-%d").date()
                draws.append(Draw(
                    draw_id=f"tt_{draw_date.isoformat()}",
                    draw_date=draw_date,
                    numbers=sorted(numbers),
                    source="timetable",
                ))
        except Exception:
            continue

    draws.sort(key=lambda d: d.draw_date)
    return draws


def _try_parse_draw_row(cells: List[str]) -> Optional[Draw]:
    """尝试从一行文本数据中解析出Draw"""
    # 寻找日期
    date_str = None
    for cell in cells:
        if re.match(r"\d{4}[/-]\d{2}[/-]\d{2}", cell):
            date_str = cell
            break

    # 寻找号码
    numbers = []
    for cell in cells:
        cell = cell.strip()
        if cell.isdigit():
            n = int(cell)
            if 1 <= n <= 39:
                numbers.append(n)

    # 寻找期号
    draw_id = None
    for cell in cells:
        if re.match(r"11\d+", cell.strip()):
            draw_id = cell.strip()

    if len(numbers) == 5 and date_str:
        try:
            draw_date = datetime.strptime(date_str.replace("/", "-"), "%Y-%m-%d").date()
            return Draw(
                draw_id=draw_id or f"auto_{draw_date.isoformat()}",
                draw_date=draw_date,
                numbers=sorted(numbers),
                source="parse",
            )
        except Exception:
            return None
    return None


def fetch_full_history() -> List[Draw]:
    """获取尽可能多的历史数据

    优先级：i539近20期 + lottolyzer多页 + timetable全量
    自动去重和合并
    """
    print("开始获取历史数据...")

    # 第一步：i539近20期（最新数据）
    recent = fetch_i539_recent()
    print(f"i539近20期: {len(recent)}期")

    # 第二步：lottolyzer多页（历史数据）
    history = fetch_lottolyzer_all(max_pages=20)
    print(f"lottolyzer: {len(history)}期")

    # 合并去重
    all_draws = recent + history
    seen = set()
    unique = []
    for d in all_draws:
        key = d.draw_date.isoformat()
        if key not in seen:
            seen.add(key)
            unique.append(d)

    # 如果数据太少，尝试timetable
    if len(unique) < 100:
        print("数据不足100期，尝试timetable...")
        tt_draws = fetch_timetable()
        for d in tt_draws:
            key = d.draw_date.isoformat()
            if key not in seen:
                seen.add(key)
                unique.append(d)
        print(f"timetable: {len(tt_draws)}期")

    unique.sort(key=lambda d: d.draw_date)
    print(f"合并去重后: {len(unique)}期")
    return unique


def fetch_latest() -> List[Draw]:
    """抓取最新数据（仅最近几期），用于日常更新"""
    recent = fetch_i539_recent()
    if recent:
        return recent

    # i539失败时，用lottolyzer第1页
    draws = fetch_lottolyzer_page(1)
    return draws[:20] if len(draws) > 20 else draws
