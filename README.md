# fakeproof-tools
Very crude data extraction tool for MP4 files created by the [FakeProof App](https://play.google.com/store/apps/details?id=com.ee.fakeproof).
```
git clone https://github.com/thandal/fakeproof-tools.git
cd fakeproof-tools
make
```

In general, FP MP4 tracks are
* Track 0: FP Metadata
* Track 1: FP Sensor Samples
* Track 2: FP Location Samples
* ...various video and audio tracks

So to extract FP Metadata, FP Sensor Data, and FP Location Data, do something like
```
./extract_track -t 0 -c fp_metadata.csv example.mp4
./extract_track -t 1 -c fp_sensor.csv example.mp4
./extract_track -t 2 -c fp_location.csv example.mp4
```

The details of the various fields are described at the top of extract_track.c, but for convenience, the CSV fields are
* FP Sensor Data -- Recording Timestamp, Sensor Type, X, Y, Z
* FP Location Data -- Recording Timestamp, Altitude, Vertical Accuracy, Bearing, Bearing Accuracy, Latitude, Longitude, Accuracy, Speed, Speed Accuracy, Time
