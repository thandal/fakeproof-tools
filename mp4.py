#!/usr/bin/python3
# Execute as a script for basic tests.
import os, struct, sys
from collections import namedtuple


################################################################################
# MP4 data structures 
################################################################################
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

def readSubBox(f, boxes, boxType, index = 0):
  f.seek(boxes[boxType][index])
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
    boxes.setdefault(header.type, []).append(offset)
    offset += header.length
    if (offset >= end_offset): break
  return boxes

def listSubBoxes(f, boxes, boxType, index = 0):
  offset = boxes[boxType][index]
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == boxType)
  return listBoxes(f, f.tell(), offset + header.length)

# Specialized functions to read sample table data: struct can't handle variable-length.

def readStscBox(f, offset):
  # Sample to block (or chunk) table
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == b'stsc')
  f.read(4)  # skip version/flags
  numberOfBlocks = int.from_bytes(f.read(4), 'big')
  spb = []
  for i in range(numberOfBlocks):
    firstBlock = int.from_bytes(f.read(4), 'big')
    numberOfSamples = int.from_bytes(f.read(4), 'big')
    sampleDescriptionId = int.from_bytes(f.read(4), 'big')  # Unused...
    spb.append((firstBlock, numberOfSamples))
  return spb

def readStszBox(f, offset):
  # Sample size table
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == b'stsz')
  f.read(4)  # skip version/flags
  fixedBlockSize = int.from_bytes(f.read(4), 'big')
  if (fixedBlockSize > 0): return fixedBlockSize
  numberOfSampleSizes = int.from_bytes(f.read(4), 'big')
  ss = []
  for i in range(numberOfSampleSizes):
    sampleSize = int.from_bytes(f.read(4), 'big')
    ss.append(sampleSize)
  return ss

def readSttsBox(f, offset):
  # Sample duration table
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == b'stts')
  f.read(4)  # skip version/flags
  numberOfEntries = int.from_bytes(f.read(4), 'big')
  st = []
  for i in range(numberOfEntries):
    count = int.from_bytes(f.read(4), 'big')
    duration = int.from_bytes(f.read(4), 'big')
    st.append((count, duration))
  return st

def readCo64Box(f, offset):
  # Block (or chunk) offset table
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == b'co64')
  f.read(4)  # skip version/flags
  numberOfBlockOffsets = int.from_bytes(f.read(4), 'big')
  bo = []
  for i in range(numberOfBlockOffsets):
    blockOffset = int.from_bytes(f.read(8), 'big')
    bo.append(blockOffset)
  return bo 

def readStcoBox(f, offset):
  # Block (or chunk) offset table (32-bit variant)
  f.seek(offset)
  header = readBoxHeader(f)
  assert(header.type == b'stco')
  f.read(4)  # skip version/flags
  numberOfBlockOffsets = int.from_bytes(f.read(4), 'big')
  bo = []
  for i in range(numberOfBlockOffsets):
    blockOffset = int.from_bytes(f.read(4), 'big')
    bo.append(blockOffset)
  return bo

# Fragmented MP4 (moof/mdat) parsing

# trun flags
TRUN_DATA_OFFSET        = 0x000001
TRUN_FIRST_SAMPLE_FLAGS = 0x000004
TRUN_SAMPLE_DURATION    = 0x000100
TRUN_SAMPLE_SIZE        = 0x000200
TRUN_SAMPLE_FLAGS       = 0x000400
TRUN_SAMPLE_CTS_OFFSET  = 0x000800

def readMoofSamples(f, moofOffset):
  """Parse a moof box and return (track_id, base_decode_time, [(size, duration), ...], data_offset).
  data_offset is absolute file position of the sample data."""
  moofSubBoxes = listSubBoxes(f, {b'moof': [moofOffset]}, b'moof')
  trafSubBoxes = listSubBoxes(f, moofSubBoxes, b'traf')

  # tfhd: track ID
  f.seek(trafSubBoxes[b'tfhd'][0])
  header = readBoxHeader(f)
  version_flags = int.from_bytes(f.read(4), 'big')
  track_id = int.from_bytes(f.read(4), 'big')

  # tfdt: base media decode time
  f.seek(trafSubBoxes[b'tfdt'][0])
  header = readBoxHeader(f)
  version_flags = int.from_bytes(f.read(4), 'big')
  version = version_flags >> 24
  if version == 1:
    base_decode_time = int.from_bytes(f.read(8), 'big')
  else:
    base_decode_time = int.from_bytes(f.read(4), 'big')

  # trun: sample table
  f.seek(trafSubBoxes[b'trun'][0])
  header = readBoxHeader(f)
  version_flags = int.from_bytes(f.read(4), 'big')
  flags = version_flags & 0xFFFFFF
  sample_count = int.from_bytes(f.read(4), 'big')

  data_offset = 0
  if flags & TRUN_DATA_OFFSET:
    data_offset = int.from_bytes(f.read(4), 'big', signed=True)
  if flags & TRUN_FIRST_SAMPLE_FLAGS:
    f.read(4)  # skip

  samples = []
  for i in range(sample_count):
    duration = 0
    size = 0
    if flags & TRUN_SAMPLE_DURATION:
      duration = int.from_bytes(f.read(4), 'big')
    if flags & TRUN_SAMPLE_SIZE:
      size = int.from_bytes(f.read(4), 'big')
    if flags & TRUN_SAMPLE_FLAGS:
      f.read(4)  # skip
    if flags & TRUN_SAMPLE_CTS_OFFSET:
      f.read(4)  # skip
    samples.append((size, duration))

  # data_offset is relative to the start of the moof box
  abs_data_offset = moofOffset + data_offset
  return track_id, base_decode_time, samples, abs_data_offset

