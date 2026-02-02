import os
import PIL
import numpy


from numpy.lib.function_base import average


from numpy import zeros
from numpy import asarray

from mrcnn.config import Config

from mrcnn.model import MaskRCNN

from skimage.draw import polygon2mask
from skimage.io import imread

from datetime import datetime



from io import BytesIO
from mrcnn.utils import extract_bboxes
from numpy import expand_dims
from matplotlib import pyplot
from matplotlib.patches import Rectangle
from keras.backend import clear_session
import json
from flask import Flask, flash, request, jsonify, redirect, url_for, send_from_directory, render_template
from werkzeug.utils import secure_filename

from skimage.io import imread
from mrcnn.model import mold_image

import tensorflow as tf
import sys

from PIL import Image
import base64
from geometry_3d_generator import FloorPlan3DGenerator



global _model
global _graph
global cfg
ROOT_DIR = os.path.abspath("./")
WEIGHTS_FOLDER = "./weights"

from flask_cors import CORS, cross_origin

sys.path.append(ROOT_DIR)

MODEL_NAME = "mask_rcnn_hq"
WEIGHTS_FILE_NAME = 'maskrcnn_15_epochs.h5'

application=Flask(__name__, static_folder='static', static_url_path='/static')
cors = CORS(application, resources={r"/*": {"origins": "*"}})


class PredictionConfig(Config):
	# define the name of the configuration
	NAME = "floorPlan_cfg"
	# number of classes (background + door + wall + window)
	NUM_CLASSES = 1 + 3
	# simplify GPU config
	GPU_COUNT = 1
	IMAGES_PER_GPU = 1
	
@application.before_first_request
def load_model():
	global cfg
	global _model
	model_folder_path = os.path.abspath("./") + "/mrcnn"
	weights_path= os.path.join(WEIGHTS_FOLDER, WEIGHTS_FILE_NAME)
	cfg=PredictionConfig()
	print(cfg.IMAGE_RESIZE_MODE)
	print('==============before loading model=========')
	_model = MaskRCNN(mode='inference', model_dir=model_folder_path,config=cfg)
	print('=================after loading model==============')
	_model.load_weights(weights_path, by_name=True)
	global _graph
	_graph = tf.get_default_graph()


def myImageLoader(imageInput):
	image =  numpy.asarray(imageInput)
	
	
	h,w,c=image.shape 
	if image.ndim != 3:
		image = skimage.color.gray2rgb(image)
		if image.shape[-1] == 4:
			image = image[..., :3]
	return image,w,h

def getClassNames(classIds):
	result=list()
	for classid in classIds:
		data={}
		if classid==1:
			data['name']='wall'
		if classid==2:
			data['name']='window'
		if classid==3:
			data['name']='door'
		result.append(data)	

	return result				
def normalizePoints(bbx,classNames):
	normalizingX=1
	normalizingY=1
	result=list()
	doorCount=0
	index=-1
	doorDifference=0
	for bb in bbx:
		index=index+1
		if(classNames[index]==3):
			doorCount=doorCount+1
			if(abs(bb[3]-bb[1])>abs(bb[2]-bb[0])):
				doorDifference=doorDifference+abs(bb[3]-bb[1])
			else:
				doorDifference=doorDifference+abs(bb[2]-bb[0])


		result.append([bb[0]*normalizingY,bb[1]*normalizingX,bb[2]*normalizingY,bb[3]*normalizingX])
	return result,(doorDifference/doorCount)	
		

def turnSubArraysToJson(objectsArr):
	result=list()
	for obj in objectsArr:
		data={}
		data['x1']=obj[1]
		data['y1']=obj[0]
		data['x2']=obj[3]
		data['y2']=obj[2]
		result.append(data)
	return result



@application.route('/viewer')
def viewer():
	"""Serve the 3D viewer web interface"""
	return send_from_directory('static', 'index.html')


@application.route('/',methods=['POST'])
def prediction():
	global cfg
	imagefile = PIL.Image.open(request.files['image'].stream)
	image,w,h=myImageLoader(imagefile)
	print(h,w)
	scaled_image = mold_image(image, cfg)
	sample = expand_dims(scaled_image, 0)

	global _model
	global _graph
	with _graph.as_default():
		r = _model.detect(sample, verbose=0)[0]

	#output_data = model_api(imagefile)

	data={}
	bbx=r['rois'].tolist()
	temp,averageDoor=normalizePoints(bbx,r['class_ids'])
	temp=turnSubArraysToJson(temp)
	data['points']=temp
	data['classes']=getClassNames(r['class_ids'])
	data['Width']=w
	data['Height']=h
	data['averageDoor']=averageDoor
	return jsonify(data)


@application.route('/generate3d', methods=['POST'])
def generate_3d():
	"""
	Generate 3D model from floor plan image
	Returns glTF 2.0 format with embedded binary data
	"""
	global cfg

	# Get optional parameters
	wall_height = float(request.form.get('wall_height', 3.0))
	wall_thickness = float(request.form.get('wall_thickness', 0.15))
	door_height = float(request.form.get('door_height', 2.1))
	window_height = float(request.form.get('window_height', 1.2))
	window_sill_height = float(request.form.get('window_sill_height', 0.9))

	# Load and process image
	imagefile = PIL.Image.open(request.files['image'].stream)
	image, w, h = myImageLoader(imagefile)
	print(f"Image dimensions: {h}x{w}")

	scaled_image = mold_image(image, cfg)
	sample = expand_dims(scaled_image, 0)

	# Run detection
	global _model
	global _graph
	with _graph.as_default():
		r = _model.detect(sample, verbose=0)[0]

	# Prepare detection JSON
	data = {}
	bbx = r['rois'].tolist()
	temp, averageDoor = normalizePoints(bbx, r['class_ids'])
	temp = turnSubArraysToJson(temp)
	data['points'] = temp
	data['classes'] = getClassNames(r['class_ids'])
	data['Width'] = w
	data['Height'] = h
	data['averageDoor'] = averageDoor

	# Generate 3D model
	generator = FloorPlan3DGenerator(
		wall_height=wall_height,
		wall_thickness=wall_thickness,
		door_height=door_height,
		window_height=window_height,
		window_sill_height=window_sill_height
	)

	gltf_dict, buffer_data, metadata = generator.export_to_gltf_dict(data)

	# Encode binary buffer as base64
	buffer_base64 = base64.b64encode(buffer_data).decode('utf-8')

	# Add buffer data as data URI to glTF
	gltf_dict['buffers'][0]['uri'] = f"data:application/octet-stream;base64,{buffer_base64}"

	# Return complete response
	response = {
		'detection': data,
		'gltf': gltf_dict,
		'metadata': metadata
	}

	return jsonify(response)


if __name__ =='__main__':
	application.debug=True
	print('===========before running==========')
	application.run()
	print('===========after running==========')
