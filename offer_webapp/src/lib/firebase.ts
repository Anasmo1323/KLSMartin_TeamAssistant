import { initializeApp, getApps, getApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyCiXcGSaa70z1aLsjdzbgJZx1kaKVCcHdI",
  authDomain: "mcc-database-718b5.firebaseapp.com",
  projectId: "mcc-database-718b5",
  storageBucket: "mcc-database-718b5.firebasestorage.app",
  messagingSenderId: "915162560203",
  appId: "1:915162560203:web:488a2e5e427d4504f24d4e",
  measurementId: "G-M5665N5ZXE"
};

// Initialize Firebase (prevent re-initialization in Next.js hot reload)
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const db = getFirestore(app);

export { db, app };
