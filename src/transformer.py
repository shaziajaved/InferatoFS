# Test Change

"""
    The following code reads the user provided directory for downloaded emails, transforms them from
    maildir format to inferatoFS format, and saves the resultant data at user specified location.
    
    Two commandline arguments are required:
        First Argument:     Path to maildir top level folder e.g. ~/Maildir/
        Second Argument:    Path to Emails folder within to-be-mounted data folder e.g. ~/Data/Emails
"""

import os
import re
import sys
import magic
import email
import shutil
import datetime
from os.path import isdir
from os import listdir

class TransformerTemplate():
    #Command
    tagCommand = "mv -t"
    
    #Duplicate Status
    absolute = "Absolute"
    attachmentsOnly = "Attachments"
    notAtAll = "Not At All"
    
    #Input Keywords
    source = "source="
    destination = "dest="
    
    #Directory Structure
    mailDir = "Maildir"
    
    current = "cur"
    new = "new"
    temp = "tmp"
    
    #Email Keywords
    _text = "text"
    _image = "image"
    _multipart = "multipart"
    _application = "application"
    
    _messageID = "Message-ID"
    _from = "From"
    _sender = "Sender"
    _to = "To"
    _cc = "Cc"
    _bcc = "Bcc"
    _date = "Date"
    _subject = "Subject"
        
    #HTML Keywords
    htmlTag = "<html>"
    
    #Extensions
    htmlExtension = ".html"
    txtExtension = ".txt"
    
    #InferatoFS Files
    messageID = "Message ID"
    header = "Header from "
    body = "Body"
    logFile = "Deduplication Log"
    
    #InferatoFS Folders
    default = "Default"
    attachments = "Attachments"
    
    #Input Email File Type
    email_message = "mail text"
    
    #Characters
    hash = "#"
    space = " "
    colon = ":"
    comma = ","
    hyphen = "-"
    apostrophe = "'"
    tick = "`"
    semicolon = ";"
    colonSpace = ": "
    atTheRateOf = "@"
    forwardSlash = "/"
    backwardSlash = "\\"
    singleQuotes = "'"
    doubleQuotes = '"'
    newLine = "\n"
    tab = "\t"
    lessThan = "<"
    greaterThan = ">"
    emptyString = ""
    openingSquareBracket = "["
    closingSquareBracket = "]"
    slashSpace = "\ "
    slashColon = "\:"
    slashOpeningBracket = "\["
    slashClosingBracket = "\]"
    slashSingleQuotes = "\'"
    slashApostrophe = "\'"
    slashTick = "\`"
    
    none = "None"
    
    #Regular Expression Strings
    forSubject = '/'
    forMessageID = '<|>'
    forSender = '"|<|>'
    forRecipients = '\n|\t|/|"|<|>'
    
    #File Operations
    fileWrite = 'w'
    fileAppend = 'a'

