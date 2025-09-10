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

// Setup event listeners for password toggles
document.addEventListener('DOMContentLoaded', function() {
    // Prevent unwanted focus behavior
    document.addEventListener('mousedown', function(e) {
        // Only allow focus on inputs, textareas, and buttons
        if (!e.target.matches('input, textarea, button, a, select')) {
            e.preventDefault();
        }
    });

    // Password toggle
    const passwordToggle = document.getElementById('password-toggle');
    const passwordInput = document.getElementById('password');
    
    passwordToggle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            passwordToggle.classList.remove('fa-eye');
            passwordToggle.classList.add('fa-eye-slash');
        } else {
            passwordInput.type = 'password';
            passwordToggle.classList.remove('fa-eye-slash');
            passwordToggle.classList.add('fa-eye');
        }
    });
    
    passwordToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });

    // Confirm password toggle
    const confirmPasswordToggle = document.getElementById('confirm-password-toggle');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    confirmPasswordToggle.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (confirmPasswordInput.type === 'password') {
            confirmPasswordInput.type = 'text';
            confirmPasswordToggle.classList.remove('fa-eye');
            confirmPasswordToggle.classList.add('fa-eye-slash');
        } else {
            confirmPasswordInput.type = 'password';
            confirmPasswordToggle.classList.remove('fa-eye-slash');
            confirmPasswordToggle.classList.add('fa-eye');
        }
    });
    
    confirmPasswordToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
});

// Auto focus on full name field
document.getElementById('full_name').focus();

// Password validation function
function validatePasswords() {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const errorDiv = document.getElementById('error-message');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    if (password !== confirmPassword && confirmPassword.length > 0) {
        errorDiv.textContent = 'Mật khẩu xác nhận không khớp';
        errorDiv.style.display = 'block';
        confirmPasswordInput.classList.add('error');
        return false;
    } else {
        errorDiv.style.display = 'none';
        confirmPasswordInput.classList.remove('error');
        return true;
    }
}

// Real-time validation on confirm password input
document.getElementById('confirm_password').addEventListener('input', function() {
    validatePasswords();
});

// Also validate when password changes
document.getElementById('password').addEventListener('input', function() {
    const confirmPassword = document.getElementById('confirm_password');
    if (confirmPassword.value.length > 0) {
        validatePasswords();
    }
});

// Form submission validation
document.getElementById('register-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const fullName = document.getElementById('full_name').value;
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-message');
    // Clear previous errors
    document.getElementById('error-message').style.display = 'none';


    // Validate passwords
    if (!validatePasswords()) {
        return false;
    }
    fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            full_name: fullName,
            username: username,
            email: email,
            password: password
        }),
        redirect: 'follow'
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
        errorDiv.style.display = 'block';
        
        if (data.success) {
            // Thay đổi style thành success
            errorDiv.className = 'success-message';
            setTimeout(() => {
                window.location.href = data.next;
            }, 1000);
        } else {
            // Giữ style error
            errorDiv.className = 'error-message';
        }
    })
    .catch(error => {
        console.log(error);
        errorDiv.textContent = 'Đã xảy ra lỗi. Vui lòng thử lại.';
        errorDiv.className = 'error-message';
        errorDiv.style.display = 'block';
    });
});