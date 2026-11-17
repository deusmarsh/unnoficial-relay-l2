#include <windows.h>
#include <stdio.h>

/* A credential-free user-mode test for the Wine kernel synchronization port.
 * Storage is deliberately oversized; the implementation owns its layout. */
typedef void (WINAPI *mutex_fn)(void *);
static DECLSPEC_ALIGN(16) unsigned char mutex_storage[512];
static mutex_fn acquire_mutex, release_mutex;
static volatile LONG inside, violations, counter;

static DWORD WINAPI worker(void *unused)
{
    unsigned int i;
    (void)unused;
    for (i = 0; i < 1000; ++i)
    {
        acquire_mutex(mutex_storage);
        if (InterlockedIncrement(&inside) != 1) InterlockedIncrement(&violations);
        SwitchToThread();
        ++counter;
        InterlockedDecrement(&inside);
        release_mutex(mutex_storage);
    }
    return 0;
}

int main(void)
{
    HMODULE module = LoadLibraryW(L"ntoskrnl.exe");
    mutex_fn init_mutex;
    HANDLE threads[4];
    unsigned int i;
    DWORD waited;
    if (!module) { printf("LOAD_FAILED %lu\n", GetLastError()); return 1; }
    init_mutex = (mutex_fn)GetProcAddress(module, "KeInitializeGuardedMutex");
    acquire_mutex = (mutex_fn)GetProcAddress(module, "KeAcquireGuardedMutex");
    release_mutex = (mutex_fn)GetProcAddress(module, "KeReleaseGuardedMutex");
    if (!init_mutex || !acquire_mutex || !release_mutex)
    {
        WCHAR filename[512];
        GetModuleFileNameW(module, filename, 512);
        printf("MISSING_EXPORT init=%p acquire=%p release=%p module=%ls\n",
               (void *)init_mutex, (void *)acquire_mutex, (void *)release_mutex, filename);
        return 2;
    }
    init_mutex(mutex_storage);
    acquire_mutex(mutex_storage);
    threads[0] = CreateThread(NULL, 0, worker, NULL, 0, NULL);
    if (!threads[0]) return 3;
    waited = WaitForSingleObject(threads[0], 100);
    if (waited != WAIT_TIMEOUT || counter != 0)
    { puts("HELD_MUTEX_DID_NOT_BLOCK"); return 4; }
    release_mutex(mutex_storage);
    for (i = 1; i < 4; ++i)
    {
        threads[i] = CreateThread(NULL, 0, worker, NULL, 0, NULL);
        if (!threads[i]) return 5;
    }
    waited = WaitForMultipleObjects(4, threads, TRUE, 15000);
    for (i = 0; i < 4; ++i) CloseHandle(threads[i]);
    if (waited != WAIT_OBJECT_0 || violations || counter != 4000)
    {
        printf("MUTEX_FAILED wait=%lu overlaps=%ld count=%ld\n", waited, violations, counter);
        return 6;
    }
    puts("GUARDED_MUTEX_OK blocked_waiter=1 threads=4 iterations=4000 overlaps=0");
    return 0;
}
