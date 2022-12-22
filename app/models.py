from app.exceptions import ValidationError
import bleach
from markdown import markdown
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
import jwt
import datetime
from flask import current_app, request, url_for, g, has_request_context
import hashlib


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT,
                          Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                              Permission.MODERATE, Permission.ADMIN]
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @staticmethod
    def to_json(instance):
        json_follower = {
            'follower': instance.follower.username,
            'follower_url': url_for('api.get_user', id=instance.follower.id),
            'follower_since': instance.timestamp}
        return json_follower

    def __repr__(self):
        return f'Follower {self.follower} Followed {self.followed}'


class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    upvote = db.Column(db.Boolean, default=False)
    downvote = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))

    def __repr__(self):
        return f'Vote {self.user} {self.post if self.post else self.comment}'


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    votes = db.relationship('Vote', backref='post', lazy='dynamic')
    vote_count = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False)
    editable = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super(Post, self).__init__(**kwargs)
        if has_request_context():
            if url_for('api.new_post') in request.url:
                self.author = g.current_user
        self.author.upvote('post', self)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),
            'title': self.title,
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'comments_url': url_for('api.get_post_comments', id=self.id),
            'comments_count': self.comments.count(),
            'vote_count': self.vote_count
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        title = json_post.get('title')
        if title is None or title == '':
            raise ValidationError('your post requires a title')
        body = json_post.get('body')
        if body == '' or body is None:
            raise ValidationError('post does not have a body')
        return Post(title=title, body=body)

    @staticmethod
    def on_delete(target, value, oldvalue, initiator):
        if value:
            target.author = User.query.filter_by(username='deleted').first()
            target.body = '**[deleted]**'
            target.editable = False

    def __repr__(self):
        return f'<Post {self.id}>'


db.event.listen(Post.body, 'set', Post.on_changed_body)
db.event.listen(Post.deleted, 'set', Post.on_delete)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    votes = db.relationship('Vote', backref='comment', lazy='dynamic')
    vote_count = db.Column(db.Integer, default=0)
    editable = db.Column(db.Boolean, default=True)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'), tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id),
            'post_url': url_for('api.get_post', id=self.post_id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'vote_count': self.vote_count}
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body == '' or body is None:
            raise ValidationError('comment does not have a body')
        return Comment(body=body)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    votes = db.relationship('Vote', foreign_keys='Vote.user_id', backref='user', lazy='dynamic')
    server_own = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        self.follow(self)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, exp=3600):
        data = {
            'confirm': self.id,
            'exp': datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(seconds=exp)
        }
        return jwt.encode(data, current_app.config['SECRET_KEY'],
                          algorithm='HS256')

    def confirm(self, token):
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, exp=3600):
        data = {
            'reset': self.id,
            'exp': datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(seconds=exp)
        }
        return jwt.encode(data, current_app.config['SECRET_KEY'],
                          algorithm='HS256')

    @staticmethod
    def reset_password(token, new_password):
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                leeway=datetime.timedelta(seconds=1),
                algorithms=['HS256']
            )
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    def generate_email_change_token(self, new_email, exp=3600):
        data = {
            'change_email': self.id,
            'new_email': new_email,
            'exp': datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(seconds=exp)
        }
        return jwt.encode(data, current_app.config['SECRET_KEY'],
                          algorithm='HS256')

    def change_email(self, token):
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                leeway=datetime.timedelta(seconds=1),
                algorithms=['HS256']
            )
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        self.last_seen = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return f'{url}/{hash}?s={size}&d={default}&r={rating}'

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

                
    def generate_auth_token(self, exp):
        data = {
            'id': self.id,
            'exp': datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(seconds=exp)
        }
        return jwt.encode(data, current_app.config['SECRET_KEY'],
                          algorithm='HS256')
    
    @staticmethod
    def verify_auth_token(token):
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
        except:
            return None
        return User.query.get(data['id'])

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts', id=self.id),
            'post_count': self.posts.count()
        }
        return json_user
    
    def upvote(self, obj_type, obj):
        if obj_type not in ['comment', 'post']:
            raise ValueError('obj_type should be either "post" or "comment"')

        if self.vote_status(obj) != 'UP':
            vote = obj.votes.filter_by(user_id=self.id).first()
            if vote is not None:
                self.remove_vote(obj)
            vote = Vote(user_id=self.id, **{f"{obj_type}_id": obj.id})
            vote.upvote = True
            obj.vote_count += 1
            db.session.add_all([vote, obj])

    def downvote(self, obj_type, obj):
        if obj_type not in ['comment', 'post']:
            raise ValueError('obj_type should be either "post" or "comment"')

        if self.vote_status(obj) != 'DOWN':
            vote = obj.votes.filter_by(user_id=self.id).first()
            if vote is not None:
                self.remove_vote(obj)
            vote = Vote(user_id=self.id, **{f"{obj_type}_id": obj.id})
            vote.downvote = True
            obj.vote_count -= 1
            db.session.add_all([vote, obj])

    def remove_vote(self, obj):
        vote = obj.votes.filter_by(user_id=self.id).first()
        if vote is not None:
            if self.vote_status(obj) == 'UP':
                obj.vote_count -= 1
            if self.vote_status(obj) == 'DOWN':
                obj.vote_count += 1
            db.session.delete(vote)
            db.session.add(obj)

    def vote_status(self, obj):
        vote = obj.votes.filter_by(user_id=self.id).first()
        if vote is not None:
            if vote.upvote:
                return 'UP'
            elif vote.downvote:
                return 'DOWN'
        return None

    @staticmethod
    def create_deleted_user():  # deleted posts are going to be linked to this user so comments can still be shown/ read.
        u = User.query.filter_by(username='deleted').first()
        if u is None:
            u = User(username='deleted', email='deleted', password='None')  # this user is not accessible and can't login
        if not u.server_own:
            u.server_own = True
            db.session.add(u)
            db.session.commit()
        
    def __repr__(self):
        return f'<User {self.username}>'


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

    def vote_status(self, post):
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


login_manager.anonymous_user = AnonymousUser
