from google.cloud import storage
from google.cloud.storage import Blob
from google.cloud import firestore

from skimage import data, transform
from skimage.measure import compare_ssim

from PIL import Image
from shutil import copyfile

from random import randint

import numpy as np
import sys, os, os.path, scipy.misc, uuid, tensorflow, imutils, cv2, math, datetime

useBucket = True

# This script has only been tested on Ubuntu

# Change path to work
inputRootPath = "../images/input/fourth_session/" # This is the folder where you put images of stickers (1 image per sticker) to try to remove the background. Change path to fit
outputRootPath = "../images/output/" 
bucketName = "--put your bucket here--"
temporaryFolderPath = "../images/temporary/"
transparentInputRootPath = "../images/input/good_transparents/" # Put all the clean transparent stickers in here to begin data generation

# These assume you are using a computer with gcloud initialized on it
client = storage.Client()
bucket = client.get_bucket(bucketName)

# These determine how many pictures get generated (offset between each)
angleModifier = 30 #30
skew1Modifier = 20 #20
skew2Modifier = 5 #5

# These control the image manipulation
startAngle = 0
endAngle = 360

startSkew1 = -30
endSkew1 = 20

startSkew2 = 10
endSkew2 = 21

# Firebase firestore
db = firestore.Client()
stickerCollectionReference = db.collection(u'stickers')	

# These let you set backgrounds for the generated images
replacementColorsDict = { # 66, 158, 238
	"reference-lg.jpg": (220, 220, 220),#, 255),
	"reference-mlg.jpg": (165, 165, 165),#, 255),
	"reference-mdg.jpg": (110, 110, 110),#, 255),
	"reference-dg.jpg": (55, 55, 55)#, 255)
}

# This will take a single image f
def main():
	stickerIdMappingDict = {}
	counter = 0
	prevRootList = []

	for root, dirs, files in os.walk(inputRootPath):
		for file in files:
			if file != "reference.jpg":
				stickerIdMappingDict[str(file)] = str(uuid.uuid4()) # save this to a csv file. cuz 
				detectSticker(root + "reference.jpg", root + file, stickerIdMappingDict[str(file)])

def fromTransparents():
	for root, dirs, files in os.walk(transparentInputRootPath):
		for file in files:
			if not os.path.isdir(outputRootPath + "/" + file.split(".")[0]):
				os.makedirs(outputRootPath + file.split(".")[0])
			copyfile(root + file, outputRootPath + file.split(".")[0] + "/" + file)
			createBaseImages(outputRootPath + file.split(".")[0]  + "/", True)
			generateImages(outputRootPath + file.split(".")[0]  + "/", file.split(".")[0], True)
			renameReferenceImages(outputRootPath + file.split('.')[0] + "/", file.split('.')[0])
	createCSV()

def oldWay():
	stickerIdMappingDict = {}
	counter = 0
	prevRootList = []

	for root, dirs, files in os.walk(inputRootPath):
		for file in files:
			if file != "reference.jpg":	
				stickerIdMappingDict[str(file)] = str(uuid.uuid4()) # save this to a csv file

				if not os.path.isdir(outputRootPath + "/" + stickerIdMappingDict[str(file)]):
					os.makedirs(outputRootPath + "/" + stickerIdMappingDict[str(file)])

				detectSticker(root + "reference.jpg", root + file, outputRootPath + stickerIdMappingDict[str(file)] + "/")
				createBaseImages(outputRootPath + stickerIdMappingDict[str(file)] + "/")
				generateImages(outputRootPath + stickerIdMappingDict[str(file)] + "/", stickerIdMappingDict[str(file)])
				renameReferenceImages(outputRootPath + stickerIdMappingDict[str(file)] + "/", stickerIdMappingDict[str(file)])
	createCSV()

