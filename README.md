# Todo Manager (Менеджер задач)

Менеджер задач на Python с GUI (tkinter) и SQLite.  

---

## Do:
- CRUD.
- Поля задачи: название, описание, дата срока (`YYYY-MM-DD`), приоритет (1–5), статус (`open`, `in_progress`, `done`).
- Поиск по названию/описанию.
- Сортировка по полям (ID, название, дата создания, срок, приоритет, статус).
- Экспорт всех задач в CSV: `tasks_export.csv`.
- Данные хранятся в локальной базе `todo.db` (SQLite).

---

## Req
- Python 3.13
- tkinter
- `sqlite3`, `csv`, `datetime`, `tkinter`
