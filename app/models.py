from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Model người dùng"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship với ChatSession
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Mã hóa và lưu password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Kiểm tra password"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Trả về ID người dùng cho Flask-Login"""
        return str(self.id)
    
    def to_dict(self):
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class ChatSession(db.Model):
    """Model phiên chat"""
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_archived = db.Column(db.Boolean, default=False)
    
    # Relationship với ChatMessage
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def get_preview(self):
        """Lấy tin nhắn đầu tiên để làm preview"""
        first_message = ChatMessage.query.filter_by(session_id=self.id, sender='user').first()
        if first_message:
            return first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
        return "Cuộc trò chuyện mới"
    
    def to_dict(self):
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.id,
            'title': self.title or self.get_preview(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': len(self.messages),
            'preview': self.get_preview()
        }

class ChatMessage(db.Model):
    """Model tin nhắn chat"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id'), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # 'user' hoặc 'bot'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    message_type = db.Column(db.String(20), default='text')  # 'text', 'image', 'file'
    extra_data = db.Column(db.JSON, nullable=True)  # Lưu thêm thông tin như thời gian phản hồi, tokens sử dụng, etc.
    
    def to_dict(self):
        """Chuyển đổi thành dictionary"""
        return {
            'id': self.id,
            'sender': self.sender,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'message_type': self.message_type,
            'extra_data': self.extra_data
        }

def init_db(app):
    """Khởi tạo database"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
