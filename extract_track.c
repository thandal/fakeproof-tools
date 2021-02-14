#include <errno.h>
#include <getopt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libmp4.h>

// MP4 sample buffer size.
#define BUF_SIZE 1024<<10

int DEBUG = 0;

struct fp_sensor_data {
    int32_t type;  // 1: Accelerometer, 2: Magnetic Field, 4: Gyroscope
    // x, y, z components are in the right-handed coordinate frame:
    //   x = right, y = up, z = out of the screen,
    // when holding the phone in its default orientation.  The axes are not
    // swapped when the screen orientation changes.
    float x, y, z;  // acceleration: m/s/s, magnetic field: uT, angular rate: rad/s
} __attribute__((packed));

struct fp_location_data {
  double altitude;                     // meters above WGS-84 reference
                                       //  ellipsoid, 0.0 if location does not
                                       //  have an altitude
  float verticalAccuracyMeters;        // vertical accuracy in meters at 68% 
                                       //  confidence (1 stddev if Gaussian),
                                       //  0.0 if location does not have
                                       //  vertical accuracy
  float bearing;                       // degrees in the horizontal direction
                                       //  of travel of the device, (0.0, 360.0]
                                       //  if the device has a bearing, 0.0 if 
                                       //  location does not have a bearing
  float bearingAccuracyDegrees;        // bearing accuracy at 68% confidence
                                       //  (1 stddev if Gaussian), 0.0 if
                                       //  location does not have a bearing
                                       //  accuracy
  double latitude;                     // degrees
  double longitude;                    // degrees
  float accuracy;                      // radial horizontal accuracy in meters
                                       //  at 68% confidence (1 stddev if
                                       //  Gaussian), 0.0 if location does not
                                       //  have a horizontal accuracy
  float speed;                         // meters per second over ground
                                       //  (horizontal), 0.0 if location does
                                       //  not have speed
  float speedAccuracyMetersPerSecond;  // speed accuracy at 68% confidence
                                       //  (1 stddev if Gaussian), 0.0 if location
                                       //  does not have speed accuracy
  long time;                           // UTC time of this fix, in milliseconds
                                       //  since January 1, 1970
                                       //  NOTE: not necessarily monotonic!
} __attribute__((packed));


