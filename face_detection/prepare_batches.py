# -*- coding: utf8 -*-
import csv, sys, os, cPickle, math, random, unicodedata
from os.path import join
import cv2, numpy
import utils

DEFAULT_FACE_SIZE = 32

def prepare_image(image, grayscale=False):
	if grayscale:
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		prepared_image = numpy.zeros((gray.size), dtype="uint8")
		bgr_index = 0
		for i in range(gray.shape[0]):
			for j in range(gray.shape[1]):
				prepared_image[bgr_index] = gray[i, j]
				bgr_index+=1
		return prepared_image
	else:
		green_start = image.size / 3  # 1/3 of batched_image size
		blue_start = green_start * 2  # 2/3 of batched_image size
		# red_start = 0
		prepared_image = numpy.zeros((image.size), dtype="uint8")
		bgr_index = 0
		for i in range(image.shape[0]):
			for j in range(image.shape[1]):
				prepared_image[bgr_index + blue_start] = image[i, j, 0]
				prepared_image[bgr_index + green_start] = image[i, j, 1]
				prepared_image[bgr_index] = image[i, j, 2]
				bgr_index+=1
		return prepared_image

def restore_image(batched_image):
	green_start = batched_image.size / 3  # 1/3 of batched_image size
	blue_start = green_start * 2  # 2/3 of batched_image size
	# red_start = 0
	batched_image_size = int(math.sqrt(green_start))  # sqrt of batched_image/3, the length of the edge
	restored_image = numpy.zeros((batched_image_size, batched_image_size, 3), dtype="uint8")
	bgr_index = 0
	for i in range(batched_image_size):
		for j in range(batched_image_size):
			restored_image[i,j]=[batched_image[bgr_index + blue_start],
								 batched_image[bgr_index + green_start],
								 batched_image[bgr_index]
								 ]
			bgr_index+=1
	return restored_image


def pickle(data, filename):
	output = open(filename, 'wb')  # write binary
	# a third argument may be given - protocol; -1 is the highest
	# cPickle.dump(data, output, -1)
	cPickle.dump(data, output)
	output.close()


def unpickle(path_to_file):
	open_file = open(path_to_file, 'rb')  # read binary
	data_dict = cPickle.load(open_file)
	open_file.close()
	return data_dict


def folder_tree_to_dictionary(path_to_folder):
	"""
	Assumes that root is folder that has a number of folders in it. Those folders have
	files in them
	"""
	folder_tree_dictionary = {}
	folders_list = os.listdir(path_to_folder)
	for folder in folders_list:
		folder_tree_dictionary[folder] = os.listdir(join(path_to_folder, folder))
	return folder_tree_dictionary


def level_list(alist, desired_length):
	"""
	Levels list to desired length.
	"""
	# remove random elements if longer
	while len(alist) > desired_length:
		alist.pop(random.randrange(len(alist)))
	# duplicate random elements if shorter
	while len(alist) < desired_length:
		alist.append(random.choice(alist))

