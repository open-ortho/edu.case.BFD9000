#!/usr/bin/env python3
"""
TreeRez
convert and resize
"""

__author__ = "Frenchfaso"
__version__ = "0.1.0"
__license__ = "MIT"


import logging
logging.basicConfig(level=logging.INFO)
from PIL import Image
import numpy as np
import os
from random import sample
import argparse


def get_patients_sample() -> list:
	""" Get patients folders from the source folder and return a list of random samples."""
	
	patients = list([obj.name for obj in os.scandir(source_folder) if obj.is_dir()])
	patients_sample = sample(patients, quantity)
	logging.info(f"Sampled {len(patients_sample)} patients out of {len(patients)} total.")
	return patients_sample


def get_scans(patients_sample) -> list:
	""" Return a list with all the scans of the sampled patients """
	
	scans = []
	for patient in patients_sample:
		xray_types = os.scandir(os.path.join(source_folder, patient))
		for xray in xray_types:
			if(xray.is_dir()):
				for img in os.scandir(xray.path):
					if(img.name.lower().endswith(('tif','tiff'))):
						scans.append(img.path)
	return scans
	
def autotrim(np_img):
	""" Crop the image discarding white 'noise' - takes a numpy array as input, returns a trimmed numpy array as output """

	mask = np_img < args.trim
	coords = np.argwhere(mask)
	x0, y0 = coords.min(axis=0)
	x1, y1 = coords.max(axis=0) + 1
	np_cropped = np_img[x0:x1, y0:y1]
	return np_cropped
	
	
def convert(scans):
	""" Open each scan, convert it to 8bit RGB format, resize to THUMBNAIL_SIZE and save it as PNG in DESTINATION_FOLDER """
	count = 0
	for xray in scans:
		try:
			with Image.open(xray) as im:
				np_im = np.array(im)
				np_im = np_im / np.amax(np_im) * 255 # Convert to 8 bit.
				try:
					cropped_np_im = autotrim(np_im)
					im = Image.fromarray(cropped_np_im)
				except:
					logging.warning(f"Error while autotrimming {xray}. Skipping.")
					im = Image.fromarray(np_im)

				im = im.convert(mode='RGB') 
				im.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
				p = os.path.join(destination_folder, os.path.relpath(xray, source_folder))
				d = os.path.dirname(p)
				f = os.path.splitext(os.path.basename(p))[0]
				try:
					if not args.dryrun:
						filename = os.path.join(d, f"{f}.png")
						logging.info(f"Writing {filename}")
						if(not os.path.exists(d)):
							os.makedirs(d)
						im.save(filename, 'PNG')
					else:
						logging.info("Dry Run Not Doing anything")
					count += 1
					logging.info(f"[{count}/{len(scans)}] SAVED: {d}|{f}.png")
				except OSError as e:
					logging.error(e)
		except Exception as e:
			logging.error(f"ERROR opening: {xray}")
			logging.error(e)


def main(args):
	""" Main entry point of the app """
	
	patients_sample = get_patients_sample()
	scans = get_scans(patients_sample)
	convert(scans)
	
if(__name__ == "__main__"):
	""" This is executed when run from the command line """
	
	parser = argparse.ArgumentParser()
	parser.add_argument("source", help="source folder - contains patients folders with xray-scans")
	parser.add_argument("destination", help="destination folder - sampled xray-scans will be copied and resized here")
	parser.add_argument("-n", "--dryrun", help="Do nothing, dry run", action='store_true', default=False)
	parser.add_argument("-r", "--resolution", help="target resolution for copied xray-scans (default: 1024)", type=int, default=1024, metavar="")
	parser.add_argument("-q", "--quantity", help="number of sampled patients (default: 1)", type=int, default=1, metavar="")
	parser.add_argument("-t", "--trim", help="auto-trimming threshold - from 0 (black) to 255 (white) (default: 240)", type=int, default=240, metavar="")
	args = parser.parse_args()
	
	source_folder = args.source
	destination_folder = args.destination
	thumbnail_size = (args.resolution, args.resolution)
	quantity = args.quantity
	
	main(args)
