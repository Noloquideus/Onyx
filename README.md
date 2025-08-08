# Onyx CLI Tools

🚀 Мощная коллекция полезных CLI утилит для Windows и Linux.

**Onyx** - это универсальный набор инструментов командной строки, объединяющий множество полезных утилит для разработчиков, системных администраторов и продвинутых пользователей. От анализа файлов и мониторинга системы до управления Git репозиториями и сетевой диагностики - все в одном инструменте!

## ✨ Основные возможности

- 📁 **Анализ файлов**: Подсчет строк кода, построение деревьев каталогов
- 🔍 **Умный поиск**: Поиск файлов по содержимому, размеру, дате, имени
- 💾 **Резервное копирование**: Создание архивов с инкрементальными бэкапами
- 📊 **Git аналитика**: Подробная статистика репозиториев и команды разработки
- 🌐 **Сетевые утилиты**: Ping, traceroute, сканирование портов, DNS
- ⬇️ **Менеджер загрузок**: Многопоточная загрузка с прогресс-барами
- 📈 **Мониторинг системы**: Отслеживание CPU, RAM, дисков, процессов

## Установка

### Из исходного кода

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd Onyx
```

2. Установите с помощью Poetry:
```bash
poetry install
```

3. Для глобальной установки:
```bash
poetry build
pip install dist/onyx-*.whl
```

### Используя pip (из локальной папки)
```bash
pip install .
```

### Настройка PATH для Windows

После установки может потребоваться добавить путь к скриптам Python в переменную PATH:

1. Откройте "Параметры системы" → "Дополнительные параметры системы"
2. Нажмите "Переменные среды"
3. В "Переменные пользователя" найдите `PATH` и нажмите "Изменить"
4. Добавьте путь: `C:\Users\{ваше_имя}\AppData\Roaming\Python\Python312\Scripts`
5. Перезапустите терминал

Альтернативно, выполните команду через полный путь:
```cmd
C:\Users\{ваше_имя}\AppData\Roaming\Python\Python312\Scripts\onyx.exe
```

## Использование

После установки команда `onyx` будет доступна глобально в вашей системе.

### Команды

#### `onyx tree` - Отображение структуры папок

Рисует цветное дерево файловой структуры указанной папки с дополнительной информацией.

```bash
# Показать структуру текущей папки
onyx tree

# Показать структуру конкретной папки
onyx tree /path/to/directory

# Ограничить глубину отображения
onyx tree --max-depth 3

# Показать скрытые файлы
onyx tree --show-hidden

# Показать только папки (без файлов)
onyx tree --no-files

# Показать размеры файлов и папок
onyx tree --show-size

# Показать время последней модификации
onyx tree --show-time

# Игнорировать определенные файлы и папки
onyx tree --ignore "*.pyc" --ignore "__pycache__"

# Сохранить результат в файл
onyx tree --save ./output

# Комбинация опций
onyx tree --show-size --show-time --max-depth 2 --ignore "*.pyc"
```

**Опции:**
- `--max-depth, -d`: Максимальная глубина отображения
- `--show-hidden, -a`: Показать скрытые файлы и папки
- `--no-files`: Показать только папки, скрыть файлы
- `--show-size, -s`: Показать размеры файлов и папок
- `--show-time, -t`: Показать время последней модификации
- `--ignore, -i`: Паттерны для игнорирования (можно указать несколько)
- `--save`: Сохранить дерево в файл

#### `onyx count` - Продвинутый подсчет строк в файлах

Считает количество строк в файлах с расширенной аналитикой и поддержкой разных алгоритмов обхода.

```bash
# Подсчитать строки во всех файлах
onyx count

# Подсчитать строки в определенной папке
onyx count /path/to/directory

# Подсчитать только Python файлы
onyx count --extensions .py

# Подсчитать файлы нескольких типов
onyx count --extensions .py --extensions .js --extensions .ts

# Показать количество строк для каждого файла с размерами
onyx count --show-files

# Исключить пустые файлы
onyx count --exclude-empty

# Исключить определенные папки
onyx count --exclude-dirs __pycache__ --exclude-dirs .git

