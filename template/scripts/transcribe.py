#!/usr/bin/env python3
"""Транскрибация интервью через mlx_whisper. Локально, запись никуда не уходит.

  python3 transcribe.py запись.m4a --company altenar-business-analyst --stage final
  python3 transcribe.py ответ.m4a --drill voice
  python3 transcribe.py запись.mp4 --company notix-games-tpm --stage screening --lang en
"""

import argparse
import datetime
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
WHISPER = pathlib.Path.home() / ".local/bin/mlx_whisper"
MODEL = "mlx-community/whisper-large-v3-turbo"
STAGES = ["screening", "hiring-manager", "tech", "final"]

# Whisper глотает английские термины в русской речи: SLA слышится как "слопы".
# Промпт задаёт словарь домена и заметно поднимает точность на терминах.
TERMS = (
    "Обсуждаем проектное управление и аналитику. Термины: SLA, ITIL, MTTD, MTTR, "
    "incident management, problem management, roadmap, backlog, delivery, stakeholder, "
    "TPM, PMO, RACI, DoR, DoD, WSJF, Scrumban, kanban, lead time, time to market, "
    "API, S2S, postback, attribution, AppsFlyer, ClickHouse, PostgreSQL, Grafana, Tableau, "
    "iGaming, BetBuilder, affiliate, retention, LTV, ROI, churn, unit economics."
)

HEADER = "СЫРОЙ ТРАНСКРИПТ — не редактировать\n\n"


def target_path(args, date):
    if args.drill:
        return ROOT / "drill" / "artifacts" / f"{date}-{args.drill}.md"
    return ROOT / "output" / args.company / "interviews" / f"{date}-{args.stage}.md"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="аудио или видео файл")
    ap.add_argument("--company", help="папка отклика в output/, например altenar-business-analyst")
    ap.add_argument("--stage", choices=STAGES, help="этап интервью")
    ap.add_argument("--drill", help="трек дрилла вместо интервью, например voice")
    ap.add_argument("--lang", help="ru или en. Не указан — определит сам")
    ap.add_argument("--terms", default="", help="дополнительные термины через запятую — имена, продукты, стек компании")
    ap.add_argument("--date", help="YYYY-MM-DD, по умолчанию сегодня")
    args = ap.parse_args()

    if not args.drill and not (args.company and args.stage):
        ap.error("нужно либо --drill, либо --company вместе с --stage")

    audio = pathlib.Path(args.audio).expanduser()
    if not audio.exists():
        sys.exit(f"нет файла: {audio}")
    if not WHISPER.exists():
        sys.exit(f"нет mlx_whisper: {WHISPER}")

    date = args.date or datetime.date.today().isoformat()
    out = target_path(args, date)
    if out.exists():
        sys.exit(f"файл уже есть, не перезаписываю: {out}")

    prompt = TERMS + (" " + args.terms if args.terms else "")
    cmd = [str(WHISPER), str(audio), "--model", MODEL, "--output-format", "txt",
           "--initial-prompt", prompt]
    if args.lang:
        cmd += ["--language", args.lang]

    with tempfile.TemporaryDirectory() as tmp:
        cmd += ["--output-dir", tmp, "--output-name", "raw"]
        print(f"расшифровываю {audio.name}, первый запуск скачает модель (~1.5 ГБ)...", flush=True)
        subprocess.run(cmd, check=True)
        text = (pathlib.Path(tmp) / "raw.txt").read_text()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(HEADER + text.strip() + "\n")

    words = len(text.split())
    print(f"\n{out}")
    print(f"{words} слов, примерно {words * 4 // 3} токенов")
    print(f"\nразобрать:  /drill debrief {out}")


if __name__ == "__main__":
    main()
