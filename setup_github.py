#!/usr/bin/env python3
"""
Скрипт для настройки GitHub репозитория и создания релизов с исполняемыми файлами
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, check=True):
    """Выполнить команду и вернуть результат"""
    print(f"🔄 Выполняю: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    if check and result.returncode != 0:
        print(f"❌ Ошибка выполнения команды: {command}")
        sys.exit(1)
    
    return result


def main():
    print("🚀 Настройка GitHub репозитория для Onyx")
    print("=" * 50)
    
    # Проверяем, что мы в правильной директории
    if not Path("pyproject.toml").exists():
        print("❌ Файл pyproject.toml не найден. Убедитесь, что вы в корневой папке проекта.")
        sys.exit(1)
    
    # Проверяем статус Git
    result = run_command("git status", check=False)
    if result.returncode != 0:
        print("❌ Git репозиторий не инициализирован")
        sys.exit(1)
    
    print("✅ Git репозиторий найден")
    
    # Проверяем, есть ли удаленный репозиторий
    result = run_command("git remote -v", check=False)
    if "origin" not in result.stdout:
        print("\n📝 Настройка удаленного репозитория:")
        username = input("Введите ваше имя пользователя GitHub: ")
        repo_name = input("Введите название репозитория (по умолчанию 'onyx'): ").strip() or "onyx"
        
        remote_url = f"https://github.com/{username}/{repo_name}.git"
        run_command(f'git remote add origin "{remote_url}"')
    
    # Отправляем код на GitHub
    print("\n📤 Отправка кода на GitHub...")
    run_command("git push -u origin master")
    
    # Отправляем теги
    print("\n🏷️ Отправка тегов...")
    run_command("git push origin --tags")
    
    print("\n✅ Код успешно отправлен на GitHub!")
    print("\n📋 Что произойдет дальше:")
    print("1. GitHub Actions автоматически соберет исполняемые файлы для Windows, Linux и macOS")
    print("2. Создастся релиз с готовыми к скачиванию файлами")
    print("3. Пользователи смогут скачать onyx-windows.exe, onyx-linux, onyx-macos")
    print("\n📖 Подробная инструкция в файле DEPLOYMENT.md")
    print("\n🔗 Ссылка на релизы: https://github.com/{username}/{repo_name}/releases")


if __name__ == "__main__":
    main()
