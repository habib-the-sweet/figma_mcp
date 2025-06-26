# Figma MCP Server (Python)

Figma Model Context Protocol (MCP) server, реализованный на Python с использованием FastMCP. Этот сервер позволяет AI ассистентам взаимодействовать с Figma через WebSocket соединение для чтения данных и анализа дизайнов.

## 🎯 Возможности

- **📖 Чтение данных**: Получение информации о документах, узлах, компонентах и стилях
- **🔍 Поиск и анализ**: Сканирование узлов по типам, поиск текстового контента
- **📤 Экспорт**: Экспорт узлов как изображений в различных форматах
- **📋 Аннотации**: Просмотр аннотаций в документах
- **🧩 Компоненты**: Работа с компонентами и их экземплярами
- **🔗 Прототипирование**: Получение информации о реакциях и связях

## 🚫 Ограничения

Для безопасности этот сервер НЕ поддерживает:
- Создание новых элементов
- Изменение стилей, цветов или текста (инструменты `set_*`)
- Операции изменения узлов (перемещение, изменение размера, удаление, клонирование)

## 📋 Доступные инструменты (15 шт.)

### 🔗 **Подключение**
- `join_channel` - Присоединиться к каналу для связи с Figma

### 📖 **Получение информации**
- `get_document_info` - Получить информацию о текущем документе Figma
- `get_selection` - Получить информацию о текущем выделении
- `read_my_design` - Получить детальную информацию о выделении включая все детали узлов
- `get_node_info` - Получить информацию о конкретном узле по ID
- `get_nodes_info` - Получить информацию о нескольких узлах
- `get_node_children` - Получить ID всех дочерних узлов с полной рекурсивной вложенностью
- `get_styles` - Получить все стили из документа
- `get_local_components` - Получить все локальные компоненты

### 🧩 **Компоненты**  
- `get_instance_overrides` - Получить переопределения экземпляра компонента

### 🔍 **Поиск и сканирование**
- `scan_text_nodes` - Сканировать текстовые узлы внутри заданного узла
- `scan_nodes_by_types` - Сканировать узлы определенных типов (TEXT, RECTANGLE, FRAME)

### 📤 **Экспорт**
- `export_node_as_image` - Экспортировать узел как изображение (PNG, JPG, SVG, PDF)

### 📋 **Аннотации**
- `get_annotations` - Получить аннотации для узла или всего документа

### 🔗 **Прототипирование**
- `get_reactions` - Получить реакции (интерактивные связи) для узлов

## 🏗️ Архитектура

```
AI Client (Cursor) ←→ MCP Server ←→ WebSocket Server ←→ Figma Plugin
```

1. **MCP Server** - Предоставляет инструменты для AI
2. **WebSocket Server** - Координирует соединения и каналы
3. **Figma Plugin** - Выполняет команды в Figma

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd python-version
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Запуск WebSocket сервера

```bash
python websocket_proxy.py --port 3055 --debug
```

### 3. Запуск в Figma

1. Откройте Figma Desktop
2. Перейдите в Plugins → Development → Import plugin from manifest...
3. Выберите `src/cursor_mcp_plugin/manifest.json`
4. Запустите плагин "Cursor MCP Plugin"
5. Подключитесь к серверу на порту 3055
6. Запомните Channel ID (например: `abc123xyz`)

### 4. Настройка MCP в Cursor

