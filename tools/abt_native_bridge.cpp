#include <jni.h>
#include <link.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>

#if defined(__aarch64__)
namespace {
static uintptr_t g_lib_base = 0;
static int find_abbs(struct dl_phdr_info *info, size_t, void *) {
    if (info->dlpi_name && strstr(info->dlpi_name, "libABBS.so")) {
        g_lib_base = static_cast<uintptr_t>(info->dlpi_addr);
        return 1;
    }
    return 0;
}
static uintptr_t abbs_base() {
    g_lib_base = 0;
    dl_iterate_phdr(find_abbs, nullptr);
    return g_lib_base;
}
static bool write_code_word(uintptr_t address, uint32_t value) {
    const long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) return false;
    const uintptr_t page = address & ~static_cast<uintptr_t>(page_size - 1);
    if (mprotect(reinterpret_cast<void *>(page), static_cast<size_t>(page_size),
                 PROT_READ | PROT_WRITE | PROT_EXEC) != 0) return false;
    *reinterpret_cast<volatile uint32_t *>(address) = value;
    __builtin___clear_cache(reinterpret_cast<char *>(address), reinterpret_cast<char *>(address + 4));
    const bool restored = mprotect(reinterpret_cast<void *>(page), static_cast<size_t>(page_size),
                                    PROT_READ | PROT_EXEC) == 0;
    return restored;
}
}

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_setFps(JNIEnv *, jclass, jint fps) {
    if (!(fps == 0 || fps == 30 || fps == 60 || fps == 90 || fps == 120 || fps == 140 || fps == 144)) return -1;
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    const uintptr_t app_fps = base + 0x6e6644;
    const uintptr_t device_fps_fallback = base + 0x6ed40c;
    const uint32_t current_app = *reinterpret_cast<volatile uint32_t *>(app_fps);
    const uint32_t current_fallback = *reinterpret_cast<volatile uint32_t *>(device_fps_fallback);
    if ((current_app & 0x7f80001fU) != 0x52800000U) return -3;
    const uint32_t csel_fallback = 0x1a800100U; // csel w0, w8, w0, eq
    const uint32_t unlimited_fallback = 0x2a1f03e0U; // mov w0, wzr
    if (current_fallback != csel_fallback && current_fallback != unlimited_fallback) return -4;
    const uint32_t new_app = 0x52800000U | (static_cast<uint32_t>(fps) << 5); // mov w0, #fps
    if (!write_code_word(app_fps, new_app)) return -5;
    const uint32_t new_fallback = fps == 0 ? unlimited_fallback : csel_fallback;
    if (!write_code_word(device_fps_fallback, new_fallback)) return -6;
    return 1;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_changeGraphics(JNIEnv *, jclass, jint direction) {
    if (direction != -1 && direction != 1) return -1;
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    using ChangePerformance = int (*)(int);
    auto change = reinterpret_cast<ChangePerformance>(base + 0x6ed4b8);
    return change(direction) ? 1 : 0;
}

#else
extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_setFps(JNIEnv *, jclass, jint) { return -9; }
extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_changeGraphics(JNIEnv *, jclass, jint) { return -9; }
#endif