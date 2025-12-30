# Image API Service

A FastAPI service to list images stored in the database.

## Endpoints

- `GET /images`: Returns a list of all images with their IDs and creation timestamps.

## Running the Service

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables for database connection (optional, defaults provided):
   - `API_DB_HOST` (default: localhost)
   - `API_DB_PORT` (default: 5432)
   - `API_DB_NAME` (default: imagomortis)
   - `API_DB_USER` (default: postgres)
   - `API_DB_PASSWORD` (default: postgres)

3. Run the server:
   ```bash
   uvicorn api:app --reload
   ```

The service will be available at http://localhost:8000

## Troubleshooting

- Ensure PostgreSQL is running and accessible.
- Check database credentials.
- Verify the `images` table exists (created by the pusher service).