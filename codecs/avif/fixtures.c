/* SPDX-License-Identifier: BSD-3-Clause
 * CI-only fixture encoder, absent from the production decoder DLL.
 */
#include <avif/avif.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <direct.h>

static void check(avifResult r) {
    if (r != AVIF_RESULT_OK) { fprintf(stderr, "libavif: %s\n", avifResultToString(r)); exit(1); }
}
static void write_file(const char *dir, const char *name, const void *p, size_t n) {
    char path[2048]; FILE *f;
    if (snprintf(path, sizeof(path), "%s/%s", dir, name) >= sizeof(path)) exit(1);
    f = fopen(path, "wb");
    if (!f || fwrite(p, 1, n, f) != n || fclose(f)) { perror(path); exit(1); }
}
static void encode(const char *dir, const char *name, avifImage *im) {
    avifEncoder *enc = avifEncoderCreate();
    avifRWData data = AVIF_DATA_EMPTY;
    if (!enc) exit(1);
    enc->codecChoice = AVIF_CODEC_CHOICE_AOM;
    enc->maxThreads = 1; enc->speed = AVIF_SPEED_FASTEST;
    enc->quality = enc->qualityAlpha = AVIF_QUALITY_BEST;
    check(avifEncoderWrite(enc, im, &data));
    write_file(dir, name, data.data, data.size);
    if (!strcmp(name, "rgba.avif")) {
        write_file(dir, "truncated.avif", data.data, data.size / 2);
        data.data[8] = 'm'; data.data[9] = 'i'; data.data[10] = 'f'; data.data[11] = '1';
        write_file(dir, "other-brand.avif", data.data, data.size);
    }
    avifRWDataFree(&data); avifEncoderDestroy(enc);
}
int main(int argc, char **argv) {
    unsigned char pixels[8 * 6 * 4], icc[128] = {0};
    avifImage *im; avifRGBImage rgb; unsigned x, y;
    if (argc != 2) { fprintf(stderr, "Usage: avif-fixtures OUTPUT_DIRECTORY\n"); return 2; }
    _mkdir(argv[1]);
    im = avifImageCreate(8, 6, 8, AVIF_PIXEL_FORMAT_YUV444);
    if (!im) return 1;
    im->colorPrimaries = AVIF_COLOR_PRIMARIES_BT709;
    im->transferCharacteristics = AVIF_TRANSFER_CHARACTERISTICS_SRGB;
    im->matrixCoefficients = AVIF_MATRIX_COEFFICIENTS_IDENTITY;
    im->yuvRange = AVIF_RANGE_FULL;
    for (y = 0; y < 6; ++y) for (x = 0; x < 8; ++x) {
        unsigned i = (y * 8 + x) * 4;
        pixels[i] = (unsigned char)(x * 31); pixels[i + 1] = (unsigned char)(y * 47);
        pixels[i + 2] = (unsigned char)((x + y) * 19); pixels[i + 3] = (unsigned char)(x % 3 == 0 ? 0 : x % 3 == 1 ? 128 : 255);
    }
    avifRGBImageSetDefaults(&rgb, im); rgb.format = AVIF_RGB_FORMAT_RGBA;
    rgb.pixels = pixels; rgb.rowBytes = 8 * 4;
    check(avifImageRGBToYUV(im, &rgb));
    encode(argv[1], "rgba.avif", im);
    im->transformFlags = AVIF_TRANSFORM_IROT; im->irot.angle = 1;
    encode(argv[1], "rotated.avif", im); im->transformFlags = AVIF_TRANSFORM_NONE;
    icc[3] = 128; memcpy(icc + 36, "acsp", 4);
    check(avifImageSetProfileICC(im, icc, sizeof(icc)));
    encode(argv[1], "icc.avif", im);
    avifImageDestroy(im);
    puts("Generated 8x6 RGBA lossless, truncated, other-brand, rotated and ICC fixtures.");
    return 0;
}
