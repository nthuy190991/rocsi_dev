#!/usr/bin/env python
#-*- coding: utf-8 -*-

import time
import sys, os
import qi
import numpy as np
import cv2
from threading import Thread
from watson_developer_cloud import NaturalLanguageClassifierV1
import face_api
import emotion_api
from read_xls import read_xls
import xlrd
import operator
import utils
from requests.exceptions import ConnectionError
import json
import requests
import HTMLParser
import random
import httplib

class RecognitionApp(object):
    def __init__(self):

        self.appli = qi.Application(sys.argv)
        self.appli.start()
        self.session = self.appli.session

        self.logger = qi.Logger("RecognitionApp")

        self.ALVideoDevice = self.session.service('ALVideoDevice')

        self.ALVideoDevice.unsubscribe("CameraTop_0")
        self.ALVideoDevice.setParameter(0, 14, 2)
        self.handle = self.ALVideoDevice.subscribeCamera("CameraTop", 0, 2, 11, 5)
        self.logger.info('Subscribe ALVideoDevice')

        self.ALTabletService = self.session.service("ALTabletService")
        self.tts = self.session.service('ALTextToSpeech')
        self.mem = self.session.service("ALMemory")

        # Train database, set up Parameters and NLC
        self.ip_robot = "192.168.1.11"
        self.app_id = "rocsi2016_dev-8d93d3"
        self.prepare()

    def speak(self, clientId, toSpeak):
        self.mem.raiseEvent('FacialRecognition/tts', toSpeak)
        self.write_logchat('Bot', toSpeak)
        self.tts.say(toSpeak)
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        global_var['tts'] = toSpeak

        try:
            self.logger.info("Robot: " + toSpeak)
        except UnicodeEncodeError as e:
            self.logger.info("Robot: ")
            self.logger.error(e)

    def listen(self, clientId):
        startListening = 1
        self.mem.insertData('FacialRecognition/startListening', 1)
        # t0 = time.time()
        while (startListening==1):
            startListening = self.mem.getData('FacialRecognition/startListening')
            time.sleep(0.2)
            pass

            # if (time.time()-t0>10):
            #     self.mem.insertData('FacialRecognition/stt', '@')
            #     break

        stt = self.mem.getData('FacialRecognition/stt')
        stt = stt.replace(" ' ", "'")
        stt = stt.replace(" - ", "-")
        self.write_logchat('Human', stt)
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        global_var['stt'] = stt

        self.mem.insertData('FacialRecognition/startListening', 1)

        try:
            self.logger.info("Human: " + stt)
        except UnicodeEncodeError as e:
            self.logger.info("Human: ")
            self.logger.error(e)
        return stt

    def question(self, clientId, question):
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

        self.speak(clientId, question) # Pepper asks a question
        response = self.listen(clientId) # Listen for an answer from User

        # if (response == '@'):
        #     result = self.question(clientId, "Je ne vous entends pas, veuillez repeeter")

        if (response == 'oui' or response == 'non'):
            responseYesOrNo = response
        elif (response == 'Oui' or response == 'Non'):
            responseYesOrNo = response
        else:
            response = response.replace(" ' ", "'")
            responseYesOrNo = self.send2WatsonNLCClassifier(clientId, response)

        if not(global_var['flag_quit']):
            if (responseYesOrNo == 'oui' or responseYesOrNo == 'Oui'):
                result = 1
            elif (responseYesOrNo == 'non' or responseYesOrNo == 'Non'):
                result = 0
            elif (responseYesOrNo=='not_relevant'):
                result = self.question(clientId, "Votre reponse n'est pas pertinente, veuillez re-repondre")

            try:
                self.logger.info("Response(" + question + "): " + responseYesOrNo + ' ('+ str(result) + ')')
            except UnicodeEncodeError as e:
                self.logger.info("Response(...): " + responseYesOrNo + ' ('+ str(result) + ')')
                self.logger.error(e)

        return result

    def send2WatsonNLCClassifier(self, clientId, response):
        self.logger.info('Send to NLC:' + response)
        try:
            classes = self.nlc.classify('1c40d6x83-nlc-137', response)
            responseYesOrNo = classes["top_class"]
            self.logger.info('Response from NLC: ' + responseYesOrNo)
            return responseYesOrNo

        except ConnectionError as e:
            self.simple_message(clientId, 'no_internet')
            self.speak(clientId, "veuillez repondre oui ou non")
            responseYesOrNo = self.listen(clientId)
            self.logger.error(e)
            return responseYesOrNo

    def write_logchat(self, actor, text):
        try:
            with open(self.log_filename, 'a') as f:
                text = text.encode('ascii', 'xmlcharrefreplace')
                f.write(actor + '\t: ' + text + '\n')
            f.close()
        except UnicodeDecodeError as e:
            self.logger.info("Error in write_logchat")
            self.logger.error(e)

    """
    Preparation for program
    """
    def prepare(self):
        # Parameters
        self.cascPath     = "haarcascade_frontalface_default.xml" # path to Haar-cascade training xml file
        self.imgPath      = "html/face_database_pepper/" # path to database of faces
        self.xls_filename = 'formation.xls' # Excel file contains Formation information
        self.log_filename = 'log_display/chat.log'
        self.imgSuffix    = '.png' # image file extention
        self.thres        = 70    # Distance threshold for recognition
        self.wait_time    = 4      # Time needed to wait for recognition
        self.nb_max_times = 4      # Maximum number of times of good recognition counted in 3 seconds (manually determined, and depends on camera)
        self.nb_img_max   = 5      # Number of photos needs to be taken for each user

        # Haar cascade detector used for face detection
        self.faceCascade = cv2.CascadeClassifier(self.cascPath)

        # For face recognition we use the Local Binary Pattern Histogram (LBPH) Face Recognizer
        self.recognizer  = cv2.createLBPHFaceRecognizer()
        self.list_nom    = []

        # Call the get_images_and_labels function and get the face images and the corresponding labels
        self.logger.info("Obtenu Images et Labels a partir de database...")
        images, labels = self.get_images_and_labels(self.imgPath)

        # Perform the training
        self.recognizer.train(images, np.array(labels))
        self.logger.info("L'apprentissage a ete bien fini...")

        # Natural Language Classifier (name: oui_non_pepper)
        self.nlc = NaturalLanguageClassifierV1(
                                          username = "ddc8decd-5b31-4dca-9395-e7bbf95246c0",
                                          password = "I2RXPXZL0eCP")

        self.mem.insertData('FacialRecognition/name', '')
        self.mem.insertData('FacialRecognition/name2', '')
        self.mem.insertData('FacialRecognition/stt', '')
        self.mem.insertData('FacialRecognition/tts', '')
        self.mem.insertData('FacialRecognition/onStart', 0)

        # Questions and Messages
        self.tb_messages = read_xls("TextToSpeakRobot_new.xls", 0) # Read Excel file
        self.text_id_idx = self.tb_messages[0][:].index('Text_ID')
        self.messages = []
        for idx in range(0, len(self.tb_messages)):
            question = self.tb_messages[idx][self.text_id_idx]
            self.messages.append(question)
        # self.logger.info(self.messages)

        # Initialisation chat.log for conversation display
        with open(self.log_filename, 'w') as f:
            f.write('')
        f.close()
        self.logger.info("Created " + self.log_filename)

    """
    Using Haar Cascade detector to detect faces from a grayscale image
    """
    def detectFaces(self, gray):
        faces = self.faceCascade.detectMultiScale(
            gray,
            scaleFactor  = 1.1,
            minNeighbors = 5,
            minSize      = (100, 100),
            flags        = cv2.cv.CV_HAAR_SCALE_IMAGE
        )
        return faces

    """
    Get all images in database alongside with their labels
    """
    def get_images_and_labels(self, path):
        image_paths = [os.path.join(path, f) for f in os.listdir(path)]
        images   = [] # images will contains face images
        labels   = [] # labels which are assigned to the image

        for image_path in image_paths:
            # Read the image
            image = cv2.imread(image_path)
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Get the label of the image
            nom = os.path.split(image_path)[1].split(".")[0]
            if nom not in self.list_nom:
                self.list_nom.append(nom)

            nbr = self.list_nom.index(nom) + 1
            images.append(gray)
            labels.append(nbr)

        return images, labels

    """
    Recognition on Video
    """
    def recognize(self, clientId, frame):

        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Convert frame to a grayscale image
        faces = self.detectFaces(gray) # Detect faces on grayscale image

        self.logger.info('Found ' + str(len(faces)) + ' faces in video')
        # self.mem.insertData('FacialRecognition/faces', str(faces))

        if (len(faces)>=1):
            if (len(faces)>1): # Consider only the biggest face appears in the video
                w_vect = faces.T[2,:]
                h_vect = faces.T[3,:]
                x0, y0, w0, h0 = faces[np.argmax(w_vect*h_vect)]
            elif (len(faces)==1): # If there is only one face
                x0, y0, w0, h0 = faces[0]

            global_var['image_save'] = gray[y0 : y0 + h0, x0 : x0 + w0]
            # self.logger.info(len(global_var['image_save']))
            nbr_predicted, conf = self.recognizer.predict(global_var['image_save']) # Predict function
            # self.mem.insertData('FacialRecognition/size(image_save)', len(global_var['image_save']))
            # self.logger.info(nbr_predicted)

            nom = self.list_nom[nbr_predicted-1] # Get resulting namesa
            # self.logger.info('Reconnu ' + nom + ', ' + str(conf))
            self.mem.insertData('FacialRecognition/name', nom)
            self.mem.insertData('FacialRecognition/conf', conf)

            if (conf < self.thres): # if recognizing distance is less than the predefined threshold
                if not global_var['flag_disable_detection']:
                    txt = nom + ', distance: ' + str(conf)[0:5]
                    self.logger.info(txt)

                    nom = ''
                    txt = ''
                global_var['tb_nb_times_recog'][nbr_predicted-1] += 1 # Increase nb of recognize times

    def runStream(self, clientId):
        self.logger.info("Start capturing images...")
        self.ALVideoDevice.releaseImage(self.handle)

        global flag_display
        flag_display = False
        thread_display = Thread(target=self.displayTablet)
        thread_display.start()

        while True:
            data = self.ALVideoDevice.getImageRemote(self.handle)
            if (data):
                width, height, nbLayers = data[0:3] # from Documentation

                data_uint8 = np.fromstring(str(data[6]), np.uint8) # take value array from string
                image_reshape = np.reshape(data_uint8, (nbLayers, width, height), order='F') # reshape array to a matrix
                self.imgRGB = np.dstack((image_reshape[2].T,image_reshape[1].T,image_reshape[0].T))

                flag_display = True
                # filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "html", "out.png")
                # cv2.imwrite(filepath, imgRGB)
                self.recognize(clientId, self.imgRGB)

            # self.ALTabletService.showImageNoCache('http://198.18.0.1/apps/track_and_record-bdd23d/out.png')
            time.sleep(0.5)
            self.ALVideoDevice.releaseImage(self.handle)

    def displayTablet(self):
        time.sleep(0.1)
        self.logger.info('Display video')
        while True:
            if (flag_display):
                # filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "html", "out.png")
                filepath = 'html/out.png'
                cv2.imwrite(filepath, self.imgRGB)
                # self.mem.raiseEvent('FacialRecognition/video', 1)
                #self.ALTabletService.showImageNoCache('http://198.18.0.1/apps/show_image_id/out.png')
                # self.ALTabletService.showImage('http://198.18.0.1/img/help_charger.png')
                time.sleep(0.5)
                # self.mem.insertData('ShowImage/show', 0)


    def quit(self):
        self.ALVideoDevice.unsubscribe(self.handle)
        self.logger.info('Unsubscribe ALVideoDevice')
        self.ALTabletService.resetTablet()
        self.logger.info('Reset Tablet')

    """
    Ask a name or id as a string
    """
    def askName(self, clientId, flag):
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        if (flag):
            self.simple_message(clientId, 'ask_id')

        # res = self.listen(clientId)
        startListening = 1
        self.mem.raiseEvent('FacialRecognition/startListening', 1)
        while (startListening==1):
            startListening = self.mem.getData('FacialRecognition/startListening')
            pass

        # name = self.mem.getData('FacialRecognition/name')
        name = self.mem.getData('FacialRecognition/stt')
        name = name.replace(" ' ", "'")
        name = name.replace(" - ", "-")
        self.write_logchat('Human', name)
        self.mem.insertData('FacialRecognition/startListening', 1)
        self.logger.info("Name: " + name)

        # TODO: get response from Tablet Keyboard
        # while (global_var['respFromHTML']==""):
        #     pass
        # res = global_var['respFromHTML']
        # global_var['respFromHTML'] = ""
        return name


    """
    Definition of used yes-no questions in program
    """
    def ask_get_info_formation(self, clientId):
        resp = self.yes_or_no(clientId, 'ask_get_info_formation')
        return resp

    def detect_face_attributes(self, clientId):
        resp = self.yes_or_no(clientId, 'detect_face_attributes')
        return resp

    def verify_recog(self, clientId, name):
        self.speak(clientId, "Bonjour "+name)
        resp = self.yes_or_no(clientId, "verify_recog")
        return resp

    def allow_streaming_video(self, clientId):
        resp = self.yes_or_no(clientId, 'allow_streaming_video')
        return resp

    def deja_photos(self, clientId):
        resp = self.yes_or_no(clientId, 'deja_photos')
        return resp

    def allow_take_photos(self, clientId):
        resp = self.yes_or_no(clientId, 'allow_take_photos')
        return resp

    def validate_photo(self, clientId):
        resp = self.yes_or_no(clientId, 'validate_photo')
        return resp

    def allow_get_info_formation_by_id(self, clientId):
        resp = self.yes_or_no(clientId, 'allow_get_info_formation_by_id')
        return resp

    def quit_formation(self, clientId):
        resp = self.yes_or_no(clientId, 'quit_formation')
        return resp

    def validate_reidf(self, clientId, name):
        self.speak(clientId, "Bonjour "+name)
        resp = self.yes_or_no(clientId, 'validate_reidf')
        return resp

    """
    Yes/No question as an asking/answering by dialogue
    """
    def yes_or_no(self, clientId, question_id):
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        if (not global_var['flag_quit']): # Put in If-condition to allow interrupt when Esc is pressed
            ind = self.messages.index(question_id)
            message = self.tb_messages[ind][self.tb_messages[0][:].index('Text')]

            #TODO: new new
            message_selected = self.textSelect(message)

            resp = self.question(clientId, message_selected)
            if (resp==1):
                confirm = self.tb_messages[ind][self.tb_messages[0][:].index('Confirmation_oui')]
            elif (resp==0):
                confirm = self.tb_messages[ind][self.tb_messages[0][:].index('Confirmation_non')]

            confirm_selected = self.textSelect(confirm)
            if 'goto' not in confirm_selected:
                self.speak(clientId, confirm_selected)
            else:
                self.logger.info(confirm_selected)
                # new_question_id = confirm.replace("goto(","")
                # new_question_id = new_question_id.replace(")","")
                # self.logger.info('goto: '+new_question_id)
                # self.yes_or_no(clientId, new_question_id)
            return resp
        else:
            return -1

    """
    Simple message as a notification speech
    """
    def simple_message(self, clientId, message_id):
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        if (not global_var['flag_quit']): # Put in If-condition to allow interrupt when Esc is pressed
            ind = self.messages.index(message_id)
            message = self.tb_messages[ind][self.tb_messages[0][:].index('Text')]

            #TODO: new new
            message_selected = self.textSelect(message)
            self.speak(clientId, message_selected)

    """
    Text Randomly Select (separated by '/')
    """
    def textSelect(self, message):
        # message     = message.encode('ascii', 'xmlcharrefreplace')
        messages    = message.split('/')
        nb_messages = len(messages)
        idx         = random.randint(0, nb_messages-1)
        message_selected = messages[idx]
        return message_selected


    """
    Formation API
    """
    def jsonProcess(self, jsonstr):
        data = json.loads(jsonstr)
        self.logger.info(data)
        # data = eval(jsonstr)
        return data

    def callFormationAPI(self, clientId, date, name, firstname):
        self.logger.info('Call Formation API with: '+ str(date) + '&' + name + '&' + firstname)
        headers = {
            'Content-Type': 'application/json',
        }
        name = name.replace(' ', '%20')
        firstname = firstname.replace(' ', '%20')

        url = "/rocsi/public/api/v1/formation/date/" + date + "/participant/name/" + name + ("/" + firstname if firstname!='' else "")
        self.logger.info("url=" + url)
        status_code = 0
        try:
            conn = httplib.HTTPConnection('192.168.1.10:8080') # API server address
            conn.request("GET", url, "", headers)
            response = conn.getresponse()
            result = response.read()
            status_code = response.status

            self.logger.info('Receive response from Formation API')
            self.logger.info(status_code)
            try:
                self.logger.info(result)
            except UnicodeEncodeError as e:
                self.logger.error(e)
            conn.close()
        except Exception as e:
            self.logger.error(e)
            self.simple_message(clientId, 'formation_api_connection_problem')
            result = ''

        if (result!='' and status_code==200):
            res = self.jsonProcess(result)
            personId   = firstname + '.' + name
            titre      = res[0]['form_titre']
            date_debut = res[0]['form_date_debut']
            date_fin   = res[0]['form_date_fin']
            salle      = res[0]['form_salle']
            salle_code = res[0]['form_salle_code']
            chemin     = res[0]['form_salle_indication']

            return personId, titre, date_debut, date_fin, salle, salle_code, chemin, True
        elif (status_code==404):
            self.logger.info('Person not found')
            self.simple_message(clientId, 'formation_api_not_found')
            return '', '', '', '', '', '', '', False
        else:
            self.logger.info('Return empty values from Formation API')
            return '', '', '', '', '', '', '', False



    """
    Send infos from Formation API to Watson
    """
    def sendAPIInfo2Watson(self, clientId, date, name, firstname):

        personId, titre, date_debut, date_fin, salle, salle_code, chemin, resReceived = self.callFormationAPI(clientId, date, name, firstname)
        host = "https://pepper-centre-formation.mybluemix.net/pepper"

        if (resReceived):
            payload = {'id':clientId, 'titre':titre, 'date_debut':date_debut, 'date_fin':date_fin, 'salle':salle, 'chemin':chemin} # pas encore envoyer la personId
            r = requests.get(host, params=payload)
            self.logger.info("Send infos to Watson OK")
        else:
            self.logger.info('No info to send')
            payload = {'id':clientId, 'text':'nothing to send'}

        r = requests.get(host, params=payload)
        try:
            self.logger.info(payload)
            self.logger.info(r.text)
        except UnicodeEncodeError as e:
            self.logger.error(e)

        hparser = HTMLParser.HTMLParser()
        res = hparser.unescape(r.text)
        return res

    """
    Send question to Watson for Formation Dialogue
    """
    def send2WatsonDialog(self, clientId, value):
        self.logger.info("Value to send to Watson: " + value)

        host = "https://pepper-centre-formation.mybluemix.net/pepper"
        payload = {'text':value, 'id':clientId}
        r = requests.get(host, params=payload)
        self.logger.info("Send to Watson OK")

        hparser = HTMLParser.HTMLParser()
        res = hparser.unescape(r.text)
        # self.logger.info(utils.replace_accents(res))
        self.logger.info("Receive from Watson OK")

        video_flag = False

        if ((value=='Quitter') or (value=='quitter')):
            res = 'END'
        elif ('rejoindre la salle' in res):
            video_flag = True
            n_salle = res[24:27] #TODO: to be changed
            self.logger.info("Afficher la video pour le chemin a la salle " + n_salle)
            self.mem.raiseEvent('FacialRecognition/videoFormation', n_salle)
        else: # la video sera arretee quand pepper repond a question suivante
            video_flag = False
            self.logger.info("Stopper la video pour le chemin")
            # self.mem.raiseEvent('FacialRecognition/videoFormation', 'STOP')  #TODO: stop video
        return res, video_flag

    """
    Get Formation info for a recognized or username-known user
    """
    def getFormationInfo(self, clientId, name):
        resp = self.ask_get_info_formation(clientId)
        if (resp==1):
            global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

            global_var['flag_disable_detection'] = 1 # Disable the detection when entering Formation page
            global_var['flag_enable_recog']      = 0

            # res = self.send2WatsonDialog(clientId, 'hello')
            res = self.sendAPIInfo2Watson(clientId, '2016-07-19', name, '')
            self.speak(clientId, res)

            while ((res!='END') and ('Au revoir' not in res)):
                question = self.listen(clientId)
                question = question.replace(" ' ", "'")
                self.logger.info('Question: ' + question)
                res, video_flag = self.send2WatsonDialog(clientId, question)

                if ((res!='END') and ('502' not in res)):
                    self.speak(clientId, res)
                elif ('502' in res):
                    self.speak(clientId, "Un erreur depuis le serveur du Watson s'est produit...")
                elif (res=='END'):
                    self.speak(clientId, "Je quitte la formation...")

                try:
                    self.logger.info('Response: '+res)
                except UnicodeEncodeError as e:
                    self.logger.error(e)

            # tb_formation = read_xls(self.xls_filename, 0) # Read Excel file which contains Formation info
            # mail = self.reform_username(name) # Find email from name
            # self.simple_message(clientId, "Bonjour " + str(name))
            #
            # if (mail == '.'):
            #     text2 = "Votre information n'est pas disponible !"
            #     text3 = "Veuillez contacter formation@orange.com"
            # else:
            #     mail_idx = tb_formation[0][:].index('Mail')
            #
            #     # Get mail list
            #     mail_list = []
            #     for idx in range(0, len(tb_formation)):
            #         mail_list.append(tb_formation[idx][mail_idx])
            #
            #     ind = mail_list.index(mail) # Find user in xls file based on his/her mail
            #     date = xlrd.xldate_as_tuple(tb_formation[ind][tb_formation[0][:].index('Date du jour')],0)
            #     # date = tb_formation[ind][tb_formation[0][:].index('Date du jour')]
            #     #
            #     # (dd, mm, yyyy) = date.split('/')
            #     # dd   = int(dd)
            #     # mm   = int(mm)
            #     # yyyy = int(yyyy)
            #     # dt   = datetime.datetime(yyyy, mm, dd)
            #
            #     text2 = "Bienvenue a la formation de "+str(tb_formation[ind][tb_formation[0][:].index('Prenom')])+" "+str(tb_formation[ind][tb_formation[0][:].index('Nom')] + ' !')
            #     text3 = "Vous avez un cours de " + str(tb_formation[ind][tb_formation[0][:].index('Formation')]) + ", dans la salle " + str(tb_formation[ind][tb_formation[0][:].index('Salle')]) + ", a partir du " + "{}/{}/{}".format(str(date[2]), str(date[1]), str(date[0]))
            #     # text3 = "Vous avez un cours de " + str(tb_formation[ind][tb_formation[0][:].index('Formation')]) + ", dans la salle " + str(tb_formation[ind][tb_formation[0][:].index('Salle')]) + ", a partir du " + date
            # self.simple_message(clientId, text2 + ' ' + text3)

            time.sleep(2)
            self.return_to_recog(clientId) # Return to recognition program immediately or 20 seconds before returning
        else:
            self.return_to_recog(clientId) # Return to recognition program immediately or 20 seconds before returning

    """
    Return to recognition program after displaying Formation
    """
    def return_to_recog(self, clientId):
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        if not global_var['flag_quit']:

            resp_quit_formation = self.quit_formation(clientId)
            if (resp_quit_formation == 0):
                time.sleep(5) # wait for more 5 seconds before quitting

            global_var['flag_disable_detection']  = 0
            global_var['flag_enable_recog']       = 1
            global_var['flag_ask']                = 1
            global_var['flag_reidentify']         = 0

    # """
    # Find valid username
    # """
    # def reform_username(self, name):
    #     if (name=='huy' or name=='GGQN0871'):
    #         firstname    = 'thanhhuy'
    #         lastname     = 'nguyen'
    #         email_suffix = '@orange.com'
    #
    #     elif (name=='cleblain' or name=='JLTS5253'):
    #         firstname    = 'christian'
    #         lastname     = 'leblainvaux'
    #         email_suffix = '@orange.com'
    #
    #     elif (name=='catherine' or name=='lemarquis' or name=='ECPI6335'):
    #         firstname    = 'catherine'
    #         lastname     = 'lemarquis'
    #         email_suffix = '@orange.com'
    #
    #     elif (name=='ionel'):
    #         firstname    = 'ionel'
    #         lastname     = 'tothezan'
    #         email_suffix = '@orange.com'
    #
    #     else:
    #         firstname    = ''
    #         lastname     = ''
    #         email_suffix = ''
    #
    #     mail = firstname + '.' + lastname + email_suffix
    #     return mail


    """
    ==============================================================================
    Taking photos
    ==============================================================================
    """
    def take_photos(self, clientId, step_time, flag_show_photos):

        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

        name = self.askName(clientId, 1)

        image_to_paths = [self.imgPath+str(name)+"."+str(i)+self.imgSuffix for i in range(self.nb_img_max)]

        self.logger.info(image_to_paths)

        if os.path.exists(image_to_paths[0]):
            self.logger.info("Les fichiers avec le nom " + str(name) + " existent deja")
            b = self.yes_or_no(clientId, "Les fichiers avec le nom " + str(name) + " existent deja, ecraser ces fichiers ?")
            if (b==1):
                self.logger.info("Ecraser les fichiers avec le nom " + str(name))
                image_del_paths = [os.path.join(self.imgPath, f) for f in os.listdir(self.imgPath) if f.startswith(name)]
                for image_del_path in image_del_paths:
                    os.remove(image_del_path)
            elif (b==0):
                name = self.askName(clientId, 1)
                image_to_paths = [self.imgPath + str(name)+"."+str(i)+self.imgSuffix for i in range(self.nb_img_max)]

        # text  = 'Prenant photos'
        # text2 = 'veuillez patienter... '
        # self.simple_message(clientId, text+', '+text2)
        self.simple_message(clientId, 'taking_photos')

        nb_img = 0
        while (nb_img < self.nb_img_max):
            image_path = image_to_paths[nb_img]
            # if global_var['image_save']!=0:
            #     self.logger.info(len(global_var['image_save']))

            cv2.imwrite(image_path, global_var['image_save'])
            self.logger.info("Enregistrer photo " + image_path + ", nb de photos prises : " + str(nb_img+1))
            # global_var['text3'] = str(nb_img+1) + ' ont ete prises, reste a prendre : ' + str(self.nb_img_max-nb_img-1)
            nb_img += 1
            time.sleep(step_time)

        # Display photos that have just been taken
        if flag_show_photos:
            # thread_show_photos = Thread(target = self.show_photos, args = (clientId, name), name = 'thread_show_photos_' + clientId)
            # thread_show_photos.start()
            self.show_photos(clientId, name)

        time.sleep(1)

        # Allow to retake photos and validate after finish taking
        thread_retake_validate_photos = Thread(target = self.retake_validate_photos, args = (clientId, step_time, flag_show_photos, name), name = 'thread_retake_validate_photos_' + clientId)
        thread_retake_validate_photos.start()

    """
    Retaking and validating photos
    """
    def retake_validate_photos(self, clientId, step_time, flag_show_photos, name):

        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

        # Ask users if they want to change photo(s) or validate them
        b = self.validate_photo(clientId)
        image_to_paths = [self.imgPath+str(name)+"."+str(j)+self.imgSuffix for j in range(self.nb_img_max)]
        self.logger.info(image_to_paths)

        while (b==0):
            # TODO: allow user to speak id of photos or click on the tablet

            # self.simple_message(clientId, "Veuillez repondre quelles photos que vous voulez changer ?")
            #
            # while (global_var['stt'] == ""):
            #     pass
            # nb = global_var['stt']
            # global_var['stt'] = ""
            #
            # a = [str(i) for i in range(0, self.nb_img_max)]
            # if ('-' in nb):
            #     nb2 = ''
            #     for i in range(int(nb[0]), int(nb[2])+1):
            #         nb2 = nb2 + str(i)
            #     nb = nb2
            # elif (nb=='*' or nb=='tous'):
            #     nb=''
            #     for j in range(0, self.nb_img_max):
            #         nb = nb+str(j+1)
            # elif any(nb[idx] in a for idx in range(0, len(nb))): # If there is any number in string
            #     nb2 = ''
            #     for j in range(0, len(nb)):
            #         if (nb[j] in a):
            #             nb2 = nb2 + nb[j]
            #     nb = nb2
            # else:
            #     self.logger.info('Fatal error: invalid response')
            #     nb = ''
            #
            # nb = utils.str_replace_chars(nb, [',',';','.',' '], ['','','',''])

            nb = "12345" # temporary set

            if (nb!=""):
                str_nb = ""
                for j in range(0, len(nb)):
                    if (j==len(nb)-1):
                        str_nb = str_nb + "'" + nb[j] + "'"
                    else:
                        str_nb = str_nb + "'" + nb[j] + "', "

                # self.simple_message(clientId, 'Vous souhaitez changer les photos: ' + str_nb + ' ?')
                self.simple_message(clientId, 'change_photos')
                self.speak(clientId, str_nb)

                # text  = 'Re-prenant photos'
                # text2 = 'Veuillez patienter... '
                # self.simple_message(clientId, text+', '+text2)
                self.simple_message(clientId, 'retaking_photos')

            # Reset display
            self.show_photos(clientId, '')
            time.sleep(3)

            for j in range(0, len(nb)):
                self.logger.info(str(j) + ' ont ete prises, reste a prendre : ' + str(len(nb)-j))
                time.sleep(step_time)
                # self.logger.info("Reprendre photo " + str(nb[j]))
                image_path = image_to_paths[int(nb[j])-1]
                os.remove(image_path) # Remove old image
                cv2.imwrite(image_path, global_var['image_save'])
                self.logger.info("Enregistrer photo " + image_path + ", nb de photos prises : " + str(nb[j]))

            a = self.yes_or_no(clientId, 'review_photos')

            if (a==1):
                # thread_show_photos2 = Thread(target = self.show_photos, args = (clientId, name), name = 'thread_show_photos2_'+clientId)
                # thread_show_photos2.start()
                self.show_photos(clientId, name)
                time.sleep(3)

            b = self.validate_photo(clientId)
            if (b==1):
                break
        # End of While(b==0)

        # Update recognizer after taking and validating photos
        self.logger.info("Mettre a jour le recognizer...")
        images, labels = self.get_images_and_labels(self.imgPath)
        self.recognizer.update(images, np.array(labels))
        self.logger.info("Recognizer a ete mis a jour...")

        global_var['flag_enable_recog'] = 1  # Re-enable recognition
        global_var['flag_ask'] = 1 # Reset asking


    """
    Display photos that have just been taken, close them if after 5 seconds or press any key
    """
    def show_photos(self, clientId, name):
        # image_to_paths = [self.imgPath + str(name) + "." + str(j) + self.imgSuffix for j in range(self.nb_img_max)]
        self.logger.info("show_photos (name: " + name + ")")
        # self.mem.removeData('FacialRecognition/name2')
        # time.sleep(1)
        self.mem.raiseEvent('FacialRecognition/name2', name)

        url = ''
        image_to_paths = [str(name) + "." + str(j) + self.imgSuffix for j in range(self.nb_img_max)]
        for img_path in image_to_paths:
            alt  = str(name) + ' - Photos'
            link = "http://" + self.ip_robot + "//apps/" + self.app_id + "/face_database_pepper/" + img_path
            url = url + '&emsp;<img src="'+ link.replace(' ', '%20') + '" class="w3-border w3-padding-4 w3-padding-tiny" alt="'+ alt +'" style="width:128px;">'

        # url = url + '&emsp;<a href=' + name.replace(' ', '%20') + '><img src="' + data + '" class="img-thumbnail" alt="photo"  style="width:128px;"></a>'
        self.logger.info('show_photos: ' + url)
        self.write_logchat('show_photos', url)


    """
    ==============================================================================
    Re-identification: when a user is not recognized or not correctly recognized
    ==============================================================================
    """
    def re_identify(self, clientId, nb_time_max, name0):

        # self.simple_message(clientId, u'Veuillez rapprocher vers la camera, ou bouger votre tete...')
        self.simple_message(clientId, 'message_reidf')

        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

        tb_old_name    = np.chararray(shape=(nb_time_max+1), itemsize=10) # All of the old recognition results, which are wrong
        tb_old_name[:] = ''
        tb_old_name[0] = name0

        nb_time = 0
        global_var['flag_enable_recog'] = 1
        global_var['flag_reidentify']   = 1
        global_var['flag_ask'] = 0

        while (nb_time < nb_time_max):
            time.sleep(self.wait_time) # wait until after the re-identification is done
            name1 = global_var['nom'] # New result

            if np.all(tb_old_name != name1) and (global_var['flag_recog']==1):
                self.logger.info('Essaie ' + str(nb_time+1) + ': reconnu comme ' + str(name1))

                resp = self.validate_reidf(clientId, str(name1))
                if (resp == 1):
                    result = 1
                    name = name1
                    break
                else:
                    result = 0
                    nb_time += 1
                    tb_old_name[nb_time] = name1

            elif (global_var['flag_recog']==0):
                self.logger.info('Essaie ' + str(nb_time+1) + ': personne inconnue')
                result = 0
                nb_time += 1

        if (result==1): # User confirms that the recognition is correct now
            global_var['flag_enable_recog'] = 0
            global_var['flag_wrong_recog']  = 0

            self.get_face_emotion_api_results(clientId)
            time.sleep(1)
            self.getFormationInfo(clientId, name)

        else: # Two time failed to recognized
            global_var['flag_enable_recog'] = 0 # Disable recognition when two tries have failed
            # self.simple_message(clientId, 'Desolee je vous reconnait pas, veuillez me donner votre identifiant')
            self.simple_message(clientId, 'not_recognized_ask_id')

            name = self.askName(clientId, 0)
            if os.path.exists(self.imgPath+str(name)+".0"+self.imgSuffix): # Assume that user's face-database exists if the photo 0.png exists
                self.speak(clientId, 'Bonjour '+ str(name))
                self.simple_message(clientId, 'conseil_change_photos')
                flag_show_photos = 1
                step_time = 1

                self.show_photos(clientId, name)

                time.sleep(1)
                thread_retake_validate_photos2 = Thread(target = self.retake_validate_photos, args = (clientId, step_time, flag_show_photos, name), name = 'thread_retake_validate_photos2_'+clientId)
                thread_retake_validate_photos2.start()
            else:
                self.logger.info("Les photos correspondant au nom " + str(name) + " n'existent pas")
                self.simple_message(clientId, 'photos_not_exist')
                time.sleep(1)
                global_var['flag_take_photo']  = 1  # Enable photo taking

        global_var['flag_reidentify']   = 0

    """
    ==============================================================================
    Face and Emotion API
    ==============================================================================
    """
    def retrieve_face_emotion_att(self, clientId):
        # global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        # t0 = time.time()

        filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "html", "out2.png")
        cv2.imwrite(filepath, self.imgRGB)

        # t1 = time.time()
        # self.logger.info('Face API: Write image in ' + str(t1-t0))
        try:
            # Face API
            faceResult = face_api.faceDetect(None, filepath, None)
            # self.logger.info(faceResult)

            # t2 = time.time()
            # self.logger.info('Face API: Call face_api.faceDetect in ' + str(t2-t1))

            # Emotion API
            emoResult = emotion_api.recognizeEmotion(None, filepath, None)
            # self.logger.info(emoResult)

            # t3 = time.time()
            # self.logger.info('Face API: Call emotion_api.recognizeEmotion in ' + str(t3-t2))

            # Results
            self.logger.info('Found {} '.format(len(faceResult)) + ('faces' if len(faceResult)!=1 else 'face'))
            # t4 = time.time()
            # self.logger.info('Face API: Receive results from API ' + str(t4-t1))

            nb_faces = len(faceResult)
            tb_face_rect = [{} for ind in range(nb_faces)]
            tb_age       = ['' for ind in range(nb_faces)]
            tb_gender    = ['' for ind in range(nb_faces)]
            tb_glasses   = ['' for ind in range(nb_faces)]
            tb_emo       = ['' for ind in range(len(emoResult))]

            if (len(faceResult)>0 and len(emoResult)>0):
                ind = 0
                for currFace in faceResult:
                    faceRectangle       = currFace['faceRectangle']
                    faceAttributes      = currFace['faceAttributes']
                    # self.logger.info(faceAttributes)

                    tb_face_rect[ind]   = faceRectangle
                    # tb_age[ind]         = str(faceAttributes['age'])
                    tb_age[ind]         = str(int(round(faceAttributes['age'])))
                    tb_gender[ind]      = faceAttributes['gender']
                    tb_glasses[ind]     = faceAttributes['glasses']
                    ind += 1

                # self.logger.info(tb_age)

                ind = 0
                for currFace in emoResult:
                    # self.logger.info(currFace)
                    tb_emo[ind] = max(currFace['scores'].iteritems(), key=operator.itemgetter(1))[0]
                    ind += 1

                # faceWidth  = np.zeros(shape=(nb_faces))
                # faceHeight = np.zeros(shape=(nb_faces))
                # for ind in range(nb_faces):
                #     faceWidth[ind]  = tb_face_rect[ind]['width']
                #     faceHeight[ind] = tb_face_rect[ind]['height']
                # ind_max = np.argmax(faceWidth*faceHeight.T)

                self.logger.info('Finish face_api and emotion_api')
                # t5 = time.time()
                # self.logger.info('Face API: Finish API ' + str(t5-t4))
                return tb_age, tb_gender, tb_glasses, tb_emo
            else:
                return 'N/A','N/A','N/A','N/A'

        except ConnectionError as e:
            self.simple_message(clientId, 'no_internet')
            self.logger.error(e)
            return None, None, None, None

    """
    Return face and emotion api by tts
    """
    def speak_api_results(self, clientId, age, gender, emotion, glasses):
        titre = ('Monsieur' if gender =='male' else 'Madame')
        ind   = self.messages.index('face_api_result')
        text  = self.tb_messages[ind][self.tb_messages[0][:].index('Text')]
        text  = utils.str_replace_chars(text, ['$age', '$gender', '$emotion', '$glasses'], [age, titre, emotion, glasses])
        self.speak(clientId, text)

    """
    Yield Face and Emotion API results
    """
    def get_face_emotion_api_results(self, clientId):

        resp = self.detect_face_attributes(clientId)
        # t0 = time.time()
        if (resp==1):

            self.logger.info('Calling APIs to retrieve facial and emotional attributes, please wait')
            tb_age, tb_gender, tb_glasses, tb_emo = self.retrieve_face_emotion_att(clientId)

            self.logger.info(tb_age)
            self.logger.info(tb_gender)
            self.logger.info(tb_glasses)
            self.logger.info(tb_emo)

            if (([tb_age, tb_gender, tb_glasses, tb_emo] != ['N/A','N/A','N/A','N/A']) and ([tb_age, tb_gender, tb_glasses, tb_emo] != [None, None, None, None])):
                # Translate emotion to french
                tb_emo_eng = ['happiness', 'sadness', 'surprise', 'anger', 'fear',
                              'contempt', 'disgust', 'neutral']
                tb_emo_correspond = ['joyeux', 'trist', 'surprise',
                                     'en colere', "d'avoir peur", ' mepris',
                                     'degout', 'neutre']

                # Translate glasses to french
                tb_glasses_eng = ['NoGlasses', 'ReadingGlasses',
                                  'sunglasses', 'swimmingGoggles']
                tb_glasses_correspond = ['ne portez pas de lunettes',
                                         'portez des lunettes',
                                         'portez des lunettes de soleil',
                                         'portez des lunettes de natation']

                for ind in range(len(tb_age)):
                    glasses_str = tb_glasses_correspond[tb_glasses_eng.index(tb_glasses[ind])]
                    emo_str     = tb_emo_correspond[tb_emo_eng.index(tb_emo[ind])]
                    # text = "D'apres mon analyse, " + ('Monsieur' if tb_gender[ind] =='male' else 'Madame') + \
                    #     ", vous avez " + tb_age[ind] + " ans, votre etat emotionnel est " + emo_str + \
                    #     ", et vous " + glasses_str
                    # self.speak(clientId, text)
                    self.speak_api_results(clientId, tb_age[ind], tb_gender[ind], emo_str, glasses_str)

            elif [tb_age, tb_gender, tb_glasses, tb_emo] == ['N/A','N/A','N/A','N/A']:
                self.logger.info('Found no faces')
                # self.simple_message(clientId, 'Desolee, aucun visage trouvee')
                self.simple_message(clientId, 'no_face_found')
        # t1 = time.time()
        # self.logger.info('Face API: get_face_emotion_api_results() in ' + str(t1-t0))

    """
    ==============================================================================
    Main program body with decision and redirection
    ==============================================================================
    """
    def runProgram(self, clientId):
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()

        time.sleep(1)
        # Autorisation to begin Streaming Video
        resp_allow_streaming_video = self.allow_streaming_video(clientId)
        time.sleep(0.2)
        self.logger.info(str(resp_allow_streaming_video))

        if (resp_allow_streaming_video == 1):
            global_var['key']       = 0
            global_var['flag_quit'] = 0

            # Thread of stream
            thread_video = Thread(target = self.runStream, args = (clientId,), name = 'thread_stream_' + clientId)
            thread_video.start()

            start_time   = time.time() # For recognition timer (will reset after each 3 secs)
            time_origine = time.time() # For display (unchanged)

            """
            Permanent loop
            """
            self.logger.info("Start recognition...")
            while True:
                """
                Decision part
                """
                if not (global_var['flag_quit']):
                    elapsed_time = time.time() - start_time
                    if ((elapsed_time > self.wait_time) and global_var['flag_enable_recog']): # Identify after each 3 seconds
                        if (max(global_var['tb_nb_times_recog']) >= self.nb_max_times/2): # If the number of times recognized is big enough
                            global_var['flag_recog']  = 1 # Known Person
                            global_var['flag_ask']    = 0
                            global_var['nom'] = self.list_nom[np.argmax(global_var['tb_nb_times_recog'])] # Get name of recognizing face
                            self.logger.info('Reconnu: ' + global_var['nom'])
                            if (not global_var['flag_reidentify']):

                                res_verify_recog = self.verify_recog(clientId, global_var['nom'])
                                if (res_verify_recog==1):
                                    global_var['key'] = ord('y')
                                elif (res_verify_recog==0):
                                    global_var['key'] = ord('n')

                        else: # If the number of times recognized anyone from database is too low
                            global_var['flag_recog'] = 0 # Unknown Person
                            global_var['nom'] = '@' # '@' is for unknown person

                            if (not global_var['flag_reidentify']):
                                global_var['flag_ask'] = 1
                                # self.simple_message(clientId, u'Desolee, je ne vous reconnait pas')
                                self.simple_message(clientId, 'not_recognized')
                                time.sleep(0.25)

                        global_var['tb_nb_times_recog'].fill(0) # reinitialize with all zeros

                        start_time = time.time()  # reset timer

                    """
                    Redirecting user based on recognition result and user's status (already took photos or not) in database
                    """
                    count_time = time.time() - time_origine
                    if (count_time <= self.wait_time): # Do nothing if count_time < 3 seconds
                        if (global_var['flag_quit']):
                            break
                    if (count_time >= 1200):
                        self.logger.info('The program has been executed more than 20 minutes...')
                        global_var['flag_quit'] = 1
                        break

                    else:
                        """
                        Start Redirecting after the first 3 seconds
                        """
                        if (global_var['flag_quit']):
                            break
                        if (global_var['flag_recog']==1):
                            if (global_var['key']==ord('y') or global_var['key']==ord('Y')): # User chooses Y to go to Formation page
                                global_var['flag_wrong_recog']  = 0
                                self.get_face_emotion_api_results(clientId)

                                time.sleep(1)
                                self.getFormationInfo(clientId, global_var['nom'])
                                global_var['key'] = 0

                            if (global_var['key']==ord('n') or global_var['key']==ord('N')): # User confirms that the recognition result is wrong by choosing N
                                global_var['flag_wrong_recog'] = 1
                                global_var['flag_ask'] = 1
                                global_var['key'] = 0

                        if ((global_var['flag_recog'] and global_var['flag_wrong_recog']) or (not global_var['flag_recog'])): # Not recognized or not correctly recognized
                            if (global_var['flag_ask']):

                                global_var['flag_enable_recog'] = 0 # Disable recognition in order not to recognize while re-identifying or taking photos

                                resp_deja_photos = self.deja_photos(clientId) # Ask user if he has already had a database of face photos

                                if (resp_deja_photos==1): # User has a database of photos
                                    global_var['flag_ask'] = 0

                                    name0 = global_var['nom']   # Save the recognition result, which is wrong, in order to compare later
                                    nb_time_max = 5             # Number of times to retry recognize

                                    thread_reidentification = Thread(target = self.re_identify, args = (clientId, nb_time_max, name0), name = 'thread_reidentification_'+clientId)
                                    thread_reidentification.start()

                                elif (resp_deja_photos == 0): # User doesnt have a database of photos
                                    resp_allow_take_photos = self.allow_take_photos(clientId)

                                    if (resp_allow_take_photos==1): # User allows to take photos
                                        global_var['flag_take_photo'] = 1  # Enable photo taking

                                    else: # User doesnt want to take photos
                                        global_var['flag_take_photo'] = 0
                                        res = self.allow_get_info_formation_by_id(clientId)
                                        if (res==1): # User agrees to go to Formation in providing his id manually
                                            name = self.askName(clientId, 1)
                                            self.getFormationInfo(clientId, name)

                                        else: # Quit if user refuses to provide manually his id (after all other functionalities)
                                            break
                                    resp_allow_take_photos = 0
                                resp_deja_photos = 0
                            global_var['flag_ask'] = 0

                        if (global_var['flag_take_photo']):# and (not flag_quit)):
                            step_time  = 1 # Interval of time (in second) between two times of taking photo
                            thread_take_photo = Thread(target = self.take_photos, args = (clientId, step_time, 1), name = 'thread_take_photo_'+clientId)
                            thread_take_photo.start()
                            global_var['tb_nb_times_recog'] = np.empty(len(self.list_nom)+1) # Extend the list with one more value for the new face
                            global_var['tb_nb_times_recog'].fill(0) # reinitialize the table with all zeros
                            global_var['flag_take_photo'] = 0
            # End Of While-loop

        elif (resp_allow_streaming_video == 0):
            res = self.allow_get_info_formation_by_id(clientId)
            if (res==1): # User agrees to go to Formation in providing his id manually
                name = self.askName(clientId, 1)
                self.getFormationInfo(clientId, name)

        # Exit the program
        self.quit_program(clientId)

    """
    Quit program
    """
    def quit_program(self, clientId):
        self.simple_message(clientId, 'finish')
        self.mem.raiseEvent('FacialRecognition/quit', 1)

    """
    Initialisation for global variables used by clientId
    """
    def global_var_init(self, clientId):
        self.global_vars.append (dict([
                                ('clientId', str(clientId)),
                                ('flag_recog', 0),
                                ('flag_take_photo', 0),
                                ('flag_wrong_recog', 0),
                                ('flag_enable_recog', 1),
                                ('flag_disable_detection', 0),
                                ('flag_quit', 0),
                                ('flag_ask', 0),
                                ('flag_reidentify', 0),
                                ('image_save', 0),
                                ('key', 0),
                                ('tts', ''),
                                ('stt', ''),
                                ('tb_nb_times_recog', np.zeros(len(self.list_nom))),
                                ('nom', '')
                                ]))
    """
    Run
    """
    def run(self):
        self.clientId = str(random.randint(1,1000000))
        self.global_vars = []
        self.global_var_init(self.clientId)

        onStart = self.mem.getData('FacialRecognition/onStart')
        self.logger.info('FacialRecognition/onStart: ' + str(onStart))
        while (onStart==0):
            onStart = self.mem.getData('FacialRecognition/onStart')
            time.sleep(0.2)
            # self.logger.info('wait FacialRecognition/onStart')
            pass

        self.logger.info('FacialRecognition/onStart: ' + str(onStart))
        self.runProgram(self.clientId)


app = RecognitionApp()
app.run()
app.quit()


# End of Program #
