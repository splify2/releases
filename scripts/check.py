#!/usr/bin/env python3
"""Проверка version.json — контракт, который читают установщик, роутер и сайт.

Только стандартная библиотека: зовётся из publish.py перед каждым коммитом и из CI на каждый push.
Код 0 — всё сходится; иначе перечень расхождений и код 1.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS = {"steer", "splify2", "steer-box-connector", "xsteer"}
VERSION = re.compile(r"^\d+(\.\d+){1,3}(-[0-9A-Za-z.]+)?$")
SHA = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    err = []
    with open(os.path.join(ROOT, "version.json")) as f:
        doc = json.load(f)
    if doc.get("schema") != 1:
        err.append("schema: ожидается 1")
    if not isinstance(doc.get("updated"), str):
        err.append("updated: нет метки времени")
    prods = doc.get("products", {})
    for name in sorted(set(prods) - PRODUCTS):
        err.append(f"products.{name}: неизвестный продукт")
    for name, p in sorted(prods.items()):
        w = f"products.{name}"
        for k in ("title", "repo", "stable", "prerelease", "versions"):
            if k not in p:
                err.append(f"{w}: нет поля {k}")
        vs = p.get("versions", [])
        seen = set()
        for v in vs:
            vw = f"{w}.versions[{v.get('version')}]"
            if not VERSION.match(str(v.get("version", ""))):
                err.append(f"{vw}: версия не похожа на версию")
            if v.get("version") in seen:
                err.append(f"{vw}: версия повторяется")
            seen.add(v.get("version"))
            if v.get("channel") not in ("stable", "prerelease"):
                err.append(f"{vw}: channel — stable или prerelease")
            if not DATE.match(str(v.get("date", ""))):
                err.append(f"{vw}: date — ГГГГ-ММ-ДД")
            if v.get("tag") != f"{name}-v{v.get('version')}":
                err.append(f"{vw}: tag обязан быть {name}-v<версия>")
            cl = v.get("changelog", "")
            if cl != f"changelogs/{name}/{v.get('version')}.md" or not os.path.isfile(os.path.join(ROOT, cl)):
                err.append(f"{vw}: нет файла списка изменений {cl}")
            if not v.get("assets"):
                err.append(f"{vw}: нет файлов")
            names = set()
            for a in v.get("assets", []):
                aw = f"{vw}.{a.get('name')}"
                if a.get("name") in names or not a.get("name") or "/" in a.get("name", "/"):
                    err.append(f"{aw}: имя файла пустое, с «/» или повторяется")
                names.add(a.get("name"))
                if not isinstance(a.get("size"), int) or a["size"] <= 0:
                    err.append(f"{aw}: size — положительное число")
                if not SHA.match(str(a.get("sha256", ""))):
                    err.append(f"{aw}: sha256 — 64 шестнадцатеричных знака")
                urls = a.get("urls") or []
                if not urls or not urls[0].startswith(f"https://github.com/splify2/releases/releases/download/{v.get('tag')}/"):
                    err.append(f"{aw}: первый адрес — выпуск в splify2/releases")
                if any(not u.startswith("https://") or not u.endswith("/" + a.get("name", "")) for u in urls):
                    err.append(f"{aw}: адрес не https или не кончается именем файла")
        st = [v["version"] for v in vs if v.get("channel") == "stable"]
        pr = [v["version"] for v in vs if v.get("channel") == "prerelease"]
        if p.get("stable") != (st[0] if st else None):
            err.append(f"{w}.stable: должен указывать на первую стабильную в versions ({st[:1]})")
        if p.get("prerelease") is not None and p["prerelease"] not in pr:
            err.append(f"{w}.prerelease: такой предварительной в versions нет")
    if err:
        print("check: расхождений — %d" % len(err))
        for e in err:
            print("  - " + e)
        return 1
    print("check: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
