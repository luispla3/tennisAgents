// Login con Firebase Auth
import { auth, signInWithEmailAndPassword } from "./firebase-auth.js";

document.addEventListener("DOMContentLoaded", () => {
  // Mostrar Cerrar sesión si ya está autenticado
  const navLogout = document.getElementById("navLogout");
  if (navLogout && typeof isAuthenticated === "function" && isAuthenticated()) {
    navLogout.style.display = "";
    navLogout.addEventListener("click", (e) => {
      e.preventDefault();
      if (typeof clearAuth === "function") clearAuth();
      window.location.href = "/";
    });
  }

  const loginForm = document.getElementById("loginForm");
  const loginError = document.getElementById("loginError");

  const showError = (message) => {
    if (loginError) {
      loginError.textContent = message;
      loginError.style.display = "block";
    }
  };

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;

      loginError.style.display = "none";
      loginError.textContent = "";

      if (!email || !password) {
        showError("Por favor, completa todos los campos");
        return;
      }

      const submitButton = document.querySelector(
        "#loginForm button[type=\"submit\"]",
      );
      const originalText = submitButton.textContent;
      submitButton.disabled = true;
      submitButton.textContent = "Iniciando sesión...";

      try {
        const userCredential = await signInWithEmailAndPassword(
          auth,
          email,
          password,
        );
        const user = userCredential.user;
        const token = await user.getIdToken();

        // `setAuth` y `getRedirect` vienen de auth.js (script global)
        setAuth(token, {
          email: user.email,
          name:
            user.displayName ||
            (user.email ? user.email.split("@")[0] : ""),
          uid: user.uid,
        });

        const redirectUrl = getRedirect() || "/";

        submitButton.textContent = "¡Éxito!";
        submitButton.style.background =
          "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)";

        setTimeout(() => {
          window.location.href = redirectUrl;
        }, 500);
      } catch (err) {
        console.error(err);
        showError("Credenciales inválidas o error al iniciar sesión.");
        submitButton.disabled = false;
        submitButton.textContent = originalText;
      }
    });
  }

  // Mensaje de éxito al venir de registro
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("registered") === "true") {
    const loginFormEl = document.getElementById("loginForm");
    if (loginFormEl) {
      const successDiv = document.createElement("div");
      successDiv.className = "auth-success";
      successDiv.style.display = "block";
      successDiv.textContent =
        "¡Cuenta creada exitosamente! Por favor, inicia sesión.";
      loginFormEl.insertBefore(successDiv, loginFormEl.firstChild);
    }
  }
});

