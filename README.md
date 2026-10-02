# splify2 releases

Актуальные версии проектов [splify2](https://github.com/splify2): ядро steer, панель splify2,
steer-box-connector и xsteer. Здесь лежат пакеты каждой версии, её список изменений и
`version.json` — один файл, по которому установщик, роутер и [сайт](https://splify2.github.io/releases/)
узнают, что сейчас выпущено.

| Продукт | Где код |
|---|---|
| `steer` — ядро steer | [splify2/steer](https://github.com/splify2/steer) |
| `splify2` — панель LuCI | [splify2/splify2](https://github.com/splify2/splify2) |
| `steer-box-connector` — sing-box для podkop и forkop | [splify2/steer-box-connector](https://github.com/splify2/steer-box-connector) |
| `xsteer` — хаб и клиенты | [splify2/xsteer](https://github.com/splify2/xsteer) |

## Где что

- **`version.json`** — последние версии и файлы каждой: размер, sha256, адреса скачивания.
- **`changelogs/<продукт>/<версия>.md`** — список изменений версии.
- **Выпуски этого репозитория** — сами пакеты: выпуск `<продукт>-v<версия>`, например
  [`steer-v1.5.9`](https://github.com/splify2/releases/releases/tag/steer-v1.5.9).

## version.json

```json
{
  "schema": 1,
  "updated": "2026-10-02T12:00:00Z",
  "products": {
    "steer": {
      "title": "Ядро steer",
      "repo": "splify2/steer",
      "stable": "1.5.9",
      "prerelease": null,
      "versions": [
        {
          "version": "1.5.9",
          "channel": "stable",
          "date": "2026-09-25",
          "tag": "steer-v1.5.9",
          "source": "https://github.com/splify2/steer/releases/tag/v1.5.9",
          "changelog": "changelogs/steer/1.5.9.md",
          "assets": [
            {
              "name": "steer-1.5.9-1_x86_64.apk",
              "size": 412345,
              "sha256": "…",
              "urls": [
                "https://github.com/splify2/releases/releases/download/steer-v1.5.9/steer-1.5.9-1_x86_64.apk",
                "https://github.com/splify2/steer/releases/download/v1.5.9/steer-1.5.9-1_x86_64.apk"
              ]
            }
          ]
        }
      ]
    }
  }
}
```

- `stable` — последняя стабильная версия; `prerelease` — предварительная, только пока она новее
  стабильной, иначе `null`.
- `versions` — от новой к старой: до десяти стабильных и текущая предварительная. Старые выпуски
  остаются на GitHub, из перечня уходят.
- `urls` — по порядку: сначала выпуск здесь, потом зеркала. Скачавший сверяет `sha256`.

Читать `version.json` можно с любого из адресов — содержимое одно:

- `https://raw.githubusercontent.com/splify2/releases/main/version.json`
- `https://cdn.jsdelivr.net/gh/splify2/releases@main/version.json`
- `https://splify2.github.io/releases/version.json`

## Как сюда попадает выпуск

Выпуск проекта (его `release.yml`) последним шагом зовёт `scripts/publish.py`: тот выкладывает
пакеты в выпуск `<продукт>-v<версия>`, пишет список изменений и `version.json`, проверяет их
`scripts/check.py` и коммитит. Повторный запуск того же выпуска ничего не ломает: файлы
заменяются, запись версии переписывается. Проектам для этого нужен секрет `RELEASES_TOKEN` — токен
с правом записи в этот репозиторий.

Руками — то же самое из клона этого репозитория:

```sh
python3 scripts/publish.py --product steer --version 1.5.9 --channel stable \
    --source-tag v1.5.9 --changelog notes.md --assets out/ \
    --mirror https://github.com/splify2/steer/releases/download/v1.5.9
```
