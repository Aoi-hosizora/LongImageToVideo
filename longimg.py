import os
import sys
from PIL import Image
import cv2
import numpy as np
import math

def toCv2(img: Image.Image):
	'''
	PIL Image 2 numpy

	@return `CV2_Image`
	'''
	img = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
	return img

def getImgs(url, ext) -> (list, list):
	'''
	获取多张图片，并处理等宽
	
	@return `Image[]`, `ImageSize[]`
	'''
	ext = ".%s" % ext
	dirs = [url + "/%s" % f for f in os.listdir(url) if f.endswith(ext)]
	
	imgs = [Image.open(dir) for dir in dirs]
	print("All Image Count: ", len(imgs))

	# 每张图片原始大小
	imgs_size = [list(img.size) for img in imgs]
	
	# 中位数
	half_cnt = int(len(imgs_size) / 2)
	middle_width = sorted(imgs_size, key=lambda img_size: img_size[0])[half_cnt][0]
	# 更新每张图片大小
	for i in range(len(imgs_size)):
		rate = middle_width / imgs_size[i][0]
		imgs_size[i][0] = middle_width
		imgs_size[i][1] = int(rate * imgs_size[i][1])
	
	# 处理图片大小，同宽
	for i in range(len(imgs)):
		imgs[i] = imgs[i].resize(imgs_size[i], Image.ANTIALIAS)
		
	return imgs, imgs_size

def toLongImg(imgs, imgs_size) -> Image.Image:
	'''
	将等宽图片组成长图

	@return `LongImage`
	'''
	# 记录到顶部的距离
	img_top = 0
	sum_height = sum([img_size[1] for img_size in imgs_size])
	long_img = Image.new(imgs[0].mode, (imgs_size[0][0], sum_height))

	# 将每一张图片添加到 long_img 内
	for i, img in enumerate(imgs):
		long_img.paste(img, box=(0, img_top))
		img_top += imgs_size[i][1]

	return long_img

def getFrameSizeCnt(long_img: Image.Image, PerMove: int, ratio: float) -> (int, int, int):
	'''
	获得帧大小和总帧数

	@return `FrameWidth`, `FrameHeight`, `FrameCnt`
	'''
	frame_width = long_img.width
	frame_height = int(long_img.width / ratio)

	# 总帧数，这里忽略了超过高度的部分，忽略（反正一帧也没多长
	frame_cnt = int((long_img.height - frame_height) / PerMove)

	return frame_width, frame_height, frame_cnt

def getFrame(long_img: Image.Image, PerMove: int, frame_width: int, frame_height: int, start: int, cnt: int) -> (list, [int, int]):
	'''
	通过长图和指定分辨率获取每一帧
	
	@param `PerMove` 每一帧移动的像素数

	@param `start` `cnt` 每次切割的像素数

	@return `ImageFrame[]`
	'''
	frames = []
	for i in range(start, start + cnt):
		# 判断是否超过了范围
		if i * PerMove + frame_height > long_img.height:
			break
		# 切割长图为帧
		frame = long_img.crop((0, i * PerMove, frame_width, i * PerMove + frame_height))
		frames.append(frame)
	
	return frames

def addFrameToVideo(videoWriter, frames: list):
	'''
	将帧添加到视频中

	@param `frames` 每次加入的帧列表
	'''
	for i, frame in enumerate(frames):
		videoWriter.write(toCv2(frame))

