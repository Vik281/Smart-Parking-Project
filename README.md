# ParkShare – Smart Parking

A parking-booking web app built with FastAPI, SQLAlchemy and SQLite, with a plain HTML/CSS/JavaScript frontend.
Users can browse parking locations, see live spot availability, book a specific spot and cancel a booking.

## Features

- Live spot map for each location showing free and booked spots
- Book individual spots for a time slot and cancel bookings; data is saved in SQLite and survives restarts
- Overlap detection plus a per-spot lock, so two simultaneous requests can never double-book a slot
- Live stats (free/booked spots, average price) and a recent-activity feed
- Search and sort locations by price, availability or rating

## Project structure

```
app/
  main.py        app setup: startup, routes, static files, error handling
  config.py      settings (database URL from the DATABASE_URL env variable)
  api/           HTTP routes – thin, they only call services
  services/      business rules (booking, cancelling, stats)
  models/        database tables (SQLAlchemy ORM)
  schemas/       request/response validation (Pydantic)
  database/      engine, per-request sessions, demo seed data
frontend/        HTML, CSS and JavaScript served by FastAPI
```

## Run locally

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\uvicorn.exe app.main:app --reload
```

Open http://127.0.0.1:8000. On first run the app creates `parkshare.db` and adds four demo locations.
Delete that file to reset the data.

Interactive API docs are available at http://127.0.0.1:8000/docs.

## API

| Method | Route | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/locations?start=&end=` | All locations with spot availability for a time window (default: next hour) |
| GET | `/api/v1/locations/{id}/spots/{spot_number}/bookings` | Upcoming bookings for one spot |
| GET | `/api/v1/stats` | Totals for locations, spots and average price; occupancy is "right now" |
| GET | `/api/v1/activity` | Recent bookings and cancellations |
| POST | `/api/v1/locations/{id}/book` | Book a spot for `start_time`–`end_time` (`409` if it overlaps another booking) |
| DELETE | `/api/v1/bookings/{booking_id}` | Cancel a booking |

Times must include a timezone (e.g. `2026-10-16T09:00:00+05:30` or `...Z`); they are stored in UTC.
Bookings last 30 minutes to 24 hours and can be made up to 30 days ahead.
