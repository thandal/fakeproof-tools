import os, sys
import struct
from collections import namedtuple


# For MP4 file format, see https://xhelmboyx.tripod.com/formats/mp4-layout.txt

# Base MP4 box
boxHeaderDescription = (
  ('I', 'length'),
  ('4s', 'type'),
)
boxHeaderStruct = struct.Struct('>' + ' '.join([x[0] for x in boxHeaderDescription]))
boxHeaderNamedTuple = namedtuple('box', ' '.join([x[1] for x in boxHeaderDescription]))

# MP4 box types
boxDescriptions = {
  b'ftyp' : (
    ('4s', 'major_brand'),
    ('I', 'major_brand_version'),
    ('4s', 'compatible_brand'),
    # may be more compatible brands
  ),
  b'hdlr' : (
    ('B', 'version'),
    ('3s', 'flags'),
    ('4s', 'type'),
    ('4s', 'subtype'),
    ('4s', 'manufacturer'),
    ('4s', 'reserved_flags'),
    ('4s', 'reserved_mask'),
    ('', 'component_name'), # component name ASCII string, use readcstr
  ),
#  b'meta' : (  # Metadata
#      # Note: there are two types of meta boxes. Ones without version/flags
#      # (found in 'moov' and 'trak' boxes), and ones *with* version/flags
#      # (found in 'udta' boxes). If without version/flags, they are just a
#      # container, so use 'box'.
#    ('B', 'version'),
#    ('3s', 'flags'),
#  ),
  b'mvhd' : (  # Movie Header
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
  ),
  b'tkhd' : (  # Track Header
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
  ),
}

boxDict = {}
for key, value in boxDescriptions.items():
  boxDict[key] = (struct.Struct('>' + ' '.join([x[0] for x in value])),
                  namedtuple(key.decode(), ' '.join([x[1] for x in value])))

################################################################################
# Low-level functions
################################################################################

def readBoxHeader(f):
  data = f.read(boxHeaderStruct.size)
  if data == b'': return None
  length, type = boxHeaderStruct.unpack(data)
  if length == 1:  # Special length trick
    print('Read long length for', type)
    length = int.from_bytes(f.read(8), 'big')
  header = boxHeaderNamedTuple._make((length, type))
  return header

def readBoxAutoType(f):
  header = readBoxHeader(f)
  boxTypeStruct, boxTypeNamedTuple = boxDict[header.type]
  data = f.read(boxTypeStruct.size)
  assert(data != b'')
  fields = boxTypeStruct.unpack(data)
  return boxTypeNamedTuple._make(fields)

def readBoxOfType(f, boxType):
  header = readBoxHeader(f)
  assert(header.type == boxType)
  boxTypeStruct, boxTypeNamedTuple = boxDict[boxType]
  data = f.read(boxTypeStruct.size)
  assert(data != b'')
  fields = boxTypeStruct.unpack(data)
  return boxTypeNamedTuple._make(fields)

def readSubBox(f, boxes, boxType):
  f.seek(boxes[boxType])
  box = readBoxOfType(f, boxType)
  return box

def listBoxes(f, start_offset = 0, end_offset = sys.maxsize):
  """Scan f for data boxes and return a dict of boxes: {type: offset}.
  Specify a start_offset and end_offset to read sub-boxes.
  """
  boxes = {}
  offset = start_offset
  while True:
    f.seek(offset)
    header = readBoxHeader(f)
    if header is None: break
    boxes[header.type] = offset
    offset += header.length
    if (offset >= end_offset): break
  return boxes

def listSubBoxes(f, boxes, boxType):
  offset = boxes[boxType]
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == boxType)
  return listBoxes(f, f.tell(), offset + header.length)


################################################################################
# High-level functions
################################################################################

def listTracks(f):
  boxes = listBoxes(f)
  assert(b'ftyp' in boxes)
  T = {}
  moovBoxes = listSubBoxes(f, boxes, b'moov')
  # Note: moov has a copy of the last trak -- handy for knowing how many to
  # expect! (But we don't use it fow now).
  workingBoxes = listSubBoxes(f, moovBoxes, b'meta')
  while True:
    if b'trak' not in workingBoxes: break
    workingBoxes = listSubBoxes(f, workingBoxes, b'trak')
    tkhdBox = readSubBox(f, workingBoxes, b'tkhd')
    print(tkhdBox)
    T[tkhdBox.track_id] = workingBoxes
  return T














def readFtyp(f):
  f.seek(0)
  length, type = readBox(f)
  assert(type == b'ftyp')
  data = f.read(ftypStruct.size)
  return ftypNamedType._make(ftypStruct.unpack(data))

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
