import sqlite3, os
for dbfile in ['outreach.db', 'scheduler.db', 'afspraak.db']:
    if os.path.exists(dbfile):
        conn = sqlite3.connect(dbfile)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        print(f"{dbfile}: {tables}")
        for t in tables:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            print(f"  {t}: {c.fetchone()[0]} rows")
        conn.close()
    else:
        print(f"{dbfile}: NIET GEVONDEN")
