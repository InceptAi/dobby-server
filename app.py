#!/usr/bin/env python

import urllib
import json
import os

from flask import Flask, request, make_response, abort, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename

import dobby


# Dobby stuff
pm = dobby.ParseManager(max_summaries=100)


# File upload stuff
UPLOAD_FOLDER = '/tmp/dobby/'
ALLOWED_EXTENSIONS = set(['json'])
SUMMARY_ID=0


# Flask app should start in global layout
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def create_dir_if_not_present(dirpath):
    try:
        os.makedirs(dirpath, exist_ok=True)
    except OSError:
        print("Error while creating dir:{0}. Error:{1}".format(dirpath, str(e)))
        return False
    else:
        return True

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
        print ("Invalid JSON input ({0})".format(str(e)))
        return False
    except (OSError, IOError) as e:
        print ("Cannot read file {file_to_read}.".format(file_to_read=filename))
        return None
    else:
        return True

def parse_summary(wireless_file=None, node_file=None,
                  tcploss_file=None, tcpmystery_file=None):
    stream_dict = {}
    if wireless_file:
        stream_dict['wireless_stream'] = open(wireless_file)
    if node_file:
        stream_dict['node_stream'] = open(node_file)
    if tcploss_file:
        stream_dict['tcploss_stream'] = open(tcploss_file)
    if tcpmystery_file:
        stream_dict['tcpmystery_stream'] = open(tcpmystery_file)
    return pm.parse_summary(**stream_dict)

def get_summary_type(summary_file):
    file_type = None
    if 'node' in summary_file.lower():
        file_type = 'node_file'
    elif 'wireless' in summary_file.lower():
        file_type = 'wireless_file'
    elif 'tcploss' in summary_file.lower():
        file_type = 'tcploss_file'
    elif 'tcpmystery' in summary_file.lower():
        file_type = 'tcpmystery_file'
    return file_type


@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/summaries/upload', methods=['GET', 'POST'])
def upload_summary():
    global SUMMARY_ID
    if request.method == 'POST':
        # check if the post request has the file part
        uploaded_files = request.files.getlist('summary_files')
        
        if not uploaded_files or len(uploaded_files) == 0:
            flash('No files')
            return redirect(request.url)
        
        files_dict = {}
        for uploaded_file in uploaded_files:
            if uploaded_file and allowed_file(uploaded_file.filename):
                filename = secure_filename(uploaded_file.filename)
                full_file_name = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_file.save(full_file_name)
                valid_summary_file = validate_json(full_file_name)
                if valid_summary_file:
                    summary_type = get_summary_type(full_file_name)
                    if summary_type:
                        files_dict[summary_type] = full_file_name
                else:
                    resp = make_response("Invalid summary format.Needs well formed json", 415)
                    return resp

        ns = parse_summary(**files_dict)
        print ("Latest Network Summary:{0}".format(str(ns)))
        resp = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename), 201)
        SUMMARY_ID = SUMMARY_ID + 1
        resp.headers['Location'] = '/summaries/' + str(SUMMARY_ID)
    return '''
        <!doctype html>
        <title>Upload new Files</title>
        <h1>Upload new Files</h1>
        <form method=post enctype=multipart/form-data>
        <p><input type=file name=summaryfiles multiple>
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
    dir_created = create_dir_if_not_present(app.config['UPLOAD_FOLDER'])
    if not dir_created:
        print("Unable to create dir:{0}".format(app.config['UPLOAD_FOLDER']))
        raise 
    port = int(os.getenv('PORT', 5000))
    print ("Starting app on port %d" % port)
    app.run(debug=True, port=port, host='0.0.0.0')
