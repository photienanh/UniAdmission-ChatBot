// Prevent unwanted focus behavior
document.addEventListener('mousedown', function(e) {
    // Only allow focus on inputs, textareas, and buttons
    if (!e.target.matches('input, textarea, button, a, select')) {
        e.preventDefault();
    }
});

const confirmInput = document.getElementById('confirm_text');
const passwordInput = document.getElementById('password');
const deleteBtn = document.getElementById('delete-btn');
const errorDiv = document.getElementById('error-message');
const successDiv = document.getElementById('success-message');

// Enable/disable delete button based on confirmation
function checkForm() {
    const confirmValue = confirmInput.value.trim();
    const passwordValue = passwordInput.value.trim();
    
    if (confirmValue === 'DELETE' && passwordValue.length > 0) {
        deleteBtn.classList.add('enabled');
    } else {
        deleteBtn.classList.remove('enabled');
    }
}

confirmInput.addEventListener('input', checkForm);
passwordInput.addEventListener('input', checkForm);

// Handle form submission
document.getElementById('delete-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Clear previous messages
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    const confirmValue = confirmInput.value.trim();
    const passwordValue = passwordInput.value.trim();
    
    if (confirmValue !== 'DELETE') {
        errorDiv.textContent = 'Vui lòng nhập chính xác "DELETE" để xác nhận';
        errorDiv.style.display = 'block';
        return;
    }
    
    if (passwordValue.length === 0) {
        errorDiv.textContent = 'Vui lòng nhập mật khẩu';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Disable button during request
    deleteBtn.disabled = true;
    deleteBtn.textContent = 'Đang xóa...';
    
    // Send request
    fetch('/api/auth/delete_account', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            confirm: confirmValue,
            password: passwordValue
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
        successDiv.textContent = data.detail;
        successDiv.style.display = 'block';
        if (data.success) {
            // Redirect to login after 2 seconds
            setTimeout(() => {
                window.location.href = data.next;
            }, 2000);
        }
    })
    .catch(error => {
        console.log(error);
        errorDiv.textContent = 'Có lỗi xảy ra. Vui lòng thử lại.';
        errorDiv.style.display = 'block';
    })
    .finally(() => {
        // Re-enable button
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = '<i class="fas fa-trash" style="margin-right: 8px;"></i>Xóa tài khoản';
    });
});