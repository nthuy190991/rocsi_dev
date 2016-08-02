#!/usr/bin/env python
#-*- coding: utf-8 -*-

import time
import sys
import qi
from requests.exceptions import ConnectionError
import json
import requests
import HTMLParser
import random

class Banque(object):
    def __init__(self):

        self.appli = qi.Application(sys.argv)
        self.appli.start()
        self.session = self.appli.session

        self.logger = qi.Logger("Banque")

        self.ALTabletService = self.session.service("ALTabletService")
        self.tts = self.session.service('ALTextToSpeech')
        self.mem = self.session.service("ALMemory")

        self.ALTabletService.resetTablet()
        self.mem.insertData('Banque/onStart', 0)

    def speak(self, clientId, toSpeak):
        self.mem.raiseEvent('Banque/tts', toSpeak)
        self.write_logchat('Bot', toSpeak)
        self.tts.say(toSpeak)
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        global_var['tts'] = toSpeak
        try:
            self.logger.info("Robot: " + toSpeak)
        except UnicodeEncodeError as e:
            self.logger.info(e)

    def listen(self, clientId):
        startListening = 1
        self.mem.insertData('Banque/startListening', 1)
        while (startListening==1):
            startListening = self.mem.getData('Banque/startListening')
            time.sleep(0.2)
            pass

        stt = self.mem.getData('Banque/stt')
        stt = stt.replace(" ' ", "'")
        self.write_logchat('Human', stt)
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        global_var['stt'] = stt
        self.logger.info("Human: " + stt)
        self.mem.insertData('Banque/startListening', 1)
        return stt

    def write_logchat(self, actor, text):
        with open(self.log_filename, 'a') as f:
            try:
                text = text.encode('ascii', 'xmlcharrefreplace')
                f.write(actor + '\t: ' + text + '\n')
            except UnicodeDecodeError as e:
                self.logger.info("Error in write_logchat")
                self.logger.error(e)

    def quit(self):
        self.ALTabletService.resetTablet()
        self.logger.info('Reset Tablet')



    def callBanqueDialog(self, clientId):
        client_id       = ""
        conversation_id = ""
        question        = ""
        res             = ""

        while ((res != 'END') and ('Au revoir' not in res)):
            url = 'https://gateway.watsonplatform.net/dialog/api/v1/dialogs/97111df6-fc4d-4714-b409-34f0c483f5f4/conversation?input='
            if ((client_id != "") or (conversation_id != "")):
                question = self.listen(clientId)
                url = url + question
                url = url + '&client_id=' + str(client_id)
                url = url + '&conversation_id=' + str(conversation_id)

            r = requests.post(url, auth=('d2b39394-6660-4948-a9ed-74a70883f784', '4LSJkrIBBupP'))
            client_id       = json.loads(r.text)["client_id"]
            conversation_id = json.loads(r.text)["conversation_id"]

            if ((question != 'quitter') and (question != 'Quitter')):
                res = " ".join(json.loads(r.text)["response"])
            else:
                res = 'END'
            # self.logger.info(res)
            if (res != 'END'):
                self.speak(clientId, res)

    """
    def send2BanqueNodeRed(self, clientId, value):
        host = "https://banque-orange-node-red.mybluemix.net/pepper"
        payload = {'text':value, 'id':int(clientId)}
        self.logger.info("Value to send to Watson: " + value + ", id="+clientId)
        r = requests.get(host, params=payload)
        self.logger.info("Send to Watson OK")

        hparser = HTMLParser.HTMLParser()
        res = hparser.unescape(r.text)
        self.logger.info("Receive from Watson OK")
        if ((value=='Quitter') or (value=='quitter')):
            res = 'END'
        return res

    def getBankInfo(self, clientId):
        res = self.send2BanqueNodeRed(clientId, 'hello')
        self.speak(clientId, res)
        while ((res!='END') and ('Au revoir' not in res)):
            question = self.listen(clientId)
            question = question.replace(" ' ", "'")
            self.logger.info('Question: ' + question)
            res = self.send2BanqueNodeRed(clientId, question)
            if ((res!='END') and ('502' not in res)):
                self.speak(clientId, res)
            elif ('502' in res):
                self.speak(clientId, "Un erreur depuis le serveur du Watson s'est produit...")
            elif (res=='END'):
                self.speak(clientId, "Je quitte la banque...")

            try:
                self.logger.info('Response: '+res)
            except UnicodeEncodeError as e:
                self.logger.error(e)
    """

    """
    ==============================================================================
    Main program body with decision and redirection
    ==============================================================================
    """
    def runProgram(self, clientId):
        time.sleep(1)
        self.callBanqueDialog(clientId)
        self.quit_program(clientId)

    """
    Quit program
    """
    def quit_program(self, clientId):
        self.mem.raiseEvent('Banque/quit', 1)

    """
    Initialisation for global variables used by clientId
    """
    def global_var_init(self, clientId):
        self.global_vars.append (dict([
                                ('clientId', str(clientId)),
                                ('tts', ''),
                                ('stt', ''),
                                ]))
    """
    Run
    """
    def run(self):
        self.clientId = str(random.randint(1,1000000))
        self.log_filename = 'log_display/chat.log'
        self.global_vars = []
        self.global_var_init(self.clientId)

        # Initialisation chat.log for conversation display
        with open(self.log_filename, 'w') as f:
            f.write('')
        f.close()
        self.logger.info("Created " + self.log_filename)

        # Wait for onStart (Pepper reaches human for conversation)
        onStart = self.mem.getData('Banque/onStart')
        self.logger.info('Banque/onStart: ' + str(onStart))
        while (onStart==0):
            onStart = self.mem.getData('Banque/onStart')
            time.sleep(0.2)
            pass

        self.logger.info('Banque/onStart: ' + str(onStart))
        self.runProgram(self.clientId)

app = Banque()
app.run()
app.quit()

# End of Program #
