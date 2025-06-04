from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import secrets
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Basit veri depolama (üretimde veritabanı kullanın)
messages = []
users = {}

# HTML Şablonları
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ModernChat - Canlı Destek</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .chat-container {
            width: 100%;
            max-width: 400px;
            height: 600px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: slideUp 0.5s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .chat-header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 20px;
            text-align: center;
            position: relative;
        }

        .chat-header h1 {
            font-size: 1.5em;
            margin-bottom: 5px;
        }

        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #4ade80;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .messages-container {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8fafc;
        }

        .message {
            margin-bottom: 15px;
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            text-align: right;
        }

        .message.admin {
            text-align: left;
        }

        .message-bubble {
            display: inline-block;
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            position: relative;
        }

        .message.user .message-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message.admin .message-bubble {
            background: white;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .message-time {
            font-size: 0.75em;
            opacity: 0.7;
            margin-top: 4px;
        }

        .input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e5e7eb;
        }

        .input-group {
            display: flex;
            gap: 10px;
        }

        #messageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        #messageInput:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        #sendBtn {
            padding: 12px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            min-width: 80px;
        }

        #sendBtn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        #sendBtn:active {
            transform: translateY(0);
        }

        .typing-indicator {
            text-align: left;
            padding: 10px 20px;
            font-style: italic;
            color: #6b7280;
            font-size: 14px;
        }

        .typing-dots {
            display: inline-block;
        }

        .typing-dots span {
            display: inline-block;
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: #6b7280;
            margin: 0 1px;
            animation: typing 1.4s infinite;
        }

        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }

        @media (max-width: 480px) {
            .chat-container {
                width: 100%;
                height: 100vh;
                border-radius: 0;
                max-width: none;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🚀 ModernChat</h1>
            <p><span class="status-indicator"></span>Canlı Destek</p>
        </div>
        
        <div class="messages-container" id="messages">
            <div class="message admin">
                <div class="message-bubble">
                    Merhaba! Size nasıl yardımcı olabilirim? 😊
                </div>
                <div class="message-time">Şimdi</div>
            </div>
        </div>
        
        <div class="typing-indicator" id="typingIndicator" style="display: none;">
            Admin yazıyor <span class="typing-dots"><span></span><span></span><span></span></span>
        </div>
        
        <div class="input-container">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="Mesajınızı yazın..." maxlength="500">
                <button id="sendBtn">Gönder</button>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const messagesContainer = document.getElementById('messages');
        const typingIndicator = document.getElementById('typingIndicator');

        let typingTimer;

        // Mesaj gönderme
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message) {
                socket.emit('user_message', {
                    message: message,
                    timestamp: new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'})
                });
                
                addMessage(message, 'user', new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'}));
                messageInput.value = '';
                sendBtn.textContent = 'Gönderildi ✓';
                setTimeout(() => sendBtn.textContent = 'Gönder', 1000);
            }
        }

        // Mesaj ekleme
        function addMessage(text, type, time) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.innerHTML = `
                <div class="message-bubble">${text}</div>
                <div class="message-time">${time}</div>
            `;
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // Admin mesajı alma
        socket.on('admin_message', function(data) {
            typingIndicator.style.display = 'none';
            addMessage(data.message, 'admin', data.timestamp);
        });

        // Admin yazıyor durumu
        socket.on('admin_typing', function() {
            typingIndicator.style.display = 'block';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        });

        socket.on('admin_stop_typing', function() {
            typingIndicator.style.display = 'none';
        });

        // Event listeners
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Yazma durumu bildirimi
        messageInput.addEventListener('input', function() {
            socket.emit('user_typing');
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => {
                socket.emit('user_stop_typing');
            }, 1000);
        });

        // Bağlantı durumu
        socket.on('connect', function() {
            console.log('Bağlandı');
        });

        socket.on('disconnect', function() {
            console.log('Bağlantı kesildi');
        });
    </script>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - ModernChat</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
        }

        .admin-container {
            display: flex;
            height: 100vh;
        }

        .sidebar {
            width: 300px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid #e5e7eb;
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
        }

        .sidebar-header h1 {
            font-size: 1.3em;
            margin-bottom: 5px;
        }

        .users-list {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }

        .user-item {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            background: #f8fafc;
        }

        .user-item:hover {
            background: #e2e8f0;
            transform: translateX(5px);
        }

        .user-item.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #4338ca;
        }

        .user-info h3 {
            font-size: 1em;
            margin-bottom: 5px;
        }

        .user-status {
            font-size: 0.8em;
            opacity: 0.8;
        }

        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 2s infinite;
        }

        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
        }

        .chat-header {
            padding: 20px;
            background: white;
            border-bottom: 1px solid #e5e7eb;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .chat-header h2 {
            color: #1f2937;
            font-size: 1.2em;
        }

        .messages-area {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8fafc;
        }

        .message {
            margin-bottom: 15px;
            animation: fadeIn 0.3s ease-in;
        }

        .message.user {
            text-align: left;
        }

        .message.admin {
            text-align: right;
        }

        .message-bubble {
            display: inline-block;
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }

        .message.user .message-bubble {
            background: white;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            border-bottom-left-radius: 4px;
        }

        .message.admin .message-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message-time {
            font-size: 0.75em;
            opacity: 0.7;
            margin-top: 4px;
        }

        .typing-indicator {
            text-align: left;
            padding: 10px 0;
            font-style: italic;
            color: #6b7280;
            font-size: 14px;
        }

        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e5e7eb;
        }

        .input-group {
            display: flex;
            gap: 10px;
        }

        #adminMessageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        #adminMessageInput:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        #adminSendBtn {
            padding: 12px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            min-width: 80px;
        }

        #adminSendBtn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .stats-bar {
            padding: 15px 20px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            text-align: center;
            font-size: 14px;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        @media (max-width: 768px) {
            .admin-container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                height: 200px;
            }
            
            .users-list {
                flex-direction: row;
                overflow-x: auto;
            }
            
            .user-item {
                min-width: 200px;
                margin-right: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="admin-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>🔧 Admin Panel</h1>
                <p>Kullanıcı Yönetimi</p>
            </div>
            
            <div class="stats-bar">
                <strong id="userCount">0</strong> Aktif Kullanıcı
            </div>
            
            <div class="users-list" id="usersList">
                <div class="user-item" onclick="selectGlobalChat()">
                    <div class="user-info">
                        <h3>🌐 Genel Chat</h3>
                        <div class="user-status">
                            <span class="status-indicator"></span>
                            Tüm mesajlar
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="chat-area">
            <div class="chat-header">
                <h2 id="chatTitle">🌐 Genel Chat - Tüm Mesajlar</h2>
            </div>
            
            <div class="messages-area" id="messagesArea">
                <div class="message admin">
                    <div class="message-bubble">
                        Admin paneline hoş geldiniz! Buradan tüm kullanıcı mesajlarını görebilir ve yanıtlayabilirsiniz.
                    </div>
                    <div class="message-time">Sistem</div>
                </div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator" style="display: none;">
                Kullanıcı yazıyor...
            </div>
            
            <div class="input-area">
                <div class="input-group">
                    <input type="text" id="adminMessageInput" placeholder="Mesajınızı yazın..." maxlength="500">
                    <button id="adminSendBtn">Gönder</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        const adminMessageInput = document.getElementById('adminMessageInput');
        const adminSendBtn = document.getElementById('adminSendBtn');
        const messagesArea = document.getElementById('messagesArea');
        const typingIndicator = document.getElementById('typingIndicator');
        const usersList = document.getElementById('usersList');
        const userCount = document.getElementById('userCount');
        const chatTitle = document.getElementById('chatTitle');

        let currentSelectedUser = 'global';
        let connectedUsers = 0;

        // Admin mesaj gönderme
        function sendAdminMessage() {
            const message = adminMessageInput.value.trim();
            if (message) {
                socket.emit('admin_message', {
                    message: message,
                    timestamp: new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'})
                });
                
                addMessage(message, 'admin', new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'}));
                adminMessageInput.value = '';
                adminSendBtn.textContent = 'Gönderildi ✓';
                setTimeout(() => adminSendBtn.textContent = 'Gönder', 1000);
            }
        }

        // Mesaj ekleme
        function addMessage(text, type, time, username = '') {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            let messageContent = text;
            if (type === 'user' && username) {
                messageContent = `<strong>${username}:</strong> ${text}`;
            }
            
            messageDiv.innerHTML = `
                <div class="message-bubble">${messageContent}</div>
                <div class="message-time">${time}</div>
            `;
            messagesArea.appendChild(messageDiv);
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }

        // Genel chat seçimi
        function selectGlobalChat() {
            currentSelectedUser = 'global';
            chatTitle.textContent = '🌐 Genel Chat - Tüm Mesajlar';
            
            // Aktif durumu güncelle
            document.querySelectorAll('.user-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelector('.user-item').classList.add('active');
        }

        // Socket olayları
        socket.on('user_message', function(data) {
            addMessage(data.message, 'user', data.timestamp, 'Kullanıcı');
            typingIndicator.style.display = 'none';
        });

        socket.on('user_typing', function() {
            typingIndicator.style.display = 'block';
            messagesArea.scrollTop = messagesArea.scrollHeight;
        });

        socket.on('user_stop_typing', function() {
            typingIndicator.style.display = 'none';
        });

        socket.on('user_connected', function(data) {
            connectedUsers++;
            userCount.textContent = connectedUsers;
        });

        socket.on('user_disconnected', function(data) {
            connectedUsers = Math.max(0, connectedUsers - 1);
            userCount.textContent = connectedUsers;
        });

        // Event listeners
        adminSendBtn.addEventListener('click', sendAdminMessage);
        adminMessageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendAdminMessage();
            }
        });

        // Yazma durumu bildirimi
        let typingTimer;
        adminMessageInput.addEventListener('input', function() {
            socket.emit('admin_typing');
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => {
                socket.emit('admin_stop_typing');
            }, 1000);
        });

        // Sayfa yüklendiğinde
        selectGlobalChat();
        
        socket.on('connect', function() {
            console.log('Admin paneline bağlandı');
        });
    </script>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Girişi - ModernChat</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .login-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 40px 30px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            width: 100%;
            max-width: 400px;
            text-align: center;
            animation: slideUp 0.5s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .login-header {
            margin-bottom: 30px;
        }

        .login-header h1 {
            color: #1f2937;
            font-size: 2em;
            margin-bottom: 10px;
        }

        .login-header p {
            color: #6b7280;
            font-size: 1em;
        }

        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #374151;
            font-weight: 600;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            font-size: 14px;
            outline: none;
            transition: all 0.3s ease;
        }

        .form-group input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .login-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .login-btn:active {
            transform: translateY(0);
        }

        .error-message {
            background: #fee2e2;
            color: #dc2626;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }

        .admin-info {
            margin-top: 30px;
            padding: 20px;
            background: #f0f9ff;
            border-radius: 10px;
            border-left: 4px solid #0ea5e9;
        }

        .admin-info h3 {
            color: #0c4a6e;
            margin-bottom: 10px;
        }

        .admin-info p {
            color: #075985;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>🔐 Admin Girişi</h1>
            <p>ModernChat yönetim paneline erişim</p>
        </div>

        <div class="error-message" id="errorMessage"></div>

        <form method="POST">
            <div class="form-group">
                <label for="username">Kullanıcı Adı</label>
                <input type="text" id="username" name="username" required>
            </div>

            <div class="form-group">
                <label for="password">Şifre</label>
                <input type="password" id="password" name="password" required>
            </div>

            <button type="submit" class="login-btn">Giriş Yap</button>
        </form>

        <div class="admin-info">
            <h3>💡 Demo Bilgileri</h3>
            <p><strong>Kullanıcı Adı:</strong> admin<br>
            <strong>Şifre:</strong> admin123</p>
        </div>
    </div>

    {% if error %}
    <script>
        document.getElementById('errorMessage').style.display = 'block';
        document.getElementById('errorMessage').textContent = '{{ error }}';
    </script>
    {% endif %}
</body>
</html>
'''

# Ana sayfa (kullanıcı chat)
@app.route('/')
def index():
    return render_template_string(MAIN_TEMPLATE)

# Health check endpoint (Render için)
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'total_messages': len(messages)
    })

# Admin giriş sayfası
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basit doğrulama (üretimde güvenli hash kullanın)
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if username == 'admin' and password == admin_password:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='Hatalı kullanıcı adı veya şifre!')
    
    return render_template_string(LOGIN_TEMPLATE)

# Admin panel
@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    return render_template_string(ADMIN_TEMPLATE)

# Admin çıkış
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# Socket.IO olayları
@socketio.on('connect')
def handle_connect():
    print(f'Kullanıcı bağlandı: {request.sid}')
    emit('user_connected', {'user_id': request.sid}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Kullanıcı ayrıldı: {request.sid}')
    emit('user_disconnected', {'user_id': request.sid}, broadcast=True)

@socketio.on('user_message')
def handle_user_message(data):
    message_data = {
        'user_id': request.sid,
        'message': data['message'],
        'timestamp': data['timestamp'],
        'type': 'user'
    }
    
    # Mesajı kaydet
    messages.append(message_data)
    
    # Admin paneline gönder
    emit('user_message', message_data, broadcast=True)
    print(f"Kullanıcı mesajı: {data['message']}")

@socketio.on('admin_message')
def handle_admin_message(data):
    message_data = {
        'message': data['message'],
        'timestamp': data['timestamp'],
        'type': 'admin'
    }
    
    # Mesajı kaydet
    messages.append(message_data)
    
    # Tüm kullanıcılara gönder
    emit('admin_message', message_data, broadcast=True)
    print(f"Admin mesajı: {data['message']}")

@socketio.on('user_typing')
def handle_user_typing():
    emit('user_typing', broadcast=True, include_self=False)

@socketio.on('user_stop_typing')
def handle_user_stop_typing():
    emit('user_stop_typing', broadcast=True, include_self=False)

@socketio.on('admin_typing')
def handle_admin_typing():
    emit('admin_typing', broadcast=True, include_self=False)

@socketio.on('admin_stop_typing')
def handle_admin_stop_typing():
    emit('admin_stop_typing', broadcast=True, include_self=False)

# API endpoint'leri
@app.route('/api/messages')
def get_messages():
    return jsonify(messages)

@app.route('/api/stats')
def get_stats():
    return jsonify({
        'total_messages': len(messages),
        'user_messages': len([m for m in messages if m['type'] == 'user']),
        'admin_messages': len([m for m in messages if m['type'] == 'admin'])
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    
    print("🚀 ModernChat başlatılıyor...")
    print(f"📱 Port: {port}")
    print(f"🔧 Environment: {'Production' if not debug_mode else 'Development'}")
    print("🔧 Admin Panel: /admin")
    print("👤 Admin Bilgileri: admin / [ADMIN_PASSWORD env var]")
    print("-" * 50)
    
    socketio.run(app, debug=debug_mode, host='0.0.0.0', port=5000)