def detectSticker(baseImagePath, stickerImagePath, stickerId):
	imageA = cv2.imread(baseImagePath)
	imageB = cv2.imread(stickerImagePath)

	grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
	grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)

	(score, diff) = compare_ssim(grayA, grayB, full=True)
	diff = (diff * 255).astype('uint8')

	thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
	cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnts = cnts[0] if imutils.is_cv2() else cnts[1]

	slack = 100
	biggestDif = 0
	bw, bh, bx, by = (0, 0, 0, 0)
	for c in cnts:
		(x, y, w, h) = cv2.boundingRect(c)
		if w * h > biggestDif:
			bw = w
			bh = h
			bx = x
			by = y
			biggestDif = w * h

	# print(stickerImagePath.split("/")[-1] + ": --> bw = " + str(bw) + ", " + "bh = " + str(bh) + ", " + "bx = " + str(bx) + ", " + "by = " + str(by))
	cropped_image = imageB[by - slack: by + bh + slack, bx - slack: bx + bw + slack]			

	cv2.imwrite(outputRootPath + "tmp.jpg", cropped_image)
	resize(outputRootPath + "tmp.jpg", outputRootPath + "reference.jpg")

	gCutImage("reference.jpg", outputRootPath, stickerId + ".png", [0, 0, 0, 0], (0, 0, 0, 0))

	os.remove(outputRootPath + "tmp.jpg")
	os.remove(outputRootPath + "reference.jpg")

def resize(imagePath, outPath):
	size = 224, 224
	im = Image.open(imagePath)
	im.thumbnail(size, Image.ANTIALIAS)
	im.save(outPath)

def gCutImage(imageName, outFolder, outImageName, colorArray, colorTuple):	
	imgo = cv2.imread(outFolder + imageName)

	height, width = imgo.shape[:2]
	mask = np.zeros(imgo.shape[:2],np.uint8)
	bgdModel = np.zeros((1, 65), np.float64)
	fgdModel = np.zeros((1, 65), np.float64)

	rect = (1, 1, width - 1, height - 1)
	cv2.grabCut(imgo, mask, rect, bgdModel, fgdModel, 15, cv2.GC_INIT_WITH_RECT)
	imgo = cv2.cvtColor(imgo, cv2.COLOR_RGB2RGBA)
	mask = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
	img1 = imgo*mask[:, :, np.newaxis]

	background = imgo - img1
	background[np.where((background > [0, 0, 0, 0]).all(axis = 2))] = colorArray
	final = background + img1

	cv2.imwrite(outFolder + "tmp.png", final)
	oimg = Image.open(outFolder + "tmp.png")
	nimg = Image.new("RGBA", (224, 224), color=colorTuple)
	
	ulw, ulh, ulshape = final.shape

	if ulw == 224:
		ulw = 0
	else:
		ulw = math.ceil((224 - ulw) / 2)

	if ulh == 224:
		ulh = 0
	else:
		ulh = math.ceil((224 - ulh) / 2)

	ul = (ulh, ulw)
	nimg.paste(oimg, ul)
	nimg.save(outFolder + outImageName)

	os.remove(outFolder + "tmp.png")

def createBaseImages(folder, isFromTransparent=False):
	for replacementColorKey in replacementColorsDict.keys():
		fileToOpen = "reference.png"
		if isFromTransparent:
			fileToOpen = folder.split('/')[-2] + ".png"
		rImg = Image.open(folder + fileToOpen)

		background = Image.new("RGB", (224, 224), replacementColorsDict[replacementColorKey])
		background.paste(rImg, (0, 0), rImg)
		background.save(folder + replacementColorKey)

def renameReferenceImages(inputPath, stickerId):
	for ref in replacementColorsDict.keys():
		os.rename(inputPath + ref, inputPath + stickerId + "_" + ref.split("reference-")[1])
		if useBucket:	
			uploadToBucket(inputPath + stickerId + "_" + ref.split("reference-")[1], stickerId + "_" + ref.split("reference-")[1], stickerId)