class Transformer(object):
    inputPath = TransformerTemplate.emptyString
    dataPath = TransformerTemplate.emptyString
    outputPath = TransformerTemplate.emptyString
    
    workingPath = TransformerTemplate.emptyString
    folderName = TransformerTemplate.default
    
    hashedEmails = {}
    commands = []
    
    def usage(self):
        return "Specify input data path, storage path and mount point as command line argument"    
    
    def verifyInput(self, argv):
        if len(argv) == 3:
            self.inputPath = argv [0]
            if(isdir(self.inputPath)):
                pass
            else:
                print "[Error-Input Path] " + self.inputPath + " is not a directory"
                sys.exit(2)
            
            self.dataPath = argv[1]
            if(isdir(self.dataPath)):
                pass
            else:
                print "[Error-Data Path] " + self.outputPath + " is not a directory"
                sys.exit(2)
            
            self.outputPath = argv[2]
            if(isdir(self.outputPath)):
                pass
            else:
                print "[Error-Output Path] " + self.outputPath + " is not a directory"
                sys.exit(2)
        else:
            print self.usage()
            sys.exit(2)
        
        return self
        
    def main(self, argv):
        #Verify Command line Arguments and Populate Transformer Object Accordingly
        self.verifyInput(argv)
        
        #Traverse the Input Directory and Render Desired Email Storage Repository (the one to be mounted)
        self.workingPath = self.inputPath
        self.traversePath()
        
        #print self.input
        shutil.rmtree(self.inputPath)
        
        #Deleting All the Hashed Emails Once The Transformation along with Deduplication has been done
        for hashedEmail in self.hashedEmails:
            del hashedEmail
            
        '''
        #Save Deduplication Commands to Text File for Future Mounts
        fileHandler = open(self.outputPath + TransformerTemplate.forwardSlash + TransformerTemplate.logFile, TransformerTemplate.fileWrite)
        for command in self.commands:
            fileHandler.write(command + TransformerTemplate.newLine + TransformerTemplate.newLine)
        fileHandler.close()
        '''
        #Delete the Transformer Object
        del self
    
    def traversePath(self):
        #Get Entire Sub-Tree on Function Call for the Directory Under Consideration 
        files = listdir(self.workingPath)
        
        for file in files:
            filePath = self.workingPath + TransformerTemplate.forwardSlash + file
            
            if isdir(filePath):
                #FolderName = Default for ~/Maildir/cur, ~/Maildir/tmp and ~/Maildir/new
                if (str(filePath).endswith(TransformerTemplate.mailDir + TransformerTemplate.forwardSlash + TransformerTemplate.current) or 
                    str(filePath).endswith(TransformerTemplate.mailDir + TransformerTemplate.forwardSlash + TransformerTemplate.new) or 
                    str(filePath).endswith(TransformerTemplate.mailDir + TransformerTemplate.forwardSlash + TransformerTemplate.temp)): 
                    self.folderName = TransformerTemplate.default
                    
                #FolderName = [Parent Directory Name] for User or Mail Server Specific Folders:
                #For Example, FolderName = .inbox for ~/Maildir/.inbox
                else:
                    #Extract FolderName Only If NOT Already Extracted:
                    #This is to handle ~/Maildir/.inbox/cur, ~/Maildir/.inbox/tmp and ~/Maildir/.inbox/new
                    if (str(filePath).find(self.folderName) == -1):
                        self.folderName = filePath[str.rfind(filePath, TransformerTemplate.forwardSlash)+1:]
            
                #Make the Current Directory the Working Directory, and Explore It
                self.workingPath = filePath
                self.traversePath()
                
                #Function Return: Change Path to Parent Path for Browsal of Siblings
                self.workingPath = self.workingPath[:str.rfind(self.workingPath, TransformerTemplate.forwardSlash)]
            else:
                #Hit a File? Determine its type
                typeDeterminant = magic.open(magic.MAGIC_NONE)
                typeDeterminant.load()
                fileType = typeDeterminant.file(filePath)
                
                #Write Email File's Contents in InferatoFS Email Storage Format
                if str(fileType).endswith(TransformerTemplate.email_message):
                    self.workingPath = filePath
                    
                    emailMessage = EmailMessage()
                    
                    emailMessage.readEmailMessage(self)
                    emailMessage.writeEmailMessage(self)
                    
                    #print self.workingPath
                    os.remove(self.workingPath)
                    
                    del emailMessage
                    
                    self.workingPath = self.workingPath[:str.rfind(self.workingPath, TransformerTemplate.forwardSlash)]
                        
        return

class Attachment(object):
    attachmentName = TransformerTemplate.emptyString
    attachedFile = TransformerTemplate.emptyString

class ContactDetails(object):
    fullName = TransformerTemplate.emptyString
    emailAddress = TransformerTemplate.emptyString
    
    def retrieveScalarDetails(self, contact):
        if contact != None:
            details = str(contact).split(TransformerTemplate.lessThan)
            
            self.fullName = str(details[0])
            if(len(details) == 2):
                self.emailAddress = str(details[1]).replace(">", "")
            else:
                self.emailAddress = str(details[0]).replace(">", "")
                
            if self.fullName == TransformerTemplate.emptyString or self.fullName.isspace():
                self.fullName = self.emailAddress 
        else:
            self = None
            
        return
    
    @staticmethod
    def retrieveMultipleDetails(recipients):
        if recipients != None:
            contacts = str(recipients).split(TransformerTemplate.comma)
            contactsList = []
                
            for contact in contacts:
                contactDetails = ContactDetails()
                contactDetails.retrieveScalarDetails(contact)
                contactsList.append(contactDetails)
                #print contactDetails.fullName
                #print contactDetails.emailAddress
            
        else:
            return []
    
