# Bot Status Polling Guide

## Архитектура polling статусов бота

Система позволяет фронтенду отслеживать состояние бота в реальном времени через polling.

### Статусы бота

1. `initialized` - Бот создан и инициализирован
2. `connecting` - Бот подключается к Google Meet
3. `connected` - Бот успешно подключился к встрече
4. `transcribing` - Идет транскрипция аудио
5. `analyzing_meeting` - Анализ встречи
6. `creating_tasks` - Создание задач в Jira
7. `done` - Процесс завершен успешно
8. `error` - Произошла ошибка

### Схема работы

```
┌──────────┐          ┌─────────────────┐         ┌──────────────────┐
│ Frontend │          │  Your Backend   │         │ External Bot     │
│          │          │  (localhost:8000)│         │ Service (:8001)  │
└────┬─────┘          └────────┬────────┘         └────────┬─────────┘
     │                         │                           │
     │ 1. POST /trigger        │                           │
     ├────────────────────────>│                           │
     │                         │ 2. POST /bots/start       │
     │                         ├──────────────────────────>│
     │                         │                           │
     │                         │ 3. bot_id + status        │
     │                         │<──────────────────────────┤
     │ 4. bot_id               │                           │
     │<────────────────────────┤                           │
     │                         │                           │
     │ 5. GET /status/{bot_id} │                           │
     ├────────────────────────>│                           │
     │  (every 2-3 seconds)    │                           │
     │                         │ 6. GET /bots/{bot_id}     │
     │                         ├──────────────────────────>│
     │                         │ (auto-syncs statuses      │
     │ 7. current status       │  for states 1-3)          │
     │<────────────────────────┤                           │
     │                         │                           │
     │      ... polling ...    │                           │
     │                         │                           │
     │                         │ 8. Bot записал аудио,     │
     │                         │    вызывает /create-tasks │
     │                         │<──────────────────────────┤
     │                         │                           │
     │                         │ (statuses 4-7 updates)    │
     │                         │                           │
     │ 9. GET /status/{bot_id} │                           │
     ├────────────────────────>│                           │
     │                         │                           │
     │ 10. status: done        │                           │
     │<────────────────────────┤                           │
     │                         │                           │
```

---

## API Reference

### 1. Запуск бота

**Endpoint:** `POST /api/v1/meet/trigger`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Request:**
```json
{
  "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
  "bot_name": "Tamir Bot"
}
```

**Response:**
```json
{
  "bot_id": "bot_123456",
  "status": "initialized",
  "message": "Bot bot_123456 started successfully for meeting"
}
```

---

### 2. Получение статуса (для polling)

**Endpoint:** `GET /api/v1/meet/status/{bot_id}`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "bot_id": "bot_123456",
  "status": "transcribing",
  "user_id": "user_789",
  "created_at": "2025-11-26T10:00:00.000Z",
  "updated_at": "2025-11-26T10:05:00.000Z",
  "error_message": null,
  "session_id": "session_abc",
  "result_data": null
}
```

**Статусы в результате:**
- `initialized`, `connecting`, `connected` - синхронизируются из внешнего сервиса `:8001`
- `transcribing`, `analyzing_meeting`, `creating_tasks`, `done`, `error` - обновляются внутри вашего бэкенда

---

### 3. Callback для внешнего сервиса (опционально)

Если внешний сервис хочет явно обновить статус на `done`:

**Endpoint:** `POST /api/v1/meet/callback/update-status`

**Request:**
```json
{
  "bot_id": "bot_123456",
  "session_id": "session_abc",
  "result_data": {
    "tasks_created": 5,
    "summary": "Meeting processed successfully"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Status updated successfully"
}
```

---

## Frontend Implementation

### React/TypeScript Example

```typescript
import { useState, useEffect, useCallback } from 'react';

interface BotStatus {
  bot_id: string;
  status: 'initialized' | 'connecting' | 'connected' | 'transcribing' |
          'analyzing_meeting' | 'creating_tasks' | 'done' | 'error';
  user_id: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  session_id?: string;
  result_data?: any;
}

export function useBotStatus(botId: string | null, token: string) {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!botId || !token) return;

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/meet/status/${botId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }

      const data: BotStatus = await response.json();
      setStatus(data);
      setError(null);

      // Останавливаем polling если статус финальный
      if (data.status === 'done' || data.status === 'error') {
        return true; // signal to stop polling
      }

      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [botId, token]);

  useEffect(() => {
    if (!botId) return;

    setLoading(true);

    // Начальный запрос
    fetchStatus().then((shouldStop) => {
      setLoading(false);
      if (shouldStop) return;

      // Polling каждые 3 секунды
      const interval = setInterval(async () => {
        const shouldStop = await fetchStatus();
        if (shouldStop) {
          clearInterval(interval);
        }
      }, 3000);

      return () => clearInterval(interval);
    });
  }, [botId, fetchStatus]);

  return { status, loading, error };
}

