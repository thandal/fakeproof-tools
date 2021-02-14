#!/usr/bin/python3
import os, sys
import struct
import numpy as np
from collections import namedtuple

import base64
import hashlib

# See https://xhelmboyx.tripod.com/formats/mp4-layout.txt
# Generic box: long unsigned offset + long ASCII text string (4 characters)
boxStruct = struct.Struct("> I 4s")

# * 8+ bytes file type box = long unsigned offset + long ASCII text string 'ftyp'
#   -> 4 bytes major brand = long ASCII text main type string
#   -> 4 bytes major brand version = long unsigned main type revision value
#   -> 4+ bytes compatible brands = list of long ASCII text used technology strings
#     - types are ISO 14496-1 Base Media = isom ; ISO 14496-12 Base Media = iso2
#     - types are ISO 14496-1 vers. 1 = mp41 ; ISO 14496-1 vers. 2 = mp42
#     - types are quicktime movie = 'qt  ' ; JVT AVC = avc1
#     - types are 3G MP4 profile = '3gp' + ASCII value ; 3G Mobile MP4 = mmp4
#     - types are Apple AAC audio w/ iTunes info = 'M4A ' ; AES encrypted audio = 'M4P '
#     - types are Apple audio w/ iTunes position = 'M4B ' ; ISO 14496-12 MPEG-7 meta data = 'mp71'
#     - NOTE: All compatible with 'isom', vers. 1 uses no Scene Description Tracks,
#       vers. 2 uses the full part one spec, M4A uses custom ISO 14496-12 info,
#       qt means the format complies with the original Apple spec, 3gp uses sample
#       descriptions in the same style as the original Apple spec.
ftypStruct = struct.Struct("> I 4s 4s I 4s 4s") 

# Version 0
mvhdList0 = (
  ('B', 'version'),
  ('3s', 'flags'),
  ('I', 'creation_time'),
  ('I', 'modification_time'),
  ('I', 'time_scale'),
  ('I', 'duration'),
  ('I', 'playback_speed'),
  ('H', 'volume'),
  ('10s', 'reserved'),
  ('H', 'A'),
  ('H', 'B'),
  ('H', 'U'),
  ('H', 'C'),
  ('H', 'D'),
  ('H', 'V'),
  ('H', 'X'),
  ('H', 'Y'),
  ('H', 'W'),
  ('I', 'preview_time'),
  ('I', 'preview_duration'),
  ('I', 'poster_time'),
  ('I', 'selection_time'),
  ('I', 'selection_duration'),
  ('I', 'current_time'),
  ('I', 'next_track_id'),
)
mvhdNamedTuple = namedtuple('mvhd', ' '.join([x[1] for x in mvhdList0]))
mvhdSubStruct0 = struct.Struct('>' + ' '.join([x[0] for x in mvhdList0]))

# Note: there are two types of meta boxes. Ones without version/flags (found in
# 'moov' and 'trak' boxes), and ones *with* version/flags (found in 'udta'
# boxes).
metaList0 = (
  ('B', 'version'),
  ('3s', 'flags'),
)
metaNamedTuple = namedtuple('meta', ' '.join([x[1] for x in metaList0]))
metaSubStruct0 = struct.Struct('>' + ' '.join([x[0] for x in metaList0]))

hdlrList = (
  ('B', 'version'),
  ('3s', 'flags'),
  ('4s', 'type'),
  ('4s', 'subtype'),
  ('4s', 'manufacturer'),
  ('4s', 'reserved_flags'),
  ('4s', 'reserved_mask'),
  ('', 'component_name'), # component name ASCII string, use readcstr
)
hdlrNamedTuple = namedtuple('hdlr', ' '.join([x[1] for x in hdlrList]))
hdlrStruct = struct.Struct('>' + ' '.join([x[0] for x in hdlrList]))

# Version 0
tkhdList0 = (
  ('B', 'version'),
  ('3s', 'flags'),
  ('I', 'creation_time'),
  ('I', 'modification_time'),
  ('I', 'track_id'),
  ('8s', 'reserved'),
  ('I', 'duration'),
  ('4s', 'reserved1'),
  ('H', 'position'),
  ('H', 'track_id1'),
  ('H', 'audio_volume'),
  ('2s', 'reserved2'),
  ('H', 'A'),
  ('H', 'B'),
  ('H', 'U'),
  ('H', 'C'),
  ('H', 'D'),
  ('H', 'V'),
  ('H', 'X'),
  ('H', 'Y'),
  ('H', 'W'),
  ('I', 'width'),
  ('I', 'height'),
)
tkhdNamedTuple = namedtuple('tkhd', ' '.join([x[1] for x in tkhdList0]))
tkhdStruct0 = struct.Struct('>' + ' '.join([x[0] for x in tkhdList0]))

