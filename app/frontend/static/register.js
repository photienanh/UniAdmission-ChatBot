// Register form handler for SSR template
document.addEventListener("DOMContentLoaded", () => {
    const registerForm = document.getElementById("register-form");
    const errorMessage = document.getElementById("error-message");
    const registerBtn = document.getElementById("register-btn");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput = document.getElementById("confirm_password");
    const passwordToggle = document.getElementById("password-toggle");
    const confirmPasswordToggle = document.getElementById("confirm-password-toggle");

    const togglePassword = (input, toggleIcon) => {
        if (!input || !toggleIcon) {
            return;
        }
        toggleIcon.addEventListener("click", () => {
            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            toggleIcon.classList.toggle("fa-eye");
            toggleIcon.classList.toggle("fa-eye-slash");
        });
    };

    togglePassword(passwordInput, passwordToggle);
    togglePassword(confirmPasswordInput, confirmPasswordToggle);

    if (!registerForm) {
        return;
    }

    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const fullName = document.getElementById("full_name").value.trim();
        const username = document.getElementById("username").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        if (errorMessage) {
            errorMessage.textContent = "";
            errorMessage.style.display = "none";
        }

        if (!fullName || !username || !email || !password || !confirmPassword) {
            if (errorMessage) {
                errorMessage.textContent = "Vui lòng điền đầy đủ thông tin.";
                errorMessage.style.display = "block";
            }
            return;
        }

        if (password !== confirmPassword) {
            if (errorMessage) {
                errorMessage.textContent = "Mật khẩu xác nhận không khớp.";
                errorMessage.style.display = "block";
            }
            return;
        }

        if (registerBtn) {
            registerBtn.disabled = true;
            registerBtn.textContent = "Đang đăng ký...";
        }

        try {
            const response = await fetch("/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    full_name: fullName,
                    username: username,
                    email: email,
                    password: password,
                }),
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = data.next || "/";
            } else {
                if (errorMessage) {
                    errorMessage.textContent = data.detail || "Đăng ký thất bại.";
                    errorMessage.style.display = "block";
                }
                if (registerBtn) {
                    registerBtn.disabled = false;
                    registerBtn.textContent = "Đăng ký";
                }
            }
        } catch (error) {
            console.error("Register error:", error);
            if (errorMessage) {
                errorMessage.textContent = "Có lỗi xảy ra. Vui lòng thử lại.";
                errorMessage.style.display = "block";
            }
            if (registerBtn) {
                registerBtn.disabled = false;
                registerBtn.textContent = "Đăng ký";
            }
        }
    });
});