def getFrameVideo(long_img: Image.Image, ratio: float, PerMove: int, PerFragment: int, fps: int, beginwait: int, finalwait: int, path: str):
	'''
	分批次处理帧切片和视频

	@param `PerMove` 每一帧移动的像素数

	@param `PerFragment` 每一批次处理的帧数

	@param `fps` `path` 输出视频帧数和路径
	'''
	# 帧大小和总帧数
	frame_width, frame_height, FrameCnt = getFrameSizeCnt(long_img, PerMove, ratio)
	# 视频解码格式
	fourcc = cv2.VideoWriter_fourcc(*'XVID')
	videoWriter = cv2.VideoWriter(path, fourcc, fps, (frame_width, frame_height))
	
	print("All Frame Count: ", FrameCnt)
	print("Final Duration:  %.2fs\n" % ((FrameCnt + beginwait + finalwait) / fps))

	# 视频开始等待的帧数
	print("Handle Begining Frame: All for %d" % beginwait)
	for i in range(beginwait):
		addFrameToVideo(videoWriter, getFrame(long_img, PerMove, frame_width, frame_height, 0, 1))

	# 总批次数，向上取整，超过部分在 getFrame 判断
	batch = math.ceil(FrameCnt / PerFragment)

	for i in range(batch):
		# 处理第 i(批次) 个 PerFragment
		print("Handle Frame #%d / %d" % (i * PerFragment, FrameCnt))
		
		frames = getFrame(long_img, PerMove, frame_width, frame_height, i * PerFragment, PerFragment)
		addFrameToVideo(videoWriter, frames=frames)

	# 视频最后等待的帧数
	print("Handle Ending Frame: All for %d" % finalwait)
	for i in range(finalwait):
		addFrameToVideo(videoWriter, [frames[len(frames) - 1]])

	# 释放资源
	videoWriter.release()

def checkFileExist(filepath):
	'''
	判断文件是否存在
	'''
	if os.path.exists(filepath):
		op = input("\nThe file %s has existed, cover it? (y/n): " % filepath)
		while not (op == "n" or op == "y"):
			op = input("Wrong option, the file has existed, cover it? (y/n): ")
		if op == "n":
			exit(1)

def getArgv() -> (str, str, float, int, int, int, int, str):
	'''
	获得系统参数
	'''
	dir = sys.argv[1] # 图片所在文件夹
	ext = sys.argv[2] # 图片的后缀名

	radioW = int(sys.argv[3])
	radioH = int(sys.argv[4])
	ratio = float(radioW) / float(radioH) # 分辨率 16 9 / 4 3
	
	fps = int(sys.argv[5]) # 帧数 30 / 60

	PerMove = int(sys.argv[6]) # 每一帧对应移动长图多少像素

	beginwait = int(sys.argv[7]) # 开始的等待时间
	finalwait = int(sys.argv[8]) # 最后的等待时间

	filename = sys.argv[9] # 保存文件名，不带后缀都指定为 avi
	filepath = "%s%s%s.avi" % (dir, os.path.sep, filename) # 保存的文件名

	print('''
Setting:
Images Directory: {}*.{}
Frame Ratio: {}:{}, FPS: {}, Pixel Move: {}, 
Begin Wait:{}, Final Wait: {}
Save FileName: {}
Video Duration: See After \
'''
	.format(dir + os.path.sep, ext,
			radioW, radioH, fps, PerMove,
			beginwait, finalwait,
			filepath))

	op = input("\nContinue? (y/n): ")
	while not (op == "n" or op == "y"):
		op = input("Wrong option, continue? (y/n): ")
	if op == "n":
		exit(1)

	return dir, ext, ratio, fps, PerMove, beginwait, finalwait, filepath

if __name__ == "__main__":

	dir, ext, ratio, fps, PerMove, beginwait, finalwait, filepath = getArgv()
	
	# 判断文件是否存在
	checkFileExist(filepath)

	### 获取图片以及长图 ###
	print("\n> Transform to Long Image Start")
	imgs, imgs_size = getImgs(dir, ext)
	long_img = toLongImg(imgs, imgs_size)
	print("> Transform to Long Image Finish\n")

	# 每一帧在长图中的移动像素数 和 每一批次处理的帧数
	# PerMove = 1
	PerFragment = 200 # 别设置太高，机子内存承受不住

	### 获取每一帧以及插入视频 ###
	print("> Get Frames and Add to Video Start")
	video = getFrameVideo(long_img=long_img, ratio=ratio,
		PerMove=PerMove, PerFragment=PerFragment, fps=fps, beginwait=beginwait, finalwait=finalwait, path=filepath)
	print("> Get Frames and Add to Video Finish\n")
	print("> Find Your Video in \"%s\"" % filepath)
	
# python longimg.py "E:\Gal Files\CIRCUS\DC4\AdvData\GRP\ED\ED" png 16 9 60 1 50 100 final