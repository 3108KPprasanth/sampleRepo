from flask import Flask

UPLOAD_FOLDER = 'DCP_Directory'

app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER