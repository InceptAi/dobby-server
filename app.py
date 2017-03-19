#!/usr/bin/env python

import urllib
import json
import os

from flask import Flask, request, make_response, abort, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename


#import my package
#import dobby

# File upload stuff
UPLOAD_FOLDER = '/tmp/dobby/'
ALLOWED_EXTENSIONS = set(['json'])
SUMMARY_ID=0


# Flask app should start in global layout
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_json(filename):
    try:
        print ("Trying to load:{0}".format(filename))
        with open(filename) as file_stream:
            summary_json = json.load(file_stream)
    #except json.decoder.JSONDecodeError as e:
    except ValueError as e:
        print ("Invalid JSON input ({0})".format(str(e.message)))
        return False
    except (OSError, IOError) as e:
        print ("Cannot read file {file_to_read}.".format(file_to_read=filename))
        return None
    else:
        return True



@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/summaries/upload', methods=['GET', 'POST'])
def upload_summary():
    global SUMMARY_ID
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        uploaded_file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if uploaded_file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            path_to_save_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print ("Path to save file:{0}".format(path_to_save_file))
            uploaded_file.save(path_to_save_file)
            #uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            valid_summary_file = validate_json(path_to_save_file)
            if valid_summary_file:
                resp = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename), 201)
                SUMMARY_ID = SUMMARY_ID + 1
                resp.headers['Location'] = '/summaries/' + str(SUMMARY_ID)
            else:
                resp = make_response("Invalid summary format. Needs well formed json", 415)
            return resp
    return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <p><input type=file name=file>
        <input type=submit value=Upload>
        </form>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = makeWebhookResult(req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def makeWebhookResult(req):
    if req.get("result").get("action") != "shipping.cost":
        return {}
    result = req.get("result")
    parameters = result.get("parameters")
    zone = parameters.get("shipping-zone")

    cost = {'Europe':100, 'North America':200, 'South America':300, 'Asia':400, 'Africa':500}

    speech = "The cost of shipping to " + zone + " is " + str(cost[zone]) + " euros."

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        #"data": {},
        # "contextOut": [],
        "source": "apiai-onlinestore-shipping"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print ("Starting app on port %d" % port)

    app.run(debug=True, port=port, host='0.0.0.0')
