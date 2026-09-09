import { initializeApp, getApps, getApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyC7vQfkrHi3xWqZpjh4Iwspnv2QdYh1Klw",
  authDomain: "klsmartin-eg-onlinecatalogue.firebaseapp.com",
  projectId: "klsmartin-eg-onlinecatalogue",
  storageBucket: "klsmartin-eg-onlinecatalogue.firebasestorage.app",
  messagingSenderId: "453521156042",
  appId: "1:453521156042:web:019e673bc86c92a84ed133"
};

// Initialize Firebase (prevent re-initialization in Next.js hot reload)
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const db = getFirestore(app);
const storage = getStorage(app);

export { db, app, storage };
