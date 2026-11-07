/* SPDX-License-Identifier: BSD-3-Clause
 * --file is read-only. --self-test creates only two decoder-owned HKLM registry
 * subtrees, refuses to overwrite existing ones, and removes them on every exit.
 */
#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincodec.h>
#include <shlwapi.h>
#include <initguid.h>
#include "../../codecs/avif/codec_ids.h"
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int failures;
#define CHECK(test) do { if (!(test)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #test); ++failures; } } while (0)
#define HR_OK(expr) do { HRESULT check_hr = (expr); if (FAILED(check_hr)) { fprintf(stderr, "FAIL line %d: %s = %08lx\n", __LINE__, #expr, (unsigned long)check_hr); ++failures; } } while (0)
#define REL(p, iface) do { if (p) { iface##_Release(p); p = NULL; } } while (0)
static const WCHAR decoder_key[] = L"Software\\Classes\\CLSID\\" DLLMGR_AVIF_CLSID;
static const WCHAR instance_key[] = L"Software\\Classes\\CLSID\\" DLLMGR_AVIF_CATEGORY L"\\Instance\\" DLLMGR_AVIF_CLSID;
static BOOL own_decoder, own_instance;

static LONG value(HKEY key, const WCHAR *name, DWORD type, const void *data, DWORD size) {
    return RegSetValueExW(key, name, 0, type, (const BYTE *)data, size);
}
static LONG string_value(HKEY key, const WCHAR *name, const WCHAR *s) {
    return value(key, name, REG_SZ, s, (DWORD)((wcslen(s) + 1) * sizeof(WCHAR)));
}
static LONG new_key(const WCHAR *path, HKEY *key, BOOL *owned) {
    DWORD disposition;
    LONG err = RegCreateKeyExW(HKEY_LOCAL_MACHINE, path, 0, NULL, 0, KEY_ALL_ACCESS, NULL, key, &disposition);
    if (!err && disposition != REG_CREATED_NEW_KEY) { RegCloseKey(*key); *key = NULL; return ERROR_ALREADY_EXISTS; }
    if (!err) *owned = TRUE;
    return err;
}
static BOOL absent(const WCHAR *path) {
    HKEY key;
    LONG err = RegOpenKeyExW(HKEY_LOCAL_MACHINE, path, 0, KEY_READ, &key);
    if (!err) RegCloseKey(key);
    return err == ERROR_FILE_NOT_FOUND;
}
static void unregister_test(void) {
    if (own_instance) { CHECK(RegDeleteTreeW(HKEY_LOCAL_MACHINE, instance_key) == ERROR_SUCCESS); own_instance = FALSE; }
    if (own_decoder) { CHECK(RegDeleteTreeW(HKEY_LOCAL_MACHINE, decoder_key) == ERROR_SUCCESS); own_decoder = FALSE; }
}
static LONG register_test(const WCHAR *dll) {
    HKEY key = NULL, sub = NULL;
    LONG err; DWORD zero = 0, one = 1, length = 8; ULONGLONG position = 4;
    BYTE mask[8] = {255,255,255,255,255,255,255,255};
    unsigned i;
#define REG(expr) do { err = (expr); if (err) goto done; } while (0)
    if (!absent(decoder_key) || !absent(instance_key)) return ERROR_ALREADY_EXISTS;
    REG(new_key(decoder_key, &key, &own_decoder));
    REG(string_value(key, L"FriendlyName", L"dllmgr AVIF decoder"));
    REG(string_value(key, L"Author", L"dllmgr contributors"));
    REG(string_value(key, L"Vendor", DLLMGR_AVIF_VENDOR));
    REG(string_value(key, L"ContainerFormat", DLLMGR_AVIF_CONTAINER));
    REG(string_value(key, L"Version", L"0.1.0"));
    REG(string_value(key, L"SpecVersion", L"1.0.0.0"));
    REG(string_value(key, L"MimeTypes", L"image/avif"));
    REG(string_value(key, L"FileExtensions", L".avif"));
    REG(value(key, L"SupportAnimation", REG_DWORD, &zero, 4));
    REG(value(key, L"SupportMultiframe", REG_DWORD, &zero, 4));
    REG(value(key, L"SupportLossless", REG_DWORD, &one, 4));
    REG(value(key, L"SupportChromakey", REG_DWORD, &zero, 4));
    REG(RegCreateKeyExW(key, L"InprocServer32", 0, NULL, 0, KEY_WRITE, NULL, &sub, NULL));
    REG(string_value(sub, NULL, dll)); REG(string_value(sub, L"ThreadingModel", L"Both"));
    RegCloseKey(sub); sub = NULL;
    REG(RegCreateKeyExW(key, L"Formats\\" DLLMGR_AVIF_BGRA, 0, NULL, 0, KEY_WRITE, NULL, &sub, NULL));
    RegCloseKey(sub); sub = NULL;
    for (i = 0; i < 2; ++i) {
        const WCHAR *path = i ? L"Patterns\\1" : L"Patterns\\0";
        const char *pattern = i ? "ftypavis" : "ftypavif";
        REG(RegCreateKeyExW(key, path, 0, NULL, 0, KEY_WRITE, NULL, &sub, NULL));
        REG(value(sub, L"Position", REG_QWORD, &position, sizeof(position)));
        REG(value(sub, L"Length", REG_DWORD, &length, 4));
        REG(value(sub, L"Pattern", REG_BINARY, pattern, 8));
        REG(value(sub, L"Mask", REG_BINARY, mask, 8));
        REG(value(sub, L"EndOfStream", REG_DWORD, &zero, 4));
        RegCloseKey(sub); sub = NULL;
    }
    RegCloseKey(key); key = NULL;
    REG(new_key(instance_key, &key, &own_instance));
    REG(string_value(key, L"CLSID", DLLMGR_AVIF_CLSID));
    REG(string_value(key, L"FriendlyName", L"dllmgr AVIF decoder"));
    err = ERROR_SUCCESS;
done:
    if (sub) RegCloseKey(sub);
    if (key) RegCloseKey(key);
    return err;
#undef REG
}
static IWICImagingFactory *new_factory(void) {
    IWICImagingFactory *factory = NULL;
    HR_OK(CoCreateInstance(&CLSID_WICImagingFactory, NULL, CLSCTX_INPROC_SERVER, &IID_IWICImagingFactory, (void **)&factory));
    return factory;
}
static UINT enumerate_ours(IWICImagingFactory *factory) {
    IEnumUnknown *items = NULL; IUnknown *item = NULL; ULONG got; UINT count = 0;
    HR_OK(IWICImagingFactory_CreateComponentEnumerator(factory, WICDecoder, WICComponentEnumerateRefresh, &items));
    if (!items) return 999;
    while (IEnumUnknown_Next(items, 1, &item, &got) == S_OK) {
        IWICComponentInfo *info = NULL; CLSID clsid;
        if (SUCCEEDED(IUnknown_QueryInterface(item, &IID_IWICComponentInfo, (void **)&info))) {
            if (SUCCEEDED(IWICComponentInfo_GetCLSID(info, &clsid)) && IsEqualGUID(&clsid, &CLSID_DllmgrAvifDecoder)) ++count;
        }
        REL(info, IWICComponentInfo); REL(item, IUnknown);
    }
    REL(items, IEnumUnknown); return count;
}
static HRESULT open_stream(const WCHAR *file, IStream **stream) {
    return SHCreateStreamOnFileEx(file, STGM_READ | STGM_SHARE_DENY_WRITE, FILE_ATTRIBUTE_NORMAL, FALSE, NULL, stream);
}
static void path_join(WCHAR *out, const WCHAR *dir, const WCHAR *name) {
    if (swprintf(out, 2048, L"%ls\\%ls", dir, name) < 0) { fputs("Path too long\n", stderr); ExitProcess(2); }
}
static void expected_bgra(UINT x, UINT y, BYTE *p) {
    p[0] = (BYTE)((x + y) * 19); p[1] = (BYTE)(y * 47); p[2] = (BYTE)(x * 31);
    p[3] = (BYTE)(x % 3 == 0 ? 0 : x % 3 == 1 ? 128 : 255);
}
static void test_pixels(IWICImagingFactory *factory, IWICBitmapFrameDecode *frame) {
    UINT w = 0, h = 0, x, y, n = 0; WICPixelFormatGUID fmt; BYTE buffer[6 * 40], expected[4];
    WICRect rect = {2, 1, 3, 2}, bad = {-1, 0, 1, 1};
    IWICFormatConverter *converter = NULL; IWICColorContext *color = NULL;
    IWICBitmapSource *source = NULL; UINT exif = 0; BOOL can = FALSE;
    HR_OK(IWICBitmapFrameDecode_GetSize(frame, &w, &h)); CHECK(w == 8 && h == 6);
    HR_OK(IWICBitmapFrameDecode_GetPixelFormat(frame, &fmt)); CHECK(IsEqualGUID(&fmt, &GUID_WICPixelFormat32bppBGRA));
    HR_OK(IWICBitmapFrameDecode_QueryInterface(frame, &IID_IWICBitmapSource, (void **)&source)); REL(source, IWICBitmapSource);
    memset(buffer, 0xcd, sizeof(buffer));
    HR_OK(IWICBitmapFrameDecode_CopyPixels(frame, NULL, 40, sizeof(buffer), buffer));
    for (y = 0; y < 6; ++y) {
        for (x = 0; x < 8; ++x) { expected_bgra(x, y, expected); CHECK(!memcmp(buffer + y * 40 + x * 4, expected, 4)); }
        for (x = 32; x < 40; ++x) CHECK(buffer[y * 40 + x] == 0xcd);
    }
    CHECK(IWICBitmapFrameDecode_CopyPixels(frame, NULL, 31, sizeof(buffer), buffer) == E_INVALIDARG);
    CHECK(IWICBitmapFrameDecode_CopyPixels(frame, NULL, 40, 231, buffer) == WINCODEC_ERR_INSUFFICIENTBUFFER);
    HR_OK(IWICBitmapFrameDecode_CopyPixels(frame, NULL, 40, 232, buffer));
    CHECK(IWICBitmapFrameDecode_CopyPixels(frame, &bad, 40, sizeof(buffer), buffer) == E_INVALIDARG);
    bad.X = 7; bad.Width = 2;
    CHECK(IWICBitmapFrameDecode_CopyPixels(frame, &bad, 40, sizeof(buffer), buffer) == E_INVALIDARG);
    bad.X = 0; bad.Width = 0;
    CHECK(IWICBitmapFrameDecode_CopyPixels(frame, &bad, 40, sizeof(buffer), buffer) == E_INVALIDARG);
    CHECK(IWICBitmapFrameDecode_CopyPixels(frame, NULL, 0xffffffff, sizeof(buffer), buffer) == WINCODEC_ERR_INSUFFICIENTBUFFER);
    HR_OK(IWICBitmapFrameDecode_CopyPixels(frame, &rect, 16, 28, buffer));
    for (y = 0; y < 2; ++y) for (x = 0; x < 3; ++x) { expected_bgra(x + 2, y + 1, expected); CHECK(!memcmp(buffer + y * 16 + x * 4, expected, 4)); }
    HR_OK(IWICBitmapFrameDecode_GetColorContexts(frame, 0, NULL, &n)); CHECK(n == 1);
    HR_OK(IWICImagingFactory_CreateColorContext(factory, &color));
    if (color) {
        HR_OK(IWICBitmapFrameDecode_GetColorContexts(frame, 1, &color, &n));
        HR_OK(IWICColorContext_GetExifColorSpace(color, &exif)); CHECK(exif == 1);
    }
    REL(color, IWICColorContext);
    HR_OK(IWICImagingFactory_CreateFormatConverter(factory, &converter));
    if (converter) {
        HR_OK(IWICFormatConverter_CanConvert(converter, &fmt, &GUID_WICPixelFormat32bppPBGRA, &can)); CHECK(can);
        HR_OK(IWICFormatConverter_Initialize(converter, (IWICBitmapSource *)frame, &GUID_WICPixelFormat32bppPBGRA, WICBitmapDitherTypeNone, NULL, 0, WICBitmapPaletteTypeCustom));
        HR_OK(IWICFormatConverter_CopyPixels(converter, NULL, 32, 192, buffer));
        for (y = 0; y < 6; ++y) for (x = 0; x < 8; ++x) {
            BYTE *p = buffer + (y * 8 + x) * 4; unsigned c;
            expected_bgra(x, y, expected); CHECK(p[3] == expected[3]);
            for (c = 0; c < 3; ++c) CHECK(abs((int)p[c] - ((int)expected[c] * expected[3] + 127) / 255) <= 1);
        }
    }
    REL(converter, IWICFormatConverter);
}
static void direct_tests(IClassFactory *class_factory, IWICImagingFactory *factory, const WCHAR *dir) {
    WCHAR path[2048]; IStream *stream = NULL; IWICBitmapDecoder *decoder = NULL;
    IWICBitmapFrameDecode *frame = NULL; LARGE_INTEGER offset; ULARGE_INTEGER current; DWORD capabilities = 0; UINT count;
    const WCHAR *bad_files[] = {L"truncated.avif", L"other-brand.avif", L"rotated.avif", L"icc.avif"};
    unsigned i;
    path_join(path, dir, L"rgba.avif"); HR_OK(open_stream(path, &stream));
    HR_OK(IClassFactory_CreateInstance(class_factory, NULL, &IID_IWICBitmapDecoder, (void **)&decoder));
    if (!stream || !decoder) goto done;
    CHECK(IWICBitmapDecoder_GetFrameCount(decoder, &count) == WINCODEC_ERR_NOTINITIALIZED);
    offset.QuadPart = 12; HR_OK(IStream_Seek(stream, offset, STREAM_SEEK_SET, NULL));
    HR_OK(IWICBitmapDecoder_QueryCapability(decoder, stream, &capabilities)); CHECK(capabilities & WICBitmapDecoderCapabilityCanDecodeSomeImages);
    offset.QuadPart = 0; HR_OK(IStream_Seek(stream, offset, STREAM_SEEK_CUR, &current)); CHECK(current.QuadPart == 12);
    HR_OK(IWICBitmapDecoder_Initialize(decoder, stream, WICDecodeMetadataCacheOnLoad));
    CHECK(IWICBitmapDecoder_Initialize(decoder, stream, WICDecodeMetadataCacheOnLoad) == WINCODEC_ERR_WRONGSTATE);
    HR_OK(IWICBitmapDecoder_GetFrameCount(decoder, &count)); CHECK(count == 1);
    CHECK(IWICBitmapDecoder_GetFrame(decoder, 1, &frame) == WINCODEC_ERR_FRAMEMISSING);
    HR_OK(IWICBitmapDecoder_GetFrame(decoder, 0, &frame));
    REL(decoder, IWICBitmapDecoder); // Frame must survive the decoder.
    if (frame) test_pixels(factory, frame);
done:
    REL(frame, IWICBitmapFrameDecode); REL(decoder, IWICBitmapDecoder); REL(stream, IStream);
    for (i = 0; i < sizeof(bad_files) / sizeof(bad_files[0]); ++i) {
        HRESULT hr;
        path_join(path, dir, bad_files[i]); HR_OK(open_stream(path, &stream));
        HR_OK(IClassFactory_CreateInstance(class_factory, NULL, &IID_IWICBitmapDecoder, (void **)&decoder));
        if (stream && decoder) {
            hr = IWICBitmapDecoder_Initialize(decoder, stream, WICDecodeMetadataCacheOnLoad);
            CHECK(FAILED(hr));
            if (i == 1) CHECK(hr == WINCODEC_ERR_UNKNOWNIMAGEFORMAT);
            if (i >= 2) CHECK(hr == WINCODEC_ERR_UNSUPPORTEDOPERATION);
            wprintf(L"Rejected %ls: %08lx\n", bad_files[i], (unsigned long)hr);
        }
        REL(decoder, IWICBitmapDecoder); REL(stream, IStream);
    }
    // Structurally invalid ftyp with the registered brand must fail safely too.
    {
        BYTE garbage[32] = {0,0,0,32,'f','t','y','p','a','v','i','f'};
        stream = SHCreateMemStream(garbage, sizeof(garbage)); CHECK(stream != NULL);
        HR_OK(IClassFactory_CreateInstance(class_factory, NULL, &IID_IWICBitmapDecoder, (void **)&decoder));
        if (stream && decoder) CHECK(FAILED(IWICBitmapDecoder_Initialize(decoder, stream, WICDecodeMetadataCacheOnLoad)));
        REL(decoder, IWICBitmapDecoder); REL(stream, IStream);
    }
}
static HRESULT generic_file(IWICImagingFactory *factory, const WCHAR *path, BOOL self_test) {
    IWICBitmapDecoder *decoder = NULL; IWICBitmapFrameDecode *frame = NULL; IWICBitmapDecoderInfo *info = NULL;
    UINT width = 0, height = 0; CLSID clsid; BYTE *pixels = NULL; HRESULT hr;
    hr = IWICImagingFactory_CreateDecoderFromFilename(factory, path, NULL, GENERIC_READ, WICDecodeMetadataCacheOnLoad, &decoder);
    wprintf(L"Generic WIC decode %ls: %08lx\n", path, (unsigned long)hr);
    if (FAILED(hr)) return hr;
    hr = IWICBitmapDecoder_GetDecoderInfo(decoder, &info);
    if (SUCCEEDED(hr)) hr = IWICBitmapDecoderInfo_GetCLSID(info, &clsid);
    if (SUCCEEDED(hr)) {
        WCHAR text[40]; StringFromGUID2(&clsid, text, 40); wprintf(L"Decoder CLSID: %ls\n", text);
        if (self_test) CHECK(IsEqualGUID(&clsid, &CLSID_DllmgrAvifDecoder));
    }
    if (SUCCEEDED(hr)) hr = IWICBitmapDecoder_GetFrame(decoder, 0, &frame);
    if (SUCCEEDED(hr)) hr = IWICBitmapFrameDecode_GetSize(frame, &width, &height);
    if (SUCCEEDED(hr)) {
        printf("Frame: %ux%u\n", width, height);
        if (!width || !height || (uint64_t)width * height > 64 * 1024 * 1024) hr = WINCODEC_ERR_IMAGESIZEOUTOFRANGE;
        else {
            UINT size = width * height * 4;
            pixels = (BYTE *)HeapAlloc(GetProcessHeap(), 0, size);
            if (!pixels) hr = E_OUTOFMEMORY;
            else hr = IWICBitmapFrameDecode_CopyPixels(frame, NULL, width * 4, size, pixels);
            if (SUCCEEDED(hr)) {
                uint64_t hash = UINT64_C(14695981039346656037); UINT i;
                for (i = 0; i < size; ++i) { hash ^= pixels[i]; hash *= UINT64_C(1099511628211); }
                printf("BGRA FNV-1a: %016llx\n", (unsigned long long)hash);
            }
        }
    }
    if (self_test && SUCCEEDED(hr)) test_pixels(factory, frame);
    if (pixels) HeapFree(GetProcessHeap(), 0, pixels);
    REL(info, IWICBitmapDecoderInfo); REL(frame, IWICBitmapFrameDecode); REL(decoder, IWICBitmapDecoder);
    return hr;
}
int wmain(int argc, WCHAR **argv) {
    HRESULT hr; IWICImagingFactory *factory = NULL; IClassFactory *class_factory = NULL; HMODULE module = NULL;
    HRESULT (WINAPI *get_class)(REFCLSID, REFIID, void **);
    HRESULT (WINAPI *can_unload)(void);
    WCHAR dll[2048], file[2048]; LONG reg_error;
    if (argc == 2 && !wcscmp(argv[1], L"--help")) {
        puts("avif-codec --file IMAGE (read-only installed WIC probe)\navif-codec --self-test DLL FIXTURES (temporary test-owned HKLM registration)"); return 0;
    }
    if (!((argc == 3 && !wcscmp(argv[1], L"--file")) || (argc == 4 && !wcscmp(argv[1], L"--self-test")))) return 2;
    hr = CoInitializeEx(NULL, COINIT_MULTITHREADED); if (FAILED(hr)) return 1;
    factory = new_factory(); if (!factory) goto done;
    if (argc == 3) { HR_OK(generic_file(factory, argv[2], FALSE)); goto done; }
    if (!GetFullPathNameW(argv[2], 2048, dll, NULL)) { ++failures; goto done; }
    if (!absent(decoder_key) || !absent(instance_key)) { fputs("Refusing existing decoder registration\n", stderr); ++failures; goto done; }
    CHECK(enumerate_ours(factory) == 0);
    module = LoadLibraryW(dll); CHECK(module != NULL); if (!module) goto done;
    get_class = (void *)GetProcAddress(module, "DllGetClassObject"); can_unload = (void *)GetProcAddress(module, "DllCanUnloadNow");
    CHECK(get_class && can_unload); if (!get_class || !can_unload) goto done;
    CHECK(can_unload() == S_OK);
    HR_OK(get_class(&CLSID_DllmgrAvifDecoder, &IID_IClassFactory, (void **)&class_factory));
    if (!class_factory) goto done;
    CHECK(can_unload() == S_FALSE);
    direct_tests(class_factory, factory, argv[3]);
    REL(class_factory, IClassFactory); CHECK(can_unload() == S_OK);
    reg_error = register_test(dll); CHECK(reg_error == ERROR_SUCCESS); if (reg_error) goto done;
    /* A real client starts after installation. Do not reuse a factory which
     * enumerated the registry before this new component existed. */
    REL(factory, IWICImagingFactory); factory = new_factory(); if (!factory) goto done;
    CHECK(enumerate_ours(factory) == 1);
    {
        IWICBitmapDecoder *registered = NULL;
        IWICComponentInfo *component = NULL;
        hr = CoCreateInstance(&CLSID_DllmgrAvifDecoder, NULL, CLSCTX_INPROC_SERVER,
                              &IID_IWICBitmapDecoder, (void **)&registered);
        printf("Registered COM activation: %08lx\n", (unsigned long)hr); HR_OK(hr);
        REL(registered, IWICBitmapDecoder);
        hr = IWICImagingFactory_CreateComponentInfo(factory, &CLSID_DllmgrAvifDecoder, &component);
        printf("Registered WIC component info: %08lx\n", (unsigned long)hr); HR_OK(hr);
        REL(component, IWICComponentInfo);
    }
    path_join(file, argv[3], L"rgba.avif"); HR_OK(generic_file(factory, file, TRUE));
    unregister_test(); CHECK(absent(decoder_key)); CHECK(absent(instance_key));
    CHECK(enumerate_ours(factory) == 0);
    // Discovery after undo must not return this decoder (a system decoder may exist).
    {
        IWICBitmapDecoder *after = NULL;
        hr = IWICImagingFactory_CreateDecoderFromFilename(factory, file, NULL, GENERIC_READ, WICDecodeMetadataCacheOnLoad, &after);
        if (SUCCEEDED(hr)) {
            IWICBitmapDecoderInfo *info = NULL; CLSID id;
            HR_OK(IWICBitmapDecoder_GetDecoderInfo(after, &info));
            if (info) { HR_OK(IWICBitmapDecoderInfo_GetCLSID(info, &id)); CHECK(!IsEqualGUID(&id, &CLSID_DllmgrAvifDecoder)); }
            REL(info, IWICBitmapDecoderInfo);
        }
        REL(after, IWICBitmapDecoder);
    }
done:
    unregister_test(); REL(class_factory, IClassFactory); REL(factory, IWICImagingFactory);
    CoUninitialize(); if (module) FreeLibrary(module);
    printf("Failures: %d\n", failures); return failures ? 1 : 0;
}
