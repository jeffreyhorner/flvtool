#from pprint import pprint as pp
from mmap import PAGESIZE
from struct import unpack, pack
from datetime import datetime

FLV_HEADER_SIZE = 9
FLV_TAG_HEADER_SIZE = 11
FLV_BACKPTR_SIZE = 4

FLV_AUDIO_TAG_HEADER_SIZE = 2
FLV_VIDEO_TAG_HEADER_SIZE = 1

FLV_TAG_TYPE_SCRIPT = 18
FLV_TAG_TYPE_AUDIO = 8
FLV_TAG_TYPE_VIDEO = 9

FLV_TAG_TYPE = {
	FLV_TAG_TYPE_AUDIO: 'audio',
	FLV_TAG_TYPE_VIDEO: 'video',
	FLV_TAG_TYPE_SCRIPT: 'script',
}


FLV_SCRIPT_VALUE_NUMBER = 0
FLV_SCRIPT_VALUE_BOOL = 1
FLV_SCRIPT_VALUE_STRING = 2
FLV_SCRIPT_VALUE_OBJECT = 3
FLV_SCRIPT_VALUE_MOVIE = 4
FLV_SCRIPT_VALUE_NULL = 5
FLV_SCRIPT_VALUE_UNDEF = 6
FLV_SCRIPT_VALUE_REF = 7
FLV_SCRIPT_VALUE_ECMA = 8
FLV_SCRIPT_VALUE_ARRAY = 10
FLV_SCRIPT_VALUE_DATE = 11
FLV_SCRIPT_VALUE_LSTRING = 12

FLV_AUDIO_FORMAT = {
	0: 'uncompressed',
	1: 'adpcm',
	2: 'mp3',
	5: 'nelymosermono',
	6: 'nellymoser',
}

# in kHz
FLV_AUDIO_RATE = {
	0: 5.5,
	1: 11,
	2: 22,
	3: 44,
}

# 8 or 16 bit
FLV_AUDIO_SAMPLE = {
	0: 8,
	1: 16,
}

FLV_VIDEO_FRAME = {
	1: 'keyframe',
	2: 'interframe',
	3: 'disposable interframe',
}

FLV_VIDEO_CODEC_H263 = 2
FLV_VIDEO_CODEC_SCREENVIDEO = 3
FLV_VIDEO_CODEC_VP6FLV = 4
FLV_VIDEO_CODEC_VP6FLVALPHA = 5
FLV_VIDEO_CODEC_SCREENV2 = 6

FLV_VIDEO_CODEC = {
	FLV_VIDEO_CODEC_H263: 'H.263',
	FLV_VIDEO_CODEC_SCREENVIDEO: 'SCREENVIDEO',
	FLV_VIDEO_CODEC_VP6FLV: 'VP6FLV',
	FLV_VIDEO_CODEC_VP6FLVALPHA: 'VP6FLVALPHA',
	FLV_VIDEO_CODEC_SCREENV2: 'SCREENV2',
}


