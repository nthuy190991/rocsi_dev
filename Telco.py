#!/usr/bin/env python
#-*- coding: utf-8 -*-

import time
import sys
import qi
from requests.exceptions import ConnectionError
import json
import requests
import random

class Telco(object):
    def __init__(self):

        self.appli = qi.Application(sys.argv)
        self.appli.start()
        self.session = self.appli.session

        self.logger = qi.Logger("Telco")

        self.ALTabletService = self.session.service("ALTabletService")
        self.tts = self.session.service('ALTextToSpeech')
        self.mem = self.session.service("ALMemory")

        self.ALTabletService.resetTablet()
        self.mem.insertData('Telco/onStart', 0)

    def speak(self, clientId, toSpeak):
        self.mem.raiseEvent('Telco/tts', toSpeak)
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
        self.mem.insertData('Telco/startListening', 1)
        while (startListening==1):
            startListening = self.mem.getData('Telco/startListening')
            time.sleep(0.2)
            pass

        stt = self.mem.getData('Telco/stt')
        stt = stt.replace(" ' ", "'")
        self.write_logchat('Human', stt)
        global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
        global_var['stt'] = stt
        self.logger.info("Human: " + stt)
        self.mem.insertData('Telco/startListening', 1)
        return stt

    # def write_logchat(self, actor, text):
    #     with open(self.log_filename, 'a') as f:
    #         try:
    #             text = text.encode('ascii', 'xmlcharrefreplace')
    #             f.write(actor + '\t: ' + text + '\n')
    #         except UnicodeDecodeError as e:
    #             self.logger.info("Error in write_logchat")
    #             self.logger.error(e)

    def write_logchat(self, actor, text):
        try:
            with open(self.log_filename, 'a') as f:
                text = text.encode('ascii', 'xmlcharrefreplace')
                f.write(actor + '\t: ' + text + '\n')
            f.close()
            time.sleep(0.1)
        except UnicodeDecodeError as e:
            self.logger.info("Error in write_logchat")
            self.logger.error(e)

    def quit(self):
        self.ALTabletService.resetTablet()
        self.logger.info('Reset Tablet')


    def callTelcoDialog(self, clientId):
        client_id       = ""
        conversation_id = ""
        question        = ""
        res             = ""

        while ((res != 'END') and ('Au revoir' not in res)):
            url = 'https://gateway.watsonplatform.net/dialog/api/v1/dialogs/41ba6bce-a429-4d84-ba84-c72d6aee5d04/conversation?input='
            if ((client_id != "") or (conversation_id != "")):
                question = self.listen(clientId)
                url = url + question
                url = url + '&client_id=' + str(client_id)
                url = url + '&conversation_id=' + str(conversation_id)

            r = requests.post(url, auth=('2777d45a-0e71-4283-87cb-77a6df11fac8', '8yGsEpiQ8uQr'))
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
    ==============================================================================
    Main program body with decision and redirection
    ==============================================================================
    """
    def runProgram(self, clientId):
        time.sleep(1)
        self.callTelcoDialog(clientId)
        self.quit_program(clientId)


    """
    Quit program
    """
    def quit_program(self, clientId):
        self.mem.raiseEvent('Telco/quit', 1)

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
        onStart = self.mem.getData('Telco/onStart')
        self.logger.info('Telco/onStart: ' + str(onStart))
        while (onStart==0):
            onStart = self.mem.getData('Telco/onStart')
            time.sleep(0.2)
            pass

        self.logger.info('Telco/onStart: ' + str(onStart))
        self.runProgram(self.clientId)

app = Telco()
app.run()
app.quit()

# End of Program #