// Пример использования в компоненте
export function MeetingBotTracker() {
  const [botId, setBotId] = useState<string | null>(null);
  const token = 'your_jwt_token'; // получите из вашего auth context

  const { status, loading, error } = useBotStatus(botId, token);

  const startBot = async (meetUrl: string) => {
    const response = await fetch('http://localhost:8000/api/v1/meet/trigger', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        meet_url: meetUrl,
        bot_name: 'Tamir Bot',
      }),
    });

    const data = await response.json();
    setBotId(data.bot_id);
  };

  return (
    <div>
      <button onClick={() => startBot('https://meet.google.com/xxx-yyyy-zzz')}>
        Start Bot
      </button>

      {loading && <p>Loading status...</p>}
      {error && <p>Error: {error}</p>}

      {status && (
        <div>
          <h3>Bot Status: {status.status}</h3>
          <StatusAnimation status={status.status} />

          {status.status === 'done' && status.result_data && (
            <div>
              <h4>Results:</h4>
              <pre>{JSON.stringify(status.result_data, null, 2)}</pre>
            </div>
          )}

          {status.status === 'error' && (
            <p className="error">Error: {status.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}

// Компонент для анимации в зависимости от статуса
function StatusAnimation({ status }: { status: string }) {
  const statusMessages = {
    initialized: '🚀 Initializing bot...',
    connecting: '🔌 Connecting to meeting...',
    connected: '✅ Connected! Recording...',
    transcribing: '🎤 Transcribing audio...',
    analyzing_meeting: '🤔 Analyzing meeting...',
    creating_tasks: '📝 Creating tasks in Jira...',
    done: '✨ Done!',
    error: '❌ Error occurred',
  };

  return (
    <div className={`status-animation status-${status}`}>
      <p>{statusMessages[status as keyof typeof statusMessages]}</p>
      {status !== 'done' && status !== 'error' && (
        <div className="spinner" />
      )}
    </div>
  );
}
```

---

## Важные замечания

### 1. Автоматическая синхронизация статусов 1-3

Фоновая задача каждые 3 секунды автоматически синхронизирует статусы `initialized`, `connecting`, `connected` из внешнего сервиса. Фронтенду не нужно беспокоиться об этом.

### 2. Переход к статусам 4-7

Когда внешний сервис записывает аудио и вызывает `/create-tasks-from-audio`, бэкенд автоматически обновляет статусы:
- `transcribing` → `analyzing_meeting` → `creating_tasks` → `done`

### 3. Интеграция внешнего сервиса

Внешний сервис должен вызывать:
```bash
POST http://localhost:8000/api/v1/create-tasks-from-audio
Content-Type: application/json

{
  "user_id": "user_789",
  "bot_id": "bot_123456",  # ВАЖНО: передать bot_id!
  "audio_url": "https://storage.googleapis.com/path/to/audio.wav"
}
```

### 4. Polling интервал

Рекомендуемый интервал: **2-3 секунды**

- Слишком частый (< 1 сек): избыточная нагрузка
- Слишком редкий (> 5 сек): задержка в UI

### 5. Остановка polling

Обязательно останавливайте polling когда статус становится `done` или `error`.

### 6. Обработка ошибок

Если статус `error`, проверьте поле `error_message` для деталей.

---

## Backend Configuration

### Настройка интервала синхронизации

В `bot_status_sync.py`:
```python
# По умолчанию 3 секунды
sync_task = BotStatusSyncTask(storage, sync_interval=3)

# Можно изменить при необходимости
sync_task = BotStatusSyncTask(storage, sync_interval=5)
```

### Настройка cleanup

В `bot_status_storage.py`:
```python
# Cleanup каждый час, удаляет записи старше 24 часов
async def _cleanup_old_entries(self):
    while True:
        await asyncio.sleep(3600)  # Изменить интервал
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # Изменить TTL
        ...
```

---

## Testing

### Тестирование потока

1. Запустите бота:
```bash
curl -X POST http://localhost:8000/api/v1/meet/trigger \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meet_url": "https://meet.google.com/xxx-yyyy-zzz",
    "bot_name": "Test Bot"
  }'
```

2. Получите bot_id из ответа

3. Проверяйте статус:
```bash
curl http://localhost:8000/api/v1/meet/status/bot_123456 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

4. Симулируйте вызов create-tasks:
```bash
curl -X POST http://localhost:8000/api/v1/create-tasks-from-audio \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_789",
    "bot_id": "bot_123456",
    "audio_url": "https://example.com/audio.wav"
  }'
```

5. Проверьте финальный статус снова

---

## Troubleshooting

### Статус не обновляется

1. Проверьте логи фоновой задачи: `Background tasks started`
2. Убедитесь что внешний сервис доступен по `http://host.docker.internal:8001`
3. Проверьте что bot_id существует в storage

### Статус застрял на `connected`

Внешний сервис не вызвал `/create-tasks-from-audio` с `bot_id`. Убедитесь что:
- Параметр `bot_id` передается в запросе
- URL правильный: `http://localhost:8000/api/v1/create-tasks-from-audio`

### 404 Not Found при polling

Бот не найден. Возможные причины:
- bot_id неправильный
- Запись была удалена cleanup задачей (> 24 часов)
- Внешний сервис вернул ошибку при создании бота

---

## Future Improvements

Возможные улучшения:

1. **WebSocket вместо polling** - более эффективно для real-time обновлений
2. **Server-Sent Events (SSE)** - односторонний stream от сервера
3. **Push notifications** - уведомления когда процесс завершен
4. **Webhook support** - callback URL для уведомлений
5. **Database persistence** - хранение статусов в БД вместо in-memory
