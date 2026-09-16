#!/usr/bin/env python3
"""Заливка адаптированного резюме из output/<slug>/resume.md на hh.ru.

Схема: клонируем базовое резюме (все анкетные поля, город, образование,
языки наследуются) и патчим только текст — заголовок, о себе, навыки,
описания мест работы. Справочники hh не трогаем, поэтому нечему ломаться.

Авторизация и запросы идут через hh-applicant-tool.

Команды:
    parse <slug>                    показать патч, ничего не отправляя
    resumes                         список резюме с id
    push <slug> --base <resume_id>  клонировать базовое и залить патч
        --publish                   опубликовать после заливки
        --into <resume_id>          патчить существующее вместо клонирования
    employers <текст>               найти id работодателя по названию
    visibility <resume_id>          показать видимость резюме
        --access <тип>              no_one | whitelist | blacklist | clients | everyone | direct
        --add <employer_id>...      добавить работодателей в список видимости
        --remove <employer_id>...   убрать работодателей из списка
        --clear                     очистить список целиком
"""

import argparse
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HHTOOL = os.path.join(REPO, "scripts", ".venv-hh", "bin", "hh-applicant-tool")

MAX_SKILLS = 30
MAX_SKILL_LEN = 100


def die(msg):
    print(f"Ошибка: {msg}", file=sys.stderr)
    sys.exit(1)


# ── вызовы hh-applicant-tool ──────────────────────────────────────────────────

def hh(*args, parse_json=True):
    if not os.path.exists(HHTOOL):
        die(f"нет {HHTOOL}, поставь пакет в scripts/.venv-hh")
    proc = subprocess.run([HHTOOL, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"hh-applicant-tool {' '.join(args)}\n{proc.stderr.strip()}")
    out = proc.stdout.strip()
    if not parse_json:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        die(f"не json в ответе на {' '.join(args)}:\n{out[:500]}")


def api(endpoint, method="GET", data=None):
    args = ["call-api", endpoint, "-X", method]
    if data is not None:
        args += ["-d", json.dumps(data, ensure_ascii=False)]
    return hh(*args)


def my_resumes():
    return api("/resumes/mine").get("items", [])


# ── разбор resume.md ──────────────────────────────────────────────────────────

def split_sections(text, level):
    """Режет markdown на (заголовок, тело) по заголовкам заданного уровня."""
    pattern = re.compile(rf"^{'#' * level} +(.+?)\s*$", re.M)
    marks = list(pattern.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1).strip(), text[m.end():end]))
    return out


def split_skills(line):
    """Делит по запятым, не разрывая скобки: 'приоритизация (WSJF, CoD)' цела."""
    parts, buf, depth = [], "", 0
    for ch in line:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def parse_resume_md(path):
    with open(path) as f:
        text = f.read()

    patch = {}

    m = re.search(r"^# +(.+)$", text, re.M)
    if m and "/" in m.group(1):
        patch["title"] = m.group(1).split("/", 1)[1].strip()
    elif m:
        patch["title"] = m.group(1).strip()

    secs = {h.lower(): body for h, body in split_sections(text, 2)}

    for key in ("summary", "о себе", "обо мне", "профиль"):
        if key in secs:
            patch["skills"] = secs[key].strip()
            break

    if (sec := secs.get("ключевые навыки")):
        skills, seen = [], set()
        for line in sec.splitlines():
            line = re.sub(r"^\*\*(.+?):\*\*", "", line.strip()).strip()
            if not line:
                continue
            for s in split_skills(line):
                s = s.strip("*• ")
                low = s.lower()
                if s and low not in seen and len(s) <= MAX_SKILL_LEN:
                    seen.add(low)
                    skills.append(s)
        patch["_skill_set"] = skills[:MAX_SKILLS]

    jobs = []
    if (sec := secs.get("опыт работы")):
        for heading, body in split_sections(sec, 3):
            company = heading.split("|", 1)[0].strip()
            lines = [ln.rstrip() for ln in body.strip().splitlines()]
            position, desc = "", []
            for ln in lines:
                if not ln.strip():
                    continue
                if DATE_LINE.match(ln.strip()):
                    continue
                pm = re.match(r"^\*\*(.+?)\*\*$", ln.strip())
                if pm and not position:
                    position = pm.group(1).split("|", 1)[0].strip()
                    continue
                desc.append(ln.strip())
            if not position and " — " in company:
                company, position = [x.strip() for x in company.split(" — ", 1)]
            jobs.append({"company": company, "position": position,
                         "description": "\n".join(desc)})
    patch["_jobs"] = jobs
    return patch


