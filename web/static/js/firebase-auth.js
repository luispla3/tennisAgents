// Firebase Auth inicialización (frontend)
// Rellena firebaseConfig con los valores de tu consola Firebase.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  updateProfile,
  signInWithEmailAndPassword,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

// TODO: sustituye estos valores por los de tu proyecto Firebase.
const firebaseConfig = {
  apiKey: "AIzaSyDmw1CzK6eOdy1z063w9R3QzGHrzOahpY4",
  authDomain: "tennisagents.firebaseapp.com",
  projectId: "tennisagents",
  storageBucket: "tennisagents.firebasestorage.app",
  messagingSenderId: "1070527591693",
  appId: "1:1070527591693:web:de6d180751003f82abec44",
  measurementId: "G-E8ZP1MFGFE"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export {
  auth,
  createUserWithEmailAndPassword,
  updateProfile,
  signInWithEmailAndPassword,
  signOut,
};

