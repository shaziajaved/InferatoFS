#!/usr/bin/env python

#    Copyright (C) 2001  Jeff Epler  <jepler@unpythonic.dhs.org>
#    Copyright (C) 2006  Csaba Henk  <csaba.henk@creo.hu>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

# Using python-magic for file type determination
import re
import magic
from transformer import Transformer, TransformerTemplate, EmailMessage
import os, sys, stat, tempfile, shutil
from uuid import uuid1
from errno import EACCES, EOPNOTSUPP, EINVAL
#from stat import *
import fcntl
#from inspect import getabsfile
from parser import Parser
from metautils import PathUtils, StateUtils
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse

import mimetypes

from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import time

if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.fuse_python_api = (0, 2)

fuse.feature_assert('stateful_files', 'has_init')

def fixTaggedLink(self, actualPath, preloc, newloc):
    paths = str(preloc[1:]).split("/")    
    concatenatedPath = actualPath[:str(actualPath).find(paths[0])]
    
    for path in paths:
        concatenatedPath = concatenatedPath + path + "/"        
        directoryList = os.listdir(concatenatedPath)
        
        for directory in directoryList:            
            if str(directory).find(FSTemplates._suffix) != -1:
                tagsFolder = concatenatedPath + directory + os.sep + FSTemplates.folder_tags
                contents = os.listdir(tagsFolder)
                
                for content in contents:
                    contentPath = tagsFolder + os.sep + content
                    if os.path.islink(contentPath):
                        target = os.readlink(contentPath)
                        #print "Target found to be " + target
                        
                        if str(target).find(preloc) != -1:
                            os.remove(contentPath)
                            #print "First Argument: " + str(target).replace(preloc, newloc)
                            #print "Second Argument: " + contentPath
                            os.symlink(str(target).replace(preloc, newloc), contentPath)
            

def fixDeletedLink(self, path, preloc, newloc):
    directoryList = os.listdir(path)
    for directory in directoryList:
        if str.find(directory, FSTemplates._meta_storage) == -1 and str.find(directory, FSTemplates._suffix) == -1:
            dirRealPath = path + os.sep + directory
            if os.path.islink(dirRealPath):
                target = os.readlink(dirRealPath)
                stringIndex = str.find(target, preloc)
                if stringIndex != -1:
                    parentPath = target[:stringIndex]
                    os.remove(dirRealPath)
                    os.symlink(parentPath + newloc, dirRealPath)        
            elif os.path.isdir(dirRealPath):
                fixDeletedLink(self, dirRealPath, preloc, newloc)

