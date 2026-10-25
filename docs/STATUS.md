# Статус проекта
Неделя 1: настройка окружения

Готово:
- load_pdf: чтение PDF по страницам (PR #1 влит)
- Приём PDF в боте (PR #7 проверен и влит)
- Заглушка search.py по контракту (add_chunks, search), в main
- config.py читает .env, все 5 переменных (PR #14 влит)
- scripts/test_llm.py: модель отвечает через OpenRouter
- .DS_Store добавлен в .gitignore
- docs/AI_PROMPT.md обновлён

В работе:
- PR #19: .env.example без секретов (ждёт ревью)
- llm.py по контракту: типы, проверка mode, заглушки ask и embed (PR открывается)
- Повтор запроса при ошибке 429 (паузы 2, 5, 10 сек)
- Черновик docs/SETUP.md (запуск с нуля, в том числе для Arch/CachyOS)
- Проверка load_pdf на остальных лекциях: проверена одна (116 страниц), нужны ещё 4 тестовых PDF
- Учебные скрипты try_embeddings.py и try_chroma.py, добавить sentence-transformers в requirements.txt
- Черновик README.md (PR #__)
- Ревью открытых pull request'ов

Договорённости:
- В main только через pull request
- Ключи только в .env, в репозиторий не попадают
- Нужен Python 3.11+ (проверьте: python --version)
