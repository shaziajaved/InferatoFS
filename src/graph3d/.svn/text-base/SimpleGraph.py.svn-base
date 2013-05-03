from ConfigParser import ConfigParser
from parser import Parser
from templates import FSTemplates
from metautils import PathUtils
import networkx as nx
import os

class simpleGraph:

    graph = {}    
    root = None
    data = None
    
    def __init__(self):
        #load properties start
        cfgfile = os.path.split(__file__)[0] + os.sep + "sys.properties"
        parser = ConfigParser()
        parser.read(cfgfile)
        self.root = parser.get("init", "root")
        self.data = parser.get("init", "dat")
        #load properties end      
        self.myLoad()

    def getRoot(self):
        return self.root

    def getNameLengthString(self, path):
        ret = 0
        #make sure that this is not a special file and the special link exists 
        if not Parser(path).isMeta():
            length = path + FSTemplates._suffix + os.sep + FSTemplates.file_len
            file = open(length, "r")
            #we need to read only the first line
            if file:
                ret = file.readline()
        return ret

    def explore(self, arg, dir, files):
        if not Parser(dir).isMeta():
            for f in files:
                if not Parser(dir + f).isMeta():
                    if not self.graph.has_node(dir):
                        self.addNode(dir, "root of FS")
                    meta = f + " is entry of " + dir + "\n"
                    meta += "length of name: "
                    meta += self.getNameLengthString(dir + os.sep + f)
                    self.addNode(dir + os.sep + f, meta)
                    self.addEdge((dir, dir + os.sep + f + ""), "")

    def loadRelations(self, arg, dir, files):
        if not Parser(dir).isMeta():
            for f in files:
                if not Parser(dir + os.sep + f).isMeta():
                    fmeta_tags = dir + os.sep + f + FSTemplates._suffix + os.sep + FSTemplates.folder_tags
                    for en in os.listdir(fmeta_tags):
                        tag = PathUtils(fmeta_tags + os.sep + en).getRealPath(self.data, self.root)                        
                        self.addEdge((tag, dir + os.sep + f), "tag")


    def myLoad(self):
        self.graph = nx.MultiDiGraph(name='File System')
        os.path.walk(self.root, self.explore, "")
        os.path.walk(self.root, self.loadRelations, "")        

    def getNXGraph(self):
        return self.graph



    #add node to the graph
    # index: key 
    # xdata: data in text format
    # pointers: pointers in text format "1,2,3,4,5,rr,dsf"
    #point
    def addNode(self, index, xdata):
        self.graph.add_node(index, data=xdata)

    #links
    def addEdge(self, index, type):
        self.graph.add_edge(index[0], index[1], data=type)


    def getNodeData(self, index):
        return self.graph.node[index]['data']

    def getNodeLink(self, index):
        #return self.graph.node[index]['url']
        return index

    def getEdgeType(self, index):
        retArray = []
        try:
            list = self.graph[index[0]][index[1]].values()
            for innerDict in list:
                retArray.append(innerDict.get('data'))
        except KeyError:
            print "ERROR: missing edge index:", index
            return []
        return retArray