# ── склейка патча с живым резюме ──────────────────────────────────────────────

def norm(s):
    return re.sub(r"[^a-zа-я0-9]+", "", (s or "").lower())


STOP_TOKENS = {"digital", "marketing", "agency", "агентство", "ltd", "llc", "global",
               "inc", "group", "ru", "com", "проект", "проекты"}

MONTHS = ("Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август|Сентябрь|Октябрь|Ноябрь|Декабрь")
# Даты периода hh рисует своими полями над описанием. Строка с датами из markdown
# в description даёт дубль в анкете, поэтому режется на парсинге.
DATE_LINE = re.compile(
    rf"^({MONTHS})\s+\d{{4}}\s*[-–—]\s*(настоящее время|({MONTHS})\s+\d{{4}})\.?$",
    re.IGNORECASE)


def tokens(s):
    return {t for t in re.split(r"[^a-zа-я0-9]+", (s or "").lower())
            if len(t) >= 3 and t not in STOP_TOKENS}


def match_company(md_company, hh_company):
    a, b = norm(md_company), norm(hh_company)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    # названия расходятся между документом и анкетой на hh:
    # "Digital-агентство (NDA)" против "NDA (Digital Marketing Agency)"
    return bool(tokens(md_company) & tokens(hh_company))


def build_patch(parsed, resume):
    """Собирает тело PUT: только текстовые поля, структура берётся из резюме."""
    patch = {}
    if parsed.get("title"):
        patch["title"] = parsed["title"]
    if parsed.get("skills"):
        patch["skills"] = parsed["skills"]
    if parsed.get("_skill_set"):
        patch["skill_set"] = parsed["_skill_set"]

    experience = resume.get("experience") or []
    if experience and parsed.get("_jobs"):
        merged, hits, misses = [], [], []
        for item in experience:
            entry = dict(item)
            for job in parsed["_jobs"]:
                if match_company(job["company"], item.get("company")):
                    entry["description"] = job["description"]
                    if job["position"]:
                        entry["position"] = job["position"]
                    hits.append(item.get("company"))
                    break
            else:
                misses.append(item.get("company"))
            merged.append(entry)
        patch["experience"] = merged
        patch["_report"] = {"обновлено": hits, "не совпало на hh": misses,
                            "не найдено в резюме на hh": [
                                j["company"] for j in parsed["_jobs"]
                                if not any(match_company(j["company"], e.get("company"))
                                           for e in experience)]}
    return patch


def resume_md_path(slug):
    path = os.path.join(REPO, "output", slug, "resume.md")
    if not os.path.exists(path):
        die(f"нет {path}")
    return path


# ── команды ───────────────────────────────────────────────────────────────────

def cmd_parse(args):
    parsed = parse_resume_md(resume_md_path(args.slug))
    print(f"Заголовок: {parsed.get('title')}")
    print(f"\nО себе ({len(parsed.get('skills',''))} симв.):\n{parsed.get('skills','')[:400]}...")
    print(f"\nНавыки ({len(parsed.get('_skill_set',[]))}):")
    for s in parsed.get("_skill_set", []):
        print(f"  - {s}")
    print("\nМеста работы:")
    for j in parsed.get("_jobs", []):
        first = j["description"].splitlines()[0] if j["description"] else ""
        print(f"  - {j['company']} / {j['position']} — {len(j['description'])} симв.")
        print(f"      {first[:90]}")


def cmd_resumes(args):
    for r in my_resumes():
        st = (r.get("status") or {}).get("name")
        print(f"{r['id']}  {r.get('title')!r}  [{st}]")


