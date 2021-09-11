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
from __future__ import print_function

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
            print('successfully sent the mail')
        except:
            print("failed to send mail")
            
NPLAB_FROM_ADDRESS = "physics-np-bounces@lists.cam.ac.uk"#np-lab-notifications@phy.cam.ac.uk"
NPLAB_SMTP_SERVER = "ppsw.cam.ac.uk"

def send_email(to_address, message, subject="[nplab] Notification", raise_exceptions=False):
    """Send an email (only works for PCs on the Physics network).
    
    Uses the np-lab-notifications email address as the "from" address and
    sends unencrypted through ppsw.cam.ac.uk, so this will only work for PCs
    on the University network."""
    try:
        header = "From: {0}\r\nTo: {1}\r\nSubject: {2}\r\n\r\n".format(NPLAB_FROM_ADDRESS, to_address, subject)
        server = smtplib.SMTP(NPLAB_SMTP_SERVER, 25)
        server.sendmail(NPLAB_FROM_ADDRESS, to_address, header + message)
        server.quit()
    except Exception as e:
        if raise_exceptions:
            raise e
        else:
            print("Warning: errror while sending email to {0}: {1}".format(to_address, e))

if __name__ == "__main__":
    import datetime
    #send_email("rwb27@cam.ac.uk", "Test email from nplab, sent at {0}".format(datetime.datetime.now().isoformat()))
    