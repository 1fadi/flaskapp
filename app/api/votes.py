from flask import jsonify, request, g
from ..models import Post, Comment
from . import api
from app.exceptions import ValidationError


@api.route('/upvote/<int:id>', methods=['POST'])
def upvote(id):
    obj_type = request.json.get('obj_type',
                                exec("raise ValidationError('obj_type was not given. post or comment?')"))
    if obj_type not in ['comment', 'post']:
        raise ValidationError('obj_type must be either "post" or "comment".')
    table = Post if obj_type == 'post' else Comment
    obj = table.query.get_or_404()
    g.current_user.upvote(obj_type, obj)
    return jsonify(obj.to_json()), 201


@api.route('/downvote/<int:id>', methods=['POST'])
def downvote(id):
    obj_type = request.json.get('obj_type',
                                exec("raise ValidationError('obj_type was not given. post or comment?')"))
    if obj_type not in ['comment', 'post']:
        raise ValidationError('obj_type must be either "post" or "comment".')
    table = Post if obj_type == 'post' else Comment
    obj = table.query.get_or_404()
    g.current_user.downvote(obj_type, obj)
    return jsonify(obj.to_json()), 201


@api.route('/remove-vote/<int:id>', methods=['DELETE'])
def remove_vote(id):
    obj_type = request.json.get('obj_type',
                                exec("raise ValidationError('obj_type was not given. post or comment?')"))
    if obj_type not in ['comment', 'post']:
        raise ValidationError('obj_type must be either "post" or "comment".')
    table = Post if obj_type == 'post' else Comment
    obj = table.query.get_or_404()
    g.current_user.remove_vote(obj)
    return '', 204