def createImage(inputImagePath, stickerId, savePath, angle, skew1, skew2, counter, isFromTransparent=False):
	if counter == "-1":
		if not isFromTransparent:
			os.rename(inputImagePath, savePath + stickerId + ".png")

		if useBucket:
			uploadToBucket(savePath + stickerId + ".png", stickerId + ".png", stickerId)
			
			print("Updating Firestore")
			stickerDocumentReference = stickerCollectionReference.document(stickerId)
			stickerDocumentReference.set({
				'name': "Sticker " + stickerId,
				'id': stickerId,
				'description': stickerId + "'s Description",
				"dateAdded": datetime.datetime.utcnow(),
				"numberOfUsersWhoHaveThisSticker": 0,
				"purchaseUrl": "google.com"
			})

		return

	pImg = Image.open(inputImagePath)
	img = np.array(pImg)

	theta = np.deg2rad(angle)
	tx = 0
	ty = 0

	S, C = np.sin(theta), np.cos(theta)
	Hz = np.array([[C, -S, tx],
				[S,  C, ty],
				[0,  0, 1]])

	r, c, e = img.shape

	T = np.array([[1, 0, -c / 2.],
				[0, 1, -r / 2.],
				[0, 0, 1]])
	
	S = np.array([[1, 0, 0],
				[0, skew2, 0],
				[0, skew1, 1]])

	generatedImage = transform.warp(img, S.dot(np.linalg.inv(T).dot(Hz).dot(T)), mode="edge")

	imageNameAddon = ""
	
	if "reference-" in inputImagePath.split("/")[-1]:
		imageNameAddon = "_" + inputImagePath.split("reference-")[1].split(".")[0]

	generatedImageFileName = stickerId + imageNameAddon +"_" + counter + ".jpg"

	generatedImageFilePath = savePath + generatedImageFileName
	scipy.misc.imsave(generatedImageFilePath, generatedImage)

	if useBucket:
		uploadToBucket(generatedImageFilePath, generatedImageFileName, stickerId)		

def uploadToBucket(filepath, filename, stickerId):
	blob = Blob("stickers/" + stickerId + '/' + filename, bucket)
	with open(filepath, 'rb') as my_file:
	    blob.upload_from_file(my_file)

def generateImages(inputRoot, stickerId, isFromTransparent=False):
	for root, dirs, files in os.walk(inputRoot):
		if files == []:
			print("No files found in folder {}".format(root))
			continue
		for file in files:
			if not isFromTransparent:

				if file == "tmp.jpg" or file == "tmp.png":
					print("Temporary files were not deleted from folder: {}".format(root))
					continue

				if file == "reference.png":
					createImage(root + "/" + file, stickerId, root, 0, 0, 0, str(-1))
					continue
			else:
				if file == stickerId + ".png":
					createImage(root + "/" + file, stickerId, root, 0, 0, 0, str(-1), True)
					continue

			counter = 1

			for angle in range(startAngle, endAngle, angleModifier):
				for skew1 in range(startSkew1, endSkew1, skew1Modifier):
					for skew2 in range(startSkew2, endSkew2, skew2Modifier):
						createImage(root + "/" + file, stickerId, root, angle, skew1 * 0.1e-3, skew2 * .1, str(counter))
						counter+=1		


def getAllStickerIds(checkBucket):
	if checkBucket:
		print("check the buckets")
	else:
		print("check local files")

def getAllStickerIdsFromBucket():
	print("todo")

def getAllStickerIdsFromOutput():
	print("todo")

def getAllStickerIdsFromFirestore():
	stickerDocs = db.collection('stickers').get()
	stickerIds = []
	for stickerDoc in stickerDocs:
		stickerIds.append(stickerDoc.id)
	return stickerIds

def checkIfStickerIDExists(stickerId):
	return stickerId in getAllStickerIds(False)

def numberOfFilesInFolders(folderPath):
	return len(os.walk(folderPath).__next__()[2])

# Generates the CSV file needed for using google cloud to do our training
def createCSV():
	eval_csv = open("eval.csv", "w+")
	train_csv = open("train.csv", "w+")

	for root, dirs, files in os.walk(outputRootPath):
		if files == []:
			continue
		for file in files:
			if "_" in file:
				if (randint(0, 9) == 1):
					eval_csv.write("gs://" + bucketName + "/stickers/" + file.split("_")[0] + "/" + file + ", " + file.split("_")[0] + "\n")
				else:
					train_csv.write("gs://" + bucketName + "/stickers/" + file.split("_")[0] + "/" + file + ", " + file.split("_")[0] + "\n")

	eval_csv.close()
	train_csv.close()

def createTxt():
	txt = open("dict.txt", "w+")
	for root, dirs, files in os.walk(outputRootPath):
		if files == []:
			continue
		txt.write(root.split("/")[-1] + "\n")

if __name__ == '__main__':
	# main() 
	#fromTransparents()
	#createCSV()
	#createTxt()