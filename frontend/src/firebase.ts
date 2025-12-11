import { initializeApp } from 'firebase/app';
import { getAuth, setPersistence, browserLocalPersistence } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyB5wNxc78iTdMCMFY0NUd7nYrVO6-VV1YM",
  authDomain: "bookinator3000.firebaseapp.com",
  projectId: "bookinator3000",
  storageBucket: "bookinator3000.firebasestorage.app",
  messagingSenderId: "985618767870",
  appId: "1:985618767870:web:dc39524c533b03415daaaf"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Enable persistence so users stay logged in
setPersistence(auth, browserLocalPersistence).catch((error) => {
  console.error('Failed to set Firebase persistence:', error);
});