def readBox(f):
  data = f.read(boxStruct.size)
  assert(data != b'')
  return(boxStruct.unpack(data))

def readBoxes(f, start_offset = 0, end_offset = sys.maxsize):
  """Scan f for data boxes and returns a dict of {text: (offset, length)}.

  Specify a start_offset and end_offset to read sub-boxes.
  """
  boxes = {}
  f.seek(start_offset)
  offset = start_offset
  while True:
    f.seek(offset)
    data = f.read(boxStruct.size)
    if data == b'': break
    length, text = boxStruct.unpack(data)
    boxes[text] = (offset, length)
    if length == 1:  # Read the true large length
      length = int.from_bytes(f.read(8), 'big')
    offset += length
    if (offset > end_offset): break
  return boxes

def readFtyp(f):
  f.seek(0)
  data = f.read(ftypStruct.size)
  return ftypStruct.unpack(data)

def readMvhdBox(f, offset):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == b'mvhd')
  data = f.read(mvhdSubStruct0.size)
  mvhd = mvhdNamedTuple._make(mvhdSubStruct0.unpack(data))
  assert(mvhd.version == 0)
  # Skip the rest of the contents for now...
  return mvhd

def readcstr(f):
  s = ''
  while len(s) < 32:
    b = f.read(1)
    if b is None or b == b'\x00':
      return s
    else:
      s += b.decode()

def readHdlrBox(f, offset):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == b'hdlr')
  # For now, always assume we have no version/flags.
  data = f.read(hdlrStruct.size)
  componentName = readcstr(f)
  fields = list(hdlrStruct.unpack(data))
  fields.append(componentName)
  return hdlrNamedTuple._make(fields)

def readTkhdBox(f, offset):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == b'tkhd')
  data = f.read(tkhdStruct0.size)
  return tkhdNamedTuple._make(tkhdStruct0.unpack(data))

def readStscBox(f, offset):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == b'stsc')
  f.read(4)  # skip version/flags
  numberOfBlocks = int.from_bytes(f.read(4), 'big')
  spb = []
  for i in range(numberOfBlocks):
    firstBlock = int.from_bytes(f.read(4), 'big')
    numberOfSamples = int.from_bytes(f.read(4), 'big')
    sampleDescriptionId = int.from_bytes(f.read(4), 'big')  # What is this for?
    spb.append((firstBlock, numberOfSamples))
  return spb

def readStszBox(f, offset):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == b'stsz')
  f.read(4)  # skip version/flags
  fixedBlockSize = int.from_bytes(f.read(4), 'big')
  if (fixedBlockSize > 0): return fixedBlockSize
  numberOfSampleSizes = int.from_bytes(f.read(4), 'big')
  #print('numberOfSampleSizes', numberOfSampleSizes)
  ss = []
  for i in range(numberOfSampleSizes):
    sampleSize = int.from_bytes(f.read(4), 'big')
    ss.append(sampleSize)
  return ss

def readCo64Box(f, offset):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == b'co64')
  f.read(4)  # skip version/flags
  numberOfBlockOffsets = int.from_bytes(f.read(4), 'big')
  bo = []
  for i in range(numberOfBlockOffsets):
    blockOffset = int.from_bytes(f.read(8), 'big')
    bo.append(blockOffset)
  return bo 

def checkAndReadBoxes(f, offset, expectedType):
  f.seek(offset)
  length, type = readBox(f)
  assert(type == expectedType)
  return readBoxes(f, offset + boxStruct.size, offset + length)

def recurseOnTracks(f):
  boxes = readBoxes(f)
  assert(b'ftyp' in boxes)
  T = {}
  moovBoxes = checkAndReadBoxes(f, boxes[b'moov'][0], b'moov') 
  metaBoxes = checkAndReadBoxes(f, moovBoxes[b'meta'][0], b'meta') 
  boxes = metaBoxes
  while True:
    if b'trak' not in boxes: break
    boxes = checkAndReadBoxes(f, boxes[b'trak'][0], b'trak') 
    tkhdBox = readTkhdBox(f, boxes[b'tkhd'][0]) 
    #print('TKHD', tkhdBox)
    T[tkhdBox.track_id] = boxes
  return T