class Header(object):
    _from = ContactDetails()
    _sender = ContactDetails()
    _to = []
    _bcc = []
    _cc = []
    _subject = TransformerTemplate.emptyString
    _dateTime = TransformerTemplate.emptyString
    _messageID = TransformerTemplate.emptyString

class Body(object):
    _body = TransformerTemplate.emptyString
    _extension = TransformerTemplate.emptyString
    _attachments = []
        
class EmailMessage(object):
    pathToParent = TransformerTemplate.emptyString
    storagePath = TransformerTemplate.emptyString
    folderName = TransformerTemplate.emptyString
    
    actualFileName = TransformerTemplate.emptyString
    entireHeader = TransformerTemplate.emptyString
    
    emailHeader = Header()
    emailBody = Body()
    
    duplicate = TransformerTemplate.notAtAll
    duplicatePath = None
    occurenceNumber = 0
    
    def printEmailHeader(self):
        print "Message ID: " + self.emailHeader._messageID
        print "Date: " + self.emailHeader._dateTime
        print "Subject: " + self.emailHeader._subject
        
        if self.emailHeader._from != None:
            print "From - Full Name: " + self.emailHeader._from.fullName
            print "From - Email Address: " + self.emailHeader._from.emailAddress
        
        if self.emailHeader._sender != None:
            print "Sender - Full Name: " + self.emailHeader._sender.fullName
            print "Sender - Email Address: " + self.emailHeader._sender.emailAddress
            
        for toContact in self.emailHeader._to:
            print "To - Full Name: " + toContact.fullName
            print "To - Email Address: " + toContact.emailAddress
                    
        for ccContact in self.emailHeader._cc:
            print "Cc - Full Name: " + ccContact.fullName
            print "Cc - Email Address: " + ccContact.emailAddress
        
        for bccContact in self.emailHeader._bcc:
            print "Bcc - Full Name: " + bccContact.fullName
            print "Bcc - Email Address: " + bccContact.emailAddress
        
        print TransformerTemplate.newLine
        
        return
    
    def readEmailMessage(self, transformer):
        #Saving Actual File Name
        self.actualFileName = transformer.workingPath[str(transformer.workingPath).rfind(TransformerTemplate.forwardSlash)+1:]
                
        #Read Original Email File
        fileHandler = open(transformer.workingPath)    
        emailMessage = email.message_from_file(fileHandler)
        fileHandler.close()
        
        parsingDone = False
        
        self.emailBody._attachments = []
        
        #Populate EmailMessage Object with Read Contents
        for part in emailMessage.walk():
            #Reading and Saving Essential Bits from Header
            if part.get_content_maintype() != TransformerTemplate._application and parsingDone == False:
                #Extracting and Saving Scalar Values
                self.emailHeader._from.retrieveScalarDetails(part[TransformerTemplate._from])
                self.emailHeader._sender.retrieveScalarDetails(part[TransformerTemplate._sender])
                self.emailHeader._dateTime = str(part[TransformerTemplate._date])
                if part[TransformerTemplate._subject] != None:
                    self.emailHeader._subject = str(part[TransformerTemplate._subject])
                else:
                    self.emailHeader._subject = TransformerTemplate.emptyString
                self.emailHeader._messageID = str(part[TransformerTemplate._messageID])
                                
                #Extracting and Saving Multiple Values
                self.emailHeader._to = ContactDetails.retrieveMultipleDetails(part[TransformerTemplate._to])
                self.emailHeader._cc = ContactDetails.retrieveMultipleDetails(part[TransformerTemplate._cc])
                self.emailHeader._bcc = ContactDetails.retrieveMultipleDetails(part[TransformerTemplate._bcc])
                parsingDone = True
                
            #Reading and Saving HTML or Text based Body    
            if part.get_content_maintype() == TransformerTemplate._text:
                #Saving TEXT information
                self.emailBody._body = part.get_payload(decode=True)
                if (str(self.emailBody._body).find(TransformerTemplate.htmlTag) != -1):
                    self.emailBody._extension = TransformerTemplate.htmlExtension
            
            #Reading and Saving Attachments
            if part.get_content_maintype() == TransformerTemplate._application or part.get_content_maintype() == TransformerTemplate._image:
                attachment = Attachment()
                attachment.attachmentName = str(part.get_filename())
                attachment.attachedFile = str(part.get_payload(decode=True))
                self.emailBody._attachments.append(attachment)
            
        #Reading and Saving the Entire Header
        headerItems = emailMessage.items()
        for headerItem in headerItems:
            self.entireHeader += headerItem[0]
            self.entireHeader += TransformerTemplate.colonSpace
            self.entireHeader += headerItem[1]
            self.entireHeader += TransformerTemplate.newLine
            
        #Sanitize the Read Email Contents for Storage
        self.sanitizeEmailMessage()
        
        return
     
    def sanitizeEmailMessage(self):
        #Cleansing Email Header:
        #Date needs not to be Cleansed
        
        #Cleansing Message ID
        if self.emailHeader._messageID != None:
            self.emailHeader._messageID = str(re.sub(TransformerTemplate.forMessageID, TransformerTemplate.emptyString, self.emailHeader._messageID)).strip()
        
        #Cleansing Subject
        if self.emailHeader._subject != None:
            self.emailHeader._subject = str(re.sub(TransformerTemplate.forSubject, TransformerTemplate.emptyString, self.emailHeader._subject)).strip()
                
        #Cleansing From Details (Full Name and Email Address)
        if self.emailHeader._from.fullName != None:
            self.emailHeader._from.fullName = str(re.sub(TransformerTemplate.forSender, TransformerTemplate.emptyString, self.emailHeader._from.fullName)).strip()
        
        if self.emailHeader._from.emailAddress != None:
            self.emailHeader._from.emailAddress = str(re.sub(TransformerTemplate.forSender, TransformerTemplate.emptyString, self.emailHeader._from.emailAddress)).strip()
        
        #Cleansing Sender Details (Full Name and Email Address)
        if self.emailHeader._sender != None and self.emailHeader._sender.fullName != None:
            self.emailHeader._sender.fullName = str(re.sub(TransformerTemplate.forSender, TransformerTemplate.emptyString, self.emailHeader._sender.fullName)).strip()
        
        if self.emailHeader._sender != None and self.emailHeader._sender.emailAddress != None:
            self.emailHeader._sender.emailAddress = str(re.sub(TransformerTemplate.forSender, TransformerTemplate.emptyString, self.emailHeader._sender.emailAddress)).strip()
        
        #Cleansing To Details (Full Name and Email Address)
        for toContact in self.emailHeader._to:
            if toContact.fullName != None:
                toContact.fullName = str(re.sub(TransformerTemplate.forRecipients, TransformerTemplate.emptyString, toContact.fullName)).strip()
                
            if toContact.emailAddress != None:
                toContact.emailAddress = str(re.sub(TransformerTemplate.forRecipients, TransformerTemplate.emptyString, toContact.emailAddress)).strip()
        
        #Cleansing Cc Details (Full Name and Email Address)
        for ccContact in self.emailHeader._cc:
            if ccContact.fullName != None:
                ccContact.fullName = str(re.sub(TransformerTemplate.forRecipients, TransformerTemplate.emptyString, ccContact.fullName)).strip()
                
            if ccContact.emailAddress != None:
                ccContact.emailAddress = str(re.sub(TransformerTemplate.forRecipients, TransformerTemplate.emptyString, ccContact.emailAddress)).strip()
        
        #Cleansing Bcc Details (Full Name and Email Address)
        for bccContact in self.emailHeader._bcc:
            if bccContact.fullName != None:
                bccContact.fullName = str(re.sub(TransformerTemplate.forRecipients, TransformerTemplate.emptyString, bccContact.fullName)).strip()
                
            if bccContact.emailAddress != None:
                bccContact.emailAddress = str(re.sub(TransformerTemplate.forRecipients, TransformerTemplate.emptyString, bccContact.emailAddress)).strip()
        
        return
    
    def determineDuplicate(self, messageList, transformer):
        #print str(len(messageList))
        for message in messageList:
            self.determineDuplicity(message, transformer)
            
            if self.duplicate != TransformerTemplate.notAtAll:
                self.duplicatePath = message.storagePath
                break
        
        return
        
    def determineDuplicity(self, hashedMessage, transformer):
        contentMatched = True
        attachmentsMatched = True
        
        #Determining if the Header and the Body Matches
        if not str(hashedMessage.emailHeader._from).__eq__(self.emailHeader._from):
            print "FROM not matched"
            contentMatched = False
        if not str(hashedMessage.emailHeader._subject).__eq__(self.emailHeader._subject):
            print "SUBJECT not matched"
            contentMatched = False
        if not str(hashedMessage.emailHeader._sender).__eq__(self.emailHeader._sender):
            print "SENDER not matched"
            contentMatched = False
        if not str(hashedMessage.emailHeader._dateTime).__eq__(self.emailHeader._dateTime):
            print "DATETIME not matched"
            contentMatched = False
        
        if len(hashedMessage.emailHeader._to) != len(self.emailHeader._to):
            print "TO (length) not matched"
            contentMatched = False
        
        index = 0
        for to in self.emailHeader._to:
            if not str(hashedMessage.emailHeader._to[index].fullName).__eq__(to.fullName):
                print "TO (full name) not matched"
                contentMatched = False
                break
            if not str(hashedMessage.emailHeader._to[index].emailAddress).__eq__(to.emailAddress):
                print "TO (email address) not matched"
                contentMatched = False
                break
            index += 1
        
        if len(hashedMessage.emailHeader._cc) != len(self.emailHeader._cc):
            print "CC (length) not matched"
            contentMatched = False
        
        index = 0
        for cc in self.emailHeader._cc:
            if not str(hashedMessage.emailHeader._cc[index].fullName).__eq__(cc.fullName):
                print "CC (full name) not matched"
                contentMatched = False
                break
            if not str(hashedMessage.emailHeader._cc[index].emailAddress).__eq__(cc.emailAddress):
                print "CC (email address) not matched"
                contentMatched = False
                break
            index += 1
        
        if len(hashedMessage.emailHeader._bcc) != len(self.emailHeader._bcc):
            print "BCC (length) not matched"
            contentMatched = False
        
        index = 0
        for bcc in self.emailHeader._bcc:
            if not str(hashedMessage.emailHeader._bcc[index].fullName).__eq__(bcc.fullName):
                print "BCC (full name) not matched"
                contentMatched = False
                break
            if not str(hashedMessage.emailHeader._bcc[index].emailAddress).__eq__(bcc.emailAddress):
                print "BCC (email address) not matched"
                contentMatched = False
                break
            index += 1
        
        if not str(hashedMessage.emailBody._body).__eq__(self.emailBody._body):
            print "BODY not matched"
            contentMatched = False
        
        #Determining if the Attachments Match
        if len(hashedMessage.emailBody._attachments) != len(self.emailBody._attachments):
            print "Attachments (length) not matched"
            attachmentsMatched = False
        
        for newAttachment in self.emailBody._attachments:
            found = False
            for oldAttachment in hashedMessage.emailBody._attachments:
                if str(oldAttachment.attachmentName).__eq__(newAttachment.attachmentName):
                    if (oldAttachment.attachedFile == oldAttachment.attachedFile):
                        found = True
                        break
                    
            if not found:
                print "Attachments (themselves) not matched"
                attachmentsMatched = False
                break 
        
        #Store Determined Nature of Duplication, and Prepared Deduplication (link creation) Command here
        #deduplicateCommand = None
        
        if contentMatched and attachmentsMatched:
            self.duplicate = TransformerTemplate.absolute
            '''firstPath = "~/mnt/Emails/" + hashedMessage.pathToParent[str(hashedMessage.pathToParent).rfind(TransformerTemplate.forwardSlash)+1:] + TransformerTemplate.forwardSlash + hashedMessage.folderName
            secondaryPath = "~/mnt/Emails/" + self.pathToParent[str(self.pathToParent).rfind(TransformerTemplate.forwardSlash)+1:] + TransformerTemplate.forwardSlash + self.folderName
            
            if not str(firstPath).__eq__(secondaryPath):
                firstPath = str(firstPath).replace(TransformerTemplate.space, TransformerTemplate.slashSpace)
                firstPath = str(firstPath).replace(TransformerTemplate.colon, TransformerTemplate.slashColon)
                firstPath = str(firstPath).replace(TransformerTemplate.apostrophe, TransformerTemplate.slashApostrophe)
                firstPath = str(firstPath).replace(TransformerTemplate.singleQuotes, TransformerTemplate.slashSingleQuotes)
                firstPath = str(firstPath).replace(TransformerTemplate.tick, TransformerTemplate.slashTick)
                firstPath = str(firstPath).replace(TransformerTemplate.openingSquareBracket, TransformerTemplate.slashOpeningBracket)
                firstPath = str(firstPath).replace(TransformerTemplate.closingSquareBracket, TransformerTemplate.slashClosingBracket)
                
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.space, TransformerTemplate.slashSpace)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.colon, TransformerTemplate.slashColon)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.apostrophe, TransformerTemplate.slashApostrophe)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.singleQuotes, TransformerTemplate.slashSingleQuotes)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.tick, TransformerTemplate.slashTick)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.openingSquareBracket, TransformerTemplate.slashOpeningBracket)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.closingSquareBracket, TransformerTemplate.slashClosingBracket)
            
                deduplicateCommand = "mv -t %(firstPath)s\[#\] %(firstPath)s %(secondaryPath)s" % locals()'''
        elif not contentMatched and attachmentsMatched:
            self.duplicate = TransformerTemplate.attachmentsOnly
            '''firstPath = "~/mnt/Emails/" + hashedMessage.pathToParent[str(hashedMessage.pathToParent).rfind(TransformerTemplate.forwardSlash)+1:] + TransformerTemplate.forwardSlash + hashedMessage.folderName + TransformerTemplate.forwardSlash + TransformerTemplate.attachments
            secondaryPath = "~/mnt/Emails/" + self.pathToParent[str(self.pathToParent).rfind(TransformerTemplate.forwardSlash)+1:] + TransformerTemplate.forwardSlash + self.folderName + TransformerTemplate.forwardSlash + TransformerTemplate.attachments
            
            if not str(firstPath).__eq__(secondaryPath):
                firstPath = str(firstPath).replace(TransformerTemplate.space, TransformerTemplate.slashSpace)
                firstPath = str(firstPath).replace(TransformerTemplate.colon, TransformerTemplate.slashColon)
                firstPath = str(firstPath).replace(TransformerTemplate.apostrophe, TransformerTemplate.slashApostrophe)
                firstPath = str(firstPath).replace(TransformerTemplate.singleQuotes, TransformerTemplate.slashSingleQuotes)
                firstPath = str(firstPath).replace(TransformerTemplate.tick, TransformerTemplate.slashTick)
                firstPath = str(firstPath).replace(TransformerTemplate.openingSquareBracket, TransformerTemplate.slashOpeningBracket)
                firstPath = str(firstPath).replace(TransformerTemplate.closingSquareBracket, TransformerTemplate.slashClosingBracket)
                
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.space, TransformerTemplate.slashSpace)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.colon, TransformerTemplate.slashColon)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.apostrophe, TransformerTemplate.slashApostrophe)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.singleQuotes, TransformerTemplate.slashSingleQuotes)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.tick, TransformerTemplate.slashTick)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.openingSquareBracket, TransformerTemplate.slashOpeningBracket)
                secondaryPath = str(secondaryPath).replace(TransformerTemplate.closingSquareBracket, TransformerTemplate.slashClosingBracket)
            
                deduplicateCommand = "mv -t %(firstPath)s\[#\] %(firstPath)s %(secondaryPath)s" % locals()'''
        elif not contentMatched and not attachmentsMatched:
            self.duplicate = TransformerTemplate.notAtAll
        
        #if deduplicateCommand != None:
            #print deduplicateCommand
            #transformer.commands.append(deduplicateCommand)
        
        return
    
    def hashEmailMessage(self, transformer):
        if(self.folderName not in transformer.hashedEmails):
            transformer.hashedEmails[self.folderName] = []
        
        sameLocation = False
        for message in transformer.hashedEmails[self.folderName]:
            #print "--- " + message.pathToParent + " ---"
            if self.pathToParent == message.pathToParent:
                sameLocation = True
                break
            
        if not sameLocation:
            #print "appending ..." + self.pathToParent
            transformer.hashedEmails[self.folderName].append(self)
            self.occurenceNumber = len(transformer.hashedEmails[self.folderName])
        #else:
            #print "Match Found: " + self.pathToParent + " --- " + message.pathToParent
            #print "Count of Email: " + str(self.occurenceNumber) + "\n"
        
        return transformer.hashedEmails[self.folderName]
    
    def prepareStorage(self, transformer):
        #Create Folder Name and Storage Path along with determination of Email Copies' Count
        transformer.folderName = str(transformer.folderName).replace(".", "_")
        self.pathToParent = transformer.outputPath + TransformerTemplate.forwardSlash + transformer.folderName
        if not isdir(self.pathToParent):
            os.mkdir(self.pathToParent)
        #print "Path to Parent Folder: " + self.pathToParent
        
        #print "### writeEmailMessage ###"
        self.prepareFolderName()
        firstMessage = self.hashEmailMessage(transformer)
        #self.prepareStoragePath()   
        #print "### Storage Path ### " + self.storagePath     
        
        if self.prepareStoragePath() and not isdir(self.storagePath):
            os.mkdir(self.storagePath)
        
        return firstMessage
        
    def writeEmailMessage(self, transformer):
        firstMessage = self.prepareStorage(transformer)
        
        #Determine Nature of Duplication and Prepare Deduplication Command
        if self.occurenceNumber > 1:
            #self.determineDuplicity(firstMessage[0], transformer)
            self.determineDuplicate(firstMessage, transformer)
                        
        if self.occurenceNumber == 1 and self.duplicate != TransformerTemplate.absolute:
            #Create Message ID File
            if self.emailHeader._messageID != None:
                fileHandler = open(self.storagePath + TransformerTemplate._messageID, TransformerTemplate.fileWrite)
                fileHandler.write(self.emailHeader._messageID)
                fileHandler.close()
                
            #Create From File
            fileHandler = open(self.storagePath + TransformerTemplate._from, TransformerTemplate.fileWrite)
            if(self.emailHeader._from.fullName != self.emailHeader._from.emailAddress):
                fileHandler.write(self.emailHeader._from.fullName + TransformerTemplate.newLine)
            fileHandler.write(self.emailHeader._from.emailAddress)
            fileHandler.close()
                
            #Create Sender File
            if (self.emailHeader._sender != None and self.emailHeader._sender.fullName != TransformerTemplate.emptyString 
                and self.emailHeader._sender.emailAddress != TransformerTemplate.emptyString):
                fileHandler = open(self.storagePath + TransformerTemplate._sender, TransformerTemplate.fileWrite)
                if(self.emailHeader._sender.fullName != self.emailHeader._sender.emailAddress):
                    fileHandler.write(self.emailHeader._sender.fullName + TransformerTemplate.newLine)
                fileHandler.write(self.emailHeader._sender.emailAddress)
                fileHandler.close()
        
            #Create Subject File
            if self.emailHeader._subject != None:
                fileHandler = open(self.storagePath + TransformerTemplate._subject, TransformerTemplate.fileWrite)
                fileHandler.write(self.emailHeader._subject)
                fileHandler.close()
            
            #Create Date File
            if self.emailHeader._dateTime != None:
                fileHandler = open(self.storagePath + TransformerTemplate._date, TransformerTemplate.fileWrite)
                fileHandler.write(self.emailHeader._dateTime)
                fileHandler.close()
                
            #Create To Folder and Store Contacts
            if len(self.emailHeader._to) != 0:
                if not isdir(self.storagePath + TransformerTemplate._to):
                    os.mkdir(self.storagePath + TransformerTemplate._to)
                    
                toPath = self.storagePath + TransformerTemplate._to + TransformerTemplate.forwardSlash
                
                for toContact in self.emailHeader._to:
                    fileHandler = open(toPath + toContact.fullName, TransformerTemplate.fileWrite)
                    if(toContact.fullName != toContact.emailAddress):
                        fileHandler.write(toContact.fullName + TransformerTemplate.newLine)
                    fileHandler.write(toContact.emailAddress)
                    fileHandler.close()
                            
            #Create Cc Folder and Store Contacts
            if len(self.emailHeader._cc) != 0:
                if not isdir(self.storagePath + TransformerTemplate._cc):
                    os.mkdir(self.storagePath + TransformerTemplate._cc)
                    
                ccPath = self.storagePath + TransformerTemplate._cc + TransformerTemplate.forwardSlash
                
                for ccContact in self.emailHeader._cc:
                    fileHandler = open(ccPath + ccContact.fullName, TransformerTemplate.fileWrite)
                    if(ccContact.fullName != ccContact.emailAddress):
                        fileHandler.write(ccContact.fullName + TransformerTemplate.newLine)
                    fileHandler.write(ccContact.emailAddress)
                    fileHandler.close()
                    
            #Create Bcc Folder and Store Contacts
            if len(self.emailHeader._bcc) != 0:
                if not isdir(self.storagePath + TransformerTemplate._bcc):
                    os.mkdir(self.storagePath + TransformerTemplate._bcc)
                    
                bccPath = self.storagePath + TransformerTemplate._bcc + TransformerTemplate.forwardSlash
                
                for bccContact in self.emailHeader._bcc:
                    fileHandler = open(bccPath + bccContact.fullName, TransformerTemplate.fileWrite)
                    if(bccContact.fullName != bccContact.emailAddress):
                        fileHandler.write(bccContact.fullName + TransformerTemplate.newLine)
                    fileHandler.write(bccContact.emailAddress)
                    fileHandler.close()
                    
            #Create Header File
            headerPath = self.storagePath + TransformerTemplate.header + self.actualFileName
            fileHandler = open(headerPath, TransformerTemplate.fileWrite)
            fileHandler.write(self.entireHeader)
            fileHandler.close()
                
            #Create Body File
            if self.emailBody != None:
                fileHandler = open(self.storagePath + TransformerTemplate.body + self.emailBody._extension, TransformerTemplate.fileWrite)
                fileHandler.write(self.emailBody._body)
                fileHandler.close()
                
            #Create Attachments Folder and Store Attachments
            if len(self.emailBody._attachments) != 0:
                if not isdir(self.storagePath + TransformerTemplate.attachments):
                    os.mkdir(self.storagePath + TransformerTemplate.attachments)
                    
                if self.duplicate != TransformerTemplate.attachmentsOnly:
                    attachmentsPath = self.storagePath + TransformerTemplate.attachments + TransformerTemplate.forwardSlash
                    
                    for attachment in self.emailBody._attachments:
                        fileHandler = open(attachmentsPath + attachment.attachmentName, TransformerTemplate.fileWrite)
                        fileHandler.write(attachment.attachedFile)
                        fileHandler.close()
                    
            del fileHandler
        elif self.occurenceNumber != 0:
            parentDataFolder = transformer.outputPath[str.rfind(transformer.outputPath, TransformerTemplate.forwardSlash):]
            duplicatePath = transformer.dataPath + self.duplicatePath[str.find(self.duplicatePath, parentDataFolder) + len(parentDataFolder):]
            #print duplicatePath
            #shortcutPath = transformer.dataPath + self.storagePath
            os.symlink(duplicatePath, os.path.realpath(self.storagePath))
        
        return
    
    def prepareFolderName(self):
        #Preparing Date Time, Time Zone and Subject for Folder Name
        dateTime = str(datetime.datetime.strptime(self.emailHeader._dateTime[:-6], '%a, %d %b %Y %H:%M:%S'))
        timeZone = self.emailHeader._dateTime[-5:]
        #subject = str(self.emailHeader._subject[:79]).ljust(80, TransformerTemplate.space)
        subject = str(self.emailHeader._subject[:79])
        
        #Extracting 16 Characters of From Information for Folder Name
        sender = self.emailHeader._from.fullName[:15]
        if (len(sender) < 16):
            sender += self.emailHeader._from.fullName[:16-len(sender)]
        str(sender).ljust(16-len(sender), TransformerTemplate.space)
        
        #Extracting 16 Characters of To Information for Folder Name
        index = 0
        recipient = ""
        while (len(recipient) < 17):
            recipient = self.emailHeader._to[index].fullName[:15]
            if (len(recipient) < 16):
                recipient += self.emailHeader._to[index].fullName[:16-len(recipient)]
                index += 1
            if(index >= len(self.emailHeader._to)):
                break
        str(recipient).ljust(16-len(recipient), TransformerTemplate.space)    
        
        #Preparing FolderName with Extracted Values
        self.folderName = "%(dateTime)s %(timeZone)s   %(subject)s   From: %(sender)0.16s   To: %(recipient)0.16s " % locals()
        
        return
    
    def prepareStoragePath(self):
        emailNumber = self.occurenceNumber
        self.folderName += "[%(emailNumber)s]" % locals()        
        self.storagePath = self.pathToParent + TransformerTemplate.forwardSlash + self.folderName + TransformerTemplate.forwardSlash
            
        if emailNumber == 1:
            return True
        else:
            return False
    
if __name__ == '__main__':
    transformer = Transformer()
    transformer.main(sys.argv[1:])   
    
