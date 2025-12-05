# Firebase Authentication Setup Guide

## 🔥 Overview

The auth-service now uses **Firebase Authentication** instead of custom JWT authentication. This provides:

- ✅ Secure authentication out of the box
- ✅ Multiple sign-in methods (email/password, Google, GitHub, etc.)
- ✅ Email verification
- ✅ Password reset
- ✅ Rate limiting and abuse prevention
- ✅ Multi-platform support (Web, iOS, Android)

## 📋 Setup Steps

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add project"**
3. Enter project name: `language-learning-app` (or your choice)
4. Disable Google Analytics (optional for development)
5. Click **"Create project"**

### 2. Enable Authentication

1. In Firebase Console, go to **Authentication**
2. Click **"Get started"**
3. Go to **"Sign-in method"** tab
4. Enable **"Email/Password"** provider
5. (Optional) Enable other providers like Google, GitHub, etc.

### 3. Get Service Account Key

For backend authentication:

1. Go to **Project Settings** (gear icon) → **Service accounts**
2. Click **"Generate new private key"**
3. Download the JSON file
4. **IMPORTANT**: Keep this file secure! Never commit it to Git

### 4. Configure Frontend

Add Firebase to your React app:

```bash
cd frontend
npm install firebase
```

Create `frontend/src/firebase.ts`:

```typescript
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

Get these values from:
**Firebase Console** → **Project Settings** → **General** → **Your apps** → **Web app**

### 5. Configure Backend (.env)

Update `services/auth-service/.env`:

```env
DATABASE_URL=postgresql://bookinatoradmin:X783y54at3Sj@bookinator.postgres.database.azure.com:5432/bookinator?sslmode=require

# Option 1: Path to service account JSON file (recommended for local dev)
FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/your/serviceAccountKey.json

# Option 2: JSON string (for production/Azure)
# FIREBASE_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"..."}
```

**For Azure deployment**, use environment variable with JSON string:
```bash
FIREBASE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'
```

## 🔌 Authentication Flow

### Frontend (React)

```typescript
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  signOut
} from 'firebase/auth';
import { auth } from './firebase';

// Sign up
async function signup(email: string, password: string) {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const idToken = await userCredential.user.getIdToken();
    
    // Sync with backend
    const response = await fetch('http://localhost:8001/api/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        id_token: idToken,
        display_name: 'User Name'  // optional
      })
    });
    
    const data = await response.json();
    console.log('User synced:', data.user);
    
    // Store token for future requests
    localStorage.setItem('firebaseToken', idToken);
    
  } catch (error) {
    console.error('Signup error:', error);
  }
}

// Login
async function login(email: string, password: string) {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const idToken = await userCredential.user.getIdToken();
    
    // Sync with backend
    await fetch('http://localhost:8001/api/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken })
    });
    
    localStorage.setItem('firebaseToken', idToken);
    
  } catch (error) {
    console.error('Login error:', error);
  }
}

// Logout
async function logout() {
  await signOut(auth);
  localStorage.removeItem('firebaseToken');
}

// Make authenticated requests to other services
async function getBooks() {
  const token = localStorage.getItem('firebaseToken');
  
  const response = await fetch('http://localhost:8003/api/books', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
}
```

### Backend API Endpoints

**1. Verify Token & Sync User**
```bash
POST /api/auth/verify
Content-Type: application/json

{
  "id_token": "firebase_id_token_here",
  "display_name": "Optional Display Name"
}

# Response:
{
  "user": {
    "id": 1,
    "firebase_uid": "firebase_uid_123",
    "email": "user@example.com",
    "display_name": "User Name",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  "message": "User verified and synchronized"
}
```

**2. Get Current User**
```bash
GET /api/auth/me
Authorization: Bearer firebase_id_token_here

# Response:
{
  "id": 1,
  "firebase_uid": "firebase_uid_123",
  "email": "user@example.com",
  "display_name": "User Name",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**3. Simple Token Verification** (for other microservices)
```bash
POST /api/auth/token/verify
Authorization: Bearer firebase_id_token_here

# Response:
{
  "valid": true,
  "user": {
    "firebase_uid": "firebase_uid_123",
    "email": "user@example.com",
    "email_verified": true
  }
}
```

## 🔄 Migration from Old Auth

The old `/api/auth/login` and `/api/auth/signup` endpoints now return HTTP 410 Gone with instructions to use Firebase.

Update your frontend to use Firebase SDK instead of calling these endpoints directly.

## 🧪 Testing

### 1. Install Dependencies
```bash
cd services/auth-service
pip install -r requirements.txt
```

### 2. Set Up Firebase Credentials
```bash
# Download service account key from Firebase Console
# Save as firebase-service-account.json

# Update .env
echo 'FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json' >> .env
```

### 3. Start Service
```bash
uvicorn main:app --port 8001 --reload
```

### 4. Test with curl

First, get an ID token from Firebase (use your frontend or Firebase REST API):

```bash
# Example: Get ID token via Firebase REST API
curl 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"test@example.com",
    "password":"password123",
    "returnSecureToken":true
  }'

# Use the returned idToken
TOKEN="eyJhbGciOiJSUzI1NiIsIm..."

# Verify and sync user
curl -X POST http://localhost:8001/api/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"id_token\":\"$TOKEN\"}"

# Get current user
curl http://localhost:8001/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## 🔐 Security Best Practices

1. **Never commit service account keys** to Git
2. **Use environment variables** for credentials
3. **Enable email verification** in Firebase Console
4. **Set up password requirements** in Firebase Console
5. **Enable reCAPTCHA** for abuse prevention
6. **Use HTTPS** in production
7. **Rotate service account keys** periodically
8. **Implement rate limiting** on your endpoints
9. **Monitor authentication logs** in Firebase Console

## 📚 Resources

- [Firebase Auth Documentation](https://firebase.google.com/docs/auth)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Firebase Security Rules](https://firebase.google.com/docs/rules)
- [Firebase REST API](https://firebase.google.com/docs/reference/rest/auth)

## ❓ Troubleshooting

### "Firebase credentials not found"
- Make sure `FIREBASE_SERVICE_ACCOUNT_PATH` or `FIREBASE_SERVICE_ACCOUNT_KEY` is set
- Check that the path to JSON file is correct
- Verify JSON file is valid

### "Invalid Firebase token"
- Token may be expired (tokens expire after 1 hour)
- Token format should be: `Bearer <token>`
- Make sure token is from the correct Firebase project

### "User not found in database"
- Call `/api/auth/verify` first to sync user to PostgreSQL
- Check database connection

### Frontend CORS errors
- Update CORS configuration in `main.py`
- Add your frontend domain to `allow_origins`

