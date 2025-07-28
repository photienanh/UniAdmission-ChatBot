from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from load_llm import initialize_gemini, ask_llm
from rag import initialize_rag
from models import db, User, ChatSession, ChatMessage, init_db
from datetime import datetime, timezone
import os
import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('tensorflow').setLevel(logging.ERROR)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chatbot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo database
init_db(app)

# Khởi tạo Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để sử dụng chatbot.'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, str(user_id))

# Khởi tạo model và RAG
gemini = initialize_gemini()

# Middleware để ngăn cache cho các trang đã đăng nhập
@app.after_request
def after_request(response):
    # Ngăn cache cho các trang yêu cầu authentication
    if request.endpoint in ['home', 'delete_account']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.json
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('home')})
            return redirect(url_for('home'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Tên đăng nhập hoặc mật khẩu không đúng'})
            flash('Tên đăng nhập hoặc mật khẩu không đúng')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.is_json:
            data = request.json
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            full_name = data.get('full_name')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
        
        # Kiểm tra xem user đã tồn tại chưa
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại'})
            flash('Tên đăng nhập đã tồn tại')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email đã tồn tại'})
            flash('Email đã tồn tại')
            return render_template('register.html')
        
        # Tạo user mới
        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        
        if request.is_json:
            return jsonify({'success': True, 'redirect': url_for('home')})
        return redirect(url_for('home'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    response = redirect(url_for('login'))
    # Thêm headers để ngăn cache
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/auth/check')
def check_auth():
    """Kiểm tra trạng thái đăng nhập"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'full_name': current_user.full_name
            }
        })
    return jsonify({'authenticated': False})

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    user_input = data.get('message', '')
    session_id = data.get('session_id')
    use_gemini = data.get('use_gemini', True)  # Thêm tham số chọn LLM
    use_web_search = data.get('use_web_search', False)  # Thêm tham số chọn web search
    
    # Tạo session mới nếu chưa có
    if not session_id:
        chat_session = ChatSession(user_id=current_user.id)
        db.session.add(chat_session)
        db.session.flush()  # Để lấy ID
        session_id = chat_session.id
    else:
        chat_session = db.session.get(ChatSession, session_id)
        if not chat_session or chat_session.user_id != current_user.id:
            return jsonify({'error': 'Session không hợp lệ'}), 403
    
    # Lưu tin nhắn của user
    user_message = ChatMessage(
        session_id=session_id,
        sender='user',
        content=user_input
    )
    db.session.add(user_message)
    
    try:
        # Tạo phản hồi từ bot với LLM được chọn và search method
        bot_response = ask_llm(user_input, gemini, session_id, use_gemini, use_web_search)
        
        # Lưu phản hồi của bot
        bot_message = ChatMessage(
            session_id=session_id,
            sender='bot',
            content=bot_response['response']
        )
        db.session.add(bot_message)
        
        # Cập nhật thời gian session
        chat_session.updated_at = datetime.now(timezone.utc)
        
        # Tự động tạo title cho session từ tin nhắn đầu tiên
        if not chat_session.title:
            chat_session.title = user_input[:50] + "..." if len(user_input) > 50 else user_input
        
        db.session.commit()
        
        return jsonify({
            'response': bot_response['response'],
            'session_id': session_id,
            'message_id': bot_message.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Lỗi xử lý: {str(e)}'}), 500

@app.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Lấy danh sách phiên chat của user"""
    sessions = ChatSession.query.filter_by(
        user_id=current_user.id,
        is_archived=False
    ).order_by(ChatSession.updated_at.desc()).all()
    
    return jsonify([session.to_dict() for session in sessions])

@app.route('/sessions/<session_id>/messages', methods=['GET'])
@login_required
def get_session_messages(session_id):
    """Lấy tin nhắn của một phiên chat"""
    chat_session = db.session.get(ChatSession, session_id)
    
    if not chat_session or chat_session.user_id != current_user.id:
        return jsonify({'error': 'Session không tồn tại'}), 404
    
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
    
    return jsonify({
        'session': chat_session.to_dict(),
        'messages': [message.to_dict() for message in messages]
    })

@app.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    """Xóa một phiên chat"""
    chat_session = db.session.get(ChatSession, session_id)
    
    if not chat_session or chat_session.user_id != current_user.id:
        return jsonify({'error': 'Session không tồn tại'}), 404
    
    db.session.delete(chat_session)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/sessions', methods=['POST'])
@login_required
def create_session():
    """Tạo phiên chat mới"""
    data = request.json
    title = data.get('title', 'Cuộc trò chuyện mới')
    
    chat_session = ChatSession(user_id=current_user.id, title=title)
    db.session.add(chat_session)
    db.session.commit()
    
    return jsonify(chat_session.to_dict())

@app.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    """Xóa tài khoản người dùng"""
    if request.method == 'GET':
        return render_template('delete_account.html')
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        confirm = data.get('confirm')
        password = data.get('password')
        
        # Kiểm tra xác nhận
        if confirm != 'DELETE':
            return jsonify({'success': False, 'message': 'Vui lòng nhập "DELETE" để xác nhận'})
        
        # Kiểm tra mật khẩu
        if not current_user.check_password(password):
            return jsonify({'success': False, 'message': 'Mật khẩu không đúng'})
        
        try:
            user_id = current_user.id
            
            # Xóa tất cả tin nhắn của user
            ChatMessage.query.filter(
                ChatMessage.session_id.in_(
                    db.session.query(ChatSession.id).filter(ChatSession.user_id == user_id)
                )
            ).delete(synchronize_session=False)
            
            # Xóa tất cả phiên chat của user
            ChatSession.query.filter(ChatSession.user_id == user_id).delete()
            
            # Đăng xuất user
            logout_user()
            
            # Xóa user
            User.query.filter(User.id == user_id).delete()
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Tài khoản đã được xóa thành công'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Có lỗi xảy ra: {str(e)}'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)