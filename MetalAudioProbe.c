/* Original project smoke test: 32-bit Metal and optional x87/audio activation. */
#define INITGUID
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <mmdeviceapi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    int audio = argc == 2 && !strcmp(argv[1], "--audio-enabled");
    IMMDeviceEnumerator *enumerator = NULL;
    IMMDeviceCollection *devices = NULL;
    UINT count = 99;
    HRESULT hr = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    if (FAILED(hr)) return 1;
    hr = CoCreateInstance(&CLSID_MMDeviceEnumerator, NULL, CLSCTX_ALL,
                          &IID_IMMDeviceEnumerator, (void **)&enumerator);
    if (FAILED(hr)) return 2;
    hr = IMMDeviceEnumerator_EnumAudioEndpoints(enumerator, eRender, DEVICE_STATE_ACTIVE, &devices);
    if (FAILED(hr)) return 3;
    hr = IMMDeviceCollection_GetCount(devices, &count);
    IMMDeviceCollection_Release(devices);
    IMMDeviceEnumerator_Release(enumerator);
    CoUninitialize();
    printf("active_render_endpoints=%u\n", count);
    if (FAILED(hr) || (audio ? count == 0 : count != 0)) return 4;
    if (audio) {
        double angle = 0.5, sine = 0;
        __asm__ volatile("fldl %1; fsin; fstpl %0" : "=m"(sine) : "m"(angle) : "st");
        if (!(sine > 0.47942553860419 && sine < 0.47942553860422)) return 10;
        printf("x87_sine=%.17g\n", sine);
    }
    IDirect3D9 *d3d = Direct3DCreate9(D3D_SDK_VERSION);
    if (!d3d) return 5;
    D3DADAPTER_IDENTIFIER9 adapter;
    hr = IDirect3D9_GetAdapterIdentifier(d3d, D3DADAPTER_DEFAULT, 0, &adapter);
    if (FAILED(hr) || !strstr(adapter.Driver, "mtld3d")) return 6;
    printf("driver=%s adapter=%s\n", adapter.Driver, adapter.Description);
    HWND window = CreateWindowA("STATIC", "Metal runtime check", WS_OVERLAPPEDWINDOW,
                               0, 0, 320, 240, NULL, NULL, GetModuleHandle(NULL), NULL);
    if (!window) return 7;
    D3DPRESENT_PARAMETERS pp = {0};
    pp.Windowed = TRUE; pp.SwapEffect = D3DSWAPEFFECT_DISCARD;
    pp.hDeviceWindow = window; pp.BackBufferWidth = 320; pp.BackBufferHeight = 240;
    IDirect3DDevice9 *device = NULL;
    hr = IDirect3D9_CreateDevice(d3d, 0, D3DDEVTYPE_HAL, window,
                                D3DCREATE_SOFTWARE_VERTEXPROCESSING, &pp, &device);
    if (FAILED(hr)) { printf("create_device=0x%08lx\n", (unsigned long)hr); return 8; }
    hr = IDirect3DDevice9_Clear(device, 0, NULL, D3DCLEAR_TARGET, 0xff204060, 1.0f, 0);
    if (SUCCEEDED(hr)) hr = IDirect3DDevice9_Present(device, NULL, NULL, NULL, NULL);
    IDirect3DDevice9_Release(device); IDirect3D9_Release(d3d); DestroyWindow(window);
    if (FAILED(hr)) return 9;
    puts(audio ? "X87_AUDIO_OK" : "METAL_AUDIO_OK");
    return 0;
}
