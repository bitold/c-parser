# c-parser

Парсит C/C++ и складывает сущности (функции, типы, макросы…) в Neo4j или JSONL.

## Установка

```bash
./scripts/build
./scripts/install
```

- `scripts/build` — собирает wheel-пакеты `neo4j-api` и `c-parser` в `scripts/`
- `scripts/install` — ставит эти `.whl` через `pip --user` (бинарник `c-parser` → `~/.local/bin`)

## Запуск и подключение локального neo4j для тестирования

```bash
cp .env.example .env
docker compose up -d
```

UI: http://localhost:7474 (логин/пароль в `.env`).

## Запуск

```bash
# в Neo4j
c-parser /path/to/sources

# в файл
c-parser /path/to/sources -o entities.jsonl

# в stdout
c-parser /path/to/sources --sink jsonl
```

Опции:

```bash
--include-documented   # не пропускать уже задокументированное
--strict-doc-comments  # документация только /** и ///
```

## Тесты
Папка tests содержит тесты сгенерированные ИИ агентом.