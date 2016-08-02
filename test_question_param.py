from read_xls import read_xls
# import qi
import sys
import random

class Question(object):
    def __init__(self):
        self.tb = read_xls("TextToSpeakRobot_new.xls", 0) # Read Excel file
        self.text_id_idx = self.tb[0][:].index('Text_ID')
        self.questions = []
        for idx in range(0, len(self.tb)):
            self.questions.append(self.tb[idx][self.text_id_idx])

        # self.appli = qi.Application(sys.argv)
        # self.appli.start()
        # self.session = self.appli.session
        # self.tts = self.session.service('ALTextToSpeech')

    def speak(self, clientId, message):
        print 'Say: ', message

    def question(self, clientId, message):


        # res = raw_input('Ask: '+ message)
        # print 'Ask: ', message
        res = 'oui'
        # print 'Answer: ', res
        return 1, message, res

    def textSelect(self, message):
        # message = message.encode('ascii', 'xmlcharrefreplace')
        messages = message.split('/')
        nb_messages = len(messages)
        idx = random.randint(0, nb_messages-1)
        mess = messages[idx]
        return mess

    """
    Yes/No question as an asking/answering by dialogue
    """
    def yes_or_no(self, clientId, question_id):
#      global_var = (item for item in self.global_vars if item["clientId"] == str(clientId)).next()
#      if (not global_var['flag_quit']): # Put in If-condition to allow interrupt when Esc is pressed
          ind = self.questions.index(question_id)
          message = self.tb[ind][self.tb[0][:].index('Text')]

          mess = self.textSelect(message)

          resp, a, b = self.question(clientId, mess)

        #   self.tts.say(a)

          if (resp==1):
              confirm = self.tb[ind][self.tb[0][:].index('Confirmation_oui')]
          elif (resp==0):
              confirm = self.tb[ind][self.tb[0][:].index('Confirmation_non')]

          confi = self.textSelect(confirm)
          self.speak(clientId, confi)

          return resp
#      else:
#          return -1

clientId = 1

app = Question()
a = app.tb
questions = app.questions
res = app.yes_or_no(clientId, 'allow_streaming_video')
print res

print 'END'
