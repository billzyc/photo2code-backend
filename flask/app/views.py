from app import db, app, oauth
from app.models import CodeFile, User
from flask import Flask, jsonify, request, render_template, redirect, send_file, make_response
from io import BytesIO
from flask import redirect, url_for, session, render_template
from app.ocr import get_image_text
from app.utils.authenticate import authenticateToken, getProfileFromToken
from google.oauth2 import id_token
from google.auth.transport import requests

import jwt
import tempfile
import os
import datetime


@app.route('/')
def index():
    sess_dict = dict(session)
    if sess_dict.get('profile', None) != None:
        profile = sess_dict.get('profile', None)
        return f'Hello, you are logged in as {profile["first_name"]}!'
    return f'Hello, you are logged in as none!'


@app.route('/googleSignin', methods=['POST'])
def googleSignin():
    try:
        google_token = request.json['gToken']
        id_info = id_token.verify_oauth2_token(
            google_token, requests.Request(), os.environ.get('GOOGLE_CLIENT_ID', None))
        if id_info['email'] and id_info['email_verified']:
            user_profile = User.query.filter_by(email=id_info['email']).first()
            if user_profile is None:
                user_profile = User(
                    id_info['email'],
                    id_info['given_name'],
                    id_info['family_name']
                )
                db.session.add(user_profile)
                db.session.commit()

        token = jwt.encode({
            'user': id_info['email'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=16)
        },
            app.config['SECRET_KEY'])
        return jsonify({'token': token})

    except ValueError:
        # Invalid token
        return make_response('Unable to verify', 403, {'WWW-Authenticate': 'login error'})


@app.route('/profile', methods=['GET'])
@authenticateToken
def testauth():
    user_data = getProfileFromToken(request)
    user_profile = User.query.filter_by(email=user_data['user']).first()
    return jsonify({'user_profile': user_profile.getMap()})

@app.route('/upload', methods=['POST'])
@authenticateToken
def upload():
    file_name = request.values['name']
    image = request.files['image']
    language = request.values['language']
    user_data = getProfileFromToken(request)
    user_id = User.query.filter_by(email=user_data['user']).first().id
    try:
        if file_name and user_id and language and image is not None:
            text = get_image_text(image)
            new_file = CodeFile(
                title=file_name,
                content=text,
                language=language,
                user_id=user_id,
            )
            db.session.add(new_file)
            db.session.commit()
            return jsonify({'message': 'Success'})
        return jsonify({'message': 'Missing upload'}), 403
    except:
        return jsonify({'message': 'Invalid upload'}), 403
    
    
@app.route('/files', methods=['GET'])
@authenticateToken
def files():
    user_data = getProfileFromToken(request)
    user_id = User.query.filter_by(email=user_data['user']).first().id
    try:
        if user_id:
            files = CodeFile.query.filter_by(user_id = user_id).all()
            return jsonify({'message': 'Success'})
        return jsonify({'message': 'Missing upload'}), 403
    except:
        return jsonify({'message': 'Invalid upload'}), 403


# All routes below left for api testing


@app.route('/login')
def login():
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize():
    google = oauth.create_client('google')  # create the google oauth client
    token = (
        google.authorize_access_token()
    )  # Access token from google (needed to get user info)
    resp = google.get('userinfo')
    user_info = resp.json()
    user = oauth.google.userinfo()
    user_profile = User.query.filter_by(email=user_info['email']).first()
    if user_profile is None:
        user_profile = User(
            user_info['email'],
            user_info['given_name'],
            user_info['family_name']
        )
        db.session.add(user_profile)
        db.session.commit()
    session['profile'] = user_profile.getMap()
    session.permanent = (
        True  # make the session permanant so it keeps existing after broweser gets closed
    )
    return redirect('/')


@app.route('/test-get-image', methods=['GET'])
def test_get_file():
    sess_dict = dict(session)
    if sess_dict.get('profile', None) != None:
        user_id = sess_dict.get('profile', None)['id']
        file_title = (
            request.values['title']
            if request.values['title'] != None
            else request.args.get('title')
        )
        file_data = CodeFile.query.filter_by(
            user_id=user_id, title=file_title).first()
        if file_data != None:
            return send_file(
                BytesIO(bytes(file_data.content, 'utf-8')),
                attachment_filename=f'{file_data.title}.{file_data.language}',
                as_attachment=True,
            )
        else:
            return f'No file name {file_title}'
    return 'please login'


@app.route('/test-upload-image', methods=['GET', 'POST'])
def test_upload_image():
    sess_dict = dict(session)
    if sess_dict.get('profile', None) != None:
        if request.method == 'POST':
            user_id = sess_dict.get('profile', None)['id']
            if request.files and user_id != None:
                file_name = request.values['title']
                image = request.files['image']
                language = request.values['language']
                text = get_image_text(image)
                new_file = CodeFile(
                    title=file_name,
                    content=text,
                    language=language,
                    user_id=user_id,
                )
                db.session.add(new_file)
                db.session.commit()
                return 'uploaded'
        return render_template('public/upload_image.html')
    return 'please login'

@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')