# Re:Action — a smart blogging platform

**English** | [Українська](README.uk.md)

**Re:Action** is a full-featured blogging web application built as a diploma project. Its key feature is a built-in machine learning module that gives readers personalized article recommendations.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7-F7931E?logo=scikitlearn&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

> The user interface is in Ukrainian.

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Project structure](#project-structure)
- [Configuration](#configuration)
- [Tests](#tests)
- [How recommendations work](#how-recommendations-work)
- [Documentation](#documentation)
- [Known limitations](#known-limitations)
- [License](#license)

## Features

- **Authentication**: sign-up with validation, log in and log out. Passwords are hashed with bcrypt.
- **Articles (CRUD)**: create, read, edit and delete your own articles.
- **Markdown editor**: SimpleMDE with a formatting toolbar and preview.
- **Social features**: comments (editable and deletable) and likes.
- **Tags**: categorize articles with autocomplete (Tagify), and browse articles by tag.
- **ML-based personalization**:
  - a **Recommended** feed with articles picked from the user's view and like history;
  - a **Similar articles** block on every article page.
- **Search** across titles, content, author names and tags.
- **Security**: CSRF protection on every form, HTML sanitization after Markdown rendering, secrets in environment variables.
- **User profiles** with Gravatar avatars.
- **Responsive design** on Bootstrap 5 and a **dark theme** that remembers your choice.

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python, Flask 3 (blueprints, application factory) |
| Database | SQLite via Flask-SQLAlchemy / SQLAlchemy 2 |
| Auth and security | Flask-Login, Flask-Bcrypt, Flask-WTF (CSRF), nh3 (HTML sanitization) |
| Machine learning | scikit-learn (TF-IDF, cosine similarity), NumPy |
| Frontend | Jinja2, HTML5, CSS3, JavaScript, Bootstrap 5 |
| JS libraries | SimpleMDE, Tagify |
| Tests | pytest |

## Quick start

**Requires:** Python 3.9+.

```bash
# 1. Clone the repository
git clone https://github.com/dmbai009/ReAction.git
cd ReAction

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. (optional) Configure the environment, see "Configuration"
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux

# 5. Run
python app.py
```

The app is served at **http://127.0.0.1:5000**. Stop the server with `Ctrl + C`.

The database `instance/blog.db` is created automatically on first run.

> **Changing the data models.** The project has no migrations: after changing `blog/models.py`, delete `instance/blog.db` and restart the app. **This deletes all data** (users, articles, comments).

## Project structure

```
ReAction/
├── app.py               # entry point
├── requirements.txt     # app dependencies
├── requirements-dev.txt # + test dependencies
├── .env.example         # configuration example
├── blog/
│   ├── __init__.py      # app factory, configuration, markdown / excerpt filters
│   ├── models.py        # SQLAlchemy models
│   ├── recommender.py   # ML recommendation module
│   ├── auth.py          # sign-up / log in / log out
│   ├── main.py          # home page (feeds) and search
│   ├── posts.py         # articles, tags, comments, likes
│   ├── users.py         # profiles
│   └── templates/       # Jinja2 templates
├── tests/               # pytest tests
├── docs/                # technical documentation
└── instance/            # SQLite database (created automatically, not in git)
```

## Configuration

Settings are read from environment variables. A `.env` file in the project root is loaded automatically (template: [`.env.example`](.env.example)).

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | random on every start | signs sessions and CSRF tokens. Without it, all users are logged out when the app restarts |
| `DATABASE_URL` | `sqlite:///blog.db` | SQLAlchemy database URL. A relative SQLite path is resolved against the `instance/` folder |
| `FLASK_DEBUG` | `0` | `1` enables the debugger and auto-reload. Never enable it on a public server |

Generate a key: `python -c "import secrets; print(secrets.token_hex(32))"`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests use an in-memory SQLite database and never touch `instance/blog.db`. They cover authentication and validation, article and comment CRUD, access control, likes, search, recommendations (including an empty database and texts with no words), CSRF, Markdown sanitization and unique indexes.

## How recommendations work

Recommendations are **content-based**: each article (title + text) is turned into a TF-IDF vector, and closeness between articles is measured with cosine similarity.

- **Similar articles**: the 3 articles closest to the current one.
- **Recommended feed**: the user profile is a weighted average of the vectors of viewed (weight 1) and liked (+2) articles. The feed shows the 10 articles closest to it that the user hasn't seen yet.

Articles with no words in common are not treated as similar. An empty database and texts with no recognizable words are handled without errors.

More details in [docs/RECOMMENDER.md](docs/RECOMMENDER.md).

## Documentation

The detailed docs are in Ukrainian.

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | architecture, routes, data model |
| [docs/RECOMMENDER.md](docs/RECOMMENDER.md) | the recommendation algorithm and its limitations |
| [SECURITY.md](SECURITY.md) | security measures, open issues, how to report vulnerabilities |
| [CHANGELOG.md](CHANGELOG.md) | change history |

## Known limitations

- No database migrations (Alembic). New tables and indexes are created automatically, but new **columns** in existing tables are not.
- No rate limiting on login attempts, see [SECURITY.md](SECURITY.md).
- Recommendations are recomputed on every request; a large number of articles would need caching.
- SQLite search is case-insensitive for Latin letters only.
- Frontend libraries load from a CDN, so the editor and tags don't work offline.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
