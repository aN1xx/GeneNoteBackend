# GeneNote Backend

> FastAPI backend for genetic lab management system. Clean Architecture + DDD, event-driven pipeline orchestration with Kafka, async PostgreSQL (SQLAlchemy 2.0), Snakemake bioinformatics pipelines. JWT auth with RBAC, 148+ tests, Docker deployment.

FastAPI backend для системы управления генетической лабораторией. Обрабатывает пайплайны вариантного анализа (Snakemake), управляет пациентами/образцами и генерирует отчеты.

## Архитектура

Проект следует принципам Clean Architecture:

```
src/
├── domain/           # Бизнес-логика (entities, enums, exceptions, value objects)
├── application/      # Use cases и DTOs
├── infrastructure/   # Внешние сервисы (DB, Kafka, Security, Pipeline)
├── presentation/     # API endpoints и dependencies
├── config.py         # Конфигурация приложения
├── main.py           # FastAPI приложение
└── worker.py         # Kafka worker для пайплайнов
```

## Требования

- Python 3.12+
- PostgreSQL 16+
- Apache Kafka
- Snakemake 7+ (для вариантного анализа)
- Conda (для Snakemake окружений)

## Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd GeneNoteBackend

# Создание виртуального окружения
python3.12 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
# или с poetry:
poetry install
```

## Конфигурация

Создайте файл `.env` в корне проекта:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/genenote

# Security
JWT_SECRET_KEY=your-secret-key-min-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# File Storage
FILE_STORAGE_PATH=/data/genenote

# Pipeline (Snakemake variant calling pipeline)
PIPELINE_PATH=/path/to/Variant_Calling_Pipeline/Pipeline_Semi-Auto
SNAKEMAKE_CORES=4

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Интеграция с Snakemake Pipeline

Backend интегрирован с пайплайном вариантного анализа (`Pipeline_Semi-Auto`), который выполняет:

### Variant Calling Pipeline
1. **Trimming** - обрезка адаптеров с `fastp`
2. **Mapping** - выравнивание на референс GRCh38 с `bwa mem`
3. **Variant Calling** - три инструмента параллельно:
   - GATK HaplotypeCaller
   - NGSEP
   - xAtlas
4. **VCF Normalization** - нормализация с `bcftools`
5. **Variant Table** - объединение результатов в TSV таблицу

### Выходные файлы
- `{sample}_variants_raw.tsv` - таблица вариантов с аннотациями
- `{sample}_CovWidthAtDepths.tsv` - статистика покрытия (0x, 5x, 30x, 50x, 100x)

### Компоненты интеграции

| Компонент | Описание |
|-----------|----------|
| `PipelineService` | Запуск Snakemake, мониторинг прогресса, парсинг результатов |
| `VariantTableParser` | Парсинг `_variants_raw.tsv` в `SampleVariant` entities |
| `CoverageParser` | Парсинг `_CovWidthAtDepths.tsv` в `SampleCoverage` entity |
| `PipelineWorker` | Kafka worker для асинхронного выполнения пайплайнов |

## Запуск

### Миграции базы данных

```bash
# Применить миграции
alembic upgrade head

# Создать новую миграцию
alembic revision --autogenerate -m "description"
```

### API сервер

```bash
# Development
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Kafka Workers

```bash
# Event processor (обновление БД по событиям пайплайнов)
python -m src.worker --mode event-processor

# Pipeline worker (выполнение Snakemake пайплайнов)
python -m src.worker --mode pipeline
```

## API Endpoints

### Аутентификация
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/v1/auth/login` | Вход пользователя |
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/refresh` | Обновление токена |
| GET | `/api/v1/auth/me` | Текущий пользователь |

### Пациенты
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/v1/patients` | Создать пациента |
| GET | `/api/v1/patients` | Список пациентов |
| GET | `/api/v1/patients/search` | Поиск пациентов |
| GET | `/api/v1/patients/{id}` | Получить пациента |

### Образцы
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/v1/samples` | Создать образец |
| POST | `/api/v1/samples/upload` | Загрузить TSV + FASTQ файлы |
| GET | `/api/v1/samples/awaiting-annotation` | Образцы для аннотации |
| GET | `/api/v1/samples/{id}` | Получить образец |
| GET | `/api/v1/samples/{id}/variants` | Варианты образца |
| GET | `/api/v1/samples/{id}/coverage` | Покрытие образца |

