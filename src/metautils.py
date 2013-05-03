import os, sys
from templates import FSTemplates
from parser import Parser
class PathUtils:
    path = ""
    def __init__(self, path):
        self.path = path

    def getName(self):
        #expects root of meta-folder for certain file
        #returns separated from special marks name
        name = os.path.split(self.path)[0]
        name = os.path.split(name)[1]
        if str(self.path).count(FSTemplates._meta_storage) > 0:
            return name[0:len(name) - 37]
        else:
            name = str(name).split(FSTemplates._suffix)[0]
            return name

    def getRealPath(self, datapath, mntpath):
        #returns real path for path in mnt path context
        ret = os.path.realpath(self.path)
        return str(ret).replace(datapath, mntpath, 1)
    
    def isAloneLink(self):
        #makes sure, that path is stand-alone meta-link
        #returns tulpe(boolean, path), where boolean marks yes/no condition 
        #and path contains a meta-link string from another side  
        what = str(self.path).rpartition(FSTemplates._suffix)[0]
        
        #short folder name, where self.path was found
        tag_carrier = os.path.basename(str(os.path.split(self.path)[0]))

        
        if not Parser(what).isMeta():    
            if not os.path.exists(what):        
                target = os.path.realpath(self.path + os.sep + "0") + FSTemplates._suffix + os.sep + FSTemplates.folder_tags + os.sep + tag_carrier
                if os.path.exists(target):
                    return (True, target) 
        return (False, "None")
        

class StateUtils:
    action = {0:"waiting",
             1:"one tag, many targets",
             2:"one target, many tags",
             3:"untag"
             }
    cur_state = [0, 0]
    
    def __init__(self):
        self.st_matrix = [[self.action.get(0)],
                          [self.action.get(1), "tag"],
                          [self.action.get(2), "target check", "tag  check", "tag"],
                          [self.action.get(3), "delete meta-link", "delete link", "delete structure"]
                          ]
    
    def next(self):
        #go to the next action state. Returns True if success
        try:            
            if not (self.cur_state[1] + 1) in range(len(self.st_matrix[self.cur_state[0]])):
                raise            
            self.cur_state[1] = self.cur_state[1] + 1            
            return True
        except:                     
            return False            

    def finishAction(self):
        #returns True, if current state can be returned to waiting
        try:
            action = self.cur_state[0]
            action_st = self.cur_state[1]           
            if (len(self.st_matrix[action]) - 1) != action_st:
                raise            
            self.cur_state = [0, 0]                       
            return True          
        except:            
            return False
        
    def initAction(self, action):
        #initialize action in cur_state. Returns True if success
        try:            
            self.cur_state[0] = action
            self.cur_state[1] = 0;
            return True
            raise
        except:
            print "initAction: Unexpected error", sys.exc_info()[0]
            return False