def cmd_push(args):
    parsed = parse_resume_md(resume_md_path(args.slug))

    if args.into:
        target = args.into
    else:
        before = {r["id"] for r in my_resumes()}
        hh("clone-resume", "--resume-id", args.base, parse_json=False)
        after = my_resumes()
        new = [r for r in after if r["id"] not in before]
        if not new:
            die("клон не появился в /resumes/mine")
        target = new[0]["id"]
        print(f"Склонировано: {target}")

    resume = api(f"/resumes/{target}")
    patch = build_patch(parsed, resume)
    report = patch.pop("_report", None)

    if args.dry_run:
        print(json.dumps(patch, ensure_ascii=False, indent=2)[:4000])
    else:
        api(f"/resumes/{target}", method="PUT", data=patch)
        print(f"Обновлено: https://hh.ru/resume/{target}")
        if args.publish:
            api(f"/resumes/{target}/publish", method="POST")
            print("Опубликовано.")

    if report:
        for k, v in report.items():
            if v:
                print(f"{k}: {', '.join(str(x) for x in v)}")


def cmd_employers(args):
    res = api(f"/employers?text={args.text}")
    for e in res.get("items", []):
        print(f"{e['id']}  {e['name']}  ({e.get('open_vacancies', 0)} вакансий)")


def cmd_visibility(args):
    """Показать или изменить видимость резюме для конкретных работодателей."""
    rid = args.resume_id
    resume = api(f"/resumes/{rid}")
    current = ((resume.get("access") or {}).get("type") or {}).get("id")

    if not args.access and not args.add and not args.remove:
        print(f"{resume.get('title')}\n  access: {current}")
        if current in ("whitelist", "blacklist"):
            lst = api(f"/resumes/{rid}/{current}")
            for e in lst.get("items", []):
                print(f"    {e['id']}  {e['name']}")
        return

    target_list = args.access or current
    if target_list not in ("whitelist", "blacklist") and (args.add or args.remove):
        die(f"список работодателей есть только у whitelist и blacklist, сейчас {target_list}")

    if args.access and args.access != current:
        api(f"/resumes/{rid}", method="PUT",
            data={"access": {"type": {"id": args.access}}})
        print(f"access: {current} -> {args.access}")

    for eid in args.add or []:
        api(f"/resumes/{rid}/{target_list}", method="POST",
            data={"items": [{"id": str(eid)}]})
        print(f"+ {eid} в {target_list}")

    for eid in args.remove or []:
        # DELETE с телом очищает ВЕСЬ список, поэтому только адресная форма
        hh("call-api", f"/resumes/{rid}/{target_list}/{eid}", "-X", "DELETE",
           parse_json=False)
        print(f"- {eid} из {target_list}")

    if args.clear:
        api(f"/resumes/{rid}/{target_list}", method="DELETE",
            data={"items": []})
        print(f"{target_list} очищен целиком")

    lst = api(f"/resumes/{rid}/{target_list}")
    print(f"{target_list} теперь: " +
          ", ".join(f"{e['name']} ({e['id']})" for e in lst.get("items", [])))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("parse", help="показать патч без отправки")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_parse)

    sr = sub.add_parser("resumes", help="список резюме")
    sr.set_defaults(func=cmd_resumes)

    su = sub.add_parser("push", help="клонировать и залить")
    su.add_argument("slug")
    su.add_argument("--base", help="id базового резюме для клонирования")
    su.add_argument("--into", help="патчить это резюме вместо клонирования")
    su.add_argument("--publish", action="store_true")
    su.add_argument("--dry-run", action="store_true")
    su.set_defaults(func=cmd_push)

    se = sub.add_parser("employers", help="найти id работодателя по названию")
    se.add_argument("text")
    se.set_defaults(func=cmd_employers)

    sv = sub.add_parser("visibility", help="показать или изменить видимость резюме")
    sv.add_argument("resume_id")
    sv.add_argument("--access", choices=["no_one", "whitelist", "blacklist",
                                         "clients", "everyone", "direct"])
    sv.add_argument("--add", nargs="+", metavar="EMPLOYER_ID")
    sv.add_argument("--remove", nargs="+", metavar="EMPLOYER_ID")
    sv.add_argument("--clear", action="store_true",
                    help="очистить список целиком (применяется после --add/--remove)")
    sv.set_defaults(func=cmd_visibility)

    args = p.parse_args()
    if args.cmd == "push" and not args.base and not args.into:
        die("нужен --base или --into")
    args.func(args)


if __name__ == "__main__":
    main()
