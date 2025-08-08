# Руководство по развертыванию Onyx

## Подготовка к публикации на GitHub

### 1. Создание репозитория на GitHub

1. Перейдите на [GitHub](https://github.com) и создайте новый репозиторий
2. Назовите его `onyx` или `onyx-cli`
3. НЕ инициализируйте с README, .gitignore или лицензией (у нас уже есть файлы)

### 2. Подключение локального репозитория к GitHub

```bash
# Добавьте удаленный репозиторий (замените YOUR_USERNAME на ваше имя пользователя)
git remote add origin https://github.com/YOUR_USERNAME/onyx.git

# Отправьте код и тег
git push -u origin master
git push origin v0.1.0
```

### 3. Автоматическое создание релизов

После отправки тега GitHub Actions автоматически:
1. Соберет исполняемые файлы для Windows, Linux и macOS
2. Создаст релиз с готовыми к скачиванию файлами
3. Добавит подробное описание релиза

### 4. Создание нового релиза

Для создания нового релиза:

1. Обновите версию в `pyproject.toml`:
   ```toml
   version = "0.1.1"
   ```

2. Создайте новый коммит и тег:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.1.1"
   git tag -a v0.1.1 -m "Release version 0.1.1"
   git push origin master
   git push origin v0.1.1
   ```

3. GitHub Actions автоматически создаст релиз с исполняемыми файлами

### 5. Структура релиза

Каждый релиз будет содержать:
- `onyx-windows.exe` - для Windows
- `onyx-linux` - для Linux
- `onyx-macos` - для macOS

### 6. Установка для пользователей

#### Windows
1. Скачайте `onyx-windows.exe`
2. Переместите в папку из PATH (например, `C:\Windows\System32\`)
3. Или используйте полный путь: `C:\path\to\onyx-windows.exe --help`

#### Linux/macOS
1. Скачайте соответствующий файл
2. Сделайте исполняемым: `chmod +x onyx-linux`
3. Переместите в папку из PATH: `sudo mv onyx-linux /usr/local/bin/onyx`
4. Или используйте полный путь: `./onyx-linux --help`

### 7. Проверка работы

После установки проверьте:
```bash
# Windows
onyx-windows.exe --help

# Linux/macOS
onyx --help
```

## Локальная сборка (для разработки)

### Сборка на Windows
```bash
# Установите PyInstaller
pip install pyinstaller

# Соберите исполняемый файл
pyinstaller --onefile --name onyx onyx/main.py

# Исполняемый файл будет в dist/onyx.exe
```

### Сборка на Linux/macOS
```bash
# Установите PyInstaller
pip install pyinstaller

# Соберите исполняемый файл
pyinstaller --onefile --name onyx onyx/main.py

# Исполняемый файл будет в dist/onyx
```

## Troubleshooting

### Проблемы с GitHub Actions
- Проверьте логи в Actions → Workflows
- Убедитесь, что тег создан правильно: `v0.1.0`
- Проверьте, что все файлы добавлены в коммит

### Проблемы с локальной сборкой
- Убедитесь, что все зависимости установлены
- Проверьте, что Python 3.12+ используется
- Для Windows может потребоваться Visual Studio Build Tools

### Проблемы с установкой
- Убедитесь, что файл скачан полностью
- Проверьте права доступа (для Linux/macOS)
- Попробуйте запустить с полным путем к файлу
