# FastApiBalancesService

FastApiBalancesService is a simple service built with FastAPI to manage and display balances.

## Features
- **FastAPI** framework for building APIs
- **PostgreSQL** for database management
- **Alembic** for database migrations
- **Granian** server for handling ASGI applications

## Setup and Usage

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Apply database migrations:
   ```bash
   alembic upgrade head
   ```

3. Start the application:
   ```bash
   python -m src.app.main
   ```

## Configuration
- Configure the application settings in `app/settings.py` to match your environment.

---

Feel free to expand based on the needs of your project.