def composeEmail(path):
    outer = MIMEMultipart()
    
    #Writing FROM content
    extractedContent = "\n"
    
    fileHandler = open(path + os.sep + "From")
    fromName = str(fileHandler.readline()).replace("\n", "")
    fromEmail = str(fileHandler.readline()).replace("\n", "") 
    if str(fromEmail).find("@") != -1:
        extractedContent += "From: \"%(fromName)s\" <%(fromEmail)s> \n" % locals()
    else:
        extractedContent += "From: \"%(fromName)s\" \n" % locals()
    fileHandler.close()
    
    #outer['From'] = extractedContent
    
    #Writing Sender content
    if os.path.exists(path + os.sep + "Sender"):
        fileHandler = open(path + os.sep + "Sender")
        senderName = str(fileHandler.readline()).replace("\n", "")
        senderEmail = str(fileHandler.readline()).replace("\n", "") 
        extractedContent += "Sender: \"%(senderName)s\" <%(senderEmail)s> \n" % locals()
        fileHandler.close()
    
    #Writing TO content
    dirPath = path + os.sep + "To" + os.sep
    dirList = os.listdir(dirPath)
        
    toContacts = "To: "
    for file in dirList:
        if str(file).find(FSTemplates._suffix) == -1:
            fileHandler = open(dirPath + file)
            toName = str(fileHandler.readline()).replace("\n", "")
            toEmail = str(fileHandler.readline()).replace("\n", "")
            if str(toEmail).find("@") != -1:
                toContacts += "\"%(toName)s\" <%(toEmail)s>, " % locals()
            else:
                toContacts += "\"%(toName)s\", " % locals()
            fileHandler.close()
            
    #outer['To'] = toContacts[:-2]
    extractedContent += toContacts[:-2] + "\n"
    
    #Writing CC content
    dirPath = path + os.sep + "Cc" + os.sep
    if os.path.exists(dirPath):
        dirList = os.listdir(dirPath)
        
        ccContacts = "Cc: "
        for file in dirList:
            print dirPath + file
            if str(file).find(FSTemplates._suffix) == -1:
                fileHandler = open(dirPath + file)
                ccName = str(fileHandler.readline()).replace("\n", "")
                ccEmail = str(fileHandler.readline()).replace("\n", "")
                if str(ccEmail).find("@") != -1:
                    ccContacts += "\"%(ccName)s\" <%(ccEmail)s>, " % locals()
                else:
                    ccContacts += "\"%(ccName)s\", " % locals()
                fileHandler.close()
        
        #outer['Cc'] = ccContacts[:-2] + "\n"
        extractedContent += ccContacts[:-2] + "\n"
                
    #Writing BCC content
    dirPath = path + os.sep + "Bcc" + os.sep
    if os.path.exists(dirPath):
        dirList = os.listdir(dirPath)
        
        bccContacts = "Bcc"
        for file in dirList:
            if str(file).find(FSTemplates._suffix) == -1:
                fileHandler = open(dirPath + file)
                bccName = str(fileHandler.readline()).replace("\n", "")
                bccEmail = str(fileHandler.readline()).replace("\n", "")
                if str(bccEmail).find("@") != -1:
                    bccContacts += "\"%(bccName)s\" <%(bccEmail)s>, " % locals()
                else:
                    bccContacts += "\"%(bccName)s\", " % locals()
                fileHandler.close()
                
        #outer['Bcc'] = bccContacts[:-2] + "\n"
        extractedContent += bccContacts[:-2] + "\n"
        
    #Writing SUBJECT content
    fileHandler = open(path + os.sep + "Subject")
    #outer['Subject'] = fileHandler.readline()
    extractedContent += ("Subject: " + fileHandler.readline() + "\n") 
    fileHandler.close()
    
    #Writing DATE content to EML file
    if os.path.exists(path + os.sep + "Date"):
        fileHandler = open(path + os.sep + "Date")
        #outer['Date'] = fileHandler.readline()
        extractedContent += ("Date: " + fileHandler.readline() + "\n")
        fileHandler.close()
    else:
        fileHandler = open(path + os.sep + "Date", TransformerTemplate.fileWrite)      
        fileHandler.write(time.strftime("%a, %d %b %Y %H:%M:%S %Z"))
        fileHandler.close()
    
    #Writing MESSAGE ID content
    if os.path.exists(path + os.sep + "Message-ID"):
        fileHandler = open(path + os.sep + "Message-ID")
        #outer['Message-ID'] = fileHandler.readline()
        extractedContent += ("Message-ID: " + fileHandler.readline() + "\n")
        fileHandler.close()
    
    #Writing Body content
    fileHandler = open(path + os.sep + "Body")
    #outer['Body'] = fileHandler.read()
    body = "\n" + fileHandler.read()
    fileHandler.close()
    
    #Writing Attachment(s)
    dirPath = path + os.sep + "Attachments" + os.sep
    if os.path.exists(dirPath):
        for filename in os.listdir(dirPath):
            path = os.path.join(dirPath, filename)
            #print "Attachment Path: " + path
            if not os.path.isfile(path):
                #print "Continuing ..."
                continue
        
            # Guess the content type based on the file's extension.  Encoding
            # will be ignored, although we should check for simple things like
            # gzip'd or compressed files.
            ctype, encoding = mimetypes.guess_type(path)
            #print "Attachment encoding: " + encoding
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            #print "Processing file ..."
            if maintype == 'text':
                fp = open(path)
                # Note: we should handle calculating the charset
                msg = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'image':
                fp = open(path, 'rb')
                msg = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'audio':
                fp = open(path, 'rb')
                msg = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
            else:
                fp = open(path, 'rb')
                msg = MIMEBase(maintype, subtype)
                msg.set_payload(fp.read())
                fp.close()
                    
                # Encode the payload using Base64
                encoders.encode_base64(msg)
            # Set the filename parameter
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            #print "Message Length: " + str(len(msg.as_string()))
            outer.attach(msg)
    
    #print "Attachment Length: " + str(len(outer.as_string()))
    # Now return the message
    extractedAttachment = outer.as_string()
    boundary = str(outer.get_boundary())
    mimePosition = str(extractedAttachment).find("MIME-Version: ")
    insertionPoint = str(extractedAttachment[mimePosition:]).find("\n")
    
    composedMessage = extractedAttachment[:mimePosition + insertionPoint] + extractedContent 
    composedMessage += "\n--" + boundary + "\n"
    composedMessage += "Content-Type: text/plain; charset=UTF-8"
    composedMessage += body
    composedMessage += "\n--" + boundary + "--\n"
    if not (len(extractedAttachment[mimePosition + insertionPoint+1:]) <= (len(2*boundary)+9)
        and len(extractedAttachment[mimePosition + insertionPoint+1:]) >= (len(2*boundary)+6)):
        composedMessage += extractedAttachment[mimePosition + insertionPoint+1:]
    #print composedMessage
    #str(composedMessage).replace("Body: ", "\n")
    
    return composedMessage

def determineFileType(self, path):
    typeDeterminant = magic.open(magic.MAGIC_NONE)
    typeDeterminant.load()
    fileType = typeDeterminant.file(path)
    typeDeterminant.close()
    
    return fileType

def determineActualDataPath(self, path):
    mountedPath = os.path.realpath(path)
    rootPath = os.path.realpath(PathUtils(path).getName())
    
    actualPath = rootPath[:str.rfind(rootPath, os.sep)]
    if (str(mountedPath).find(FSTemplates._suffix) != -1 and str.rfind(mountedPath, '[') != -1):
        actualPath += mountedPath[:str.rfind(mountedPath, '[')]
    else:
        actualPath += mountedPath
        
    return actualPath    

def flag2mode(flags):
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]
    
    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)
    
    return m

duplicatePaths = {}
transformer = Transformer()
transform = False

#@deprecated: 
class FSTemplates():
    #define your prefixes for types here    
    _file_ = "file_"
    _folder_ = "folder_"
    _none_ = "no type"
    _suffix = "[#]"
    _meta_storage = "#[meta-storage]#"
    _up = ".."
    
    #define your variables here for meta-content
    file_len = "length"
    file_type = "type"
    email_message = "email.eml"
    folder_back = "back"
    folder_tags = "tags"
    
    #Define the email integration constants here
    inferatoFS_email = "InferatoFS Email"
    _to = "To"
    _from = "From"
    
    #Switches
    transformation_switch = "-m"
