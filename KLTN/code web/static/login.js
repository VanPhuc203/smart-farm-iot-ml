// login.js
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('isLoggedIn')) {
           window.location.href = '/static/data-sensor.html';
    }

    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const rememberMe = document.getElementById('remember-me').checked;

        fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                localStorage.setItem('isLoggedIn', 'true');
                localStorage.setItem('username', username);
                if (rememberMe) {
                    localStorage.setItem('rememberMe', 'true');
                }
                   window.location.href = '/static/data-sensor.html';
            } else {
                errorMessage.textContent = data.message || 'Tên đăng nhập hoặc mật khẩu không đúng';
                errorMessage.classList.remove('hidden');
            }
        })
        .catch(error => {
            errorMessage.textContent = 'Lỗi kết nối đến server';
            errorMessage.classList.remove('hidden');
        });
    });
});