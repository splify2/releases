#!/usr/bin/env python3
"""Опубликовать выпуск продукта в splify2/releases: пакеты, список изменений, version.json.

Зовут release.yml проектов (steer, splify2, steer-box-connector, xsteer) последним шагом, и тот же
скрипт годится руками. Только стандартная библиотека и `gh` (авторизованный токеном с правом
записи в splify2/releases — в Actions это секрет RELEASES_TOKEN в GH_TOKEN).

    python3 scripts/publish.py --product steer --version 2.0.0 --channel stable \\
        --source-tag v2.0.0 --changelog notes.md --assets out/ [--mirror URL_BASE ...] [--date 2026-10-02]

Что делает, по порядку:
  1. выпуск `<продукт>-v<версия>` в splify2/releases: создаёт или (повторный запуск) дописывает
     вложения с заменой одноимённых — публикация идемпотентна;
  2. changelogs/<продукт>/<версия>.md — текст списка изменений;
  3. version.json: запись версии (размер и sha256 каждого файла, адреса скачивания — сначала
     выпуск в splify2/releases, затем зеркала из --mirror), указатели stable/prerelease;
  4. scripts/check.py — тот же контракт, что проверяет CI; затем коммит и push с повтором поверх
     чужого push (два проекта выпускаются одновременно — обычное дело).

Скрипт запускается ИЗ КЛОНА splify2/releases (cwd), в который он и коммитит.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

REPO = "splify2/releases"
PRODUCTS = {
    "steer": ("Ядро steer", "splify2/steer"),
    "splify2": ("splify2", "splify2/splify2"),
    "steer-box-connector": ("steer-box-connector", "splify2/steer-box-connector"),
    "xsteer": ("xsteer", "splify2/xsteer"),
}
# Сколько стабильных версий продукта держит version.json. Старые выпуски в GitHub остаются, из
# перечня уходят: роутер выбирает среди актуальных, а не среди всей истории.
KEEP_STABLE = 10


def run(*cmd, check=True, capture=False):
    r = subprocess.run(cmd, check=False, text=True,
                       stdout=subprocess.PIPE if capture else None)
    if check and r.returncode != 0:
        sys.exit(f"publish: не удалось: {' '.join(cmd)} (код {r.returncode})")
    return r


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def vkey(v):
    """Порядок по строке версии: числа по частям, предварительная (с «-») — раньше той же без
    суффикса. Суффиксы предварительных между собой НЕ сравниваются: у коннектора это хеш коммита
    (2.0.0-pre.79788be), и строковый порядок шёл бы по хешу, а не по времени."""
    base, _, pre = v.partition("-")
    nums = [int(x) if x.isdigit() else 0 for x in base.split(".")]
    return (nums, 0 if pre else 1)


def ekey(e, current):
    """Порядок записей: версия, затем дата, а при равенстве — та, что публикуется сейчас."""
    return (vkey(e["version"]), e["date"], e["version"] == current)


def update_json(path, a, assets, tag):
    with open(path) as f:
        doc = json.load(f)
    title, src = PRODUCTS[a.product]
    p = doc["products"].setdefault(a.product, {"title": title, "repo": src, "stable": None,
                                               "prerelease": None, "versions": []})
    entry = {
        "version": a.version,
        "channel": a.channel,
        "date": a.date,
        "tag": tag,
        "source": f"https://github.com/{src}/releases/tag/{a.source_tag}",
        "changelog": f"changelogs/{a.product}/{a.version}.md",
        "assets": assets,
    }
    vs = [v for v in p["versions"] if v["version"] != a.version] + [entry]
    vs.sort(key=lambda v: ekey(v, a.version), reverse=True)
    stable = [v for v in vs if v["channel"] == "stable"]
    p["stable"] = stable[0]["version"] if stable else None
    # Предварительная показывается, только пока она новее стабильной: вышла 2.0.0 — pre 2.0.0
    # больше не «последняя».
    pre = [v for v in vs if v["channel"] == "prerelease"
           and (not stable or vkey(v["version"]) > vkey(stable[0]["version"]))]
    p["prerelease"] = pre[0]["version"] if pre else None
    keep = set(v["version"] for v in stable[:KEEP_STABLE]) | ({pre[0]["version"]} if pre else set())
    p["versions"] = [v for v in vs if v["version"] in keep]
    doc["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return sorted(set(x["version"] for x in vs) - keep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True, choices=sorted(PRODUCTS))
    ap.add_argument("--version", required=True)
    ap.add_argument("--channel", required=True, choices=["stable", "prerelease"])
    ap.add_argument("--source-tag", required=True)
    ap.add_argument("--changelog", required=True, help="markdown-файл списка изменений")
    ap.add_argument("--assets", required=True, help="каталог с файлами выпуска")
    ap.add_argument("--mirror", action="append", default=[],
                    help="база зеркала: к ней дописывается /<имя файла>; можно несколько")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-push", action="store_true", help="коммит без push (проверка руками)")
    a = ap.parse_args()

    if not os.path.isfile("version.json") or not os.path.isdir("changelogs"):
        sys.exit("publish: запускать из клона splify2/releases")
    files = sorted(f for f in os.listdir(a.assets) if os.path.isfile(os.path.join(a.assets, f)))
    if not files:
        sys.exit(f"publish: в {a.assets} нет файлов")

    tag = f"{a.product}-v{a.version}"
    title = f"{PRODUCTS[a.product][0]} {a.version}" + (" (предварительный)" if a.channel == "prerelease" else "")
    paths = [os.path.join(a.assets, f) for f in files]
    exists = run("gh", "release", "view", tag, "--repo", REPO, check=False, capture=True).returncode == 0
    if exists:
        run("gh", "release", "upload", tag, *paths, "--repo", REPO, "--clobber")
        run("gh", "release", "edit", tag, "--repo", REPO, "--title", title,
            "--notes-file", a.changelog, *(["--prerelease"] if a.channel == "prerelease" else ["--prerelease=false"]))
    else:
        run("gh", "release", "create", tag, *paths, "--repo", REPO, "--title", title,
            "--notes-file", a.changelog, *(["--prerelease"] if a.channel == "prerelease" else []),
            # «Latest» у releases ничего не значит: продуктов четыре. Последнюю версию каждого
            # называет version.json.
            "--latest=false")

    assets = []
    for f, p in zip(files, paths):
        urls = [f"https://github.com/{REPO}/releases/download/{tag}/{f}"]
        urls += [m.rstrip("/") + "/" + f for m in a.mirror]
        assets.append({"name": f, "size": os.path.getsize(p), "sha256": sha256(p), "urls": urls})

    with open(a.changelog) as src:
        notes = src.read().rstrip() + "\n"
    for attempt in range(5):
        # Внутри цикла: после неудачного push коммит снимается целиком, вместе с этим файлом.
        os.makedirs(f"changelogs/{a.product}", exist_ok=True)
        with open(f"changelogs/{a.product}/{a.version}.md", "w") as dst:
            dst.write(notes)
        dropped = update_json("version.json", a, assets, tag)
        run(sys.executable, "scripts/check.py")
        run("git", "add", "version.json", f"changelogs/{a.product}/{a.version}.md")
        if run("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
            print("publish: version.json уже такой — коммитить нечего")
            return
        run("git", "commit", "-q", "-m", f"{title}" + (f"\n\nИз перечня ушли: {', '.join(dropped)}" if dropped else ""))
        if a.no_push:
            return
        if run("git", "push", "-q", check=False).returncode == 0:
            print(f"publish: {tag} опубликован")
            # Сайт (splify2.github.io/releases/) и сам сверяет version.json раз в час; толчок —
            # чтобы выпуск появился сразу. Нужен доступ токена к splify2/splify2.github.io; без
            # него сайт догонит по расписанию, публикация от этого не проваливается.
            if run("gh", "api", "-X", "POST", "repos/splify2/splify2.github.io/dispatches",
                   "-f", "event_type=releases", check=False, capture=True).returncode != 0:
                print("publish: сайт пересоберётся по расписанию (нет доступа к splify2.github.io)")
            return
        # Кто-то опубликовал свой выпуск раньше: берём его version.json и пишем свою версию заново.
        run("git", "reset", "-q", "--hard", "HEAD~1")
        run("git", "pull", "-q", "--ff-only")
    sys.exit("publish: push не прошёл пять раз подряд")


if __name__ == "__main__":
    main()