### Аннотация (для генетиков)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/v1/annotation/samples/{id}/variants` | Варианты для аннотации |
| POST | `/api/v1/annotation/variants/{id}/annotate` | Аннотировать вариант |
| POST | `/api/v1/annotation/samples/{id}/complete` | Завершить аннотацию |

### Отчёты
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/v1/reports/samples/{id}/generate` | Сгенерировать PDF отчёт |
| GET | `/api/v1/reports/samples/{id}/download` | Скачать PDF отчёт |

### Пайплайны
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/v1/pipelines/start` | Запустить пайплайн |
| GET | `/api/v1/pipelines/{id}` | Статус пайплайна |
| POST | `/api/v1/pipelines/{id}/cancel` | Отменить пайплайн |

### Служебные
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/health` | Проверка здоровья |
| GET | `/openapi.json` | OpenAPI спецификация |

## Роли пользователей

- **Лаборант** (`laborant`): загрузка образцов, запуск вариантного анализа
- **Генетик** (`geneticist`): аннотация вариантов, генерация отчетов
- **Администратор** (`administrator`): управление пользователями

## Workflow обработки образца

```
1. Лаборант загружает TSV + FASTQ файлы
   └── POST /api/v1/samples/upload

2. Система создаёт пациента и образец
   └── Статус: PENDING → PROCESSING

3. Запускается Snakemake pipeline
   └── GATK + NGSEP + xAtlas variant calling

4. Результаты парсятся и сохраняются в БД
   └── Статус: PROCESSING → AWAITING_ANNOTATION

5. Генетик аннотирует варианты
   └── Классификация: is_variant / is_artifact
   └── ACMG: Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign

6. Генерируется PDF отчёт
   └── Статус: ANNOTATED → REPORT_GENERATED
```

## Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Только unit тесты
pytest tests/unit/

# Только интеграционные тесты
pytest tests/integration/

# Тесты pipeline компонентов
pytest tests/unit/infrastructure/test_variant_table_parser.py
pytest tests/unit/infrastructure/test_coverage_parser.py
pytest tests/unit/infrastructure/test_pipeline_service.py
```

## Линтинг

```bash
# Проверка кода
ruff check src/

# Автоисправление
ruff check src/ --fix

# Проверка типов
mypy src/
```

## Docker

### Первый запуск (скачивание reference файлов)

Перед первым запуском необходимо скачать reference файлы генома GRCh38 (~8-10 GB):

```bash
# 1. Установить необходимые инструменты (на хост-машине)
# Требуются: wget, samtools, bwa, gatk

# 2. Запустить скрипт скачивания reference файлов
./scripts/download_references.sh

# Это скачает:
# - GRCh38.fa (~3 GB) - референсный геном
# - GRCh38.fa.fai - индекс FASTA
# - GRCh38.dict - dictionary для GATK
# - BWA index (~5 GB) - индекс для bwa mem
```

### Запуск

```bash
# Только API + DB + Kafka (без pipeline worker)
docker compose up -d

# Полный стек с pipeline worker
docker compose --profile full up -d
```

### Docker Compose сервисы

| Сервис | Описание | Порт |
|--------|----------|------|
| `api` | FastAPI backend | 8000 |
| `worker` | Kafka consumer + Snakemake pipeline | - |
| `db` | PostgreSQL 16 | 5432 |
| `kafka` | Apache Kafka (KRaft mode) | 9092 |
| `kafka-ui` | Kafka UI (dev profile) | 8080 |

### Volumes

| Volume | Описание |
|--------|----------|
| `postgres_data` | Данные PostgreSQL |
| `kafka_data` | Данные Kafka |
| `file_storage` | Загруженные файлы |
| `pipeline_results` | Результаты пайплайна |
| `./pipeline/references` | Reference файлы (mount) |

## Структура Kafka топиков

- `genenote.pipeline.commands` - команды для запуска пайплайнов
- `genenote.pipeline.events` - события выполнения пайплайнов
- `genenote.sample.events` - события связанные с образцами

## База данных

### Основные таблицы
- `users` - пользователи системы
- `patients` - пациенты
- `samples` - образцы (связь с patient)
- `sample_variants` - варианты образца (результаты pipeline)
- `sample_coverages` - покрытие образца
- `germline_variants` - база известных вариантов
- `germline_artifacts` - база артефактов
- `pipeline_runs` - история запусков пайплайнов

## Лицензия

MIT
