// Login page functionality
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');

    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('rememberMe').checked;

            // Hide previous errors
            loginError.style.display = 'none';
            loginError.textContent = '';

            // Basic validation
            if (!email || !password) {
                showError('Por favor, completa todos los campos');
                return;
            }

            // Simulate authentication (since we're not connecting to a database)
            // In a real app, this would be an API call
            simulateLogin(email, password, rememberMe);
        });
    }
});

/**
 * Simulate login process
 * In a real application, this would make an API call to authenticate
 */
function simulateLogin(email, password, rememberMe) {
    // Show loading state
    const submitButton = document.querySelector('#loginForm button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Iniciando sesión...';

    // Simulate API delay
    setTimeout(() => {
        // For demo purposes, accept any email/password combination
        // In a real app, this would validate against a database
        if (email && password) {
            // Create mock user data
            const user = {
                email: email,
                name: email.split('@')[0], // Use email prefix as name
                id: Date.now().toString()
            };

            // Generate a simple token (in real app, this comes from the server)
            const token = 'mock_token_' + Date.now();

            // Save authentication
            setAuth(token, user);

            // Get redirect URL or default to home
            const redirectUrl = getRedirect() || '/';

            // Show success message briefly
            submitButton.textContent = '¡Éxito!';
            submitButton.style.background = 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)';

            // Redirect after short delay
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 500);
        } else {
            // This shouldn't happen due to validation, but handle it anyway
            showError('Error al iniciar sesión. Por favor, intenta de nuevo.');
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }, 1000); // Simulate 1 second API call
}

/**
 * Show error message
 */
function showError(message) {
    const loginError = document.getElementById('loginError');
    if (loginError) {
        loginError.textContent = message;
        loginError.style.display = 'block';
    }
}
