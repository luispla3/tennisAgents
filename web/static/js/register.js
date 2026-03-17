// Registro de usuario con Firebase Auth
import {
  auth,
  createUserWithEmailAndPassword,
  updateProfile,
} from "./firebase-auth.js";

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

  const registerForm = document.getElementById("registerForm");
  const registerError = document.getElementById("registerError");
  const registerSuccess = document.getElementById("registerSuccess");

  const passwordInput = document.getElementById("registerPassword");
  const passwordConfirmInput = document.getElementById(
    "registerPasswordConfirm",
  );

  if (passwordConfirmInput) {
    passwordConfirmInput.addEventListener("input", () => {
      if (passwordInput.value !== passwordConfirmInput.value) {
        passwordConfirmInput.setCustomValidity("Las contraseñas no coinciden");
      } else {
        passwordConfirmInput.setCustomValidity("");
      }
    });
  }

  const showError = (message) => {
    if (registerError) {
      registerError.textContent = message;
      registerError.style.display = "block";
    }
  };

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const name = document.getElementById("registerName").value.trim();
      const email = document.getElementById("registerEmail").value.trim();
      const password = document.getElementById("registerPassword").value;
      const passwordConfirm = document.getElementById(
        "registerPasswordConfirm",
      ).value;
      const acceptTerms = document.getElementById("acceptTerms").checked;

      registerError.style.display = "none";
      registerError.textContent = "";
      registerSuccess.style.display = "none";
      registerSuccess.textContent = "";

      if (!name || !email || !password || !passwordConfirm) {
        showError("Por favor, completa todos los campos");
        return;
      }
      if (password.length < 8) {
        showError("La contraseña debe tener al menos 8 caracteres");
        return;
      }
      if (password !== passwordConfirm) {
        showError("Las contraseñas no coinciden");
        return;
      }
      if (!acceptTerms) {
        showError("Debes aceptar los términos y condiciones");
        return;
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        showError("Por favor, ingresa un correo electrónico válido");
        return;
      }

      const submitButton = document.querySelector(
        "#registerForm button[type=\"submit\"]",
      );
      const originalText = submitButton.textContent;
      submitButton.disabled = true;
      submitButton.textContent = "Creando cuenta...";

      try {
        const userCredential = await createUserWithEmailAndPassword(
          auth,
          email,
          password,
        );
        if (name) {
          await updateProfile(userCredential.user, { displayName: name });
        }

        registerSuccess.textContent =
          "¡Cuenta creada exitosamente! Redirigiendo a inicio de sesión...";
        registerSuccess.style.display = "block";

        submitButton.textContent = "¡Éxito!";
        submitButton.style.background =
          "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)";

        setTimeout(() => {
          window.location.href = "/login?registered=true";
        }, 1500);
      } catch (err) {
        console.error(err);
        showError(
          err?.message ||
            "Error al crear la cuenta. Por favor, inténtalo de nuevo.",
        );
        submitButton.disabled = false;
        submitButton.textContent = originalText;
      }
    });
  }
});

