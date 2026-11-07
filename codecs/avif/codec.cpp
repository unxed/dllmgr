/* SPDX-License-Identifier: BSD-3-Clause
 * A deliberately small, read-only WIC AVIF decoder. No registration side effects.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincodec.h>
#include <initguid.h>
#include "codec_ids.h"
#include <avif/avif.h>
#include <new>
#include <stdint.h>
#include <string.h>
#include <stdio.h>

static void trace(const char *method, HRESULT value) {
    char enabled[2];
    if (GetEnvironmentVariableA("DLLMGR_AVIF_TRACE", enabled, sizeof(enabled)))
        fprintf(stderr, "dllmgr-avif %s: %08lx\n", method, static_cast<unsigned long>(value));
}

static LONG objects, serverLocks;
static const UINT MAX_DIMENSION = 16384;
static const UINT MAX_PIXELS = 64 * 1024 * 1024;
static const ULONGLONG MAX_INPUT = 128 * 1024 * 1024;

struct SharedLock {
    SRWLOCK *lock;
    explicit SharedLock(SRWLOCK *p) : lock(p) { AcquireSRWLockShared(p); }
    ~SharedLock() { ReleaseSRWLockShared(lock); }
};
struct ExclusiveLock {
    SRWLOCK *lock;
    explicit ExclusiveLock(SRWLOCK *p) : lock(p) { AcquireSRWLockExclusive(p); }
    ~ExclusiveLock() { ReleaseSRWLockExclusive(lock); }
};
struct Bytes {
    BYTE *p = nullptr;
    ~Bytes() { if (p) HeapFree(GetProcessHeap(), 0, p); }
    bool alloc(SIZE_T n) { p = static_cast<BYTE *>(HeapAlloc(GetProcessHeap(), 0, n)); return p != nullptr; }
};
static bool brand(const BYTE *p, size_t n) {
    return n >= 16 && !memcmp(p + 4, "ftyp", 4) &&
           (!memcmp(p + 8, "avif", 4) || !memcmp(p + 8, "avis", 4));
}
static HRESULT avifError(avifResult r) {
    switch (r) {
    case AVIF_RESULT_OK: return S_OK;
    case AVIF_RESULT_OUT_OF_MEMORY: return E_OUTOFMEMORY;
    case AVIF_RESULT_NO_CODEC_AVAILABLE: return WINCODEC_ERR_COMPONENTNOTFOUND;
    case AVIF_RESULT_UNSUPPORTED_DEPTH: return WINCODEC_ERR_UNSUPPORTEDPIXELFORMAT;
    case AVIF_RESULT_NOT_IMPLEMENTED: return WINCODEC_ERR_UNSUPPORTEDOPERATION;
    case AVIF_RESULT_IO_ERROR: return WINCODEC_ERR_STREAMREAD;
    case AVIF_RESULT_TRUNCATED_DATA: return WINCODEC_ERR_BADSTREAMDATA;
    default: return WINCODEC_ERR_BADIMAGE;
    }
}
static HRESULT colorContexts(UINT n, IWICColorContext **contexts, UINT *actual) {
    if (!actual) return E_INVALIDARG;
    *actual = 1;
    if (!n) return S_OK;
    if (!contexts || !contexts[0]) return E_INVALIDARG;
    return contexts[0]->InitializeFromExifColorSpace(1); // sRGB
}

class Frame final : public IWICBitmapFrameDecode {
    LONG refs = 1;
public:
    UINT width = 0, height = 0;
    bool allFrames = true;
    Bytes pixels;
    Frame() { InterlockedIncrement(&objects); }
    ~Frame() { InterlockedDecrement(&objects); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void **out) override {
        if (!out) return E_POINTER;
        *out = nullptr;
        if (iid != IID_IUnknown && iid != IID_IWICBitmapSource && iid != IID_IWICBitmapFrameDecode) return E_NOINTERFACE;
        *out = static_cast<IWICBitmapFrameDecode *>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { ULONG n = InterlockedDecrement(&refs); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE GetSize(UINT *w, UINT *h) override {
        if (!w || !h) return E_INVALIDARG; *w = width; *h = height; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetPixelFormat(WICPixelFormatGUID *format) override {
        if (!format) return E_INVALIDARG; *format = GUID_WICPixelFormat32bppBGRA; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetResolution(double *x, double *y) override {
        if (!x || !y) return E_INVALIDARG; *x = *y = 96.0; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE CopyPalette(IWICPalette *) override { return WINCODEC_ERR_PALETTEUNAVAILABLE; }
    HRESULT STDMETHODCALLTYPE CopyPixels(const WICRect *rect, UINT stride, UINT size, BYTE *buffer) override {
        WICRect all = {0, 0, static_cast<INT>(width), static_cast<INT>(height)};
        if (!rect) rect = &all;
        if (!buffer || rect->X < 0 || rect->Y < 0 || rect->Width <= 0 || rect->Height <= 0 ||
            static_cast<UINT>(rect->X) >= width || static_cast<UINT>(rect->Y) >= height ||
            static_cast<UINT>(rect->Width) > width - rect->X || static_cast<UINT>(rect->Height) > height - rect->Y)
            return E_INVALIDARG;
        UINT row = static_cast<UINT>(rect->Width) * 4;
        if (stride < row) return E_INVALIDARG;
        if (static_cast<uint64_t>(rect->Height - 1) * stride + row > size) return WINCODEC_ERR_INSUFFICIENTBUFFER;
        for (INT y = 0; y < rect->Height; ++y)
            memcpy(buffer + static_cast<size_t>(y) * stride,
                   pixels.p + (static_cast<size_t>(rect->Y + y) * width + rect->X) * 4, row);
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetMetadataQueryReader(IWICMetadataQueryReader **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr; return WINCODEC_ERR_UNSUPPORTEDOPERATION;
    }
    HRESULT STDMETHODCALLTYPE GetColorContexts(UINT n, IWICColorContext **c, UINT *actual) override { return colorContexts(n, c, actual); }
    HRESULT STDMETHODCALLTYPE GetThumbnail(IWICBitmapSource **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr; return WINCODEC_ERR_CODECNOTHUMBNAIL;
    }
};

static HRESULT decode(IStream *stream, Frame **out) {
    LARGE_INTEGER pos = {};
    ULARGE_INTEGER length = {};
    HRESULT hr = stream->Seek(pos, STREAM_SEEK_END, &length);
    if (FAILED(hr)) return hr;
    if (length.QuadPart < 16) return WINCODEC_ERR_BADHEADER;
    if (length.QuadPart > MAX_INPUT) return WINCODEC_ERR_IMAGESIZEOUTOFRANGE;
    hr = stream->Seek(pos, STREAM_SEEK_SET, nullptr); // WIC pattern matching leaves the stream positioned inside its header.
    if (FAILED(hr)) return hr;
    Bytes input;
    UINT size = static_cast<UINT>(length.QuadPart), done = 0;
    if (!input.alloc(size)) return E_OUTOFMEMORY;
    while (done < size) {
        ULONG got = 0;
        hr = stream->Read(input.p + done, size - done, &got);
        if (FAILED(hr)) return hr;
        if (!got || got > size - done) return WINCODEC_ERR_BADSTREAMDATA;
        done += got;
    }
    if (!brand(input.p, size)) return WINCODEC_ERR_UNKNOWNIMAGEFORMAT;
    avifDecoder *d = avifDecoderCreate();
    if (!d) return E_OUTOFMEMORY;
    d->maxThreads = 2;
    d->imageDimensionLimit = MAX_DIMENSION;
    d->imageSizeLimit = MAX_PIXELS;
    d->imageCountLimit = 1024;
    avifResult result = avifDecoderSetIOMemory(d, input.p, size);
    if (result == AVIF_RESULT_OK) result = avifDecoderParse(d);
    if (result == AVIF_RESULT_OK) result = avifDecoderNextImage(d);
    hr = avifError(result);
    Frame *f = nullptr;
    if (SUCCEEDED(hr)) {
        const avifImage *im = d->image;
        // No color-management or spatial-transform engine is hidden behind this API.
        // Reject data we cannot honestly expose as straight, oriented sRGB pixels.
        if (im->icc.size || im->exif.size ||
            (im->colorPrimaries != AVIF_COLOR_PRIMARIES_BT709 && im->colorPrimaries != AVIF_COLOR_PRIMARIES_UNSPECIFIED) ||
            (im->transferCharacteristics != AVIF_TRANSFER_CHARACTERISTICS_SRGB && im->transferCharacteristics != AVIF_TRANSFER_CHARACTERISTICS_UNSPECIFIED) ||
            (im->transformFlags & (AVIF_TRANSFORM_CLAP | AVIF_TRANSFORM_IMIR)) ||
            ((im->transformFlags & AVIF_TRANSFORM_IROT) && im->irot.angle) ||
            ((im->transformFlags & AVIF_TRANSFORM_PASP) && im->pasp.hSpacing != im->pasp.vSpacing))
            hr = WINCODEC_ERR_UNSUPPORTEDOPERATION;
        else if (!im->width || !im->height || im->width > MAX_DIMENSION || im->height > MAX_DIMENSION ||
                 static_cast<uint64_t>(im->width) * im->height > MAX_PIXELS)
            hr = WINCODEC_ERR_IMAGESIZEOUTOFRANGE;
        else {
            f = new(std::nothrow) Frame;
            if (!f || !f->pixels.alloc(static_cast<size_t>(im->width) * im->height * 4)) hr = E_OUTOFMEMORY;
            else {
                f->width = im->width; f->height = im->height;
                f->allFrames = d->imageCount <= 1;
                avifRGBImage rgb;
                avifRGBImageSetDefaults(&rgb, im);
                rgb.depth = 8; rgb.format = AVIF_RGB_FORMAT_BGRA;
                rgb.alphaPremultiplied = AVIF_FALSE;
                rgb.pixels = f->pixels.p; rgb.rowBytes = im->width * 4;
                hr = avifError(avifImageYUVToRGB(im, &rgb));
            }
        }
    }
    avifDecoderDestroy(d);
    if (FAILED(hr)) { if (f) f->Release(); return hr; }
    *out = f;
    return S_OK;
}

class Decoder final : public IWICBitmapDecoder {
    LONG refs = 1;
    SRWLOCK lock = SRWLOCK_INIT;
    Frame *frame = nullptr;
public:
    Decoder() { InterlockedIncrement(&objects); }
    ~Decoder() { if (frame) frame->Release(); InterlockedDecrement(&objects); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void **out) override {
        if (!out) return E_POINTER; *out = nullptr;
        if (iid != IID_IUnknown && iid != IID_IWICBitmapDecoder) return E_NOINTERFACE;
        *out = static_cast<IWICBitmapDecoder *>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { ULONG n = InterlockedDecrement(&refs); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE QueryCapability(IStream *stream, DWORD *capability) override {
        if (!stream || !capability) return E_INVALIDARG; *capability = 0;
        LARGE_INTEGER zero = {}, saved;
        ULARGE_INTEGER old;
        HRESULT hr = stream->Seek(zero, STREAM_SEEK_CUR, &old);
        if (FAILED(hr)) return hr;
        Frame *candidate = nullptr;
        hr = decode(stream, &candidate);
        saved.QuadPart = old.QuadPart;
        HRESULT restore = stream->Seek(saved, STREAM_SEEK_SET, nullptr);
        if (candidate) {
            if (SUCCEEDED(hr) && SUCCEEDED(restore))
                *capability = candidate->allFrames ? WICBitmapDecoderCapabilityCanDecodeAllImages : WICBitmapDecoderCapabilityCanDecodeSomeImages;
            candidate->Release();
        }
        trace("QueryCapability", FAILED(restore) ? restore : hr);
        if (FAILED(restore)) return restore;
        if (FAILED(hr)) return hr;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE Initialize(IStream *stream, WICDecodeOptions options) override {
        if (!stream || (options != WICDecodeMetadataCacheOnDemand && options != WICDecodeMetadataCacheOnLoad)) return E_INVALIDARG;
        ExclusiveLock guard(&lock);
        if (frame) return WINCODEC_ERR_WRONGSTATE;
        HRESULT hr = decode(stream, &frame); trace("Initialize", hr); return hr;
    }
    HRESULT STDMETHODCALLTYPE GetContainerFormat(GUID *out) override {
        if (!out) return E_INVALIDARG; *out = GUID_DllmgrAvifContainer; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetDecoderInfo(IWICBitmapDecoderInfo **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr;
        IWICImagingFactory *factory = nullptr; IWICComponentInfo *info = nullptr;
        HRESULT hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&factory));
        if (SUCCEEDED(hr)) hr = factory->CreateComponentInfo(CLSID_DllmgrAvifDecoder, &info);
        if (SUCCEEDED(hr)) hr = info->QueryInterface(IID_PPV_ARGS(out));
        if (info) info->Release(); if (factory) factory->Release(); return hr;
    }
    HRESULT STDMETHODCALLTYPE CopyPalette(IWICPalette *) override { return WINCODEC_ERR_PALETTEUNAVAILABLE; }
    HRESULT STDMETHODCALLTYPE GetMetadataQueryReader(IWICMetadataQueryReader **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr; return WINCODEC_ERR_UNSUPPORTEDOPERATION;
    }
    HRESULT STDMETHODCALLTYPE GetPreview(IWICBitmapSource **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr; return WINCODEC_ERR_UNSUPPORTEDOPERATION;
    }
    HRESULT STDMETHODCALLTYPE GetColorContexts(UINT n, IWICColorContext **c, UINT *actual) override {
        SharedLock guard(&lock); if (!frame) return WINCODEC_ERR_NOTINITIALIZED; return colorContexts(n, c, actual);
    }
    HRESULT STDMETHODCALLTYPE GetThumbnail(IWICBitmapSource **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr; return WINCODEC_ERR_CODECNOTHUMBNAIL;
    }
    HRESULT STDMETHODCALLTYPE GetFrameCount(UINT *out) override {
        trace("GetFrameCount initialized", frame ? S_OK : WINCODEC_ERR_NOTINITIALIZED);
        if (!out) return E_INVALIDARG; *out = 0; SharedLock guard(&lock);
        if (!frame) return WINCODEC_ERR_NOTINITIALIZED; *out = 1; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetFrame(UINT index, IWICBitmapFrameDecode **out) override {
        if (!out) return E_INVALIDARG; *out = nullptr; SharedLock guard(&lock);
        if (!frame) return WINCODEC_ERR_NOTINITIALIZED;
        if (index) return WINCODEC_ERR_FRAMEMISSING;
        frame->AddRef(); *out = frame; return S_OK;
    }
};

class Factory final : public IClassFactory {
    LONG refs = 1;
public:
    Factory() { InterlockedIncrement(&objects); }
    ~Factory() { InterlockedDecrement(&objects); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void **out) override {
        if (!out) return E_POINTER; *out = nullptr;
        if (iid != IID_IUnknown && iid != IID_IClassFactory) return E_NOINTERFACE;
        *out = static_cast<IClassFactory *>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&refs); }
    ULONG STDMETHODCALLTYPE Release() override { ULONG n = InterlockedDecrement(&refs); if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE CreateInstance(IUnknown *outer, REFIID iid, void **out) override {
        if (!out) return E_POINTER; *out = nullptr;
        if (outer) return CLASS_E_NOAGGREGATION;
        Decoder *d = new(std::nothrow) Decoder; if (!d) return E_OUTOFMEMORY;
        HRESULT hr = d->QueryInterface(iid, out); d->Release(); return hr;
    }
    HRESULT STDMETHODCALLTYPE LockServer(BOOL value) override {
        if (value) InterlockedIncrement(&serverLocks); else InterlockedDecrement(&serverLocks); return S_OK;
    }
};
extern "C" HRESULT WINAPI DllGetClassObject(REFCLSID clsid, REFIID iid, void **out) {
    if (!out) return E_POINTER; *out = nullptr;
    if (clsid != CLSID_DllmgrAvifDecoder) return CLASS_E_CLASSNOTAVAILABLE;
    Factory *f = new(std::nothrow) Factory; if (!f) return E_OUTOFMEMORY;
    HRESULT hr = f->QueryInterface(iid, out); f->Release(); return hr;
}
extern "C" HRESULT WINAPI DllCanUnloadNow() {
    return !InterlockedCompareExchange(&objects, 0, 0) && !InterlockedCompareExchange(&serverLocks, 0, 0) ? S_OK : S_FALSE;
}
