#!/usr/bin/env python3
"""Рынок профессии: где практики обсуждают работу, и что оттуда взять в тренажёр.

Источники берутся из таблицы <field>/sources.md, словарь темы — из <field>/vocab.txt.
Ничего не зашито под конкретную профессию. Только стандартная библиотека Python.

Команды:
    field.py find-se <слово> [слово ...]        сайты Stack Exchange по теме
    field.py find-reddit <префикс> [...] [--min-subs N]  сабреддиты по началу названия
    field.py check <field>                      живы ли источники из sources.md
    field.py harvest <field> [--days N]         собрать посты в <field>/raw/<дата>.json
    field.py digest <field> [--since ДАТА] [--top N]  выжимка свежего сырья для отбора семян
    field.py yield <field>                      сколько семян дал каждый источник

Типы источников в sources.md (колонки «Тип» и «Адрес»):
    telegram       имя публичного канала без @
    reddit         имя сабреддита без r/
    stackexchange  сайт или сайт:тег, например ux, serverfault:monitoring, stackoverflow:kubernetes
    hn             поисковый запрос к Hacker News
    rss            адрес RSS- или Atom-ленты: хабы Хабра, теги dev.to и Medium, блоги
    поиск          поисковый запрос вроде «site:vc.ru <тема> кейс» — скрипт его пропускает,
                   такие источники Claude читает своими инструментами поиска
"""
import argparse
import gzip
import html
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MIN_LEN = 200
CUT = 450
DROP_AFTER = 3
NOISE = re.compile(
    r"вебинар|регистрац|скидк|промокод|интенсив|розыгрыш|#вакансия|вакансия|подпишитесь|реклама|"
    r"webinar|sponsored|discount|promo code|giveaway|we.re hiring|sign up now",
    re.IGNORECASE,
)
# Вакансии и поиск работы — никогда не семена; проверяется только начало поста
JOBS = re.compile(
    r"\[hiring\]|\bhiring\b|вакансi|ищу работу|ищем в команду|open to work|available for (work|hire)|"
    r"looking for\W{0,4}(new\W+)?(opportunit|a job|work\b|roles?\b|positions?)",
    re.IGNORECASE,
)
KINDS = {
    "вопрос": re.compile(
        r"\?|подскаж|посоветуйт|что делать|как (лучше|быть|правильно)|кто.нибудь|"
        r"how (do|should|can) (i|we|you)|any advice|what would you|should i|is it normal",
        re.IGNORECASE),
    "ситуация": re.compile(
        r"\b(я|мы|меня|мне|нас|нам|мой|моя|наш|наша|у нас|i|i'm|i've|my|we|our|us)\b", re.IGNORECASE),
    "спор": re.compile(
        r"миф|холивар|не соглас|переоцен|на самом деле|спорн|unpopular opinion|overrated|myth|"
        r"hot take|controvers|disagree|\bvs\.?\b",
        re.IGNORECASE),
    "совет": re.compile(
        r"советую|рекоменд|книг|must.read|recommend|reading list|resources|best (book|course|tool)",
        re.IGNORECASE),
}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data, r.geturl()


def get_json(url, timeout=40):
    try:
        return json.loads(get(url, timeout)[0].decode("utf-8"))
    except urllib.error.HTTPError as e:
        # архив Reddit под нагрузкой отвечает 422 с {"error": "Timeout..."} — это повод повторить, а не сбой
        if e.code in (422, 429, 503):
            try:
                return json.loads(e.read().decode("utf-8")) or {"error": str(e)}
            except ValueError:
                return {"error": str(e)}
        raise


def clean(text):
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def noisy(text):
    return len(NOISE.findall(text)) >= 2 or bool(JOBS.search(text[:300]))


# ---------- адаптеры: каждый возвращает список постов ----------

class _TGParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.posts, self.cur, self.depth, self.buf = [], None, 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "data-post" in a:
                self.cur = {"post": a["data-post"], "text": "", "date": None}
                self.posts.append(self.cur)
            elif self.cur is not None and "js-message_text" in cls and not self.cur["text"]:
                self.depth, self.buf = 1, []
        elif tag == "br" and self.depth:
            self.buf.append("\n")
        elif tag == "time" and self.cur is not None and a.get("datetime") and not self.cur["date"]:
            self.cur["date"] = a["datetime"]

    def handle_endtag(self, tag):
        if tag == "div" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.cur["text"] = "".join(self.buf).strip()

    def handle_data(self, data):
        if self.depth:
            self.buf.append(data)


