from flask import Blueprint, render_template
from .models import User

users = Blueprint('users', __name__)

@users.route('/user/<string:username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)