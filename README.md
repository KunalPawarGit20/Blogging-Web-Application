# Flask Blog Capstone

A Flask blog with registration, login, posts, comments, CKEditor, Bootstrap, CSRF protection, and email contact support.

## Local setup

1. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set at least `SECRET_KEY`.
4. Run the app:
   ```powershell
   python main.py
   ```

Open `http://127.0.0.1:5003`.

## Environment variables

- `SECRET_KEY`: required Flask session and CSRF key.
- `ADMIN_EMAILS`: comma-separated emails allowed to edit or delete posts.
- `DB_URI`: optional SQLAlchemy database URL; defaults to local SQLite.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `CONTACT_EMAIL`: optional contact email settings.

Never commit `.env`, virtual environments, or `instance/Blogs.db`.