Добавьте следующую конфигурацию в настройки MCP Cursor (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "figma-mcp": {
      "command": "python",
      "args": ["-m", "src.figma_mcp.server", "--server", "localhost:3055"],
      "cwd": "/path/to/your/figma_mcp"
    }
  }
}
```

**Альтернативный способ (с виртуальным окружением):**
```json
{
  "mcpServers": {
    "figma-mcp": {
      "command": "/path/to/your/figma_mcp/venv/bin/python",
      "args": ["/path/to/your/figma_mcp/src/figma_mcp/server.py", "--server", "localhost:3055"]
    }
  }
}
```

> **Примечание**: Замените `/path/to/your/figma_mcp` на реальный путь к проекту.

### 5. Запуск MCP сервера

```bash
python -m src.figma_mcp.server --server localhost:3055
```

### 6. Подключение к каналу

Используйте инструмент `join_channel` с полученным Channel ID:

```json
{
  "tool": "join_channel",
  "arguments": {
    "channel": "abc123xyz"
  }
}
```

## 🛠️ Примеры использования

### Получение информации о документе
```json
{
  "tool": "get_document_info",
  "arguments": {}
}
```

### Получение информации о узле
```json
{
  "tool": "get_node_info", 
  "arguments": {
    "node_id": "4472:98013"
  }
}
```

### Получение всех дочерних узлов
```json
{
  "tool": "get_node_children",
  "arguments": {
    "node_id": "4472:98012"
  }
}
```

### Поиск текстовых узлов
```json
{
  "tool": "scan_text_nodes",
  "arguments": {
    "node_id": "4472:98012",
    "use_chunking": true,
    "chunk_size": 50
  }
}
```

### Экспорт как изображение
```json
{
  "tool": "export_node_as_image",
  "arguments": {
    "node_id": "4472:98013",
    "format": "PNG",
    "scale": 2.0
  }
}
```

## 🔧 Конфигурация

### WebSocket Server
- **Порт**: 3055 (по умолчанию)
- **Host**: localhost
- **Debug режим**: `--debug`

### MCP Server  
- **Server URL**: localhost:3055 (по умолчанию)
- **Протокол**: MCP 2024-11-05
- **Transport**: stdio

### Cursor MCP Settings

Создайте файл `.cursor/mcp.json` в корне вашего проекта или в домашней директории:

```json
{
  "$schema": "https://schema.cursor.com/mcp.json",
  "mcpServers": {
    "figma-mcp": {
      "command": "python",
      "args": ["-m", "src.figma_mcp.server", "--server", "localhost:3055"],
      "cwd": "/absolute/path/to/figma_mcp",
      "env": {
        "PYTHONPATH": "/absolute/path/to/figma_mcp"
      }
    }
  }
}
```

**Основные параметры:**
- `command`: Команда для запуска Python
- `args`: Аргументы для запуска MCP сервера
- `cwd`: Рабочая директория (абсолютный путь к проекту)
- `env`: Переменные окружения (опционально)

## 📁 Структура проекта

```
python-version/
├── src/figma_mcp/
│   ├── __init__.py
│   ├── server.py          # Главный MCP сервер
│   ├── websocket_client.py # WebSocket клиент
│   ├── types.py           # Типы Pydantic
│   └── utils.py           # Утилиты
├── tests/                 # Тесты (41 тест)
├── websocket_proxy.py     # WebSocket сервер
├── requirements.txt       # Зависимости
└── README.md             # Документация
```

## 🧪 Тестирование

Запуск всех тестов:
```bash
python -m pytest tests/ -v
```

Тестирование подключения:
```bash
python test_mcp.py
```

## 🔒 Безопасность

- Фильтрация конфиденциальных данных из ответов Figma
- Валидация всех параметров с Pydantic
- Обработка ошибок и таймаутов
- Логирование в stderr для отладки

## 📦 Зависимости

- **fastmcp**: 2.4.0 - MCP сервер фреймворк
- **websockets**: 15.0.1 - WebSocket клиент/сервер
- **pydantic**: 2.11.5 - Валидация данных
- **pytest**: 8.3.5 - Тестирование

## 🐛 Отладка

1. **Проблемы с подключением**: Проверьте статус WebSocket сервера
2. **Таймауты**: Увеличьте timeout в WebSocket клиенте
3. **Ошибки каналов**: Убедитесь, что используете правильный Channel ID
4. **Логи**: Смотрите вывод в stderr для детальной информации

## 📝 Лицензия

MIT License

## 🤝 Вклад

1. Форкните репозиторий
2. Создайте ветку для функции
3. Добавьте тесты
4. Отправьте pull request 