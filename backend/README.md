# Google OAuth + Cloud SQL Orders API (deployment scaffold)

This API is designed for the GitHub Pages demo front end. It verifies Google Identity Services ID tokens, stores members/orders/inventory in PostgreSQL, and returns signed pickup QR URLs. It does not include a real payment gateway; online payments are deliberately rejected until a provider and webhook are configured.

## Required Google Cloud setup

1. Create a GCP project and enable billing, Cloud Run, Cloud SQL Admin, and Secret Manager APIs.
2. Create a Cloud SQL PostgreSQL instance/database and an application DB user.
3. Create a Google OAuth **Web application** client. Add `https://qian03777.github.io` to authorized JavaScript origins. Put the client ID in `site-config.js` and `GOOGLE_CLIENT_ID` in the API service.
4. Give the Cloud Run service account the Cloud SQL Client role; store `DB_PASSWORD` and `QR_SIGNING_SECRET` in Secret Manager.
5. Build/deploy from the repository root using `backend/Dockerfile`, then configure the environment values in `.env.example`.
6. Initialize the tables and demo catalog by running `python backend/seed_data.py` with the same Cloud SQL connection settings.
7. Set `API_BASE_URL` in the public site's `site-config.js` to the deployed Cloud Run URL.

Cloud SQL and Cloud Run can incur ongoing charges. No Google Cloud resources are created by this scaffold. Check the Google Cloud pricing calculator and approve a budget before deployment.

## Local API development

Install `backend/requirements.txt`, set `DATABASE_URL` to a PostgreSQL connection (for example `postgresql+pg8000://user:password@localhost:5432/xiaobei`) and the required OAuth/QR environment variables, then run:

```powershell
uvicorn backend.main:app --reload --port 8080
```

The currently bundled local Ollama server is separate and remains bound to localhost. Do not expose Ollama port 11434 or this development API directly to the internet.
