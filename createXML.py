import os
import flask 
import pathlib
import shutil
import xml.etree.ElementTree as ET
import uuid
import datetime 
import hashlib as hl
import base64 as b64
import mimetypes as mt

from pathlib import Path
from flask import request, jsonify
from os import scandir
from zipfile import ZipFile

app = flask.Flask(__name__)

dirPath = ""
name = ""
dcplist = []

# Create a new resource.
@app.route("/dcp", methods=['POST'])
def getfile():
    files = request.files.getlist("file")
    for file in files:
        with ZipFile(file,'r') as zip:
            zip.extractall(os.getcwd())
        dcplist.append(file.filename)
    return jsonify(dcplist)


# Retrieve an existing resource.
@app.route("/dcp", methods=['GET'])
def fileinfo():
    information=[]
    for i in range(len(dcplist)):
        name = Path(dcplist[i]).stem
        subinfo = []
        dirpath = os.getcwd()+'\ '+name
        dirpath = dirpath.replace(" ","")
        for (d_path, d_names,f_names) in os.walk(dirpath):
            subinfo.extend(f_names)
        information.append(subinfo)
    return jsonify(os.listdir(os.getcwd()),information)

# Delete a resource.
@app.route("/dcp", methods=['DELETE'])
def deldcp():
    for i in range(len(dcplist)):
        name = Path(dcplist[i]).stem
        dirpath = os.getcwd()+'\ '+name
        dirpath = dirpath.replace(" ","")
        # print(dirpath)
        shutil.rmtree(dirpath,ignore_errors=False, onerror=None)
    return jsonify(os.listdir(os.getcwd()))


# Generate xml files
@app.route("/dcp", methods=["PUT"])
def Generate_PKL_AssetMAP():
    for i in range(len(dcplist)):
        name = Path(dcplist[i]).stem
        filename = name + '.pkl'
        dirPath = os.getcwd()+' \ '+name + ' \ '
        PackingList = ET.Element("PackingList", attrib={'xmlns':'http://www.smpte-ra.org/schemas/429-8/2007/PKL'})
    
        ET.SubElement(PackingList,"Id").text = "urn:uuid:" + str(uuid.uuid4())
        ET.SubElement(PackingList,"AnnotationText").text = filename.rsplit('.')[0]
        ET.SubElement(PackingList,"IssueDate").text = str(datetime.datetime.utcnow().isoformat(timespec="seconds")+"+00:00")
        ET.SubElement(PackingList, "Issuer").text = "Prasanth"
        ET.SubElement(PackingList, "Creator").text = "Qube wire"
        AssetList = ET.SubElement(PackingList, "AssetList")
        dirPath = dirPath.replace(" ","")
        for (dirpath, subdirnames, filenames) in os.walk(dirPath):
            for file in filenames:
                if '.mxf' ==  pathlib.Path(file).suffix:
                
                    Asset = ET.SubElement(AssetList,"Asset")
                    ET.SubElement(Asset, "Id").text = "urn:uuid:" + str(uuid.uuid4())
                    ET.SubElement(Asset, "AnnotationText").text = file
                    Hash = ET.SubElement(Asset, "Hash")
                    # print(dirpath+'/'+file)
                    h = hl.sha1()
                    Path_file = dirpath+' \ '+file
                    Path_file = Path_file.replace(" ","")
                    with open(Path_file,'rb') as hash_file:
                        chunk = 0
                        while chunk != b'':
                            chunk =hash_file.read(1024)
                            h.update(chunk)
                    Hash.text = b64.b64encode(h.digest()).decode("utf-8")
                
                    ET.SubElement(Asset, "Size").text = str(os.stat(Path_file).st_size)
                
                    Type = ET.SubElement(Asset, "Type")
                    f = str(file)
                    if "pcm" in f:
                        Dcpkind = "Sound"
                    elif "j2k" in f or "jp2k" in f:
                        Dcpkind = "Picture"
                    else:
                        Dcpkind = "None"
                    
                    if ".mxf" in f:
                        Type.text = "application/x-smpte-mxf;asdcpKind=" + Dcpkind
                    else:
                        Type.text = str(mt.guess_type(file)[0]) + ";asdcpKind=" + Dcpkind
            
        tree2 = ET.ElementTree(PackingList)
        ET.indent(tree2, space="\t", level=0)
            
        tree2.write(os.path.join(dirPath,filename), encoding='utf-8', xml_declaration=True)
    
        filename = "ASSETMAP"
    
        dirPath = os.getcwd()+' \ '+ name + ' \ '
        dirPath = dirPath.replace(" ","")
        pkltree = ET.parse(dirPath + name + '.pkl')
        pklroot = pkltree.getroot()
        ns = {'myns':'http://www.smpte-ra.org/schemas/429-8/2007/PKL'}
        AssetMap = ET.Element("AssetMap", attrib={'xmlns':'http://www.smpte-ra.org/schemas/429-9/2007/AM'})
    
        ET.SubElement(AssetMap,"Id").text = "urn:uuid:" + str(uuid.uuid4())
        ET.SubElement(AssetMap,"AnnotationText").text = "Assets of " + filename.rsplit('.')[0]  # name instead of filename.
        ET.SubElement(AssetMap, "Creator").text = "Qube wire"
        ET.SubElement(AssetMap, "VolumeCount").text  = str(1)
        ET.SubElement(AssetMap,"IssueDate").text = str(datetime.datetime.utcnow().isoformat(timespec="seconds")+"+00:00")
        ET.SubElement(AssetMap, "Issuer").text = "Prasanth"
        AssetList = ET.SubElement(AssetMap, "AssetList")

    
        for (dirpath, subdirnames, filenames) in os.walk(dirPath):
            for file in filenames:
                f=str(file)
                if "mxf" in f or "pkl" in f:
                
                    Asset = ET.SubElement(AssetList, "Asset")
                
                    AnnotationText = ET.Element("AnnotationText")
                    if "pkl" in f:
                        AnnotationText.text = file.rsplit('.')[0]
                    else:
                        AnnotationText.text = file
                
                
                    Id = ET.SubElement(Asset, "Id")
                    if "pkl" in f:
                        Id.text = pklroot.find('myns:Id',ns).text
                    
                    else:
                        for node in pklroot.findall('myns:AssetList',ns):
                            for snode in node.findall('myns:Asset',ns):
                                if AnnotationText.text == snode.find('myns:AnnotationText',ns).text:
                                    Id.text = snode.find('myns:Id',ns).text
                                
                    Asset.append(AnnotationText)
                
                    if "pkl" in f:
                        ET.SubElement(Asset,"PackingList").text = 'true'
                
                    ChunkList = ET.SubElement(Asset, "ChunkList")
                    Chunk = ET.SubElement(ChunkList, "Chunk")
                    directory = ''
                    for i in range(dirpath.index(dirPath) + len(dirPath) , len(dirpath)):
                        directory = directory + dirpath[i]
                    if directory == '':
                        path = file
                    else:
                        path = directory + " \ " + file
                        path = path.replace(' ','')
                    ET.SubElement(Chunk, "Path").text = path
            
        tree1 = ET.ElementTree(AssetMap)
        ET.indent(tree1, space="\t", level=0)    
        tree1.write(os.path.join(dirPath,filename), encoding='utf-8', xml_declaration=True)
        
    return " Successfully PKL and ASSETMAP files are uploaded."
    
if __name__ == "__main__":
    app.run()