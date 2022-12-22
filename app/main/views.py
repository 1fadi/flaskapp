from flask import render_template, session, redirect, url_for, flash, abort, request, current_app
from flask import make_response, jsonify
from . import main
from .forms import PostForm, EditProfileForm, EditProfileAdminForm, CommentForm
from .. import db
from ..models import User, Role, Post, Permission, Comment, Vote
from flask_login import login_required, current_user
from ..decorators import admin_required, permission_required
from datetime import timedelta, datetime
from flask_sqlalchemy import get_debug_queries
import json


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                    'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' %
                        (query.statement, query.parameters, query.duration, query.context))
    return response
                            

@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(title=form.title.data,
                    body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.filter(Post.deleted != True).order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           show_followed=show_followed, pagination=pagination)


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user.server_own:
        abort(404)
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False
    )
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts, pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1) + f"#{comment.id}")
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
                current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    top_comments = bool(request.cookies.get('top_comments', ''))
    if top_comments:
        query = post.comments.order_by(Comment.vote_count.desc())
    else:
        query = post.comments.order_by(Comment.timestamp.desc())
    pagination = query.paginate(
        page=page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form, comments=comments,
                           pagination=pagination, request=request, top_comments=top_comments)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    if not post.editable:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.title.data = post.title
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None or user.server_own:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(f'You are now following {username}!')
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None or user.server_own:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('you don\'t follow this user')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'you do not follow {username} anymore.')
    return redirect(url_for('.user', username=username))


@main.route('/user/<username>/followers')
def followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user,title='Followers of', pagination=pagination,
                           follows=follows, endpoint='.followers')


@main.route('/user/<username>/followed_by')
def followed_by(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title='Followed by', pagination=pagination,
                           follows=follows, endpoint='.followed_by')


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp


@main.route('/post/<int:post_id>/comments/<int:id>', methods=['GET', 'POST'])
def edit_comment(id, post_id):
    page = request.args.get('page')
    post = Post.query.get_or_404(post_id)
    comment = post.comments.filter_by(id=id).first()
    if current_user != comment.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = CommentForm()
    if form.validate_on_submit():
        comment.body = form.body.data
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been updated.')
        return redirect(url_for('.post', id=comment.post_id, page=page) + f"#{comment.id}")
    form.body.data = comment.body
    return render_template('edit_comment.html', posts=[post], form=form)


@main.route('/upvote/<obj_type>/<int:id>', methods=['GET', 'POST'])
@login_required
def upvote(id, obj_type):
    if obj_type not in ['post', 'comment']:
        abort(404)
    query = Post.query if obj_type == 'post' else Comment.query
    obj = query.get_or_404(id)
    status = None
    if obj.editable:
        if current_user.vote_status(obj) == 'UP':
            current_user.remove_vote(obj)
        else:
            current_user.upvote(obj_type, obj)
            status = 'UP'
        db.session.commit()

    if request.is_json and request.method == 'POST':
        id = json.loads(request.data).get('id')
        print(id, obj.vote_count)
        return jsonify({'id': id, 'data': obj.vote_count, 'status': status})

    elif request.method == 'GET':
        return redirect(url_for('.post', id=id if obj_type == 'post' else obj.post_id))


@main.route('/downvote/<obj_type>/<int:id>', methods=['GET', 'POST'])
@login_required
def downvote(id, obj_type):
    if obj_type not in ['post', 'comment']:
        abort(404)
    query = Post.query if obj_type == 'post' else Comment.query
    obj = query.get_or_404(id)
    status = None
    if obj.editable:
        if current_user.vote_status(obj) == 'DOWN':
            current_user.remove_vote(obj)
        else:
            current_user.downvote(obj_type, obj)
            status = 'DOWN'
        db.session.commit()

    if request.is_json and request.method == 'POST':
        id = json.loads(request.data).get('id')
        return jsonify({'id': id, 'data': obj.vote_count, 'status': status})

    elif request.method == 'GET':
        return redirect(url_for('.post', id=id if obj_type == 'post' else obj.post_id))


@main.route('/shutdown')
def shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/upvoted', methods=['GET'])
@login_required
def upvoted():
    page = request.args.get('page', 1, type=int)
    query = current_user.votes.filter(Vote.comment == None).filter_by(upvote=True)
    pagination = query.paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = [vote.post for vote in pagination.items if vote.post.author != current_user]
    return render_template('upvoted_posts.html', posts=posts,
                           pagination=pagination)


@main.route('/post/<int:id>/new-comment')
def new_comments(id):
    resp = make_response(redirect(url_for('.post', id=id)))
    resp.set_cookie('top_comments', '', max_age=30*24*60*60)
    return resp


@main.route('/post/<int:id>/top-comments')
def top_comments(id):
    resp = make_response(redirect(url_for('.post', id=id)))
    resp.set_cookie('top_comments', '1', max_age=30*24*60*60)
    return resp


@main.route('/delete/post/<int:id>', methods=['GET', 'POST'])
def delete_post(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    post.deleted = True
    db.session.add(post)
    db.session.commit()
    flash('Your post has been deleted.')
    return redirect(request.referrer)


@main.route('/delete/comment/<int:id>', methods=['GET', 'POST'])
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    if current_user != comment.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted.')
    return redirect(request.referrer)


@main.route('/test123', methods=['GET', 'POST'])
def test123():
    if request.is_json:
        if request.method == 'POST':
            text = json.loads(request.data).get('id')
            return jsonify({'data': text})
