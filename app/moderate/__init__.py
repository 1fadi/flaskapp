from flask import Blueprint

moderate = Blueprint('moderate', __name__)

from . import views
