# Integration Guide - Bot Status Polling

## Что было реализовано

Система polling для отслеживания статусов бота с автоматической синхронизацией из внешнего сервиса.

## Архитектура

### Компоненты

1. **BotStatusStorage** (`bot_status_storage.py`)
   - In-memory хранилище статусов
   - Thread-safe операции с async/await
   - Автоматический cleanup старых записей (> 24 часов)

2. **BotStatusSyncTask** (`bot_status_sync.py`)
   - Фоновая задача для синхронизации статусов 1-3
   - Каждые 3 секунды обновляет статусы из `http://host.docker.internal:8001`
   - Останавливает синхронизацию для финальных статусов (done/error)

3. **API Endpoints** (`router.py`)
   - `POST /api/v1/meet/trigger` - Запуск бота
   - `GET /api/v1/meet/status/{bot_id}` - Polling endpoint
   - `POST /api/v1/meet/callback/update-status` - Callback для внешнего сервиса

4. **Task Processing** (`routes.py`)
   - `POST /api/v1/create-tasks-from-audio` - Обработка задач с обновлением статусов

## Статусы

```
initialized → connecting → connected → transcribing → analyzing_meeting → creating_tasks → done
                                                                                          ↓
                                                                                       error
```

### Источники статусов

**Статусы 1-3** (синхронизируются из внешнего сервиса):
- `initialized` - из внешнего API
- `connecting` - из внешнего API
- `connected` - из внешнего API

**Статусы 4-7** (обновляются внутри бэкенда):
- `transcribing` - начало обработки в `/create-tasks-from-audio`
- `analyzing_meeting` - после создания сессии агента
- `creating_tasks` - перед запуском агента
- `done` - после успешного завершения
- `error` - при ошибке

## Интеграция внешнего сервиса

### Что нужно изменить в сервисе на порту 8001

Когда бот закончил запись и готов обработать аудио, вызовите:

```python
import httpx

async def process_recorded_audio(bot_id: str, audio_url: str, user_id: str):
    """После записи аудио вызываем обработку задач"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            'http://host.docker.internal:8000/api/v1/create-tasks-from-audio',
            json={
                'user_id': user_id,
                'bot_id': bot_id,  # ВАЖНО!
                'audio_url': audio_url
            }
        )
        response.raise_for_status()
        return response.json()
```

### Пример интеграции в ваш код на :8001

```python
# Где-то в коде после завершения записи:

# 1. Бот записал аудио
audio_file_path = await bot.stop_recording()

# 2. Загружаем в storage
audio_url = await upload_to_storage(audio_file_path)

# 3. ВАЖНО: Вызываем обработку с bot_id
result = await process_recorded_audio(
    bot_id=bot.id,
    audio_url=audio_url,
    user_id=bot.user_id
)

logger.info(f"Tasks created: {result}")
```

## Frontend Polling

### Простой пример на JavaScript

```javascript
async function pollBotStatus(botId, token) {
  const pollInterval = 3000; // 3 секунды

  while (true) {
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/meet/status/${botId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      const status = await response.json();
      console.log('Bot status:', status.status);

      // Обновляем UI
      updateUI(status.status);

      // Останавливаем polling если финальный статус
      if (status.status === 'done' || status.status === 'error') {
        if (status.status === 'done') {
          console.log('Results:', status.result_data);
        } else {
          console.error('Error:', status.error_message);
        }
        break;
      }

      // Ждем перед следующим запросом
      await new Promise(resolve => setTimeout(resolve, pollInterval));

    } catch (error) {
      console.error('Polling error:', error);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }
}

// Использование
const startBot = async (meetUrl) => {
  const response = await fetch('http://localhost:8000/api/v1/meet/trigger', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${yourToken}`
    },
    body: JSON.stringify({
      meet_url: meetUrl,
      bot_name: 'My Bot'
    })
  });

  const { bot_id } = await response.json();

  // Начинаем polling
  pollBotStatus(bot_id, yourToken);
};
```

## Тестирование

### 1. Запустите сервис

```bash
cd /Users/Lazynx/PythonProjects/kernel/scrum-master
python scrum_master/main.py
```

В логах должны появиться:
```
INFO: Background tasks started
INFO: Bot status cleanup task started
INFO: Bot status sync task started
```

### 2. Создайте бота

```bash
curl -X POST http://localhost:8000/api/v1/meet/trigger \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
    "bot_name": "Test Bot"
  }'
