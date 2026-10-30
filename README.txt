Research Data Management System
═══════════════════════════════════════════════════════════

START
-----
   cd /sdcard/DMS
   python3 app.py

   or:

   bash /sdcard/DMS/start.sh

Then open:
   http://localhost:5000

FILES
-----
   app.py                 — main Flask application
   database.py            — SQLite schema + helpers
   *_routes.py            — route modules
   templates/             — HTML pages
   static/                — CSS, JS, images
   data/research.db       — your database
   data/uploads/          — participant files
   branding/              — uploaded brand assets
   backups/               — app-level backups

REQUIREMENTS
------------
   pip install -r requirements.txt