def telegram(channel, since, pages):
    posts, before = [], None
    for _ in range(pages):
        url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
        body, final = get(url)
        if "/s/" not in final:
            raise RuntimeError("канал не найден или закрыт")
        parser = _TGParser()
        parser.feed(body.decode("utf-8", "replace"))
        ids, old = [], False
        for p in parser.posts:
            m = re.match(r"^[\w]+/(\d+)$", p["post"])
            if not (m and p["date"]):
                continue
            ids.append(int(m.group(1)))
            date = datetime.fromisoformat(p["date"])
            if date < since:
                old = True
                continue
            text = re.sub(r"[ \t]+", " ", p["text"])
            if len(text) >= MIN_LEN and not noisy(text):
                posts.append({"key": f"tg:{p['post']}", "url": f"https://t.me/{p['post']}",
                              "date": date.date().isoformat(), "engagement": 0, "text": text})
        if not ids or old:
            break
        before = min(ids)
        time.sleep(1)
    return posts


def reddit(sub, since, pages):
    posts, before = [], int(time.time())
    for _ in range(pages):
        q = urllib.parse.urlencode({"subreddit": sub, "after": int(since.timestamp()), "before": before,
                                    "limit": 100, "fields": "id,title,selftext,num_comments,score,created_utc"})
        data = None
        for attempt in range(3):
            res = get_json(f"https://arctic-shift.photon-reddit.com/api/posts/search?{q}", timeout=60)
            if not res.get("error"):
                data = res.get("data") or []
                break
            time.sleep(10 * (attempt + 1))
        if data is None:
            raise RuntimeError(f"архив Reddit не ответил: {res.get('error')}")
        for p in data:
            body = p.get("selftext") or ""
            if body in ("[removed]", "[deleted]"):
                body = ""
            text = f"{p['title']}\n\n{body}".strip()
            if noisy(text):
                continue
            posts.append({"key": f"reddit:{p['id']}", "url": f"https://www.reddit.com/r/{sub}/comments/{p['id']}/",
                          "date": datetime.fromtimestamp(p["created_utc"], timezone.utc).date().isoformat(),
                          "engagement": p.get("num_comments", 0), "text": text})
        if len(data) < 100:
            break
        before = int(min(p["created_utc"] for p in data))
        time.sleep(2)
    return posts


def stackexchange(address, since, pages):
    site, _, tag = address.partition(":")
    posts = []
    for page in range(1, min(pages, 3) + 1):
        params = {"order": "desc", "sort": "votes", "site": site, "pagesize": 100, "page": page,
                  "filter": "withbody", "fromdate": int(since.timestamp())}
        if tag:
            params["tagged"] = tag
        res = get_json("https://api.stackexchange.com/2.3/questions?" + urllib.parse.urlencode(params))
        if res.get("error_message"):
            raise RuntimeError(res["error_message"])
        for q in res.get("items", []):
            text = f"{html.unescape(q['title'])}\n\n{clean(q.get('body', ''))}"
            posts.append({"key": f"se:{site}:{q['question_id']}", "url": q["link"],
                          "date": datetime.fromtimestamp(q["creation_date"], timezone.utc).date().isoformat(),
                          "engagement": q.get("score", 0), "text": text})
        if not res.get("has_more"):
            break
        time.sleep(1)
    return posts


