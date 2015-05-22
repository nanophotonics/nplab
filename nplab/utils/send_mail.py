"""
Mailing Utilities
=============

Allows to send emails from a NP gmail account. CAn e.g. be used to monitor an experiment, example:

import threading

self._monitoring_thread = threading.Thread(target=self._status_check)
self._monitoring_thread.start()

def _status_check(self):
    email = "CRSID@cam.ac.uk"
    while self.running:
        value_to_check = get.variable
        
        if(value_to_check>threashold):email = "CRSID@cam.ac.uk"
            subject = "CAUTION: critical error"
            message = "your message"
            self.SendMessage(email,message,subject)
        time.sleep(10)
    
    subject = "Experiment finished"
    message = "your message"
    self.SendMessage(email,message,subject)

"""

import smtplib
import imp

def SendMessage(address,msg,subject):    
        "get the username and password from a file"        
        f = open("R:\\0-SHARED\\Computing\\NP_mailing.txt")
        global credentials
        credentials = imp.load_source('data', '', f)
        f.close()
        
        FROM = 'np.lab.messenger@gmail.com '
        TO = [address] #must be a list
        SUBJECT = subject
        TEXT = msg
        
        # Prepare actual message
        message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
            server.ehlo()
            server.starttls()
            server.login(credentials.user, credentials.pw)
            server.sendmail(FROM, TO, message)
            server.close()
            print 'successfully sent the mail'
        except:
            print "failed to send mail"