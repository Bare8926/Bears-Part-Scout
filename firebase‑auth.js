// firebase‑auth.js – Firebase init, auth, tier limits

import { initializeApp } from "https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js";
import { getAuth, onAuthStateChanged, signInWithEmailAndPassword,
         createUserWithEmailAndPassword, signOut } from
         "https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js";
import { getFirestore, doc, setDoc, getDoc, updateDoc,
         increment, serverTimestamp } from
         "https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyAQYztxv7U-wVqKDd4zFo065xWBgMNZles",
  authDomain: "bears-part-scout.firebaseapp.com",
  projectId: "bears-part-scout",
  storageBucket: "bears-part-scout.firebasestorage.app",
  messagingSenderId: "729412734347",
  appId: "1:729412734347:web:0575aa17f3e4728bdf738e"
};

const app   = initializeApp(firebaseConfig);
const auth  = getAuth(app);
const db    = getFirestore(app);

const TIER_LIMITS = {
  free:    { searches: 5,  maxResults: 20 },
  basic:   { searches: 25, maxResults: 50 },
  premium: { searches: 100, maxResults: 100 }
};

/* Helper: check‑and‑consume one search */
async function checkAndConsumeSearch() {
  const user = auth.currentUser;
  if (!user) { alert('Please log in first.'); return false; }

  const userRef = doc(db, "users", user.uid);
  const snap   = await getDoc(userRef);
  if (!snap.exists()) {
    await setDoc(userRef, {
      email: user.email,
      tier: "free",
      searchesUsed: 0,
      resetAt: serverTimestamp()
    });
    return checkAndConsumeSearch(); // retry
  }

  const data   = snap.data();
  const tier   = data.tier || "free";
  const limit  = TIER_LIMITS[tier];
  const used   = data.searchesUsed || 0;

  if (used >= limit.searches) {
    alert("You’ve hit your monthly limit. Upgrade to keep searching.");
    return false;
  }

  await updateDoc(userRef, { searchesUsed: increment(1) });
  const usageEl = document.getElementById("userUsage");
  if (usageEl) usageEl.textContent = `${used + 1} / ${limit.searches}`;
  return true;
}

/* UI wiring – call after page loads */
function initAuthUI() {
  // (modal handling code will live here – we’ll add it later)
}

/* expose for other scripts */
window.checkAndConsumeSearch = checkAndConsumeSearch;
window.initAuthUI = initAuthUI;