"""
batch dictionary keys:
	data <type 'numpy.ndarray'> - transformed numpy images in numpy list
	labels <type 'list'> - nth index in meta[label_names]
	batch_label <type 'str'> batch name i of j a.la training batch 1 of 5
	filenames <type 'list'> nth in filenames is the image filename of nth in data

meta dictionary keys:
	num_cases_per_batch <type 'int'> - number of samples in batch
	label_names <type 'list'> - list of person names
	num_vis <type 'int'> - image.size
"""
def create_batches(path_to_structured_folder_tree, path_to_results, num_cases_per_batch, nr_of_images, image_size=DEFAULT_FACE_SIZE, use_grayscale=False):
	utils.mkdir(path_to_results)
	meta = {"label_names": [],
			"num_cases_per_batch": num_cases_per_batch,
			"num_vis": image_size * image_size}  # being used below
	if not use_grayscale:
		meta["num_vis"] *= 3
	folder_tree_dictionary = folder_tree_to_dictionary(path_to_structured_folder_tree)
	person_indexes = {}
	# 1. randomly copy images until the folder has the needed number of images
	# 2. remove randomly surplus images from folders than have more images than needed
	for folder in folder_tree_dictionary.keys():
		level_list(folder_tree_dictionary[folder], nr_of_images)
		# create dictionary of person names and their respective index in meta
		converted_folder_name =  unicodedata.normalize('NFKD', folder.decode("latin-1")).encode('ascii','ignore')
		meta["label_names"].append(converted_folder_name)
		person_indexes[folder] = len(meta["label_names"]) - 1

	total_nr_of_images = sum([len(folder_tree_dictionary[folder]) for folder in folder_tree_dictionary])
	if num_cases_per_batch <= total_nr_of_images:
		real_batch_size = num_cases_per_batch
	else:
		real_batch_size = total_nr_of_images
	data_means = numpy.zeros((meta["num_vis"], math.ceil(total_nr_of_images / float(num_cases_per_batch))))
	batch = {"data": numpy.empty((meta["num_vis"], real_batch_size),  dtype="uint8"),
			 "labels": [],
			 "batch_label": "",
			 "filenames": []}
	batch_data_index = 0
	batch_number = 0
	while folder_tree_dictionary:
		# 1. take out random filename from dictionary
		random_folder = random.choice(folder_tree_dictionary.keys())
		random_filename = folder_tree_dictionary[random_folder].pop(random.randrange(len(folder_tree_dictionary[random_folder])))
		# if folder has been popped empty, remove the folder
		if not folder_tree_dictionary[random_folder]:
			del folder_tree_dictionary[random_folder]
		# load and prepare the face
		face = cv2.imread(join(path_to_structured_folder_tree, random_folder, random_filename))
		face = cv2.resize(face, (image_size, image_size))
		transformed_face = prepare_image(face, use_grayscale)
		# fill the data in current batch
		batch["data"][:, batch_data_index] = transformed_face
		batch["labels"].append(person_indexes[random_folder])
		batch["filenames"].append(random_filename)
		batch_data_index += 1

		# if the batch is full then dump this into file
		if batch_data_index == real_batch_size:
			data_means[:,batch_number] = numpy.mean(batch['data'], 1)
			# dump batch
			batch["batch_label"] = "data batch %d" % batch_number
			batch_number += 1
			pickle(batch, join(path_to_results, batch["batch_label"].replace(" ", "_")))

			# reset the depending variables
			total_nr_of_images = sum([len(folder_tree_dictionary[folder]) for folder in folder_tree_dictionary])
			if num_cases_per_batch <= total_nr_of_images:
				real_batch_size = num_cases_per_batch
			else:
				real_batch_size = total_nr_of_images
			batch = {"data": numpy.empty((meta["num_vis"], real_batch_size),  dtype="uint8"),
					 "labels": [],
					 "batch_label": "",
					 "filenames": []}
			batch_data_index = 0
	# dump metadata
	meta['data_mean'] = numpy.mean(data_means,1)
	pickle(meta, join(path_to_results, "batches.meta"))


"""
prepare_batches.py <folder with people-named-folders> <min nr of images>
"""
if (len(sys.argv) > 4):
	path_to_structured_folder_tree = sys.argv[1]
	path_to_results = sys.argv[2]
	num_cases_per_batch = int(sys.argv[3])
	nr_of_images = int(sys.argv[4])
	face_size = DEFAULT_FACE_SIZE
	if (len(sys.argv) > 5):
		face_size = int(sys.argv[5])
	use_gray = False
	if (len(sys.argv) > 6) and (sys.argv[6].lower() == "true"):
		use_gray = True
	create_batches(path_to_structured_folder_tree, path_to_results, num_cases_per_batch, nr_of_images, face_size, use_gray)
else:
	raise KeyError('Not enough arguments')

