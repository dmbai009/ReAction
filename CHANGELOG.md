# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), версіонування — [SemVer](https://semver.org/lang/uk/).

## [Unreleased]

### Додано
- Документація: `README.md`, `docs/ARCHITECTURE.md`, `docs/RECOMMENDER.md`, `SECURITY.md`, `CHANGELOG.md`.
- Ліцензія MIT.
- `.gitignore` (віртуальне середовище, кеш Python, база даних `instance/`).

### Змінено
- `requirements.txt` перекодовано з UTF-16 в UTF-8.

## [1.0.0] — 2025-11-29

Дипломна версія.

### Додано
- Реєстрація, вхід і вихід користувачів (Flask-Login, bcrypt).
- CRUD статей з Markdown-редактором SimpleMDE.
- Теги з автодоповненням (Tagify) і сторінка статей за тегом.
- Коментарі з редагуванням і видаленням, лайки.
- Повнотекстовий пошук по заголовках, змісту, авторах і тегах.
- ML-рекомендації на основі TF-IDF: «Схожі статті» та персональна стрічка «Рекомендовані».
- Профілі користувачів з аватарами Gravatar.
- Адаптивний дизайн (Bootstrap 5) і темна тема.
