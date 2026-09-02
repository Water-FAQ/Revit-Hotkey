# Revit Hotkey

Revit Hotkey — бесплатная Windows-программа для просмотра и изменения файла
`KeyboardShortcuts.xml` Autodesk Revit.

[Страница проекта](https://water-faq.github.io/Revit-Hotkey/) ·
[Скачать последнюю версию](https://github.com/Water-FAQ/Revit-Hotkey/releases/latest/download/Revit-Hotkey.zip) ·
[Все выпуски](https://github.com/Water-FAQ/Revit-Hotkey/releases)

## Возможности

- выбор XML-файла вручную или загрузка из найденной версии Revit;
- поиск команд и фильтрация по разделам, назначенным и неназначенным сочетаниям;
- отображение полных названий команд, сочетаний и путей Revit;
- ввод по физическим клавишам с автоматическим преобразованием EN ↔ RU;
- назначение сочетания в одной или обеих раскладках;
- обнаружение конфликтов и безопасная замена занятого сочетания;
- защита системных сочетаний Revit от изменения;
- резервная копия исходного XML при перезаписи файла Revit;
- проверка итогового XML перед заменой;
- полностью русский интерфейс.

## Начало работы

1. [Скачайте последнюю версию](https://github.com/Water-FAQ/Revit-Hotkey/releases/latest/download/Revit-Hotkey.zip).
2. Распакуйте архив в удобную папку.
3. Запустите `Revit Hotkey.exe` — установка не требуется.
4. Выберите `KeyboardShortcuts.xml` или нажмите «Загрузить из Revit».

Файл горячих клавиш обычно находится здесь:

```text
%APPDATA%\Autodesk\Revit\Autodesk Revit 20XX\KeyboardShortcuts.xml
```

Перед сохранением в файл используемой версии рекомендуется закрыть Revit.
После замены XML перезапустите Revit, чтобы изменения вступили в силу.

## Запуск и сборка из исходников

Требуются Windows и Python 3.10.

- `Запустить.bat` запускает приложение из подготовленного виртуального окружения.
- `Собрать_EXE.bat` создаёт окружение, устанавливает зависимости, выполняет тесты
  и собирает `dist\Revit Hotkey.exe`.

Проверка тестов отдельно:

```powershell
python -m unittest discover -s tests -v
```

## Безопасность данных

Программа работает локально и не отправляет XML-файлы или сочетания клавиш в
интернет. При перезаписи файла Revit рядом сохраняется резервная копия вида
`KeyboardShortcuts - YYYY-MM-DD_HHMMSS.xml`.

## Обратная связь

- [Сообщить об ошибке](https://github.com/Water-FAQ/Revit-Hotkey/issues/new?template=bug_report.yml)
- [Предложить улучшение](https://github.com/Water-FAQ/Revit-Hotkey/issues/new?template=feature_request.yml)

Разработчик: WaterFAQ.