```

Ответ:
```json
{
  "bot_id": "bot_123",
  "status": "initialized",
  "message": "Bot bot_123 started successfully for meeting"
}
```

### 3. Проверьте polling

```bash
# Вызывайте несколько раз с интервалом 3 сек
curl http://localhost:8000/api/v1/meet/status/bot_123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Статус будет автоматически обновляться: `initialized` → `connecting` → `connected`

### 4. Симулируйте обработку задач

```bash
curl -X POST http://localhost:8000/api/v1/create-tasks-from-audio \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "bot_id": "bot_123",
    "text": "Test meeting transcription"
  }'
```

Статус изменится: `transcribing` → `analyzing_meeting` → `creating_tasks` → `done`

### 5. Проверьте финальный результат

```bash
curl http://localhost:8000/api/v1/meet/status/bot_123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Ответ:
```json
{
  "bot_id": "bot_123",
  "status": "done",
  "user_id": "user_123",
  "created_at": "2025-11-26T10:00:00.000Z",
  "updated_at": "2025-11-26T10:05:00.000Z",
  "error_message": null,
  "session_id": "session_abc",
  "result_data": {
    "tasks": [...],
    "summary": "..."
  }
}
```

## Настройки

### Изменить интервал синхронизации

В `main.py`:
```python
sync_task = BotStatusSyncTask(storage, sync_interval=5)  # 5 секунд вместо 3
```

### Изменить TTL записей

В `bot_status_storage.py`:
```python
cutoff_time = datetime.utcnow() - timedelta(hours=48)  # 48 часов вместо 24
```

### Изменить интервал cleanup

В `bot_status_storage.py`:
```python
await asyncio.sleep(7200)  # 2 часа вместо 1
```

## Troubleshooting

### Статус не обновляется автоматически (1-3)

**Проблема:** Статус остается `initialized`

**Решение:**
1. Проверьте доступность внешнего сервиса:
   ```bash
   curl http://host.docker.internal:8001/api/v1/bots/bot_123
   ```
2. Проверьте логи фоновой задачи
3. Убедитесь что sync task запущен

### Статус не переходит к 4-7

**Проблема:** Застрял на `connected`

**Решение:**
1. Убедитесь что внешний сервис вызывает `/create-tasks-from-audio`
2. Проверьте что передается `bot_id` в запросе
3. Проверьте логи обработки

### 403 Forbidden при polling

**Проблема:** Пользователь не может получить статус чужого бота

**Решение:** Это правильное поведение. Каждый пользователь может видеть только свои боты.

### 404 Not Found

**Проблема:** Бот не найден

**Решение:**
1. Проверьте правильность `bot_id`
2. Возможно запись удалена cleanup задачей (> 24 часа)
3. Создайте бота заново

## Файлы изменены

```
scrum_master/
├── main.py                                            # Добавлены startup/shutdown events
├── modules/google_meet/
│   ├── infrastructure/
│   │   ├── bot_status_storage.py                     # Уже существовал
│   │   └── bot_status_sync.py                        # НОВЫЙ
│   └── presentation/api/meet/
│       ├── router.py                                  # Добавлены endpoints
│       └── schemas.py                                 # Уже существовал
└── agents/meet_agent/api/
    └── routes.py                                      # Обновлен create-tasks-from-audio

Документация:
├── BOT_STATUS_POLLING_GUIDE.md                        # НОВЫЙ - детальный гайд
└── INTEGRATION_GUIDE.md                               # НОВЫЙ - краткий гайд интеграции
```

## Следующие шаги

1. **Запустите сервис** и проверьте что фоновые задачи стартуют
2. **Обновите внешний сервис** на порту 8001 чтобы передавать `bot_id`
3. **Реализуйте polling на фронтенде** согласно примерам
4. **Протестируйте** полный flow от создания до завершения

## Дополнительно

Полное руководство с примерами React/TypeScript, диаграммами и troubleshooting:
- См. `BOT_STATUS_POLLING_GUIDE.md`
