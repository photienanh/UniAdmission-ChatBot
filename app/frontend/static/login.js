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

// Setup event listener for password toggle
document.addEventListener('DOMContentLoaded', function() {
    // Prevent unwanted focus behavior
    document.addEventListener('mousedown', function(e) {
        // Only allow focus on inputs, textareas, and buttons
        if (!e.target.matches('input, textarea, button, a, select')) {
            e.preventDefault();
        }
    });

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
    
    // Prevent click event from bubbling to input
    passwordToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
});

document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-message');
    
    // Hide previous messages
    errorDiv.style.display = 'none';
    errorDiv.className = 'error-message'; // Reset to default class
    
    fetch('/login', {
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
            setTimeout(() => {
                window.location.href = data.next;
            }, 1000);
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