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
/* ──────────────────────────────────────────────────────────────
   initAuthUI – wires up the UI elements (login, signup, logout,
   opening/closing of modals, auth‑state UI updates)
   ────────────────────────────────────────────────────────────── */
function initAuthUI() {
  // Grab the elements we’ll need
  const loginBtn      = document.getElementById('loginBtn');
  const accountBtn    = document.getElementById('accountBtn');
  const authModal     = document.getElementById('authModal');
  const accountModal  = document.getElementById('accountModal');
  const logoutBtn     = document.getElementById('logoutBtn');
  const loginForm     = document.getElementById('loginForm');
  const signupForm    = document.getElementById('signupForm');
  const userEmailSpan = document.getElementById('userEmail');
  const userTierSpan  = document.getElementById('userTier');
  const userUsageSpan = document.getElementById('userUsage');

  // ---- UI interactions -------------------------------------------------
  // Show the login/signup modal when the button is clicked
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      authModal.style.display = 'block';
    });
  }

  // Open the “My Account” modal when the account button is clicked
  if (accountBtn) {
    accountBtn.addEventListener('click', () => {
      accountModal.style.display = 'block';
    });
  }

  // Close modals when clicking outside of them
  window.addEventListener('click', (e) => {
    if (e.target === authModal)  authModal.style.display  = 'none';
    if (e.target === accountModal) accountModal.style.display = 'none';
  });

  // Log out
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      await signOut(auth);
      accountModal.style.display = 'none';
    });
  }

  // ---- Login form ------------------------------------------------------
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email    = e.target.elements.loginEmail.value;
      const password = e.target.elements.loginPassword.value;
      try {
        await signInWithEmailAndPassword(auth, email, password);
        authModal.style.display = 'none';
      } catch (err) {
        alert('Login failed: ' + err.message);
      }
    });
  }

  // ---- Sign‑up form ----------------------------------------------------
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email    = e.target.elements.signupEmail.value;
      const password = e.target.elements.signupPassword.value;
      try {
        const cred = await createUserWithEmailAndPassword(auth, email, password);
        // Create a Firestore doc for the new user (starts on the free tier)
        await setDoc(doc(db, 'users', cred.user.uid), {
          email,
          tier: 'free',
          searchesUsed: 0,
          resetAt: serverTimestamp()
        });
        authModal.style.display = 'none';
      } catch (err) {
        alert('Signup failed: ' + err.message);
      }
    });
  }

  // ---- Auth‑state listener – updates UI based on login status ---------
  onAuthStateChanged(auth, async (user) => {
    if (user) {
      // User is signed in
      if (loginBtn)   loginBtn.style.display = 'none';
      if (accountBtn) accountBtn.style.display = 'inline-block';

      // Pull the latest user doc (tier + usage)
      const snap = await getDoc(doc(db, 'users', user.uid));
      const data = snap?.data() || {};

      if (userEmailSpan) userEmailSpan.textContent = data.email || '';
      if (userTierSpan)  userTierSpan.textContent  = data.tier  || 'free';

      const limits = TIER_LIMITS[data.tier || 'free'];
      if (userUsageSpan) userUsageSpan.textContent = `${data.searchesUsed || 0} / ${limits.searches}`;
    } else {
      // No user – show the login button again
      if (loginBtn)   loginBtn.style.display = 'inline-block';
      if (accountBtn) accountBtn.style.display = 'none';
    }
  });
}

/* expose for other scripts */
window.checkAndConsumeSearch = checkAndConsumeSearch;
window.initAuthUI = initAuthUI;
