from .. import db
from ..models import User, Permission, Follow
from flask import jsonify, g, request, url_for, current_app
from .decorators import permission_required
from . import api


@api.route('/users/<int:id>/followers/')
def get_user_followers(id):
    page = request.args.get('page', 1, type=int)
    user = User.query.get_or_404(id)
    pagination = user.followers.order_by(Follow.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    followers = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_followers', id=id, page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_followers', id=id, page=page+1)
    return jsonify({
        'followers': [Follow.to_json(follower) for follower in followers],
        'prev_url': prev,
        'next_url': next,
        'count': pagination.total})


@api.route('/follow/<int:id>', methods=['POST'])
@permission_required(Permission.FOLLOW)
def follow(id):
   u = User.query.get_or_404(id)
   g.current_user.follow(u)
   db.session.commit()
   return jsonify(Follow.to_json(u.followers.filter_by(follower=g.current_user).first())), 201

@api.route('/unfollow/<int:id>', methods=['DELETE'])
@permission_required(Permission.FOLLOW)
def unfollow(id):
    u = User.query.get_or_404(id)
    g.current_user.unfollow(u)
    db.session.commit()
    return '', 204
