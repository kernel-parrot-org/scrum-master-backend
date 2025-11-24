# Google Meet Module

Модуль для автоматического подключения ботов к Google Meet встречам с использованием Selenium WebDriver.

## Возможности

- Автоматическое подключение к Google Meet встречам по ссылке
- Управление состоянием встреч (подключение, отключение, статусы)
- Автоматическое отключение микрофона и камеры при входе
- Кастомизация имени бота
- История всех встреч пользователя
- Обработка различных сценариев (встреча не найдена, требуется одобрение хоста)

## API Endpoints

### 1. Подключение к встрече

```http
POST /api/v1/meet/connect
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
  "bot_name": "Scrum Bot" // опционально
}
```

**Ответ:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
  "status": "CONNECTED",
  "bot_name": "Scrum Bot",
  "error_message": null,
  "connected_at": "2025-11-24T12:00:00Z",
  "disconnected_at": null,
  "created_at": "2025-11-24T12:00:00Z",
  "updated_at": "2025-11-24T12:00:00Z"
}
```

**Статусы встречи:**
- `PENDING` - встреча создана, подключение еще не началось
- `CONNECTING` - идет процесс подключения
- `CONNECTED` - бот успешно подключен к встрече
- `DISCONNECTED` - бот отключен от встречи
- `FAILED` - ошибка при подключении

### 2. Отключение от встречи

```http
POST /api/v1/meet/disconnect
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "meeting_id": "uuid"
}
```

### 3. Получение списка встреч

```http
GET /api/v1/meet/meetings
Authorization: Bearer <access_token>
```

**Ответ:**
```json
{
  "meetings": [...],
  "total": 10
}
```

## Установка и запуск

### Локальная разработка (macOS/Linux)

1. Установите Google Chrome:
```bash
# macOS
brew install --cask google-chrome

# Linux (Debian/Ubuntu)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

2. Установите зависимости:
```bash
uv sync
```

3. ChromeDriver установится автоматически при первом запуске через `webdriver-manager`

4. Запустите приложение:
```bash
uv run uvicorn scrum_master.main:create_app --factory --reload
```

### Docker

1. Пересоберите контейнер:
```bash
docker-compose build
```

2. Запустите:
```bash
docker-compose up
```

Google Chrome уже включен в Docker-образ и будет работать в headless режиме.

## Конфигурация

Добавьте в `.env` файл:

```env
# Google Meet Configuration (опционально)
GOOGLE_MEET_CHROMEDRIVER_PATH=/usr/local/bin/chromedriver  # путь к chromedriver
GOOGLE_MEET_HEADLESS=true                                   # headless режим (по умолчанию true)
GOOGLE_MEET_ENABLE_LOGGING=true                             # логирование (по умолчанию true)
GOOGLE_MEET_BOT_NAME=Scrum Bot                              # имя бота по умолчанию
GOOGLE_MEET_AUTO_JOIN=true                                  # автоматическое подключение
```

## Архитектура

Модуль следует Clean Architecture принципам:

```
google_meet/
├── domain/               # Бизнес-логика и сущности
│   └── entities.py       # Meeting, MeetingStatus
├── application/          # Use cases
│   ├── interfaces.py     # Интерфейсы репозиториев
│   ├── dtos/            # Data Transfer Objects
│   └── interactors/     # Бизнес-логика
├── infrastructure/       # Внешние зависимости
│   ├── selenium/        # Selenium адаптер
│   └── repositories/    # Реализация репозиториев
├── presentation/         # API слой
│   └── api/meet/        # FastAPI endpoints
├── config.py            # Конфигурация
└── ioc.py              # Dependency Injection
```

## Технические детали

### Selenium WebDriver

- Используется Chrome WebDriver через Selenium
- Автоматическая установка ChromeDriver через `webdriver-manager`
- Поддержка headless режима для серверного запуска
- Отключение автоматизации флагов для обхода детекции

### Асинхронность

- Selenium операции выполняются в ThreadPoolExecutor
- Основной код использует async/await
- Не блокирует event loop FastAPI

### База данных

- Таблица `meetings` хранит информацию о всех встречах
- Связана с таблицей `users` через foreign key
- Миграция: `a1b2c3d4e5f6_add_meetings_table.py`

## Troubleshooting

### Ошибка: "Unable to obtain driver for chrome"

**Решение:** Убедитесь, что Google Chrome установлен:
```bash
# Проверка установки Chrome
which google-chrome  # Linux
which /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome  # macOS
```

### Ошибка: "ChromeDriver version mismatch"

**Решение:** `webdriver-manager` автоматически скачает совместимую версию. Если ошибка сохраняется:
```bash
# Очистите кеш webdriver-manager
rm -rf ~/.wdm
```

### Ошибка: "Meeting not found"

**Причины:**
- Неверная ссылка на встречу
- Встреча уже завершена
- Доступ к встрече ограничен

### Ошибка при запуске в Docker: "no DISPLAY environment variable"

**Решение:** Headless режим уже включен в конфигурации по умолчанию. Если ошибка сохраняется, проверьте настройки в `config.py`.

## Примеры использования

### Python

```python
import httpx

# Получить access token через OAuth
access_token = "your_access_token"

# Подключиться к встрече
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/meet/connect",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
            "bot_name": "My Bot"
        }
    )
    meeting = response.json()
    print(f"Meeting ID: {meeting['id']}")
    print(f"Status: {meeting['status']}")
```

### cURL

```bash
# Подключение к встрече
curl -X POST http://localhost:8000/api/v1/meet/connect \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
    "bot_name": "Scrum Bot"
  }'

# Получить список встреч
curl http://localhost:8000/api/v1/meet/meetings \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Отключиться от встречи
curl -X POST http://localhost:8000/api/v1/meet/disconnect \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meeting_id": "MEETING_UUID"}'
```

## Ограничения

1. **Google Account:** Для подключения к приватным встречам может потребоваться авторизация в Google аккаунт (в текущей версии не реализовано)

2. **Одновременные подключения:** Один экземпляр GoogleMeetAdapter может поддерживать только одно активное подключение

3. **Ресурсы:** Каждый экземпляр Chrome использует ~200-300MB RAM

4. **Rate Limiting:** Google Meet может блокировать частые автоматические подключения

## TODO

- [ ] Поддержка авторизации через Google OAuth для доступа к приватным встречам
- [ ] Запись аудио/видео встречи
- [ ] Транскрипция речи в реальном времени
- [ ] Отправка сообщений в чат встречи
- [ ] Управление несколькими встречами одновременно
- [ ] WebSocket для real-time обновлений статуса
