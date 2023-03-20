import os
import zipfile
import flask 
from flask import request, redirect, flash,  send_file, send_from_directory
from werkzeug.utils import secure_filename

import xml.etree.ElementTree as ET
import uuid
import datetime 
import hashlib as hl
import base64 as b64
import mimetypes as mt

app = flask.Flask(__name__)
app.secret_key = "secret key"

ALLOWED_EXTENSIONS = set(['mxf','py'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

dirPath = ""

def GeneratePKL(filename, dirPath):
    
    PackingList = ET.Element("PackingList", attrib={'xmlns':'http://www.smpte-ra.org/schemas/429-8/2007/PKL'})
    
    ET.SubElement(PackingList,"Id").text = "urn:uuid:" + str(uuid.uuid4())
    ET.SubElement(PackingList,"AnnotationText").text = filename.rsplit('.')[0]
    ET.SubElement(PackingList,"IssueDate").text = str(datetime.datetime.utcnow().isoformat(timespec="seconds")+"+00:00")
    ET.SubElement(PackingList, "Issuer").text = "Prasanth"
    ET.SubElement(PackingList, "Creator").text = "Qube wire"
    AssetList = ET.SubElement(PackingList, "AssetList")
    
    for (dirpath, subdirnames, filenames) in os.walk(dirPath):
        for file in filenames:
            f=str(file)
            if "mxf" in f:
                
                Asset = ET.SubElement(AssetList,"Asset")
                ET.SubElement(Asset, "Id").text = "urn:uuid:" + str(uuid.uuid4())
                ET.SubElement(Asset, "AnnotationText").text = file
                Hash = ET.SubElement(Asset, "Hash")
                # print(dirpath+'/'+file)
                h = hl.sha1()
                with open(dirpath+'/'+file,'rb') as hash_file:
                    chunk = 0
                    while chunk != b'':
                        chunk =hash_file.read(1024)
                        h.update(chunk)
                Hash.text = b64.b64encode(h.digest()).decode("utf-8")
                
                ET.SubElement(Asset, "Size").text = str(os.stat(dirpath+'/'+file).st_size)
                
                Type = ET.SubElement(Asset, "Type")
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
                
def GenerateAsset(filename,name,dirPath):
    pkltree = ET.parse(dirPath+'/'+name)
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
                for i in range(dirpath.index(dirPath) + len(dirPath) + 1, len(dirpath)):
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

def dir_finding(direc,file_with_dir):
    file_wout_dir = ''
    for i in range(0, file_with_dir.index('/')):
        direc = direc + file_with_dir[i]
    direc = direc + '/'

    # print("make directory with this name: ",direc)
    for i in range(file_with_dir.index('/')+1,len(file_with_dir)):
        file_wout_dir = file_wout_dir + file_with_dir[i]
    return direc,file_wout_dir
    
@app.route('/upload', methods=['GET'])
def upload_form():
	return flask.render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('files[]')
    # dirPath = "C:/Users/3108p/OneDrive/Desktop/QUBE/SampleREpo/sampleRepo/"
    global dirPath
    dirPath = dirPath + str(request.form.get("foldername"))
    for file in files:
        if file and allowed_file(file.filename):
            direc = ''
            while '/' in file.filename:
                direc, file.filename = dir_finding(direc,file.filename)
            # print(file.filename)
            direc = direc.rstrip(direc[-1])
            if not os.path.exists(direc):
                os.makedirs(direc)
                # print("Created: ", direc)
            # else:
                # print("Already created: ", direc)
            filename = secure_filename(file.filename)
            app.config['UPLOAD_FOLDER'] = direc
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # print(filename)
    
    name = dirPath[::-1]
    if "/" in dirPath:
        name = name[:(name.find("/"))][::-1] + ".pkl.xml"
    else:
        name = name[::-1] + ".pkl.xml"
    print(name)
    GeneratePKL(name,dirPath)
    GenerateAsset("ASSETMAP",name,dirPath)
    return "Folder Uploaded Successfully to your Current Working Directory"
    # return str(file)

@app.route('/download', methods=['GET'])
def download_folder():
    global dirPath
    Path_dir = os.getcwd() + " \ " + dirPath #+ " \ "
    Path_dir = Path_dir.replace(" ","")
    zipfolder = zipfile.ZipFile('DCP.zip','w', compression=zipfile.ZIP_STORED)
    for root,dirs, files in os.walk(Path_dir):
        for file in files:
            path = root[root.find(dirPath):] + " \ "+file
            path = path.replace(" ","")
            # print(path)
            zipfolder.write(path)
    zipfolder.close()
    
    return send_file('DCP.zip', mimetype = 'zip', attachment_filename = 'DCP.zip', as_attachment = True)

    
if __name__ == "__main__":
    
    app.run()
    
    
    
# zipfolder = zipfile.ZipFile('DCP.zip','w', compression=zipfile.ZIP_STORED)
    # for root,dirs, files in os.walk(dirPath):
    #     for file in files:
    #         zipfolder.write(dirPath+file)
    # zipfolder.close()
    
    # return send_file('DCP.zip', mimetype = 'zip', attachment_filename = 'DCP.zip', as_attachment = True)
