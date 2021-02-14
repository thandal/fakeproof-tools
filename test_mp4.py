#!/usr/bin/python3
import mp4

# 
filename = '../../videos/walk.mp4'
f = open(filename, 'rb')

if 1:  # Low-level tests
  print('===== Low-level tests =====')
  #
  boxes = mp4.listBoxes(f)
  print(boxes)
  
  #
  print(mp4.readSubBox(f, boxes, b'ftyp'))
  
  #
  moovBoxes = mp4.listSubBoxes(f, boxes, b'moov')
  print('moov', moovBoxes)
  trakBoxes = mp4.listSubBoxes(f, moovBoxes, b'trak')
  print('trak', trakBoxes)
  metaBoxes = mp4.listSubBoxes(f, moovBoxes, b'meta')
  print('meta', metaBoxes)

if 1:  # High-level tests
  print('===== High-level tests =====')
  tracks = mp4.listTracks(f)
  print(tracks)
