CC=gcc
CFLAGS=-Ilibmp4/include

LM4=libmp4/src

extract_track : extract_track.c $(LM4)/mp4.c $(LM4)/mp4_box.c $(LM4)/mp4_demux.c $(LM4)/mp4_track.c

clean :
	rm extract_track