def hn(query, since, pages):
    params = {"query": query, "tags": "(story,ask_hn)", "hitsPerPage": 100,
              "numericFilters": f"created_at_i>{int(since.timestamp())}"}
    res = get_json("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(params))
    posts = []
    for h in res.get("hits", []):
        text = f"{h.get('title') or ''}\n\n{clean(h.get('story_text') or '')}".strip()
        posts.append({"key": f"hn:{h['objectID']}", "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
                      "date": (h.get("created_at") or "")[:10],
                      "engagement": (h.get("points") or 0) + (h.get("num_comments") or 0), "text": text})
    return posts


def rss(url, since, pages):
    root = ET.fromstring(get(url)[0])
    atom = "{http://www.w3.org/2005/Atom}"
    posts = []
    for item in root.iter():
        if item.tag not in ("item", atom + "entry"):
            continue
        def field(*names):
            for n in names:
                el = item.find(n)
                if el is not None:
                    return el.get("href") if n.endswith("link") and el.get("href") else (el.text or "")
            return ""
        title = clean(field("title", atom + "title"))
        link = field("link", atom + "link").strip()
        parts = urllib.parse.urlsplit(link)
        query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_")]
        link = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
        raw_date = field("pubDate", atom + "updated", atom + "published")
        try:
            date = parsedate_to_datetime(raw_date) if "," in raw_date else datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        if date < since:
            continue
        text = f"{title}\n\n{clean(field('description', atom + 'summary', atom + 'content'))}".strip()
        if noisy(text):
            continue
        posts.append({"key": f"rss:{link}", "url": link, "date": date.date().isoformat(),
                      "engagement": 0, "text": text})
    return posts


ADAPTERS = {"telegram": telegram, "reddit": reddit, "stackexchange": stackexchange, "hn": hn, "rss": rss}


# ---------- файлы поля ----------

def read_sources(field):
    path = Path(field) / "sources.md"
    rows, header = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if header is None:
            if "Тип" in cells and "Адрес" in cells:
                header = cells
            continue
        row = dict(zip(header, cells))
        kind = row.get("Тип", "").lower()
        status = row.get("Статус", "").lower()
        if kind in ADAPTERS and row.get("Адрес") and not status.startswith("выбыл"):
            rows.append((kind, row["Адрес"]))
    if header is None:
        sys.exit(f"В {path} нет таблицы с колонками «Тип» и «Адрес».")
    return rows


def bank_date(field):
    seeds = Path(field) / "seeds.md"
    m = re.search(r"Последнее обновление банка:\s*(\d{4}-\d{2}-\d{2})",
                  seeds.read_text(encoding="utf-8")) if seeds.exists() else None
    return m.group(1) if m else "0000-00-00"


def vocab_regex(field):
    path = Path(field) / "vocab.txt"
    words = [w.strip() for w in path.read_text(encoding="utf-8").splitlines()
             if w.strip() and not w.startswith("#")] if path.exists() else []
    if not words:
        return None
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in words) + ")", re.IGNORECASE)


# ---------- команды ----------

def cmd_find_se(words):
    res = get_json("https://api.stackexchange.com/2.3/sites?pagesize=400")
    for s in res.get("items", []):
        hay = f"{s.get('name', '')} {s.get('audience', '')} {s['api_site_parameter']}".lower()
        if "meta" not in s["api_site_parameter"] and any(w.lower() in hay for w in words):
            print(f"{s['api_site_parameter']:<24} {html.unescape(s.get('name', ''))} — {html.unescape(s.get('audience', ''))}")


def cmd_find_reddit(prefixes, min_subs):
    found = {}
    for prefix in prefixes:
        q = urllib.parse.urlencode({"subreddit_prefix": prefix, "limit": 25})
        res = get_json(f"https://arctic-shift.photon-reddit.com/api/subreddits/search?{q}", timeout=60)
        for s in res.get("data") or []:
            if (s.get("subscribers") or 0) >= min_subs:
                found[s["display_name"]] = s["subscribers"]
        time.sleep(2)
    for name, subs in sorted(found.items(), key=lambda x: -x[1]):
        print(f"r/{name:<28} подписчиков: {subs}")
    if not found:
        print(f"Ничего крупнее {min_subs} подписчиков. Попробуй другие префиксы или поиск site:reddit.com.")


def cmd_check(field):
    since = datetime.now(timezone.utc) - timedelta(days=90)
    print("| Тип | Адрес | Статус | Постов за 90 дней (1 страница) | Последний пост |")
    print("|---|---|---|---|---|")
    for kind, address in read_sources(field):
        try:
            posts = ADAPTERS[kind](address, since, 1)
            last = max((p["date"] for p in posts), default="—")
            status = "живой" if posts else "нет пригодных постов за 90 дней: нет новых или нет текста"
            print(f"| {kind} | {address} | {status} | {len(posts)} | {last} |")
        except Exception as e:
            print(f"| {kind} | {address} | ошибка: {str(e)[:60]} | — | — |")
        time.sleep(1)


