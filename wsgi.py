"""Render-compatible entry point."""
import os
from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.create_all()
    # Auto-seed on first deploy (check if any user exists)
    try:
        from app.models import User
        if User.query.count() == 0:
            from scripts.seed_demo import seed_database
            seed_database()
    except Exception as e:
        print(f"Seed skipped: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
