# Backend Setup Instructions

## Prerequisites

1. You've downloaded your Firebase service account JSON file from:
   - Firebase Console → Project Settings → Service Accounts → Generate new private key
2. You have your PostgreSQL database URL from Azure

## Step 1: Create .env File

Create a `.env` file in `/services/auth-service/` directory:

```bash
cd services/auth-service
touch .env
```

## Step 2: Configure Environment Variables

### For Local Development

Add the following to your `.env` file:

```env
# Your Azure PostgreSQL connection string
DATABASE_URL=postgresql://bookinatoradmin:X783y54at3Sj@bookinator.postgres.database.azure.com:5432/bookinator?sslmode=require

# Path to your downloaded Firebase service account JSON file
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
```

**Steps:**
1. Save your downloaded service account JSON file as `firebase-service-account.json` in the `services/auth-service/` directory
2. Update the `FIREBASE_SERVICE_ACCOUNT_PATH` to point to this file
3. Verify the `DATABASE_URL` matches your Azure PostgreSQL credentials

### For Azure/Production Deployment

For production, use the JSON string approach instead:

```env
DATABASE_URL=postgresql://bookinatoradmin:X783y54at3Sj@bookinator.postgres.database.azure.com:5432/bookinator?sslmode=require

FIREBASE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"bookinator3000","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...@bookinator3000.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}'
```

**To get the JSON string:**
1. Open your service account JSON file
2. Copy the entire contents
3. Minify it (remove newlines) or keep it as one line
4. Set it as the `FIREBASE_SERVICE_ACCOUNT_KEY` environment variable in Azure

## Step 3: Install Dependencies

```bash
cd services/auth-service
pip install -r requirements.txt
```

## Step 4: Test the Service Locally

```bash
uvicorn main:app --port 8001 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

## Step 5: Verify It Works

Test the health endpoint:
```bash
curl http://localhost:8001/health
```

Expected response:
```json
{"status": "healthy"}
```

## Security Checklist

- [ ] `.env` file is listed in `.gitignore`
- [ ] Firebase service account JSON file is NOT committed to Git
- [ ] Service account key has appropriate IAM permissions (Firebase Authentication Admin)
- [ ] Database credentials are secure and not exposed

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to service account JSON (local dev) | `./firebase-service-account.json` |
| `FIREBASE_SERVICE_ACCOUNT_KEY` | Service account JSON as string (production) | `'{"type":"service_account",...}'` |

## Troubleshooting

### "Firebase credentials not found"
- Check that either `FIREBASE_SERVICE_ACCOUNT_PATH` or `FIREBASE_SERVICE_ACCOUNT_KEY` is set in `.env`
- Verify the path to the JSON file is correct
- Ensure the JSON file is valid

### "Database connection failed"
- Verify your `DATABASE_URL` is correct
- Check that your IP is whitelisted in Azure PostgreSQL firewall rules
- Ensure SSL mode is set correctly (`sslmode=require`)

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Consider using a virtual environment: `python -m venv venv && source venv/bin/activate`

