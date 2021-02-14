#!/usr/bin/python3
# Execute as a script for basic tests.
import struct
from collections import namedtuple

import base64
import hashlib

import mp4


################################################################################
# FakeProof data structures 
################################################################################

sensorDescription = (
  ('I', 'type'),
  ('f', 'x'),
  ('f', 'y'),
  ('f', 'z'),
)

locationDescription = (
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

def parseDescriptionAsFields(description):
  sampleStruct = struct.Struct('<' + ' '.join([x[0] for x in description]))
  print(' '.join([x[1] for x in description]))
  def cb(time, sample):
    for offset in range(0, len(sample), sampleStruct.size):
      print(time, *sampleStruct.unpack_from(sample, offset))
  return cb

def parseDescriptionAsNamedTuple(description):
  sampleNamedTuple = namedtuple('sample', ' '.join([x[1] for x in description]))
  sampleStruct = struct.Struct('<' + ' '.join([x[0] for x in description]))
  def cb(time, sample):
    for offset in range(0, len(sample), sampleStruct.size):
      fields = sensorStruct.unpack_from(sample, offset)
      print(time, sampleNamedTuple._make(fields))
  return cb

def updateDigest(digest):
  return lambda time, sample : digest.update(sample)

def computeFakeProofDigest(filename):
  print('Processing', filename)
  with open(filename, 'rb') as f:
    trakOffsets = mp4.listTraks(f)
    digests = [hashlib.sha512() for i in range(len(trakOffsets))]
    for t in range(1, len(trakOffsets)):
      mp4.processSamples(f, 1, updateDigest(digests[t]))
    for t in range(2, len(trakOffsets)):
      digests[1].update(digests[t].digest())
    digest = base64.b64encode(digests[1].digest())
    return digest


# Tests
if __name__ == '__main__':
  filename = 'test_recording.mp4'
  if 1:  # Track tests
    f = open(filename, 'rb')
    mp4.processSamples(f, 0, print)
    mp4.processSamples(f, 1, parseDescriptionAsFields(sensorDescription))
    mp4.processSamples(f, 2, parseDescriptionAsFields(locationDescription))
  if 0:  # Digest tests
    print(computeFakeProofDigest(filename))
