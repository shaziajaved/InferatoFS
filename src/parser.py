from templates import FSTemplates
import os, re

templates = {"storage":"", #meta-storage
             "suffix":"", #special suffix used to separate special files from regular
             "sep":""#os.sep or default OS path separator
             }

#loads template strings and adds a backslashes before special symbols
def loadTemplates():
    string = ""
    replace = ["\\", "[", "]", "(", ")"]
    for i in FSTemplates._meta_storage:
        if i in replace:
            string = string + "\\"
        string = string + str(i)
    templates["storage"] = string
    string = ""
    for i in FSTemplates._suffix:
        if i in replace:
            string = string + "\\"
        string = string + str(i)
    templates["suffix"] = string
    if os.sep in replace:
        templates["sep"] = "\\" + os.sep
    else:
        templates["sep"] = os.sep

loadTemplates()

#RE templates for matching
meta_re = "([^" + templates["sep"] + "])+(" + templates["suffix"] + ")+|(" + templates["storage"] + ")+"
metapath_re = "((" + templates["suffix"] + ")|(" + templates["storage"] + "))+([" + templates["sep"] + "]){1}([^" + templates["sep"] + "])+"
istagfolder_re = "([^" + templates["sep"] + "]+(" + templates["suffix"] + ")+[" + templates["sep"] + "]" + FSTemplates.folder_tags + ")|((" + templates["storage"] + ")+[" + templates["sep"] + "]{1}[^" + templates["sep"] + "]+[" + templates["sep"] + "]{1}" + FSTemplates.folder_tags + "$)"
length_re = "([^" + templates["sep"] + "]+[" + templates["sep"] + "]" + FSTemplates.file_len + ")$"
metafolder_re = "(" + templates["suffix"] + ")$|(" + templates["storage"] + "[" + templates["sep"] + "]{1}[^" + templates["sep"] + "]+)$"

class Parser:
    abspath = ""


    #parses absolute path and gets its properties
    def __init__(self, abspath):
        self.abspath = abspath


    #any Meta file/folder in a proper view
    def isMeta(self):
        if not str(re.search(meta_re, self.abspath)).__eq__("None"):
            return True
        else:
            return False

    #isMeta + regular ending of path
    def isMetaPath(self):
        if self.isMeta() and not str(re.search(metapath_re, self.abspath)).__eq__("None"):
            return True
        return False

    #isMeta + endsWith([suffix])
    def isMetaLink(self):
        if self.isMeta() and str(self.abspath).endswith(FSTemplates._suffix):
            return True
        else:
            return False

    #isMeta() + comparison
    def isTagFolder(self):
        #ensures that given path is a special folder 'tags'. Strict location.
        if self.isMeta() and not str(re.search(istagfolder_re, self.abspath)).__eq__("None"):
            return True
        else:
            return False

    #isMeta() + comparison
    def isLenghFile(self):
        #ensures that given path is a special file 'length'. Non strict location.
        if self.isMetaPath() and not str(re.search(length_re, self.abspath)).__eq__("None"):
            return True
        else:
            return False

    #
    def isMetaFolder(self):
        if self.isMeta() and not str(re.search(metafolder_re, self.abspath)).__eq__("None"):
            return True
        else:
            return False
