# Tech Stack

## Backend
- **Language**: Python 3.x
- **Framework**: FastAPI (Async API development)
- **Database/ORM**: SQLAlchemy with `aiosqlite` for asynchronous SQLite interactions.
- **Optimization**: PuLP (Linear Programming for battery scheduling).
- **Machine Learning**: LightGBM (Forecasting load and PV production), Scikit-learn.
- **Task Scheduling/Real-time**: `python-socketio` for live dashboard updates.

## Frontend
- **Framework**: React 19 (TypeScript)
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Visualization**: Chart.js (Data-heavy energy charts), Framer Motion (Animations).
- **State Management**: Standard React hooks and Socket.io-client.

## Infrastructure & Integration
- **Containerization**: Docker & Docker Compose.
- **Home Automation**: Native Home Assistant Add-on integration.
- **Forecasting Sources**: Open-Meteo Solar Forecast API, Nordpool Price API.
