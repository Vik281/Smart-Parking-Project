# ParkShare – Smart Parking Demo

A small FastAPI parking-booking demo built with Python, HTML, CSS, JavaScript, and in-memory data.

## Run the demo

From the project folder, run:

```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser.

## What to show the panel

1. Open the ParkShare home page and enter a location or area.
2. Click **Show parking** to display the demo parking spaces.
3. Point out the available spots and hourly price on each parking card.
4. Click **BOOK** for a location.
5. Enter a name and vehicle number, then confirm the booking.
6. Show the confirmation message and the available-spot count decreasing by one.

## API routes

- `GET /api/v1/health` – confirms the backend is running.
- `GET /api/v1/locations` – returns the hardcoded parking locations.
- `POST /api/v1/locations/{location_id}/book` – books one in-memory parking spot.

The parking data resets to its original values whenever the server restarts. This is intentional for the basic demo.