#Creates meta-data in meta-storage for given name and returns path to meta-data 
def createMetaData(self, abspath):
    #path in meta-storage
    name = os.path.basename(abspath)
    metapath = os.path.join(self.root, FSTemplates._meta_storage, name + "-" + str(uuid1()))
    if not os.path.exists(metapath):
        os.mkdir(metapath)
    #location of folder where related tags are stored      
    tags_path = os.path.join(metapath, FSTemplates.folder_tags)
    #print "tags_path: " + tags_path
    if not os.path.isdir(tags_path):
        os.mkdir(tags_path)
    return metapath

def addMetaData(self, metasource, abspath):
    #print "addMetaData - metasource: " + metasource
    #print "addMetaData - abspath: " + abspath
    
    metapath = os.path.realpath(metasource)
    #location of folder where related with object tags are stored    
    tags_path = os.path.join(metapath, FSTemplates.folder_tags)
    #print "-------------------> " + tags_path
    if not os.path.isdir(tags_path):
        os.mkdir(tags_path)
    else:
        #TODO: do something. Normally should not happen
        pass

#Creates meta-data in meta-storage for given name and returns path to meta-data 
def createMetaData4tag(self, abspath):
    name = os.path.basename(abspath)
    #path in meta-storage
    metapath_real = os.path.realpath(abspath + FSTemplates._suffix)
    metapath = abspath + FSTemplates._suffix
    if not os.path.exists(metapath):
        storage = os.path.join(self.root, FSTemplates._meta_storage, name + "-" + str(uuid1()))
        os.mkdir(storage)
        return storage
    else:
        return metapath_real

def checkMeta(self, path):
    global transform
    
    for e in os.listdir("." + path):
        abspath = os.path.abspath(e)
        if not Parser(e).isMeta():
            #physical location of link to meta-data                
            linkpath = self.root
            if str(path).startswith(os.sep):
                linkpath = os.path.join(linkpath, str(path)[1:], e + FSTemplates._suffix)
            else:
                linkpath = os.path.join(linkpath, path, e + FSTemplates._suffix)

            if not os.path.exists(linkpath):
                metapath = createMetaData(self, abspath)
                if os.path.islink(linkpath):
                    os.unlink(linkpath)
                #Linking shortcut from actual data to folder in Metadata containing tags folder
                #print metapath
                #print linkpath + "\n"
                
                #print "Metapath: " + metapath
                #print "Linkpath: " + linkpath + "\n"
                
                if transform:
                    suffixLength = -1 * len(FSTemplates._suffix)
                    fileType = determineFileType(self, linkpath[:suffixLength])
                    #print "T R A N S F O R M"
                    if ((str(fileType).endswith(TransformerTemplate.email_message) and
                         str.find(linkpath, TransformerTemplate.header) != -1) or  
                        not str(fileType).endswith(TransformerTemplate.email_message)):
                        #print "About to Create Symlink ... "
                        os.symlink(metapath, linkpath)
                        #print "Done with Symlink Creation ... "
                else:
                    os.symlink(metapath, linkpath)
            elif not os.path.exists(linkpath + os.sep + FSTemplates.file_type):
                addMetaData(self, linkpath, abspath)
            else:
                #Logger.log( " Dublicate metadata creation for " + e + ". Canceled."                    
                pass
        else:
            #TODO: other types handling?
            pass

#takes absolute path of link to meta-storage and adds new link to meta-data for current source
#use only after tagging operation 
def addlink2tag(meta_path, source):
    max = 1000
    i = 0
    while(i < max):
        mlink = os.path.normpath(meta_path + os.sep + str(i))
        if not os.path.exists(mlink):
            break
        i = i + 1
    if i == 1000:
        print "Maximum limit is reached for link name (" + str(max) + "). Clear you you dublicate entries in '" + meta_path + "'"
    else:
        s2 = os.path.split(source)[0]
        d2 = os.path.normpath(meta_path + os.sep + str(i) + "_sourcedir")
        os.symlink(source, mlink)
        os.symlink(s2, d2)

#tags specified object
#NB! only absolute path allowed here
def tag(self, path, tag):
    #create link to tag in ..::/tags folder to tag    
    lnk = ""
    if str(path).count(FSTemplates._meta_storage) > 0:
        lnk = path
    else:
        #It doesn't find the # named shortcut in actual data folders
        lnk = path + FSTemplates._suffix + os.sep + FSTemplates.folder_tags + os.sep + os.path.split(tag)[1]
        #Faulty Calculation owing to appended Unique Number: 
        #lnk = self.root + os.sep + FSTemplates._meta_storage + path[str.rfind(path, "/"):] + FSTemplates._suffix + os.sep + FSTemplates.folder_tags + os.sep + os.path.split(tag)[1]
        
        if not os.path.exists(path + FSTemplates._suffix) and not os.path.exists(path + FSTemplates._suffix + os.sep + FSTemplates.folder_tags):
            desiredDirectory = path [str.rfind(path, "/")+1:]
            #print "Directories Path: " + self.root + os.sep + FSTemplates._meta_storage
            directoryList = os.listdir(self.root + os.sep + FSTemplates._meta_storage)
            #print "Directories Count: " + str(len(directoryList))
            
            directoryPath = None
            for directory in directoryList:
                #print "Directory: " + directory
                if str.find(directory, desiredDirectory) != -1:
                    #print "Match Found"
                    directoryPath = self.root + os.sep + FSTemplates._meta_storage + os.sep + directory + os.sep
                    lnk =  directoryPath + FSTemplates.folder_tags + os.sep + os.path.split(tag)[1]
                    break
    print lnk
    
    #print "Tag Exists: " + str(os.path.exists(tag))
    #print "Lnk Exists: " + str(os.path.exists(lnk))
    #print "Path to Tag Folder: " + lnk[:str.rfind(lnk, os.sep)]
    
    if (lnk != None and str.find(lnk, FSTemplates.folder_tags) != -1 
        and not os.path.exists(lnk + os.sep + "0") and not os.path.exists(lnk + os.sep + "0_sourcedir") 
        and not os.path.exists(lnk) and os.path.exists(lnk[:str.rfind(lnk, os.sep)])):
        os.symlink(tag, lnk)
        #create folder in meta-storage and obtain the link
        #look up in tag, if there is no "object::" link exists
        #then create it. Otherwise use existing one.    
        obj_link_path = tag + os.sep + os.path.basename(path) + FSTemplates._suffix
        obj_fake_path = tag + os.sep + os.path.basename(path)
        meta_link = createMetaData4tag(self, obj_fake_path)
        #reserve and create two links in meta-data to file and to its root-dir                
        addlink2tag(meta_link, path)
        #create link in folder to meta                
        if not os.path.exists(obj_link_path):
            os.symlink(meta_link, obj_link_path)

