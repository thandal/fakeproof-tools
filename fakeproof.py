#!/usr/bin/python3
import struct
from collections import namedtuple

import base64
import hashlib


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

