
import os
import sys
import email
import smtplib
from transformer import ContactDetails

class CourierTemplates():
    #define your prefixes for types here    
    _suffix = "[#]"
    _originalEmail = "email.eml"
    
    _yes = "yes"
    _colon = ":"
    _slashColon = "\:"
    _space = " "
    _slashSpace = "\ "
    
    _outbox = "Outbox-Path"
    _sentMessages = "Sent-Messages-Path"
    _server = "Server"
    _port = "Port"
    _emailAddress = "Login-ID"
    _password = "Password"
    _tls = "TLS"
    
    _from = "From"
    _to = "To"
    _cc = "Cc"
    _bcc = "Bcc"
    
    _lessThan = "<"
    _greaterThan = ">"
    _enter = "\n"

class Courier():
    outbox = ""
    sentMessages = ""
    configurationFile = ""
    
    server = ""
    port = 0
    emailAddress = ""
    password = ""
    tls = "No"
    
    senderAddress = ""
    receiverAddress = []
    
    def loadConfiguration(self):
        fileHandler = open(self.configurationFile)
        for line in fileHandler:
            
            if str(line).find(CourierTemplates._outbox) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.outbox = line[colonPosition+2:-1]
            
            if str(line).find(CourierTemplates._sentMessages) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.sentMessages = line[colonPosition+2:-1]
            
            if str(line).find(CourierTemplates._server) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.server = line[colonPosition+2:-1]
            
            if str(line).find(CourierTemplates._port) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.port = line[colonPosition+2:-1]
            
            if str(line).find(CourierTemplates._emailAddress) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.emailAddress = line[colonPosition+2:-1]
            
            if str(line).find(CourierTemplates._password) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.password = line[colonPosition+2:-1]
            
            if str(line).find(CourierTemplates._tls) != -1:
                colonPosition = str(line).find(CourierTemplates._colon)
                self.tls = line[colonPosition+2:-1]   
        return
        
    def despatchEmails(self):
        if os.path.exists(self.outbox) and os.path.isdir(self.outbox):
            directoryList = os.listdir(self.outbox)
        else:
            print "directory not found: " + self.outbox
            #directoryList = os.listdir("/home/mnt/Emails/Test/")
            directoryList = ""
        
        if len(directoryList) != 0:
            for directory in directoryList:
                if str(directory).find(CourierTemplates._suffix) != -1:
                    fileHandler = open(self.outbox + directory + os.sep + CourierTemplates._originalEmail)
                    fh = open(self.outbox + directory + os.sep + CourierTemplates._originalEmail)
                    message = fileHandler.read()
                    emailMessage = email.message_from_file(fh)
                    
                    for part in emailMessage.walk():
                        fromAddress = ContactDetails()
                        fromAddress.retrieveScalarDetails(part[CourierTemplates._from])
                         
                        toAddresses = ContactDetails.retrieveMultipleDetails(part[CourierTemplates._to])
                        ccAddresses = ContactDetails.retrieveMultipleDetails(part[CourierTemplates._cc])
                        bccAddresses = ContactDetails.retrieveMultipleDetails(part[CourierTemplates._bcc])
                        
                        if (fromAddress != None and toAddresses != None and len(toAddresses) != 0):
                            break
                                        
                    try:
                        mailServer = smtplib.SMTP(self.server, self.port)
                        #mailServer.ehlo()
                        if str(self.tls).lower() == CourierTemplates._yes:
                            mailServer.starttls()
                        #mailServer.ehlo()
                        mailServer.login(self.emailAddress, self.password)
                        #for toAddress in toAddresses:
                        mailServer.sendmail("thirtyninedegree@gmail.com", "thirtyninedegree@gmail.com", message)
                            
                        for ccAddress in ccAddresses:
                            mailServer.sendmail(fromAddress.emailAddress, ccAddress.emailAddress, message)
                        for bccAddress in bccAddresses:
                            mailServer.sendmail(fromAddress.emailAddress, bccAddress.emailAddress, message)
                        mailServer.close()
                                                
                        dir = directory[: -1*len(CourierTemplates._suffix)]                        
                        dir = str(dir).replace(CourierTemplates._space, CourierTemplates._slashSpace)
                        dir = str(dir).replace(CourierTemplates._colon, CourierTemplates._slashColon)
                        
                        #rename
                        #os.system("mv " + self.outbox + dir + " " + self.sentMessages)
                        
                        #print "\nOld: " + self.outbox + dir
                        #print "New: " + self.sentMessages + dir + "\n"
                        
                        #if not (os.path.exists(self.outbox + dir)):
                            #print "Outbox doesn't Exist!"
                        
                        #if not (os.path.exists(self.sentMessages + dir)):
                            #print "Sent Messages doesn't Exist!\n"
                        
                        #os.rename(self.outbox + dir, self.sentMessages + dir)
                        
                        print "Successfully sent email"
                    except smtplib.SMTPException:
                        print "Error: unable to send email"
    
    def usage(self):
        #return "Specify Outbox path and Sent Messages path as command line argument"
        return "Please specify the configuration file path as command line argument"    
    
    def verifyInput(self, argv):
        if len(argv) == 1:
            self.configurationFile = argv[0]
            if not os.path.exists(self.configurationFile):
                print "Specified configuration file doesn't exist"
                sys.exit(2)
            elif not os.path.isfile(self.configurationFile):
                print "Specified path isn't a configuration file"
                sys.exit(2)
        else:
            print self.usage()
            sys.exit(2)
        
        return self
    
    def main(self, argv):
        #Verify Command line Arguments and Populate Transformer Object Accordingly
        self.verifyInput(argv)
        
        #Retrieve the folder names, server details and login credentials
        self.loadConfiguration()
        
        #Compose and Despatch Emails from Outbox Path
        self.despatchEmails()
        
if __name__ == '__main__':
    courier = Courier()
    courier.main(sys.argv[1:])   