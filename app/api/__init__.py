from flask import Blueprint

api = Blueprint('api', __name__)

from . import authentication, posts, comments, users, errors, followers