################################################################################
# High-level functions
################################################################################

def isFragmented(f):
  """Check if the file uses fragmented MP4 (has moof boxes)."""
  boxes = listBoxes(f)
  return b'moof' in boxes

def listTraks(f):
  boxes = listBoxes(f)
  assert(b'ftyp' in boxes)
  moovBoxes = listSubBoxes(f, boxes, b'moov')
  return moovBoxes[b'trak']

def processSamples(f, index, callback):
  boxes = listBoxes(f)
  moovSubBoxes = listSubBoxes(f, boxes, b'moov')
  trakSubBoxes = listSubBoxes(f, moovSubBoxes, b'trak', index)

  # Get the track ID for this index
  tkhdBox = readSubBox(f, trakSubBoxes, b'tkhd')
  track_id = tkhdBox.track_id

  if b'moof' in boxes:
    # Fragmented MP4: samples are in moof/mdat pairs
    for moofOffset in boxes[b'moof']:
      moof_track_id, base_decode_time, samples, data_offset = readMoofSamples(f, moofOffset)
      if moof_track_id != track_id:
        continue
      f.seek(data_offset)
      time = base_decode_time
      for size, duration in samples:
        sample = f.read(size)
        callback(time, sample)
        time += duration
  else:
    # Non-fragmented MP4: samples are in stbl tables
    mdiaSubBoxes = listSubBoxes(f, trakSubBoxes, b'mdia')
    minfSubBoxes = listSubBoxes(f, mdiaSubBoxes, b'minf')
    stblSubBoxes = listSubBoxes(f, minfSubBoxes, b'stbl')

    blockToSamplesTable = readStscBox(f, stblSubBoxes[b'stsc'][0])
    sampleSizes = readStszBox(f, stblSubBoxes[b'stsz'][0])
    sampleDurations = readSttsBox(f, stblSubBoxes[b'stts'][0])
    if b'co64' in stblSubBoxes:
      blockOffsets = readCo64Box(f, stblSubBoxes[b'co64'][0])
    else:
      blockOffsets = readStcoBox(f, stblSubBoxes[b'stco'][0])

    tableCounter = 0
    blockInTableCounter = 0
    sampleInBlockCounter = 0
    sampleInDurationCounter = 0
    durationCounter = 0
    blockCounter = 0
    f.seek(blockOffsets[blockCounter])
    time = 0
    for sampleCounter in range(len(sampleSizes)):
      if sampleInDurationCounter >= sampleDurations[durationCounter][0]:
        durationCounter += 1
        sampleInDurationCounter = 0
      if sampleInBlockCounter >= blockToSamplesTable[tableCounter][1]:
        blockCounter += 1
        sampleInBlockCounter = 0
        if blockCounter + 1 >= blockToSamplesTable[tableCounter + 1][0]:
          tableCounter += 1
        f.seek(blockOffsets[blockCounter])
      sample = f.read(sampleSizes[sampleCounter])
      callback(time, sample)
      sampleInBlockCounter += 1
      sampleInDurationCounter += 1
      time += sampleDurations[durationCounter][1]


# Tests
if __name__ == '__main__':
  filename = 'test_recording.mp4'
  f = open(filename, 'rb')

  if 1:  # Low-level tests
    print('===== Low-level tests =====')
    #
    boxes = listBoxes(f)
    print(boxes)
    
    #
    print(readSubBox(f, boxes, b'ftyp'))
    
    #
    moovSubBoxes = listSubBoxes(f, boxes, b'moov')
    print('moov sub-boxes', moovSubBoxes)
    for t in range(len(moovSubBoxes[b'trak'])):
      trakSubBoxes = listSubBoxes(f, moovSubBoxes, b'trak', t)
      print('trak sub-boxes', trakSubBoxes)
      tkhdBox = readSubBox(f, trakSubBoxes, b'tkhd')
      print('tkhd', tkhdBox)
  
  if 1:  # High-level tests
    print('===== High-level tests =====')
    processSamples(f, 0, print)