def cmd_harvest(field, days, pages):
    field = Path(field)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    seen_path = field / "seen.json"
    seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()
    found, errors = [], []
    for kind, address in read_sources(field):
        try:
            for p in ADAPTERS[kind](address, since, pages):
                p["source"] = f"{kind}:{address}"
                found.append(p)
        except Exception as e:
            errors.append(f"{kind}:{address}: {e}")
        time.sleep(1)
    new = [p for p in found if p["key"] not in seen]
    raw = field / "raw"
    raw.mkdir(exist_ok=True)
    out = raw / f"{datetime.now().date().isoformat()}.json"
    earlier = json.loads(out.read_text(encoding="utf-8"))["posts"] if out.exists() else []
    out.write_text(json.dumps({"since": since.date().isoformat(), "posts": earlier + new, "errors": errors},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    seen_path.write_text(json.dumps(sorted(seen | {p["key"] for p in new})))
    print(f"{out.name}: новых постов {len(new)}, ошибок {len(errors)}")
    for e in errors:
        print("  " + e)


def cmd_digest(field, since, top):
    field = Path(field)
    since = since or bank_date(field)
    vocab = vocab_regex(field)
    if vocab is None:
        print("Внимание: vocab.txt пуст — выжимка без фильтра по теме.")
    posts = []
    for f in sorted((field / "raw").glob("*.json")):
        if f.stem > since:
            posts += json.loads(f.read_text(encoding="utf-8"))["posts"]
    scored = []
    for p in posts:
        text = p["text"]
        if noisy(text):
            continue
        hits = len(set(m.lower() for m in vocab.findall(text))) if vocab else 1
        if not hits:
            continue
        head = text[:600]
        kinds = [k for k, rx in KINDS.items() if rx.search(head)]
        score = min(hits, 5) * 2 + len(kinds) + math.log1p(max(p.get("engagement", 0), 0))
        scored.append((score, kinds, p))
    scored.sort(key=lambda x: -x[0])
    # Один источник — не больше трети выжимки: громкий сабреддит не должен заслонять остальные
    cap, picked, per_source = max(2, top // 3), [], {}
    for item in scored:
        src = item[2].get("source", "?")
        if per_source.get(src, 0) < cap and len(picked) < top:
            picked.append(item)
            per_source[src] = per_source.get(src, 0) + 1
    picked += [i for i in scored if i not in picked][:top - len(picked)]
    print(f"Сырьё новее {since}: постов {len(posts)}, по теме {len(scored)}. Показаны {len(picked)}, "
          f"не больше {cap} из одного источника.\n")
    for score, kinds, p in picked:
        text = re.sub(r"\s+", " ", p["text"])[:CUT]
        print(f"- [{', '.join(kinds) or 'прочее'}] {p.get('source', '?')} · {p['date']} · отклик {p.get('engagement', 0)} · {p['url']}")
        print(f"  {text}\n")


def cmd_yield(field):
    field = Path(field)
    done = bank_date(field)
    seeds_text = (field / "seeds.md").read_text(encoding="utf-8") if (field / "seeds.md").exists() else ""
    seed_urls = set(re.findall(r"https?://[^\s|)]+", seeds_text))
    posts, batches, seeds = {}, {}, {}
    for f in sorted((field / "raw").glob("*.json")):
        if f.stem > done:
            continue
        for p in json.loads(f.read_text(encoding="utf-8"))["posts"]:
            src = p.get("source", "?")
            posts[src] = posts.get(src, 0) + 1
            batches.setdefault(src, set()).add(f.stem)
            if p["url"] in seed_urls:
                seeds[src] = seeds.get(src, 0) + 1
    print("| Источник | Сборов разобрано | Постов | Семян | Вывод |")
    print("|---|---|---|---|---|")
    for kind, address in read_sources(field):
        src = f"{kind}:{address}"
        n_batches, n_seeds = len(batches.get(src, ())), seeds.get(src, 0)
        verdict = "кандидат на удаление" if n_batches >= DROP_AFTER and not n_seeds else "—"
        print(f"| {src} | {n_batches} | {posts.get(src, 0)} | {n_seeds} | {verdict} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find-se").add_argument("words", nargs="+")
    r = sub.add_parser("find-reddit")
    r.add_argument("prefixes", nargs="+")
    r.add_argument("--min-subs", type=int, default=2000, help="отсечь мелкие сабреддиты, по умолчанию 2000")
    sub.add_parser("check").add_argument("field")
    h = sub.add_parser("harvest")
    h.add_argument("field")
    h.add_argument("--days", type=int, default=30)
    h.add_argument("--pages", type=int, default=10, help="страниц на источник, по умолчанию 10")
    d = sub.add_parser("digest")
    d.add_argument("field")
    d.add_argument("--since")
    d.add_argument("--top", type=int, default=30)
    sub.add_parser("yield").add_argument("field")
    args = ap.parse_args()

    if args.cmd == "find-se":
        cmd_find_se(args.words)
    elif args.cmd == "find-reddit":
        cmd_find_reddit(args.prefixes, args.min_subs)
    elif args.cmd == "check":
        cmd_check(args.field)
    elif args.cmd == "harvest":
        cmd_harvest(args.field, args.days, args.pages)
    elif args.cmd == "digest":
        cmd_digest(args.field, args.since, args.top)
    elif args.cmd == "yield":
        cmd_yield(args.field)


if __name__ == "__main__":
    main()
