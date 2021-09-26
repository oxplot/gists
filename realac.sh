#!/bin/sh

parallel ffmpeg -i {} -vn -acodec alac {.}.tmp.m4a '&&' mv -f {.}.tmp.m4a {.}.m4a ::: "$@"
