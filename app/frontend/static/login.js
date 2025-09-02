// Function to toggle password visibility
function togglePassword(event, inputId, toggleIcon) {
    // Prevent the input from getting focus when clicking the icon
    event.preventDefault();
    event.stopPropagation();
    
    const passwordInput = document.getElementById(inputId);
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.remove('fa-eye');
        toggleIcon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
    }
}

// Check if this is admin login mode
function isAdminMode() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('admin') === 'true';
}

// Setup event listener for password toggle
document.addEventListener('DOMContentLoaded', function() {
    // Check if admin mode and update UI
    if (isAdminMode()) {
        document.getElementById('login-title').textContent = 'Admin Login';
        document.getElementById('login-subtitle').textContent = 'Đăng nhập với quyền quản trị';
        document.getElementById('login-button').textContent = 'Đăng nhập Admin';
        document.getElementById('register-link').style.display = 'none';
    }

    // Simple password toggle
    const passwordToggle = document.getElementById('password-toggle');
    const passwordInput = document.getElementById('password');
    
    if (passwordToggle && passwordInput) {
        passwordToggle.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                passwordToggle.className = 'fas fa-eye-slash password-toggle';
            } else {
                passwordInput.type = 'password';
                passwordToggle.className = 'fas fa-eye password-toggle';
            }
        };
    }
});

document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-message');
    
    // Hide previous messages
    errorDiv.style.display = 'none';
    errorDiv.className = 'error-message'; // Reset to default class
    
    fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => {
        if (response.status == 422) {
            return {
                "success": false,
                "detail": "Vui lòng nhập dữ liệu hợp lệ"
            }
        }
        else {
            return response.json();
        }
    })
    .then(data => {
        errorDiv.textContent = data.detail;
        
        // Change class based on success/failure
        if (data.success) {
            errorDiv.className = 'success-message';
        } else {
            errorDiv.className = 'error-message';
        }
        
        errorDiv.style.display = 'block';
        
        if (data.success) {
            // Check if we're in admin mode and redirect accordingly
            if (isAdminMode()) {
                setTimeout(() => {
                    window.location.href = '/admin';
                }, 1000);
            } else {
                setTimeout(() => {
                    window.location.href = data.next;
                }, 1000);
            }
        }
    })
    .catch(error => {
        console.log(error);
        errorDiv.textContent = 'Đã xảy ra lỗi. Vui lòng thử lại.';
        errorDiv.className = 'error-message';
        errorDiv.style.display = 'block';
    });
});

// Auto focus on username field
document.getElementById('username').focus();