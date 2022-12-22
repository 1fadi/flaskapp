from flask import render_template, redirect, url_for, request, current_app, make_response, abort, render_template
from . import moderate
from .. import db
from ..models import Comment, Permission, User, Role
from ..decorators import admin_required, permission_required
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries


@moderate.before_request
@login_required
@permission_required(Permission.MODERATE)
def before_request():
   if not current_user.is_anonymous and \
            not current_user.confirmed:
        abort(403)


@moderate.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                    'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' %
                        (query.statement, query.parameters, query.duration, query.context))
    return response


@moderate.route('/')
def _moderate():
    page = request.args.get('page', 1,  type=int)
    comments_24h = bool(request.cookies.get('comments_24h', ''))
    if comments_24h:
        since = datetime.now() - timedelta(hours=24)
        query = Comment.query.filter(Comment.timestamp >= since).order_by(Comment.timestamp.desc())
    else:
        query = Comment.query.order_by(Comment.timestamp.desc())
    pagination = query.paginate(
        page=page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments, pagination=pagination, page=page, comments_24h=comments_24h)


@moderate.route('/enable/<int:id>')
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('._moderate', page=request.args.get('page', 1, type=int)))


@moderate.route('/disable/<int:id>')
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('._moderate', page=request.args.get('page', 1, type=int)))


@moderate.route('/all_comments')
def all_comments():
    resp = make_response(redirect(url_for('._moderate')))
    resp.set_cookie('comments_24h', '', max_age=30*24*60*60)
    return resp


@moderate.route('/comments_24h')
def show_comments_24h():
    resp = make_response(redirect(url_for('._moderate')))
    resp.set_cookie('comments_24h', '1', max_age=30*24*60*60)
    return resp


@moderate.route('/all-mods')
@admin_required
def list_mods():
    page = request.args.get('page', 1, type=int)
    mod_role = Role.query.filter_by(name='Moderator').first()
    mods = User.query.filter(User.role == mod_role).order_by(User.username.desc())
    pagination = mods.paginate(page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'], error_out=False)
    mods = pagination.items
    return render_template('mods.html', mods=mods, pagination=pagination)