# Игнорировать пустые строки и комментарии
onyx count --ignore-empty-lines --ignore-comments

# Использовать разные алгоритмы обхода
onyx count --algorithm dfs  # Depth-First Search
onyx count --algorithm bfs  # Breadth-First Search  
onyx count --algorithm both # Сравнить оба алгоритма

# Показать ТОП-5 самых больших файлов
onyx count --top 5 --show-files

# Включить скрытые файлы
onyx count --show-hidden

# Полный анализ Python проекта
onyx count --extensions .py --ignore-empty-lines --ignore-comments --show-files --top 10 --exclude-dirs __pycache__ --exclude-dirs .git
```

**Опции:**
- `--extensions, -e`: Расширения файлов для включения (можно указать несколько)
- `--recursive, -r`: Рекурсивный поиск (по умолчанию включен)
- `--exclude-empty, -x`: Исключить пустые файлы
- `--show-files, -f`: Показать количество строк для каждого файла с размерами
- `--exclude-dirs`: Папки для исключения (можно указать несколько)
- `--ignore-empty-lines`: Игнорировать пустые строки при подсчете
- `--ignore-comments`: Игнорировать строки-комментарии (начинающиеся с #)
- `--algorithm`: Алгоритм обхода файлов (dfs/bfs/both)
- `--top`: Количество файлов в ТОП-списке (по умолчанию 10)
- `--show-hidden`: Включить скрытые файлы в анализ

## 🆕 Расширенные команды

### `onyx find` - Интеллектуальный поиск файлов

Мощный инструмент поиска файлов по различным критериям.

```bash
# Поиск файлов по имени
onyx find files --name "*.py"

# Поиск по размеру
onyx find files --size ">10MB"

# Поиск по дате модификации
onyx find files --modified "<7d"

# Поиск в содержимом файлов
onyx find content "def main" --extensions .py

# Комбинированный поиск
onyx find files --name "*.log" --size ">1MB" --modified "<1d" --output json
```

**Подкоманды:**
- `files`: Поиск файлов и папок
- `content`: Поиск в содержимом файлов

### `onyx backup` - Система резервного копирования

Создание и управление резервными копиями с поддержкой инкрементальных бэкапов.

```bash
# Создать архив
onyx backup create /path/to/source backup.zip

# Инкрементальный бэкап
onyx backup incremental /path/to/source /backup/dir

# Восстановление
onyx backup restore backup.zip /restore/path

# Просмотр бэкапов
onyx backup list /backup/dir
```

**Подкоманды:**
- `create`: Создать новый бэкап
- `incremental`: Инкрементальный бэкап
- `restore`: Восстановить из бэкапа
- `list`: Показать список бэкапов

### `onyx git` - Git аналитика

Анализ Git репозиториев и статистика разработки.

```bash
# Анализ коммитов
onyx git commits --since "1 month ago" --author "john"

# Статистика авторов
onyx git authors --top 5

# Анализ файлов
onyx git files --file-pattern "*.py"

# Поиск больших файлов
onyx git large-files --threshold 10MB

# Активность по времени
onyx git activity --period week --last 12
```

**Подкоманды:**
- `commits`: Анализ коммитов
- `authors`: Статистика авторов
- `files`: Анализ изменений файлов
- `large-files`: Поиск больших файлов
- `activity`: Анализ активности

### `onyx net` - Сетевые утилиты

Диагностика сети и тестирование подключений.

```bash
# Ping хоста
onyx net ping google.com --count 10

# Traceroute
onyx net traceroute google.com

# Проверка порта
onyx net port google.com 80

# Сканирование портов
onyx net scan 192.168.1.1 --start-port 1 --end-port 1000

# DNS lookup
onyx net dns example.com --record-type A

# WHOIS информация
onyx net whois google.com
```

**Подкоманды:**
- `ping`: Проверка доступности хоста
- `traceroute`: Трассировка маршрута
- `port`: Проверка конкретного порта
- `scan`: Сканирование диапазона портов
- `dns`: DNS запросы
- `whois`: WHOIS информация

### `onyx download` - Менеджер загрузок

Загрузка файлов с прогресс-барами и продвинутыми возможностями.

```bash
# Загрузка одного файла
onyx download single https://example.com/file.zip