class FLVFile:
	"Class for parsing Adoble Flash FLV files"

	def __init__(self,file):
		self.f = open(file,'rb',PAGESIZE)
		self.read_header()
		#self.read_tags()

	def read_header(self):
		self.f.seek(0)
		(flvtag,version,flags,flvHeaderLen,prevTagSize) = unpack('>3sBBLL',self.f.read(FLV_HEADER_SIZE+FLV_BACKPTR_SIZE))

		if flvtag != "FLV": sys.exit("Not an FLV file") # should probably raise an exception here

		self.hasAudio = (flags & 0x4) == 4

		self.hasVideo = flags & 0x1 == 1

		if (flvHeaderLen != FLV_HEADER_SIZE): sys.exit("FLV Header length wrong")

		if (prevTagSize != 0): sys.exit("Flv PrevTagSize0 is wrong")

	def find_event(self,event):
		for i in self.events:
			for key in self.events[i].keys():
				if key == event:
					return self.events[i][key]
		return 	None

	def read_tags(self):
		self.f.seek(FLV_HEADER_SIZE+FLV_BACKPTR_SIZE)
		self.tags = []
		self.events = {}
		self.numScriptTags = self.numVideoTags = self.numAudioTags = 0
		self.lastAudioTag = self.lastVideoTag = 0

		offset = FLV_HEADER_SIZE+FLV_BACKPTR_SIZE
		tag=0
		self.eofReached = 0

		while 1:
			tagType = self.read_ui8()
			if self.eofReached: break
			self.tags.append( {
				'offset': offset,
				'tagType': FLV_TAG_TYPE[tagType],
				'dataSize': self.read_ui24(),
				'timeStamp': self.read_ui24() + (self.read_ui8()<<24),
				'streamId': self.read_ui24()
				} )
			self.tags[tag]['tagSize'] = FLV_TAG_HEADER_SIZE + self.tags[tag]['dataSize']

			if tagType == FLV_TAG_TYPE_SCRIPT:
				self.numScriptTags += 1
				self.tags[tag]['data'] = self.read_script_tag(self.tags[tag])
				self.events[tag] = self.tags[tag]['data']
			elif tagType == FLV_TAG_TYPE_AUDIO:
				self.lastAudioTag = tag
				self.numAudioTags += 1
				self.tags[tag]['data'] = self.read_audio_tag(self.tags[tag])
			elif tagType == FLV_TAG_TYPE_VIDEO:
				self.lastVideoTag = tag
				self.numVideoTags += 1
				self.tags[tag]['data'] = self.read_video_tag(self.tags[tag])
			else:
				print "WARNING: Unknown tag type: %d" % tagType

			offset += self.tags[tag]['tagSize']
			self.f.seek(offset)

			backptr = self.read_ui32()
			if backptr != self.tags[tag]['tagSize']:
				#print "WARNING: backptr of %d does not match tagsize of %d" % (backptr, self.tags[tag]['tagSize'])
				None
			offset += FLV_BACKPTR_SIZE
			tag += 1


		# The timstamp associated with each tag is the time at which the tag data should be viewed relative
		# to the beginning of the video, so the duration of the entire video is the last video timestamp
		# plus 1 / fps (the duration of the last frame
		self.fps = float(self.numVideoTags - 1) / (self.tags[self.lastVideoTag]['timeStamp'] / 1000.0)
		self.videoDuration = (self.tags[self.lastVideoTag]['timeStamp'] / 1000.0) + (1.0/self.fps)
		self.eofReached = 0

	def find_first_tag(self,type):
		self.f.seek(FLV_HEADER_SIZE+FLV_BACKPTR_SIZE)

		offset = FLV_HEADER_SIZE+FLV_BACKPTR_SIZE
		tag=0
		self.eofReached = 0

		while 1:
			tagType = self.read_ui8()
			if self.eofReached: break
			newtag = {
				'offset': offset,
				'tagType': FLV_TAG_TYPE[tagType],
				'dataSize': self.read_ui24(),
				'timeStamp': self.read_ui24() + (self.read_ui8()<<24),
				'streamId': self.read_ui24()
				}
			newtag['tagSize'] = FLV_TAG_HEADER_SIZE + newtag['dataSize']

			if tagType == FLV_TAG_TYPE_SCRIPT:
				return self.read_script_tag(newtag)
			elif tagType == FLV_TAG_TYPE_AUDIO:
				return self.read_audio_tag(newtag)
			elif tagType == FLV_TAG_TYPE_VIDEO:
				return self.read_video_tag(newtag)
			else:
				print "WARNING: Unknown tag type: %d" % tagType

			offset += newtag['tagSize']
			self.f.seek(offset)

			backptr = self.read_ui32()
			if backptr != self.tags[tag]['tagSize']:
				#print "WARNING: backptr of %d does not match tagsize of %d" % (backptr, self.tags[tag]['tagSize'])
				None
			offset += FLV_BACKPTR_SIZE

	def read_ui8(self):
		byte = self.f.read(1)
		if len(byte) != 1:
			self.eofReached = 1
			return 0
		return ord(byte)

	def read_ui16(self):
		return (self.read_ui8()<<8) + self.read_ui8()

	def read_si16(self):
		return unpack('>h',self.f.read(2))[0]

	def read_ui24(self):
		return (self.read_ui8()<<16) + (self.read_ui8()<<8) + self.read_ui8()

	def read_ui32(self):
		return (self.read_ui8()<<24) + (self.read_ui8()<<16) + (self.read_ui8()<<8) + self.read_ui8()

	def read_DOUBLE(self):
		return unpack('>d',self.f.read(8))[0]

	def read_DATE(self):
		val = datetime.fromtimestamp(self.read_DOUBLE() / 1000)
		self.read_si16() # offset from utc, ignore.
		return val

	def ScriptDataObject(self,tag):
		objects = {}
		while tag['dataOffset'] < tag['dataSize']:
			name = self.ScriptDataString(tag)
			if not name and (self.read_ui8() == 9):
				tag['dataOffset'] += 1
				break;

			objects[name] = self.ScriptDataValue(tag)

		return objects

	def ScriptDataValue(self,tag):
		val = ''
		type = self.read_ui8()
		tag['dataOffset'] += 1
		if type == FLV_SCRIPT_VALUE_NUMBER:
			val = self.read_DOUBLE()
			tag['dataOffset'] += 8
		elif type == FLV_SCRIPT_VALUE_BOOL:
			val = self.read_ui8()
			tag['dataOffset'] += 1
		elif type == FLV_SCRIPT_VALUE_STRING:
			val = self.ScriptDataString(tag)
		elif type == FLV_SCRIPT_VALUE_OBJECT:
			val = self.ScriptDataObject(tag)
		elif type == FLV_SCRIPT_VALUE_ECMA:
			val = self.ScriptDataVariable(tag)
		elif type == FLV_SCRIPT_VALUE_ARRAY:
			val = []
			for i in range(self.read_ui32()):
				val.append(self.ScriptDataValue(tag))
			tag['dataOffset'] += 4
		elif type == FLV_SCRIPT_VALUE_DATE:
			val = self.read_DATE()
			tag['dataOffset'] += 10
		else:
			print "WARNING: unknown Script Data Value Type: %d" % (type)

		return val

	def ScriptDataString(self,tag):
		slen = self.read_ui16()
		tag['dataOffset'] += 2 + slen
		return unpack('>%ss' % slen,self.f.read(slen))[0]

	def ScriptDataVariable(self,tag):
		val = {}

		arrayLen = self.read_ui32() # not always reliable
		tag['dataOffset'] += 4
		while tag['dataOffset'] < tag['dataSize']:
			name = self.ScriptDataString(tag)
			if not name and (self.read_ui8() == 9):
				tag['dataOffset'] += 1
				break
			val[name] = self.ScriptDataValue(tag)

		return val

	def read_script_tag(self,tag):
		self.f.seek(tag['offset']+FLV_TAG_HEADER_SIZE)
		type = self.read_ui8() # should be 2
		if (type != 2):
			print "WARNING: objecttype not 2, is %d" % (type)

		tag['dataOffset'] = 1 # accounting to make sure we don't read past tag['dataSize']-1
		events =  self.ScriptDataObject(tag)
		del tag['dataOffset']

		return events

	def read_video_tag(self,tag):
		val = {}
		self.f.seek(tag['offset']+FLV_TAG_HEADER_SIZE)
		flag = self.read_ui8()
		val['frameType'] = FLV_VIDEO_FRAME[(flag & 0xf0) >> 4]
		codec = (flag & 0xf)
		val['codecId'] = FLV_VIDEO_CODEC[codec]
		val['rawOffset'] = tag['offset'] + FLV_TAG_HEADER_SIZE + FLV_VIDEO_TAG_HEADER_SIZE

		#if codec == FLV_VIDEO_CODEC_H263:
		#	val['packetInfo'] = read_h263_packet(val['rawOffset'])
		#elif codec == FLV_VIDEO_CODEC_VP6FLV:
		#	val['packetInfo'] = read_vp6flv_packet(val['rawOffset'])
		#else:
		#	val['packetInfo'] = {}

		return val

	def read_audio_tag(self,tag):
		val = {}
		self.f.seek(tag['offset']+FLV_TAG_HEADER_SIZE)
		flag = self.read_ui8()
		val['format'] = FLV_AUDIO_FORMAT[(flag & 0xf0) >> 4]
		val['rate'] = FLV_AUDIO_RATE[(flag & 0x0d0) >> 2]
		val['sampleSize'] = FLV_AUDIO_SAMPLE[int((flag & 0x2) > 1)]
		val['stereo']  = bool(flag & 0x1)
		val['rawOffset'] = tag['offset'] + FLV_TAG_HEADER_SIZE + FLV_AUDIO_TAG_HEADER_SIZE
		return val

	def read_h263_packet(self,offset):
		val = {}
		self.f.seek(offset + 17 + 5 + 8)


#returns type, width, height, duration, framerate
def inspect_flv( file ):
	tag = FLVFile(file).find_first_tag(FLV_TAG_TYPE_SCRIPT)
	if 'onMetaData' not in tag:
		return None, None, None, None, None
	ret = {
			'videocodecid': None,
			'width': None,
			'height': None,
			'duration': None,
			'framerate': None
	}

	#pp(tag)

	for k, v in tag['onMetaData'].iteritems():
		for kk, vv in ret.iteritems():
			if k.lower() == kk:
				ret[kk] = v

	return ret['videocodecid'], ret['width'], ret['height'], ret['duration'], ret['framerate']
