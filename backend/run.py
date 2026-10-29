"""Entry point for running the Micro E-Commerce application."""

import os
from app import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # Default to 5001 to avoid conflict with macOS AirPlay Receiver on port 5000
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_ENV") != "production"
    print(f"\n🚀 Micro E-Commerce Engine running at: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)