# Пакетная загрузка
onyx download batch urls.txt --workers 4

# Ускоренная загрузка
onyx download accelerated https://example.com/large-file.zip --parts 8

# С проверкой контрольной суммы
onyx download single https://example.com/file.zip --checksum abc123...
```

**Подкоманды:**
- `single`: Загрузка одного файла
- `batch`: Пакетная загрузка из списка
- `accelerated`: Многопоточная загрузка

### `onyx monitor` - Системный мониторинг

Мониторинг системных ресурсов в реальном времени.

```bash
# Общий мониторинг системы
onyx monitor system --interval 1

# Мониторинг процессов
onyx monitor processes --top 10 --sort-by cpu

# Сетевая активность
onyx monitor network --interface eth0

# Мониторинг дисков
onyx monitor disk --path /home

# Бенчмарк производительности
onyx monitor performance --duration 60
```

**Подкоманды:**
- `system`: Общий мониторинг системы
- `processes`: Мониторинг процессов
- `network`: Сетевая активность
- `disk`: Использование дисков
- `performance`: Бенчмарк производительности

### Справка

```bash
# Общая справка
onyx --help

# Справка по основным командам
onyx tree --help
onyx count --help

# Справка по расширенным командам
onyx find --help
onyx backup --help
onyx git --help
onyx net --help
onyx download --help
onyx monitor --help

# Справка по подкомандам
onyx find files --help
onyx backup create --help
onyx git commits --help
onyx net ping --help
onyx download single --help
onyx monitor system --help
```

## Примеры

### Анализ Python проекта
```bash
# Показать структуру проекта с размерами и общей статистикой
onyx tree --max-depth 4 --show-size --ignore "*.pyc" --ignore "__pycache__"

# Полный анализ кода с игнорированием комментариев и пустых строк
onyx count --extensions .py --ignore-empty-lines --ignore-comments --show-files --top 10 --exclude-dirs __pycache__ --exclude-dirs .pytest_cache

# Сравнение алгоритмов обхода для больших проектов
onyx count --extensions .py --algorithm both --exclude-dirs __pycache__
```

### Анализ веб-проекта
```bash
# Подсчитать строки в JS/TS файлах
onyx count --extensions .js --extensions .ts --extensions .jsx --extensions .tsx --exclude-dirs node_modules

# Показать структуру с ограничением глубины
onyx tree --max-depth 3

# Найти большие файлы
onyx find files --size ">1MB" --extensions .js --extensions .css

# Создать бэкап проекта (исключив node_modules)
onyx backup create . project_backup.zip --exclude node_modules --exclude .git
```

### Системное администрирование
```bash
# Мониторинг системы с алертами
onyx monitor system --alert-cpu 80 --alert-memory 85

# Проверка сетевого подключения
onyx net ping 8.8.8.8 --continuous

# Сканирование локальной сети
onyx net scan 192.168.1.0/24 --common-ports

# Поиск файлов логов за последний день
onyx find files --name "*.log" --modified "<1d" --size ">10MB"
```

### Git разработка
```bash
# Анализ активности в репозитории
onyx git activity --period month --last 6

# Найти самые изменяемые файлы
onyx git files --top 15 --since "3 months ago"

# Статистика команды
onyx git authors --min-commits 5

# Очистка больших файлов из истории
onyx git large-files --threshold 50MB
```

### Управление загрузками
```bash
# Загрузка с проверкой размера
onyx download single https://example.com/file.iso --max-size 4GB

# Пакетная загрузка с продолжением при ошибках
onyx download batch urls.txt --continue-on-error --resume

# Ускоренная загрузка больших файлов
onyx download accelerated https://example.com/bigfile.zip --parts 16
```

## Развитие

Проект создан для добавления новых полезных утилит. Каждая утилита реализуется как отдельная команда в папке `onyx/commands/`.

## Автор

Noloquideus (daniilmanukian@gmail.com)