def processSamples(f, trakBoxes, callback):
  #print('TRAK BOXES', trakBoxes)
  tkhdBox = readTkhdBox(f, trakBoxes[b'tkhd'][0]) 
  #print('TKHD', tkhdBox)
  mdiaBoxes = checkAndReadBoxes(f, trakBoxes[b'mdia'][0], b'mdia') 
  #print('MDIA BOXES', mdiaBoxes)
  hdlrBox = readHdlrBox(f, mdiaBoxes[b'hdlr'][0]) 
  #print('HDLR', hdlrBox)
  minfBoxes = checkAndReadBoxes(f, mdiaBoxes[b'minf'][0], b'minf') 
  #print('MINF BOXES', minfBoxes)
  stblBoxes = checkAndReadBoxes(f, minfBoxes[b'stbl'][0], b'stbl') 
  #print('STBL BOXES', stblBoxes)

  blockToSamplesTable = readStscBox(f, stblBoxes[b'stsc'][0]) 
  #print('STSC', blockToSamplesTable)
  sampleSizes = readStszBox(f, stblBoxes[b'stsz'][0]) 
  #print('STSZ', sampleSizes)
  blockOffsets = readCo64Box(f, stblBoxes[b'co64'][0]) 
  #print('CO64', blockOffsets)

  tableCounter = 0
  blockInTableCounter = 0
  sampleInBlockCounter = 0
  blockCounter = 0
  f.seek(blockOffsets[blockCounter])
  for sampleCounter in range(len(sampleSizes)):
    if sampleInBlockCounter >= blockToSamplesTable[tableCounter][1]:
      blockCounter += 1
      sampleInBlockCounter = 0
      if blockCounter + 1 >= blockToSamplesTable[tableCounter + 1][0]:
        tableCounter += 1
      f.seek(blockOffsets[blockCounter])
    sample = f.read(sampleSizes[sampleCounter])
    callback(sample)
    sampleInBlockCounter += 1

sensorList = (
  ('I', 'type'),
  ('f', 'x'),
  ('f', 'y'),
  ('f', 'z'),
)
sensorNamedTuple = namedtuple('sensor', ' '.join([x[1] for x in sensorList]))
sensorStruct = struct.Struct('>' + ' '.join([x[0] for x in sensorList]))

locationList = (
  ('d', 'altitude'),
  ('f', 'verticalAccuracyMeters'),
  ('f', 'bearing'),
  ('f', 'bearingAccuracyDegrees'),
  ('d', 'latitude'),
  ('d', 'longitude'),
  ('f', 'accuracy'),
  ('f', 'speed'),
  ('f', 'speedAccuracyMetersPerSecond'),
  ('Q', 'time'),
)
locationNamedTuple = namedtuple('location', ' '.join([x[1] for x in locationList]))
locationStruct = struct.Struct('>' + ' '.join([x[0] for x in locationList]))

def parseSensor(sample):
  print(sensorStruct.unpack(sample))

def parseLocation(sample):
  print(locationStruct.unpack(sample))

def computeDigest(digest):
  return lambda sample : digest.update(sample)


def processMP4(filename):
  print('Processing', filename)
  
  with open(filename, 'rb') as f:

    TRACKS = recurseOnTracks(f)
    #print(TRACKS)

    processSamples(f, TRACKS[1], print)
#    processSamples(f, TRACKS[2], parseSensor)
#    processSamples(f, TRACKS[3], parseLocation)

    digest2 = hashlib.sha512()
    processSamples(f, TRACKS[2], computeDigest(digest2))
    #print('digest2', digest2.digest())

    digest3 = hashlib.sha512()
    processSamples(f, TRACKS[3], computeDigest(digest3))
    #print('digest3', digest3.digest())
    digest2.update(digest3.digest())

    digest4 = hashlib.sha512()
    processSamples(f, TRACKS[4], computeDigest(digest4))
    #print('digest4', digest4.digest())
    digest2.update(digest4.digest())

    digest5 = hashlib.sha512()
    processSamples(f, TRACKS[5], computeDigest(digest5))
    #print('digest5', digest5.digest())
    digest2.update(digest5.digest())

    print('total digest', base64.b64encode(digest2.digest()))


if True:
  video_dir = '../../videos/'
  video_list = os.listdir(video_dir)
  processMP4(os.path.join(video_dir, video_list[0]))