def untagInMeta(self, path):    
    self.state.initAction(3)
    
    #short name with suffix
    what = os.path.basename(os.path.dirname(os.path.dirname(path)))
    
    #real location of link in tag
    where = os.path.realpath(path) + os.sep + what
    
    #real location of meta-structure  
    metastructure = os.path.realpath(where)
    
    print "++++++++"
    print path
    print what
    print where
    print metastructure
    print "++++++++"
    
    if  os.path.exists(path):
        self.state.next()
        os.unlink(path)
        
    if  os.path.exists(where):
        self.state.next()
        os.unlink(where)        
        
    if  os.path.exists(metastructure):
        self.state.next()
        shutil.rmtree(metastructure)        
        
    if self.state.finishAction():
        print "Untagged successfully from " + str(path)
    else:
        print "Not all operation were performed while untagging from " + str(path) + ". Current state: " + str(self.state.cur_state)
    

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0777
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

class InferatoFS(Fuse):#TODO: refactor this
    #Fuse has no information about the usage of these files.   
    forbidden = ["autorun.inf", ".Trash", ".Trash-1000", "BDMV", ".xdg-volume-info", ".directory", ".krcdirs", ".kateconfig"]
    #True - disable VF + sequence deleting functionality for this flag
    hide_vfs = False

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        self.root = '/'
        self.state = StateUtils();
        #uncomment this to see what operation are supported
        #print Fuse._attrs

    def getattr(self, path):
        if os.path.split(path)[1] in self.forbidden:
            #ignore this stuff
            #TODO: find the right way of usage 
            pass        
        else:
            #capture the case, when user follows the symbolic link.
            if Parser(path).isMetaLink():
                st = MyStat()
                st.st_mode = stat.S_IFDIR | 0777
                st.st_nlink = 5
                return st
            elif not self.hide_vfs:               
                if Parser(path).isLenghFile():
                    st = MyStat()
                    st.st_mode = stat.S_IFREG 
                    st.st_nlink = 1
                    st.st_size = len(str(len(PathUtils(path).getName())))
                    return st
                elif str(path).endswith(FSTemplates.file_type):
                    st = MyStat()
                    st.st_mode = stat.S_IFREG 
                    st.st_nlink = 1
                    st.st_size = 0
                    return st
                elif str(path).endswith(FSTemplates.email_message):
                    st = MyStat()
                    st.st_mode = stat.S_IFREG 
                    st.st_nlink = 1
                    st.st_size = 0
                    return st
                else:
                    return os.lstat("." + path)
            return os.lstat("." + path)

    def readlink(self, path):        
        return os.readlink("." + path)
    
    def writeInferatoFSEmail(self, emailMessage):
        emailMessage.storagePath = emailMessage.storagePath + TransformerTemplate.forwardSlash
        
        #Create Message ID File
        if emailMessage.emailHeader._messageID != None:
            fileHandler = open(emailMessage.storagePath + TransformerTemplate._messageID, TransformerTemplate.fileWrite)
            fileHandler.write(emailMessage.emailHeader._messageID)
            fileHandler.close()
        
        #Create From File
        fileHandler = open(emailMessage.storagePath + TransformerTemplate._from, TransformerTemplate.fileWrite)
        if(emailMessage.emailHeader._from.fullName != emailMessage.emailHeader._from.emailAddress):
            fileHandler.write(emailMessage.emailHeader._from.fullName + TransformerTemplate.newLine)
        fileHandler.write(emailMessage.emailHeader._from.emailAddress)
        fileHandler.close()
        
        #Create Sender File
        if (emailMessage.emailHeader._sender != None and emailMessage.emailHeader._sender.fullName != TransformerTemplate.emptyString 
            and emailMessage.emailHeader._sender.emailAddress != TransformerTemplate.emptyString):
            fileHandler = open(emailMessage.storagePath + TransformerTemplate._sender, TransformerTemplate.fileWrite)
            if(emailMessage.emailHeader._sender.fullName != emailMessage.emailHeader._sender.emailAddress):
                fileHandler.write(emailMessage.emailHeader._sender.fullName + TransformerTemplate.newLine)
            fileHandler.write(emailMessage.emailHeader._sender.emailAddress)
            fileHandler.close()
        
        #Create Subject File
        if emailMessage.emailHeader._subject != None:
            fileHandler = open(emailMessage.storagePath + TransformerTemplate._subject, TransformerTemplate.fileWrite)
            fileHandler.write(emailMessage.emailHeader._subject)
            fileHandler.close()
            
        #Create Date File
        if emailMessage.emailHeader._dateTime != None:
            fileHandler = open(emailMessage.storagePath + TransformerTemplate._date, TransformerTemplate.fileWrite)
            fileHandler.write(emailMessage.emailHeader._dateTime)
            fileHandler.close()
        
        #Create Header File
        if emailMessage.actualFileName != None:
            headerFileName = TransformerTemplate.header + emailMessage.actualFileName
            #print "Header Path: " + emailMessage.storagePath + headerFileName
            fileHandler = open(emailMessage.storagePath + headerFileName, TransformerTemplate.fileWrite)
            fileHandler.write(emailMessage.entireHeader)
            fileHandler.close()
                
        #Create Body File
        if emailMessage.emailBody != None:
            fileHandler = open(emailMessage.storagePath + TransformerTemplate.body + emailMessage.emailBody._extension, TransformerTemplate.fileWrite)
            fileHandler.write(emailMessage.emailBody._body)
            fileHandler.close()
        
            #Create To Folder and Store Contacts
            if len(emailMessage.emailHeader._to) != 0:
                if not os.path.exists(emailMessage.storagePath + TransformerTemplate._to):
                    os.mkdir(emailMessage.storagePath + TransformerTemplate._to)
                    
                toPath = emailMessage.storagePath + TransformerTemplate._to + TransformerTemplate.forwardSlash
                
                for toContact in emailMessage.emailHeader._to:
                    fileHandler = open(toPath + toContact.fullName, TransformerTemplate.fileWrite)
                    if(toContact.fullName != toContact.emailAddress):
                        fileHandler.write(toContact.fullName + TransformerTemplate.newLine)
                    fileHandler.write(toContact.emailAddress)
                    fileHandler.close()
                            
            #Create Cc Folder and Store Contacts
            if len(emailMessage.emailHeader._cc) != 0:
                if not os.path.exists(emailMessage.storagePath + TransformerTemplate._cc):
                    os.mkdir(emailMessage.storagePath + TransformerTemplate._cc)
                    
                ccPath = emailMessage.storagePath + TransformerTemplate._cc + TransformerTemplate.forwardSlash
                
                for ccContact in emailMessage.emailHeader._cc:
                    fileHandler = open(ccPath + ccContact.fullName, TransformerTemplate.fileWrite)
                    if(ccContact.fullName != ccContact.emailAddress):
                        fileHandler.write(ccContact.fullName + TransformerTemplate.newLine)
                    fileHandler.write(ccContact.emailAddress)
                    fileHandler.close()
                    
            #Create Bcc Folder and Store Contacts
            if len(emailMessage.emailHeader._bcc) != 0:
                if not os.path.exists(emailMessage.storagePath + TransformerTemplate._bcc):
                    os.mkdir(emailMessage.storagePath + TransformerTemplate._bcc)
                    
                bccPath = emailMessage.storagePath + TransformerTemplate._bcc + TransformerTemplate.forwardSlash
                
                for bccContact in emailMessage.emailHeader._bcc:
                    fileHandler = open(bccPath + bccContact.fullName, TransformerTemplate.fileWrite)
                    if(bccContact.fullName != bccContact.emailAddress):
                        fileHandler.write(bccContact.fullName + TransformerTemplate.newLine)
                    fileHandler.write(bccContact.emailAddress)
                    fileHandler.close()
            
            #Create Attachments Folder and Store Attachments
            if len(emailMessage.emailBody._attachments) != 0:
                if not os.path.exists(emailMessage.storagePath + TransformerTemplate.attachments):
                    os.mkdir(emailMessage.storagePath + TransformerTemplate.attachments)
                
                if True: #self.duplicate != TransformerTemplate.attachmentsOnly:
                    attachmentsPath = emailMessage.storagePath + TransformerTemplate.attachments + TransformerTemplate.forwardSlash
                    
                    for attachment in emailMessage.emailBody._attachments:
                        fileHandler = open(attachmentsPath + attachment.attachmentName, TransformerTemplate.fileWrite)
                        fileHandler.write(attachment.attachedFile)
                        fileHandler.close()
                    
            del fileHandler
         
        return
    
    def readdir(self, path, offset):        
        global transform, transformer, duplicatePaths
        emailMessage = EmailMessage()
        
        yield fuse.Direntry(".")
        yield fuse.Direntry("..")
        
        if Parser(path).isMetaFolder():
            if not self.hide_vfs:
                # wanted to change the passed argument from 'file_len' to 'file_type
                #print "(1) " + path
                yield fuse.Direntry(FSTemplates.file_len)
                yield fuse.Direntry(FSTemplates.file_type)
                
                folder = path[str(path).rfind(os.sep):]
                if str(folder).find("From:") != -1 and str(folder).find("To:") != -1: 
                    yield fuse.Direntry(FSTemplates.email_message)
                
        if os.path.exists("." + path):
            for e in os.listdir("." + path):
                if transform:
                    #Check file type for email files
                    fileType = determineFileType(self, "." + path + TransformerTemplate.forwardSlash + e)
                    
                    #Process email file if found
                    if emailMessage and emailMessage.actualFileName and e.__eq__(emailMessage.actualFileName + FSTemplates._suffix):
                        pass
                    elif str(fileType).endswith(TransformerTemplate.email_message):
                        if str.find(e, TransformerTemplate.header) == -1:
                            transformer.workingPath = self.root + path + TransformerTemplate.forwardSlash + e
                            transformer.outputPath = emailMessage.pathToParent = "." + path + TransformerTemplate.forwardSlash
                            
                            #Read Input Email File
                            emailMessage.readEmailMessage(transformer)
                            
                            #Prepare Output Folder Name and Duplicity Count
                            emailMessage.prepareFolderName()
                            messageList = emailMessage.hashEmailMessage(transformer)        
                            emailNumber = emailMessage.occurenceNumber
                            if emailNumber != 0:
                                emailMessage.folderName += "[%(emailNumber)s]" % locals()        
                                
                                #Storage Path ~ Parent Folder for InferatoFS Email
                                emailMessage.storagePath = transformer.outputPath + emailMessage.folderName
                                
                                #Determine Nature of Duplication
                                if emailMessage.occurenceNumber != 1:
                                    emailMessage.determineDuplicate(messageList, transformer)
                                    #print emailMessage.duplicate + " - " + duplicate
                                    
                                if (os.path.exists(transformer.outputPath) and not os.path.exists(emailMessage.storagePath)
                                    and str(transformer.outputPath).find(emailMessage.folderName) == -1 
                                    ):#and emailMessage.duplicate != TransformerTemplate.absolute):
                                    #yield fuse.Direntry(emailMessage.folderName)
                                    if emailMessage.duplicate != TransformerTemplate.absolute:
                                        #print "Duplicate not found!"
                                        os.mkdir(emailMessage.storagePath)
                                        self.writeInferatoFSEmail(emailMessage)
                                    else:
                                        #os.mkdir(emailMessage.storagePath)
                                        self.symlink(os.path.realpath(emailMessage.duplicatePath), transformer.outputPath[1:] + emailMessage.folderName)
                                        
                                if emailMessage.duplicate != None and emailMessage.duplicate == TransformerTemplate.absolute:
                                    #os.link(emailMessage.duplicatePath, emailMessage.storagePath)
                                    #os.mkdir(emailMessage.storagePath[:-1] + FSTemplates._suffix)
                                    
                                    #You can't create a link on Mount's #. For renaming store the duplicate's path in global
                                    #and call rename after the # folder has been read and corresponding link on actual has been
                                    #created
                                    #print "Key: " + emailMessage.folderName[:-3]
                                    if emailMessage.folderName[:-3] not in duplicatePaths:
                                        duplicatePaths[emailMessage.folderName[:-3]] = emailMessage.duplicatePath 
                        else:
                            #For writing Header Files
                            yield fuse.Direntry(e)
                    elif not os.path.islink(e):
                        yield fuse.Direntry(e)
                        #print "Movement allowed for " + e
                        #if (str(e[-5:-4]).isdigit() and e[-6:-5] == TransformerTemplate.openingSquareBracket 
                            #and e[-4:-3] == TransformerTemplate.closingSquareBracket and e[-5:-4] != "1"):
                        if re.search("\[[2-9]\]\[\#\]\Z", e) != None:
                            hashedName = e[str.find(e, os.sep)+1:-6]
                            #print "Hash Key: " + hashedName
                            #print "Duplicate Path: " + duplicatePaths[hashedName]
                            if hashedName in duplicatePaths:
                                #print "Duplicate Path: " + duplicatePaths[hashedName]
                                self.rename(e[:-3], duplicatePaths[hashedName][:-1] + FSTemplates._suffix + os.sep + e[:-3])
                    else:
                        #print "(2) " + e
                        yield fuse.Direntry(e)
                else:
                    #print "\n(3) " + e
                    yield fuse.Direntry(e)
                    
                    if re.search("\[[2-9]\]\[\#\]\Z", e) != None:
                        ePath = self.root + path + TransformerTemplate.forwardSlash + e[:-3]
                        #print "Full Path: " + ePath
                        fileType = determineFileType(self, ePath)
                        #print "File Type is " + str(fileType)
                        if fileType != None and str.find(str.lower(fileType), "link") != -1:
                            pointedPath = fileType[str.find(fileType, os.sep):-1]
                            #print "Pointed Path is " + str(pointedPath[len(self.root):-1])
                            self.rename(e[:-3], "." + pointedPath[len(self.root):-1] + FSTemplates._suffix + os.sep + e[:-3])     
    #delete
    def unlink(self, path):
        if Parser(path).isMeta():
            
            if Parser(path).isTagFolder():                
                untagInMeta(self, self.getabs(path))                
                return
            
            elif Parser(path).isLenghFile():
                #do nothing since it is a virtual file
                return
            
            if self.state.cur_state[0] == 3:                
                #allow deleting VF for action 3    
                return
            print "Can not unlink " + str(path) + ". It is a system file."
            return
        else:
            mode = os.lstat("." + path)[0]
            #self.hide_vfs=True also means that first usr call was rmdir 
            #(folders could also contain meta-data links)
            if not self.hide_vfs:
                # if regular file, then delete meta-data before
                if  (mode & stat.S_IFREG) and (mode < stat.S_IFLNK):
                    metalink = os.path.realpath(self.root + path + FSTemplates._suffix)
                    os.unlink("." + path + FSTemplates._suffix)
                    shutil.rmtree(metalink)
            else:
                if Parser(path).isMeta() and (mode & stat.S_IFLNK) and (mode >= stat.S_IFLNK):
                    metalink = os.path.realpath(self.root + path)
                    shutil.rmtree(metalink)
        os.unlink("." + path)



    def rmdir(self, path):
        if Parser(path).isMeta():
            tulpe = PathUtils(self.getabs(path)).isAloneLink()
            print tulpe
            if tulpe[0]:
                untagInMeta(self, tulpe[1])
                return
            print " rmdir, this operation is restricted for path: " + path
        else:
            #disable temporary all virtual files
            self.hide_vfs = True
            metalink = os.path.realpath(self.root + path + FSTemplates._suffix)
            if os.path.exists("." + path + FSTemplates._suffix):
                os.unlink("." + path + FSTemplates._suffix)
            if os.path.exists(metalink):
                shutil.rmtree(metalink)
            os.rmdir("." + path)
            #enable vfiles
            
            self.hide_vfs = False

    def symlink(self, path, path1):
        #print "symlink - path: " + path
        #print "symlink - path1: " + path1
        
        #print "Path Exists: " + str(os.path.exists(path))
        #print "Path1 Exists: " + str(os.path.exists("." + path1))
                
        if Parser(path).isMeta():
            print "symlink: this operation is restricted for path: " + path
        else:
            os.symlink(path, "." + path1)

    def rename(self, path, path1):        
        
        print "Path: " + path
        print "Path1: " + path1
        
        #path to tag
        path_abs = self.getabs(path)
        
        #if not os.path.exists(path_abs):
            #pass
        
        #path of link in tags folder
        path1_abs = self.getabs(path1)
                    
        # equals to "[suffix]/tags"
        suf = FSTemplates._suffix + os.sep + FSTemplates.folder_tags
               
        # get ../tags abs_path
        path1_abs_minus = os.path.split(path1_abs)[0]
             
        # eliminate FSTemplates._suffix and get origin if exists
        path1_abs_minus_orig = str(path1_abs_minus).split(FSTemplates._suffix)[0]
                
        #destination root
        s = os.path.split(path1_abs)[0]
        
        print "====="
        
        #target and tag are equals
        if str(path_abs).__eq__(path1_abs_minus_orig):
            print "Can not tag itself!"
            return
                
        #expected sample input for path: [regular file/dir] and ...[FSTemplates._suffix]/[file/dir] where last one is metalink of directory
        if str(path1_abs_minus).endswith(FSTemplates._suffix) and not Parser(path_abs).isMeta() and os.path.isdir(path1_abs_minus_orig):
            print "tagging: multiple targets"
            self.state.initAction(1)
            self.state.next()
            tag(self, path_abs, path1_abs_minus_orig)
            self.state.finishAction()
        #expected sample input for path: ...[FSTemplates._suffix]/tags and [regular directory]
        elif os.path.isdir(path_abs):            
            print "tagging: multiple tags"
            self.state.initAction(2)
            self.state.next()            
            #already tagged with this name case
            if os.path.exists(str(path1_abs_minus + os.sep + os.path.split(path_abs)[1])):
                print str(path1_abs_minus + os.sep + os.path.split(path_abs)[1])
                print "Can not tag " + path1_abs_minus_orig + " with " + path_abs + ". You already tagged it with this name. Please, untag it first and then repeat."
            if  Parser(s).isTagFolder():                
                #candidate for tag can not be a special file/folder
                self.state.next()
                self.state
                if not Parser(path).isMeta():                    
                    obj_path = str(path1_abs).split(suf)[0]
                    self.state.next()
                    tag(self, obj_path, path_abs)
                    self.state.finishAction()
                else:
                    print "Restricted operation for tagging"
            else:
                print " forbidden operation for tagging: " + s + " is not a special folder as expected"
                #Still a Question: Should we actually allow the folder movement without considering various scenarios?
                print "Path-Suffix: ." + path + FSTemplates._suffix, "- ." + path1 + FSTemplates._suffix
                print "Just-Path: ." + path, "." + path1
                os.rename("." + path + FSTemplates._suffix, "." + path1 + FSTemplates._suffix)
                os.rename("." + path, "." + path1)
                
                #fix the broken link
                if os.path.isdir(s):
                    fixTaggedLink(self, s, path, path1) 

        elif Parser(path).isMeta() or Parser(path1).isMeta():
            print "rename: this operation is restricted for path " + path
        else:
            print "Here!"
            
            os.rename("." + path + FSTemplates._suffix, "." + path1 + FSTemplates._suffix)
            os.rename("." + path, "." + path1)
            
            if os.path.isdir(s):
                fixDeletedLink(self, s, path, path1)  
            
    def link(self, path, path1):
        #print "link - path: " + path
        #print "link - path1: " + path1
        
        os.link("." + path, "." + path1)

    def chmod(self, path, mode):
        if Parser(path).isMeta():
            print "chmod: this operation is restricted for path " + path
        else:
            os.chmod("." + path, mode)

    def chown(self, path, user, group):
        os.chown("." + path, user, group)

    def truncate(self, path, len):
        f = open("." + path, "a")
        f.truncate(len)
        f.close()

    def mknod(self, path, mode, dev):
        #print "mknod - path: " + path
        os.mknod("." + path, mode, dev)

    def mkdir(self, path, mode):
        if Parser(path).isMeta():
            print "mkdir: this operation is restricted for path " + path
        else:
            os.mkdir("." + path, mode)

    def utime(self, path, times):
        os.utime("." + path, times)

    def access(self, path, mode):
        #print "access - path: " + path
        if Parser(path).isMeta():
            pass
        elif not os.access("." + path, mode):
            #TODO: do custom access controls
            return -EACCES
            pass
        if not Parser(path).isMeta():
            checkMeta(self, path)
            #print "Done with checkMeta!"

    def statfs(self):
        """
        Should return an object with statvfs attributes (f_bsize, f_frsize...).
        Eg., the return value of os.statvfs() is such a thing (since py 2.2).
        If you are not reusing an existing statvfs object, start with
        fuse.StatVFS(), and define the attributes.

        To provide usable information (ie., you want sensible df(1)
        output, you are suggested to specify the following attributes:

            - f_bsize - preferred size of file blocks, in bytes
            - f_frsize - fundamental size of file blcoks, in bytes
                [if you have no idea, use the same as blocksize]
            - f_blocks - total number of blocks in the filesystem
            - f_bfree - number of free blocks
            - f_files - total number of file inodes
            - f_ffree - number of free file inodes
        """
        return os.statvfs(".")
    
    def fsinit(self):
        os.chdir(self.root)
        #TODO: make possible to resolve also relative path with data and mount folders
        if os.path.exists(FSTemplates._meta_storage):
            print " meta-storage found in '" + self.root + "'"
        else:
            print "creating meta-storage '" + self.root + "' ..."
            os.mkdir(FSTemplates._meta_storage)
            print "...done"
            
    #for local u
    #for local usage only
    def getabs(self, path):
        p = self.root + os.sep + path
        return os.path.normpath(p) 

    class InferatoFile(object):
        """
        Virtual File Manipulation
        TODO: Re-factor Class Name
        TODO: Relocate Class
        """
        
        direct_io = 1
        keep_cache = 0
        
        def __init__(self, path, flags, *mode):
            self.path = path
            if Parser(path).isLenghFile():
            #if cmp(path[str.rfind(path, '/')+1:len(path)], FSTemplates.file_len):
                self.file = tempfile.NamedTemporaryFile(mode='r+t')
                #File Name Length is being written to 'length' file here.
                self.file.writelines([str(len(PathUtils(path).getName()))])                
                self.fd = self.file.fileno()
            elif str(path).endswith(FSTemplates.file_type):
                self.file = tempfile.NamedTemporaryFile(mode='r+t')
                                
                actualPath = determineActualDataPath(self, path)
                fileType = determineFileType(self, actualPath)
                self.file.write(str(fileType))
                if fileType != None and str.find(str.lower(fileType), "link") != -1:
                    pointedPath = fileType[str.find(fileType, os.sep):-1]
                    #print "Link Target: " + pointedPath
                    fileType = determineFileType(self, pointedPath)
                    self.file.write("\nLink Target Type: ")
                    self.file.write(str(fileType))
                
                if(os.path.isdir(actualPath) and 
                   os.path.isdir(actualPath + os.sep + FSTemplates._to) and
                   os.path.isfile(actualPath + os.sep + FSTemplates._from)):
                    self.file.write("\n")
                    self.file.write(FSTemplates.inferatoFS_email)
                
                self.fd = self.file.fileno()
            elif str(path).endswith(FSTemplates.email_message):
                self.file = tempfile.NamedTemporaryFile(mode='r+t')
                tail = -1 * (len(FSTemplates.email_message) + len(FSTemplates._suffix) + 1)
                contentPath = determineActualDataPath(self, path[:tail])
                self.file.write(composeEmail(contentPath))
                self.fd = self.file.fileno()
            else:
                self.file = os.fdopen(os.open("." + path, flags, *mode), flag2mode(flags))
                #self.file = os.fdopen(os.open("." + path, flags, *mode), flag2mode(flags))
                self.fd = self.file.fileno()

        
        def read(self, length, offset):
            self.file.seek(offset)
            return self.file.read(length)

        def write(self, buf, offset):
            self.file.write(buf)
            return len(buf)

        def release(self, flags):
            self.file.close()

        def _fflush(self):
            if 'w' in self.file.mode or 'a' in self.file.mode:
                self.file.flush()

        def fsync(self, isfsyncfile):
            self._fflush()
            if isfsyncfile and hasattr(os, 'fdatasync'):
                os.fdatasync(self.fd)
            else:
                os.fsync(self.fd)

        def flush(self):
            self._fflush()
            # cf. xmp_flush() in fusexmp_fh.c
            os.close(os.dup(self.fd))


        def fgetattr(self):
            return os.fstat(self.fd)

        def ftruncate(self, len):
            self.file.truncate(len)

        def lock(self, cmd, owner, **kw):
            op = { fcntl.F_UNLCK : fcntl.LOCK_UN,
                   fcntl.F_RDLCK : fcntl.LOCK_SH,
                   fcntl.F_WRLCK : fcntl.LOCK_EX }[kw['l_type']]
            if cmd == fcntl.F_GETLK:
                return -EOPNOTSUPP
            elif cmd == fcntl.F_SETLK:
                if op != fcntl.LOCK_UN:
                    op |= fcntl.LOCK_NB
            elif cmd == fcntl.F_SETLKW:
                pass
            else:
                return -EINVAL
            fcntl.lockf(self.fd, op, kw['l_start'], kw['l_len'])

    def main(self, *a, **kw):        
        self.file_class = self.InferatoFile        
        return Fuse.main(self, *a, **kw)
    
def main():
    global transform
    
    #Process the transformation switch beforehand
    for arg in sys.argv:
        if str.__eq__(arg, FSTemplates.transformation_switch):
            transform = True
            sys.argv.remove(arg)
            break
    
    usage = """
Userspace nullfs-alike: mirror the filesystem tree from some point on.

""" + Fuse.fusage
    
    server = InferatoFS(version="%prog " + fuse.__version__,
                 usage=usage,
                 dash_s_do='setsingle')

    #multithread flag. If True, please protect all FS methods with locks 
    server.multithreaded = False

    server.parser.add_option(mountopt="root", metavar="PATH", default='/',
                             help="mirror filesystem from under PATH [default: %default]")
    server.parse(values=server, errex=1)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.root)
    except OSError:
        print >> sys.stderr, "can't enter root of underlying filesystem"
        sys.exit(1)
        
    #Calling the Length File Creation Method in Process
    server.main()


if __name__ == '__main__':
    main()
