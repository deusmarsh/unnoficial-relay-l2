/* Frame or minimize only the original launcher's WPF top-level window. */
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>
#include <stdio.h>
static int action = 0, matches = 0;
static HICON large_icon, small_icon;
static int configure_background_apps(void) {
    const wchar_t *names[] = {L"Inn.games.exe", L"Launcher.exe", L"explorer.exe", L"CefSharp.BrowserSubprocess.exe", L"NativeLauncherWindow.exe"};
    for (unsigned i = 0; i < sizeof(names)/sizeof(names[0]); i++) {
        wchar_t key[256]; HKEY handle;
        swprintf(key,256,L"Software\\Wine\\AppDefaults\\%ls\\Mac Driver",names[i]);
        if (RegCreateKeyExW(HKEY_CURRENT_USER,key,0,NULL,0,KEY_SET_VALUE,NULL,&handle,NULL)) return 1;
        LONG result=RegSetValueExW(handle,L"LineageBackgroundApp",0,REG_SZ,(const BYTE *)L"Y",2*sizeof(wchar_t));
        RegCloseKey(handle);
        if (result) return 1;
    }
    return 0;
}
static BOOL CALLBACK visit(HWND hwnd, LPARAM unused) {
    DWORD pid = 0, count = 32768;
    wchar_t path[32768], cls[256];
    if (GetWindow(hwnd, GW_OWNER)) return TRUE;
    GetClassNameW(hwnd, cls, 256);
    if (wcsncmp(cls, L"HwndWrapper[", 12)) return TRUE;
    GetWindowThreadProcessId(hwnd, &pid);
    HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!process) return TRUE;
    BOOL ok = QueryFullProcessImageNameW(process, 0, path, &count);
    CloseHandle(process);
    if (!ok) return TRUE;
    const wchar_t *name = wcsrchr(path, L'\\'); name = name ? name+1 : path;
    if (_wcsicmp(name, L"Launcher.exe")) return TRUE;
    if (large_icon && (action == 1 || action == 3 || action == 4)) {
        SendMessageTimeoutW(hwnd, WM_SETICON, ICON_BIG, (LPARAM)large_icon, SMTO_ABORTIFHUNG, 500, NULL);
        SendMessageTimeoutW(hwnd, WM_SETICON, ICON_SMALL, (LPARAM)small_icon, SMTO_ABORTIFHUNG, 500, NULL);
    }
    if (action == 2) {
        if (GetPropW(hwnd,L"LineageRelayMinimized") || GetPropW(hwnd,L"LineageRelayHidden")) {
            ShowWindowAsync(hwnd, SW_RESTORE); RemovePropW(hwnd,L"LineageRelayMinimized"); RemovePropW(hwnd,L"LineageRelayHidden"); matches++;
        }
        return TRUE;
    }
    if (action == 3 || action == 1 || action == 4) {
        RECT size;
        if (!GetWindowRect(hwnd, &size) || size.right-size.left < 600 || size.bottom-size.top < 400) return TRUE;
        LONG_PTR style = GetWindowLongPtrW(hwnd, GWL_STYLE);
        LONG_PTR framed = (style & ~WS_POPUP) | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_THICKFRAME;
        if (style != framed) {
            SetWindowLongPtrW(hwnd, GWL_STYLE, framed);
            SetWindowPos(hwnd, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
        }
        SetWindowTextW(hwnd, L"Lineage II Runtime - keep open; closing may stop the game");
        if (action == 3) { matches++; return TRUE; }
        if (action == 4) {
            SetPropW(hwnd,L"LineageRelayHidden",(HANDLE)1);
            ShowWindowAsync(hwnd, SW_HIDE);
            matches++; return TRUE;
        }
    }
    RECT rect;
    if (action == 0 && GetWindowRect(hwnd,&rect) && rect.right-rect.left >= 600 && rect.bottom-rect.top >= 400) {
        LONG_PTR style = GetWindowLongPtrW(hwnd, GWL_STYLE);
        printf("Runtime window: caption=%d close_menu=%d minimize=%d maximize=%d resizable=%d minimized=%d\n",
               (style & WS_CAPTION)==WS_CAPTION, !!(style & WS_SYSMENU), !!(style & WS_MINIMIZEBOX),
               !!(style & WS_MAXIMIZEBOX), !!(style & WS_THICKFRAME), !!IsIconic(hwnd));
        matches++; return TRUE;
    }
    if (!IsWindowVisible(hwnd) || IsIconic(hwnd) || !GetWindowRect(hwnd,&rect) ||
        rect.right-rect.left < 600 || rect.bottom-rect.top < 400) return TRUE;
    matches++;
    if (action == 1) {
        SetPropW(hwnd,L"LineageRelayMinimized",(HANDLE)1);
        ShowWindowAsync(hwnd, SW_MINIMIZE);
    }
    return TRUE;
}
static int run(int argc, wchar_t **argv) {
    if (argc > 1 && !wcscmp(argv[1], L"--background-setup")) return configure_background_apps();
    if (argc > 1 && !wcscmp(argv[1], L"--minimize")) action = 1;
    if (argc > 1 && !wcscmp(argv[1], L"--restore")) action = 2;
    if (argc > 1 && !wcscmp(argv[1], L"--frame")) action = 3;
    if (argc > 1 && !wcscmp(argv[1], L"--hide")) action = 4;
    if (argc > 2) {
        large_icon = LoadImageW(NULL, argv[2], IMAGE_ICON, 256, 256, LR_LOADFROMFILE);
        small_icon = LoadImageW(NULL, argv[2], IMAGE_ICON, 32, 32, LR_LOADFROMFILE);
    }
    EnumWindows(visit, 0);
    printf("Launcher WPF windows: %d; action: %d\n", matches, action);
    return 0;
}
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command, int show) {
    int argc = 0;
    LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) return 1;
    int result = run(argc, argv);
    LocalFree(argv);
    return result;
}
