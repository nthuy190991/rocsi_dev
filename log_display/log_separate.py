# -*- coding: utf-8 -*-
"""
Created on Jul 29 23:43:38 2016

@author: thnguyen
"""

import os
import numpy as np
import time
from threading import Thread
from flask import Flask, request, render_template, send_from_directory

"""
==============================================================================
Flask Initialization
==============================================================================
"""
app  = Flask(__name__, static_url_path='')

@app.route('/')
def render_hmtl():
    return render_template('index.html')

@app.route('/css/<path:filename>')
def sendCSS(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'templates', 'css'), filename)

@app.route('/javascript/<path:filename>')
def sendJavascript(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'templates', 'javascript'), filename)

@app.route('/images/<path:filename>')
def sendImages(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'templates', 'images'), filename)

@app.route('/start', methods=['POST'])
def onStart():
    clientId = str(request.args.get('id')) # ClientId for creating new thread
    global_var_init(clientId)

    filename = 'chat.log'
    thread = Thread(target = extract, args = (filename, clientId), name='thread_'+clientId)
    thread.start()
    return "", 200

@app.route('/wait', methods=['POST'])
def waitForServerInput():
    clientId = str(request.args.get('id'))
    # global sendToHTML
    global global_vars
    global_var  = (item for item in global_vars if item["clientId"] == str(clientId)).next()

    # time.sleep(0.1)
    temp = global_var['sendToHTML']
    global_var['sendToHTML'] = ""
    return temp, 200

def read_log(filename):
    with open(filename, 'r') as f:
        log = f.read()
    f.close()
    return log

def extract(filename, clientId):
    # global lineNo
    # global sendToHTML

    global global_vars
    global_var  = (item for item in global_vars if item["clientId"] == str(clientId)).next()

    while True:
        logChat = read_log(filename)
        listItemChat = logChat.split('\n')[0:len(logChat.split('\n'))-1] # Not take the last item
        lineMaxNo = len(listItemChat)-1

        if (lineMaxNo > global_var['lineNo']):
            newLines = listItemChat[global_var['lineNo']+1:lineMaxNo+1]
            for line in newLines:
                global_var['sendToHTML'] = line
                print global_var['lineNo'], global_var['sendToHTML']
                global_var['lineNo'] += 1
                time.sleep(0.5)

"""
Initialisation for global variables used by clientId
"""
def global_var_init(clientId):
    global global_vars
    global_vars.append (dict([
                            ('clientId', str(clientId)),
                            ('lineNo', -1),
                            ('sendToHTML', ''),
                            ]))

"""
==============================================================================
    MAIN PROGRAM
==============================================================================
"""
global_vars = []
# sendToHTML = ''
# lineNo = -1

port = int(os.getenv('PORT', '9099'))
app.run(host = '0.0.0.0', port = port, threaded = True)
