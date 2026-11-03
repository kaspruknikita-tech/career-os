#!/usr/bin/env python3
"""Собирает SVG для README в стиле листа персонажа RPG.

    python3 assets/readme/source/build.py

Пишет hero.svg, classes.svg, quest-map.svg в assets/readme/. Всё рисуется
прямоугольниками: пиксель-арт без растра и без внешних шрифтов.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent

BG, PANEL, PANEL2, EDGE, HI = "#14162E", "#23264A", "#2C3060", "#0B0C1D", "#454B8C"
INK, MUTED, GOLD, HP, XP, MANA, VIOLET = "#F4E9C9", "#A9ADD6", "#F2C14E", "#E4572E", "#5FBF6A", "#4EA8DE", "#B48CF2"
MONO = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"

PAL = {"K": EDGE, "W": INK, "G": GOLD, "R": HP, "X": XP, "B": MANA, "V": VIOLET, "M": MUTED,
       "S": "#E8B48A", "H": "#5A3A22", "D": "#3A3F7A", "N": "#7A5230"}

SPRITES = {
    "hero": [
        "....HHHH....",
        "...HHHHHH...",
        "..HHSSSSHH..",
        "..HSKSSKSH..",
        "..HSSSSSSH..",
        "...SSRRSS...",
        "....SSSS....",
        "..BBBGGBBB..",
        ".BBBBGGBBBB.",
        ".SBBBGGBBBS.",
        ".SBBBBBBBBS.",
        "..BBBBBBBB..",
        "..DDDDDDDD..",
        "..DDD..DDD..",
        "..DDD..DDD..",
        ".NNNN..NNNN.",
    ],
    "scroll": [
        ".WWWWWW.",
        "WMMMMMMW",
        ".WKKKKW.",
        ".WWWWWW.",
        ".WKKKWW.",
        ".WWWWWW.",
        "WMMMMMMW",
        ".WWWWWW.",
    ],
    "bubble": [
        ".BBBBBB.",
        "BWWWWWWB",
        "BWKWKWWB",
        "BWWWWWWB",
        "BWKKKWWB",
        ".BBBBBB.",
        "..BB....",
        ".B......",
    ],
    "sword": [
        "......WW",
        ".....WMW",
        "....WMW.",
        "...WMW..",
        "G.WMW...",
        ".GGW....",
        ".NGG....",
        "N..G....",
    ],
    "chest": [
        ".NNNNNN.",
        "NGGGGGGN",
        "NNNNNNNN",
        "NNNGGNNN",
        "NNNKGNNN",
        "NNNNNNNN",
        "NGGGGGGN",
        "NNNNNNNN",
    ],
    "compass": [
        "..GGGG..",
        ".GWWWWG.",
        "GWWRWWWG",
        "GWWRRWWG",
        "GWWKKWWG",
        "GWWWKWWG",
        ".GWWWWG.",
        "..GGGG..",
    ],
    "letter": [
        "........",
        "WWWWWWWW",
        "WRWWWWRW",
        "WWRWWRWW",
        "WWWRRWWW",
        "WWWWWWWW",
        "WWWWWWWW",
        "........",
    ],
    "board": [
        "NNNNNNNN",
        "NWWWNWWN",
        "NWKWNWKN",
        "NWWWNWWN",
        "NNNNNNNN",
        "...NN...",
        "...NN...",
        "..NNNN..",
    ],
    "flag": [
        ".RRRR...",
        ".RRRRRR.",
        ".RRRR...",
        ".N......",
        ".N......",
        ".N......",
        ".N......",
        "NNN.....",
    ],
    "tower": [
        "V.V.V.V.",
        "VVVVVVVV",
        ".VVVVVV.",
        ".VVKKVV.",
        ".VVVVVV.",
        ".VVKKVV.",
        ".VVVVVV.",
        "VVVVVVVV",
    ],
    "eye": [
        "........",
        "..BBBB..",
        ".BWWWWB.",
        "BWWKKWWB",
        "BWWKKWWB",
        ".BWWWWB.",
        "..BBBB..",
        "........",
    ],
}


def sprite(name, x, y, cell):
    out = []
    for r, row in enumerate(SPRITES[name]):
        for c, ch in enumerate(row):
            if ch != ".":
                out.append(f'<rect x="{x + c * cell}" y="{y + r * cell}" width="{cell}" height="{cell}" fill="{PAL[ch]}"/>')
    return "".join(out)


def panel(x, y, w, h, fill=PANEL, n=8):
    """Рамка с вырезанными углами: так выглядят окна в старых RPG."""
    def poly(x, y, w, h, n):
        return (f"{x+n},{y} {x+w-n},{y} {x+w-n},{y+n} {x+w},{y+n} {x+w},{y+h-n} {x+w-n},{y+h-n} "
                f"{x+w-n},{y+h} {x+n},{y+h} {x+n},{y+h-n} {x},{y+h-n} {x},{y+n} {x+n},{y+n}")
    return (f'<polygon points="{poly(x - 4, y - 4, w + 8, h + 8, n)}" fill="{EDGE}"/>'
            f'<polygon points="{poly(x, y, w, h, n)}" fill="{HI}"/>'
            f'<polygon points="{poly(x + 4, y + 4, w - 8, h - 8, n - 2)}" fill="{fill}"/>')


def text(x, y, s, size, fill=INK, weight="700", anchor="start", shadow=False):
    t = f'font-family="{MONO}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"'
    sh = f'<text x="{x + 3}" y="{y + 3}" {t} fill="{EDGE}">{s}</text>' if shadow else ""
    return f'{sh}<text x="{x}" y="{y}" {t} fill="{fill}">{s}</text>'


def bar(x, y, label, hint, filled, color, cells=10):
    out = [text(x, y + 20, label, 20, INK)]
    bx = x + 150
    for i in range(cells):
        out.append(f'<rect x="{bx + i * 22}" y="{y + 4}" width="18" height="18" fill="{color if i < filled else PANEL2}"/>')
    out.append(text(bx + cells * 22 + 12, y + 20, hint, 18, MUTED, "400"))
    return "".join(out)


def stars(w, h, seed):
    out, s = [], seed
    for _ in range(46):
        s = (s * 1103515245 + 12345) % 2 ** 31
        x, y = s % w, (s // w) % h
        out.append(f'<rect x="{x}" y="{y}" width="3" height="3" fill="{HI}"/>')
    return "".join(out)


def svg(w, h, title, desc, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" role="img" '
            f'aria-labelledby="t d" shape-rendering="crispEdges">'
            f'<title id="t">{title}</title><desc id="d">{desc}</desc>'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>\n')


def hero():
    b = [stars(1200, 460, 7)]
    b.append(panel(48, 40, 640, 380))
    b.append(text(80, 86, "ЛИСТ ПЕРСОНАЖА · плагин Claude Code", 18, GOLD))
    b.append(text(78, 160, "CAREER OS", 76, INK, shadow=True))
    b.append(text(80, 200, "Поиск работы как ролевая игра", 24, INK))
    b.append(sprite("hero", 84, 236, 10))
    b.append(text(232, 254, "КЛАСС: любой", 20, GOLD))
    b.append(text(232, 254 + 26, "дизайн · код · данные · продажи · ...", 18, MUTED, "400"))
    b.append(bar(232, 300, "ОПЫТ", "база", 7, GOLD, 8))
    b.append(bar(232, 334, "ФОРМА", "дрилл", 5, XP, 8))
    b.append(bar(232, 368, "РЫНОК", "кейсы", 6, MANA, 8))
    b.append(panel(724, 40, 428, 380))
    b.append(text(756, 86, "ИНВЕНТАРЬ", 18, GOLD))
    items = [("scroll", "Резюме", False), ("bubble", "Интервью", False), ("sword", "Тренажёр", False),
             ("chest", "Опыт", False), ("compass", "Каналы", True), ("letter", "Письма", True)]
    for i, (icon, name, beta) in enumerate(items):
        cx, cy = 756 + (i % 3) * 126, 108 + (i // 3) * 140
        b.append(f'<rect x="{cx}" y="{cy}" width="114" height="124" fill="{PANEL2}"/>')
        b.append(f'<rect x="{cx + 2}" y="{cy + 2}" width="110" height="4" fill="{HI}"/>')
        g = sprite(icon, cx + 33, cy + 18, 6)
        b.append(f'<g opacity="0.45">{g}</g>' if beta else g)
        b.append(text(cx + 57, cy + 102, name, 18, MUTED if beta else INK, anchor="middle"))
        if beta:
            b.append(f'<rect x="{cx + 78}" y="{cy + 8}" width="28" height="24" fill="{HP}"/>')
            b.append(text(cx + 92, cy + 27, "β", 18, INK, anchor="middle"))
    b.append(text(756, 400, "&gt; /career-init", 22, XP))
    b.append(f'<rect x="952" y="382" width="14" height="22" fill="{XP}"/>')
    return svg(1200, 460, "Career OS — поиск работы как ролевая игра",
               "Лист персонажа: класс — любая профессия, шкалы опыта, формы и рынка, инвентарь из шести скиллов, два из них в бета-версии.",
               "".join(b))


def classes():
    b = [text(600, 70, "ВЫБЕРИ КЛАСС", 40, INK, anchor="middle", shadow=True),
         text(600, 108, "У каждой профессии свои задачи на собеседовании, и тренажёр даёт именно их", 20, MUTED, "400", anchor="middle")]
    cards = [("ENG", "Разработка", "system design вслух", MANA), ("DATA", "Данные", "кейс на метрики", MANA),
             ("DES", "Дизайн", "разбор портфолио", VIOLET), ("PROD", "Продукт", "product sense", VIOLET),
             ("DEL", "Проекты", "ситуационный кейс", GOLD), ("GTM", "Продажи", "ролевая игра", HP),
             ("OPS", "Операции", "кейс на процесс", GOLD), ("SUP", "Поддержка", "трудный клиент", HP)]
    for i, (cid, name, track, color) in enumerate(cards):
        x, y = 56 + (i % 4) * 276, 150 + (i // 4) * 156
        b.append(panel(x, y, 256, 132, n=6))
        b.append(f'<rect x="{x + 20}" y="{y + 22}" width="{len(cid) * 14 + 20}" height="30" fill="{color}"/>')
        b.append(text(x + 30, y + 44, cid, 20, EDGE))
        b.append(text(x + 20, y + 86, name, 24, INK))
        b.append(text(x + 20, y + 114, track, 18, MUTED, "400"))
    b.append(text(600, 488, "Нет твоей профессии? /career-role узнает, как на неё нанимают, и подстроит тренажёр", 20, GOLD, anchor="middle"))
    return svg(1200, 520, "Классы Career OS",
               "Восемь готовых профессий и главная задача тренажёра для каждой; для другой профессии /career-role найдёт, как на неё нанимают.",
               "".join(b))


def quest_map():
    b = [text(600, 64, "КАРТА КВЕСТА", 40, INK, anchor="middle", shadow=True)]
    nodes = [("flag", "Создание героя", "/career-init"), ("tower", "Выбор класса", "/career-role"),
             ("chest", "Сундук опыта", "/career import"), ("scroll", "Кузница резюме", "вакансия → резюме"),
             ("board", "Доска квестов", "/career-funnel"), ("bubble", "Арена", "interview-prep"),
             ("eye", "Разбор боя", "/drill debrief"), ("sword", "Тренировки", "/drill")]
    pos = []
    for i in range(8):
        row, col = divmod(i, 4)
        col = col if row == 0 else 3 - col
        pos.append((60 + col * 280, 110 + row * 230))
    path = []
    for i in range(7):
        (x1, y1), (x2, y2) = pos[i], pos[i + 1]
        if y1 == y2:
            a, z = (x1 + 248, x2) if x2 > x1 else (x2 + 248, x1)
            for xx in range(a + 6, z - 6, 14):
                path.append(f'<rect x="{xx}" y="{y1 + 74}" width="8" height="8" fill="{GOLD}"/>')
        else:
            for yy in range(y1 + 158, y2 - 6, 14):
                path.append(f'<rect x="{x1 + 120}" y="{yy}" width="8" height="8" fill="{GOLD}"/>')
    b += path
    for i, ((icon, name, cmd), (x, y)) in enumerate(zip(nodes, pos)):
        b.append(panel(x, y, 248, 150, n=6))
        b.append(text(x + 18, y + 36, f"{i + 1}", 22, GOLD))
        b.append(sprite(icon, x + 172, y + 18, 6))
        b.append(text(x + 18, y + 104, name, 22, INK))
        b.append(text(x + 18, y + 132, cmd, 18, XP, "400"))
    # рынок кормит тренировки, разбор боя возвращает ошибки в тренировки
    b.append(text(600, 560, "Задачи берутся из постов людей твоей профессии, а ошибки возвращаются на повтор", 20, MUTED, "400", anchor="middle"))
    return svg(1200, 600, "Карта квеста Career OS",
               "Восемь шагов: создание героя, выбор класса, сундук опыта, кузница резюме, доска квестов, арена, разбор боя, тренировки. Рынок профессии питает тренировки кейсами.",
               "".join(b))


def social():
    """Превью для соцсетей 1280×640: GitHub Settings → Social preview, загружается руками."""
    inner = hero().split('<rect width="1200" height="460" fill="#14162E"/>', 1)[1].rsplit("</svg>", 1)[0]
    body = (stars(1280, 640, 11) + f'<g transform="translate(40,70)">{inner}</g>'
            + text(640, 600, "github.com/kaspruknikita-tech/career-os", 22, MUTED, "400", anchor="middle"))
    return svg(1280, 640, "Career OS", "Превью репозитория.", body)


if __name__ == "__main__":
    for name, fn in [("hero", hero), ("classes", classes), ("quest-map", quest_map), ("source/social", social)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print(f"{name}.svg")
