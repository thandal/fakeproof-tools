#!/usr/bin/python3

import argparse
import mp4
import fakeproof

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('input', help = 'Input MP4 filename')
  parser.add_argument('-t', '--track', help = 'Zero-index track to extract')
  args = parser.parse_args()
  print(args)

  # TODO -- select on type of output desired, rather than track, and be smart
  # about digging into the file.
  f = open(args.input, 'rb')
  if (args.track == '0'):
    mp4.processSamples(f, 0, print)
  elif (args.track == '1'):
    mp4.processSamples(f, 1, fakeproof.parseDescriptionAsFields(fakeproof.sensorDescription))
  elif (args.track == '2'):
    mp4.processSamples(f, 2, fakeproof.parseDescriptionAsFields(fakeproof.locationDescription))
  else:
    print('No default parser for track', args.track)
