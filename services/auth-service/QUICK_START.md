# Quick Start - Firebase Auth Service

## ✅ What Changed

Your auth-service now uses **Firebase Authentication** instead of custom JWT:

- ✅ Removed: bcrypt, pyjwt, password hashing
- ✅ Added: Firebase Admin SDK
- ✅ Updated: Database schema (added `firebase_uid` column)
- ✅ New endpoints for Firebase token verification

## 🚀 Quick Setup (5 minutes)

### 1. Get Firebase Service Account

```bash
# 1. Go to: https://console.firebase.google.com/
# 2. Create project or select existing
# 3. Go to Project Settings → Service Accounts
# 4. Click "Generate new private key"
# 5. Save as: firebase-service-account.json
# 6. Move it to: services/auth-service/firebase-service-account.json
```

### 2. Update .env File

Create `services/auth-service/.env`:

```env
DATABASE_URL=postgresql://bookinatoradmin:X783y54at3Sj@bookinator.postgres.database.azure.com:5432/bookinator?sslmode=require
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
```

### 3. Install Dependencies & Run

```bash
cd services/auth-service

# Install dependencies
pip install -r requirements.txt

# Initialize database (if not done already)
psql "postgresql://bookinatoradmin:X783y54at3Sj@bookinator.postgres.database.azure.com:5432/bookinator?sslmode=require" -f ../../database/init.sql

# Start service
uvicorn main:app --port 8001 --reload
```

### 4. Test It

Visit: http://localhost:8001/docs

You should see:
- `POST /api/auth/verify` - Main endpoint for Firebase auth
- `GET /api/auth/me` - Get current user
- `POST /api/auth/token/verify` - Simple token verification

## 🔥 Firebase Frontend Setup

### Install Firebase SDK

```bash
cd frontend
npm install firebase
```

### Configure Firebase

Create `frontend/src/config/firebase.ts`:

```typescript
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIza...",  // Get from Firebase Console
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123..."
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

Get config from: **Firebase Console** → **Project Settings** → **Your apps** → **Web**

### Use in React Components

```typescript
import { useState } from 'react';
import { 
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
} from 'firebase/auth';
import { auth } from './config/firebase';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSignup = async () => {
    try {
      // Sign up with Firebase
      const userCredential = await createUserWithEmailAndPassword(
        auth, 
        email, 
        password
      );
      
      // Get ID token
      const idToken = await userCredential.user.getIdToken();
      
      // Sync with backend
      const response = await fetch('http://localhost:8001/api/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken })
      });
      
      const data = await response.json();
      console.log('User created:', data.user);
      
      // Store token for API calls
      localStorage.setItem('authToken', idToken);
      
    } catch (error: any) {
      console.error('Signup failed:', error.message);
    }
  };
  
  const handleLogin = async () => {
    try {
      const userCredential = await signInWithEmailAndPassword(
        auth,
        email,
        password
      );
      
      const idToken = await userCredential.user.getIdToken();
      
      // Sync with backend
      await fetch('http://localhost:8001/api/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken })
      });
      
      localStorage.setItem('authToken', idToken);
      
    } catch (error: any) {
      console.error('Login failed:', error.message);
    }
  };
  
  return (
    <div>
      <input 
        type="email" 
        value={email} 
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input 
        type="password" 
        value={password} 
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button onClick={handleSignup}>Sign Up</button>
      <button onClick={handleLogin}>Login</button>
    </div>
  );
}

// Make authenticated requests
async function fetchBooks() {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch('http://localhost:8003/api/books', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
}
```

## 📊 Database Schema Changes

The `users` table now includes `firebase_uid`:

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    firebase_uid    TEXT UNIQUE NOT NULL,  -- New!
    email           TEXT UNIQUE NOT NULL,
    display_name    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

The `auth_credentials` table is no longer needed (removed).

## 🔌 API Flow

```
1. User signs up/logs in on frontend with Firebase SDK
   ↓
2. Frontend gets Firebase ID token
   ↓
3. Frontend calls: POST /api/auth/verify with token
   ↓
4. Backend verifies token with Firebase
   ↓
5. Backend creates/updates user in PostgreSQL
   ↓
6. Backend returns user data
   ↓
7. Frontend stores token and uses for all API calls
   ↓
8. Other services verify token by calling auth-service
```

## ⚠️ Important Notes

1. **Firebase credentials are required** - Service won't work without them
2. **Tokens expire after 1 hour** - Frontend should refresh tokens
3. **HTTPS required in production** - Firebase enforces this
4. **Never commit** `firebase-service-account.json` to Git (it's in .gitignore)

## 📚 Next Steps

1. ✅ Set up Firebase project
2. ✅ Download service account key
3. ✅ Update .env file
4. ✅ Run auth-service
5. ⬜ Update frontend to use Firebase SDK
6. ⬜ Test authentication flow
7. ⬜ Update other services to verify Firebase tokens

## 🆘 Troubleshooting

**"Firebase credentials not found"**
- Check that `.env` file exists in `services/auth-service/`
- Verify `FIREBASE_SERVICE_ACCOUNT_PATH` points to correct file
- Make sure JSON file is valid

**"Module 'firebase-admin' not found"**
```bash
pip install -r requirements.txt
```

**"Invalid token"**
- Token may be expired (1 hour lifespan)
- Make sure you're using the token from the correct Firebase project
- Check that token format is `Bearer <token>` in Authorization header

**Frontend CORS errors**
- Add your frontend URL to `allow_origins` in `main.py`

For detailed setup, see: `FIREBASE_SETUP.md`

