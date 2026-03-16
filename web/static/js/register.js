// Register page functionality
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    const registerError = document.getElementById('registerError');
    const registerSuccess = document.getElementById('registerSuccess');

    // Password confirmation validation
    const passwordInput = document.getElementById('registerPassword');
    const passwordConfirmInput = document.getElementById('registerPasswordConfirm');

    if (passwordConfirmInput) {
        passwordConfirmInput.addEventListener('input', function() {
            if (passwordInput.value !== passwordConfirmInput.value) {
                passwordConfirmInput.setCustomValidity('Las contraseñas no coinciden');
            } else {
                passwordConfirmInput.setCustomValidity('');
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const name = document.getElementById('registerName').value;
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const passwordConfirm = document.getElementById('registerPasswordConfirm').value;
            const acceptTerms = document.getElementById('acceptTerms').checked;

            // Hide previous messages
            registerError.style.display = 'none';
            registerError.textContent = '';
            registerSuccess.style.display = 'none';
            registerSuccess.textContent = '';

            // Validation
            if (!name || !email || !password || !passwordConfirm) {
                showError('Por favor, completa todos los campos');
                return;
            }

            if (password.length < 8) {
                showError('La contraseña debe tener al menos 8 caracteres');
                return;
            }

            if (password !== passwordConfirm) {
                showError('Las contraseñas no coinciden');
                return;
            }

            if (!acceptTerms) {
                showError('Debes aceptar los términos y condiciones');
                return;
            }

            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                showError('Por favor, ingresa un correo electrónico válido');
                return;
            }

            // Simulate registration
            simulateRegister(name, email, password);
        });
    }
});

/**
 * Simulate registration process
 * In a real application, this would make an API call to register the user
 */
function simulateRegister(name, email, password) {
    // Show loading state
    const submitButton = document.querySelector('#registerForm button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Creando cuenta...';

    // Simulate API delay
    setTimeout(() => {
        // For demo purposes, always succeed
        // In a real app, this would validate and create the user in a database

        // Show success message
        const registerSuccess = document.getElementById('registerSuccess');
        registerSuccess.textContent = '¡Cuenta creada exitosamente! Redirigiendo a inicio de sesión...';
        registerSuccess.style.display = 'block';

        submitButton.textContent = '¡Éxito!';
        submitButton.style.background = 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)';

        // Redirect to login after short delay
        setTimeout(() => {
            window.location.href = '/login?registered=true';
        }, 1500);
    }, 1000); // Simulate 1 second API call
}

/**
 * Show error message
 */
function showError(message) {
    const registerError = document.getElementById('registerError');
    if (registerError) {
        registerError.textContent = message;
        registerError.style.display = 'block';
    }
}

// Check if user came from successful registration
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('registered') === 'true') {
        // Show a success message on login page if coming from registration
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            const successDiv = document.createElement('div');
            successDiv.className = 'auth-success';
            successDiv.style.display = 'block';
            successDiv.textContent = '¡Cuenta creada exitosamente! Por favor, inicia sesión.';
            loginForm.insertBefore(successDiv, loginForm.firstChild);
        }
    }
});
