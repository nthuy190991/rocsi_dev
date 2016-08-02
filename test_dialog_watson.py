from watson_developer_cloud import NaturalLanguageClassifierV1
from watson_developer_cloud import DialogV1
import json
import time

nlc = NaturalLanguageClassifierV1(
                            username = "ddc8decd-5b31-4dca-9395-e7bbf95246c0",
                            password = "I2RXPXZL0eCP")

dialog = DialogV1(
            username='d2b39394-6660-4948-a9ed-74a70883f784',
            password='4LSJkrIBBupP')

def send2WatsonNLCClassifier(text):
    classes = nlc.classify('1c40d6x83-nlc-137', text)
    responseYesOrNo = classes["top_class"]
    print ('Response from NLC: ' + responseYesOrNo)

def send2WatsonBanqueDialog(text):
    response = dialog.func('97111df6-fc4d-4714-b409-34f0c483f5f4', text)
    print ('Response from Dialog: ' + response)

if __name__ == '__main__':
    send2WatsonNLCClassifier('Tout a fait')

    send2WatsonBanqueDialog('Je veux faire un virement')

    print 'END'