static int extract_track(char *mp4_filename, int track, char *csv_filename) {
    int ret = 0;

    // Check arguments.
    if (mp4_filename == NULL) {
        fprintf(stderr, "No mp4 filename provided\n");
        return -1;
    }

    if (track < 0) {
        fprintf(stderr, "Invalid track provided: %d\n", track);
        return -1;
    }

    if (csv_filename == NULL) {
        fprintf(stderr, "No CSV filename provided\n");
        return -1;
    }

    // Open files.
    FILE *csv_file = fopen(csv_filename, "w");
    if (csv_file == NULL) {
        fprintf(stderr, "Failed to open CSV file '%s'\n", csv_filename);
        return -1;
    }

    struct mp4_demux *demux = NULL;
    ret = mp4_demux_open(mp4_filename, &demux);
    if (ret < 0 || demux == NULL) {
        fprintf(stderr, "Failed to read MP4 file '%s'\n", mp4_filename);
        return ret;
    }

    // Find MP4 tracks.
    int count = mp4_demux_get_track_count(demux);
    fprintf(stderr, "Track count: %d\n", count);
    
    if (track >= count) {
        fprintf(stderr, "Invalid track provided: %d\n", track);
        return -1;
    }

    fprintf(stderr, "Track info:\n");
    struct mp4_track_info tk;
    for (int t = 0; t < count; ++t) {
        ret = mp4_demux_get_track_info(demux, t, &tk);
        if (ret < 0) {
            fprintf(stderr, "Failed getting track info\n");
            return ret;
        }
        fprintf(stderr, "  index:%d, id:%d, name:%s, type:%d, mime_format:%s\n",
            t, tk.id, tk.name, tk.type, tk.metadata_mime_format);
    }

    ret = mp4_demux_get_track_info(demux, track, &tk);
    if (ret < 0) {
        fprintf(stderr, "Failed getting track info\n");
        return ret;
    }
    fprintf(stderr, "Selected track index: %d, id:%d, name:%s, type:%d, mime_format:%s\n",
        track, tk.id, tk.name, tk.type, tk.metadata_mime_format);

    // Get the samples and process them.
    uint8_t metadata_buffer[BUF_SIZE];
    uint8_t sample_buffer[BUF_SIZE];
    struct mp4_track_sample sample;
    int sample_count = 0;
    do {
        int err = mp4_demux_get_track_sample(
            demux, tk.id, 1, sample_buffer, BUF_SIZE, metadata_buffer, BUF_SIZE, &sample);
        ++sample_count;
        if (err < 0) {
            fprintf(stderr, "Error getting track sample\n");
            continue;
        }
        if (DEBUG) {
            fprintf(stderr, "sample.size %d, sample time %g  ", sample.size,
                    mp4_sample_time_to_usec(sample.dts, tk.timescale) / 1000000.0);
            for (int k = 0; k < sample.size; ++k) {
                fprintf(stderr, "%x ", sample_buffer[k]);
            }
            fprintf(stderr, "\n");
        }
        if (track == 0) {  // FP Metadata Sample
          // FP Metadata is just strings, treat them with some caution by null
          // terminating at sample.size
          sample_buffer[sample.size] = 0;
          fprintf(csv_file, "%g, %s\n",
                  mp4_sample_time_to_usec(sample.dts, tk.timescale) / 1000000.0,
                  sample_buffer);
          continue;
        }
        if (sample.size == 56) {  // FP Location Sample
          struct fp_location_data *p = 
            (struct fp_location_data*)&sample_buffer;
          fprintf(csv_file, "%g, %g, %g, %g, %g, %g, %g, %g, %g, %g, %ld\n",
                  mp4_sample_time_to_usec(sample.dts, tk.timescale) / 1000000.0,
                  p->altitude, p->verticalAccuracyMeters, p->bearing,
                  p->bearingAccuracyDegrees, p->latitude, p->longitude,
                  p->accuracy, p->speed, p->speedAccuracyMetersPerSecond,
                  p->time);
        } else {  // FP Sensor Samples come in multiples of 16 bytes
            for (uint8_t k = 0; k < sample.size; k += 16) {
                struct fp_sensor_data *p =
                  (struct fp_sensor_data*)&sample_buffer[k];
                fprintf(csv_file, "%g, %d, %g, %g, %g\n",
                        mp4_sample_time_to_usec(sample.dts, tk.timescale) / 1000000.0,
                        p->type, p->x, p->y, p->z);
            }
        }
    } while (sample.size);

    mp4_demux_close(demux);
    fclose(csv_file);

    return ret;
}


static const char short_options[] = "ht:c:";

static const struct option long_options[] = {
    {"help", no_argument, NULL, 'h'},
    {"track", required_argument, NULL, 't'},
    {"csv", required_argument, NULL, 'c'},
    {0, 0, 0, 0},
};

static void usage(char *name) {
    printf("Usage: %s [options] <input mp4 file>\n"
           "\n"
           "Options:\n"
           "-h | --help              Print this message\n"
           "     --track <index>     Selected track index\n"
           "     --csv  <file>       Output to CSV file\n"
           "\n",
           name);
}

int main(int argc, char *argv[]) {
    int idx, c;
    char *mp4_filename = NULL;
    char *csv_filename = NULL;
    int track = -1;

    if (argc < 2) {
        usage(argv[0]);
        exit(EXIT_FAILURE);
    }

    // Process the command-line parameters.
    while ((c = getopt_long(
            argc, argv, short_options, long_options, &idx)) != -1) {
        switch (c) {
        case 0:
            break;

        case 'h':
            usage(argv[0]);
            exit(EXIT_SUCCESS);
            break;

        case 't':
            track = atoi(optarg);
            break;

        case 'c':
            csv_filename = optarg;
            break;

        default:
            usage(argv[0]);
            exit(EXIT_FAILURE);
            break;
        }
    }

    if (argc - optind < 1) {
        usage(argv[0]);
        exit(EXIT_FAILURE);
    }

    mp4_filename = argv[optind];

    int ret = extract_track(mp4_filename, track, csv_filename);
    if (ret != 0) {
        fprintf(stderr, "Failed.\n");
        exit(EXIT_FAILURE);
    }

    fprintf(stderr, "Done.\n");
    exit(EXIT_SUCCESS);
}
