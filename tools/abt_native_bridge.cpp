#define _GNU_SOURCE
#include <jni.h>
#include <link.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>

#if defined(__aarch64__)
namespace {
static uintptr_t g_abbs_base = 0;
static int find_abbs(struct dl_phdr_info *info, size_t, void *) {
    if (info->dlpi_name && strstr(info->dlpi_name, "libABBS.so")) {
        g_abbs_base = static_cast<uintptr_t>(info->dlpi_addr);
        return 1;
    }
    return 0;
}
static uintptr_t abbs_base() {
    g_abbs_base = 0;
    dl_iterate_phdr(find_abbs, nullptr);
    return g_abbs_base;
}
static bool write_code_word(uintptr_t address, uint32_t value) {
    const long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) return false;
    const uintptr_t page = address & ~static_cast<uintptr_t>(page_size - 1);
    if (mprotect(reinterpret_cast<void *>(page), static_cast<size_t>(page_size), PROT_READ | PROT_WRITE | PROT_EXEC) != 0) return false;
    *reinterpret_cast<volatile uint32_t *>(address) = value;
    __builtin___clear_cache(reinterpret_cast<char *>(address), reinterpret_cast<char *>(address + 4));
    return mprotect(reinterpret_cast<void *>(page), static_cast<size_t>(page_size), PROT_READ | PROT_EXEC) == 0;
}
static int current_graphics(uintptr_t base) {
    using GetCurrent = int (*)();
    auto get = reinterpret_cast<GetCurrent>(base + 0x6ed610);
    return get();
}
static int set_graphics(uintptr_t base, int target) {
    if (target < 0 || target > 3) return -1;

    int current = current_graphics(base);
    if (current < 0 || current > 4) return -2;
    if (current == target) return target + 1;

    // Native ChangePerformance treats the special value 4 as an effective
    // starting profile 1, but keeps the global value at 4 until a transition
    // succeeds. Normalize it through the engine's own adjacent transitions:
    // 4 -> 0/2/3, and 4 -> 1 via 2 -> 1.
    using ChangePerformance = int (*)(int);
    auto change = reinterpret_cast<ChangePerformance>(base + 0x6ed4b8);
    if (current == 4) {
        current = 1; // exact normalization performed by ChangePerformance
        if (target == 1) {
            const int up = change(1);
            if (up != 1 || current_graphics(base) != 2) return -3;
            const int down = change(-1);
            if (down != 1 || current_graphics(base) != 1) return -4;
            return 2; // 1-based success code for manual Medium
        }
    }

    for (int step = 0; step < 3 && current != target; ++step) {
        const int direction = target > current ? 1 : -1;
        const int changed = change(direction);
        if (changed != 1) return -5;
        const int updated = current_graphics(base);
        if (updated != current + direction) return -6;
        current = updated;
    }

    return current == target ? target + 1 : -7;
}

} // namespace

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_setFps(JNIEnv *, jclass, jint fps) {
    if (!(fps == 0 || fps == 30 || fps == 60 || fps == 90 || fps == 120 || fps == 140 || fps == 144)) return -1;
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    // Verified MOVZ immediates in CApp::GetDesiredFramerate and CDeviceConfig::GetDesiredFramerate.
    const uintptr_t app_site = base + 0x6e6644;
    const uintptr_t fallback_site = base + 0x6ed3fc;
    const uint32_t old_app = *reinterpret_cast<volatile uint32_t *>(app_site);
    const uint32_t old_fallback = *reinterpret_cast<volatile uint32_t *>(fallback_site);
    if ((old_app & 0x7f80001fU) != 0x52800000U) return -3;
    if ((old_fallback & 0x7f80001fU) != 0x52800008U) return -4;
    const uint32_t new_app = 0x52800000U | (static_cast<uint32_t>(fps) << 5); // mov w0, #fps
    const uint32_t new_fallback = 0x52800008U | (static_cast<uint32_t>(fps) << 5); // mov w8, #fps
    if (!write_code_word(app_site, new_app)) return -5;
    if (!write_code_word(fallback_site, new_fallback)) { write_code_word(app_site, old_app); return -6; }
    return 1;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_getGraphicsLevel(JNIEnv *, jclass) {
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    return current_graphics(base);
}

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_changeGraphics(JNIEnv *, jclass, jint direction) {
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    if (direction != -1 && direction != 1) return -1;
    const int current = current_graphics(base);
    if (current < 0 || current > 4) return -3;
    const int effective = current == 4 ? 1 : current;
    return set_graphics(base, effective + direction);
}

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_setPendingGraphicsLevel(JNIEnv *, jclass, jint target) {
    if (target < 0 || target > 3) return -1;
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    // Override the startup profile getter in CApp::MainLoadingDeviceConfig.
    // The engine then performs its own LoadDeviceConfigByPerformance call.
    const uintptr_t site = base + 0x6e3ee8;
    const uint32_t current = *reinterpret_cast<volatile uint32_t *>(site);
    if ((current & 0xfc000000U) != 0x94000000U) {
        const uint32_t expected = 0x52800000U | (static_cast<uint32_t>(target) << 5);
        return current == expected ? 1 : -3;
    }
    const uint32_t replacement = 0x52800000U | (static_cast<uint32_t>(target) << 5);
    return write_code_word(site, replacement) ? 1 : -4;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_rovio_angrybirdstransformers_RevivalNative_setGraphicsLevel(JNIEnv *, jclass, jint target) {
    if (target < 0 || target > 3) return -1;
    const uintptr_t base = abbs_base();
    if (!base) return -2;
    return set_graphics(base, target); // 1..4 = successfully applied profile
}

#elif defined(__arm__)
namespace {
static uintptr_t g_abbs_base = 0;
static int find_abbs(struct dl_phdr_info *info, size_t, void *) {
    if (info->dlpi_name && strstr(info->dlpi_name, "libABBS.so")) {
        g_abbs_base = static_cast<uintptr_t>(info->dlpi_addr);
        return 1;
    }
    return 0;
}
static uintptr_t abbs_base() {
    g_abbs_base = 0;
    dl_iterate_phdr(find_abbs, nullptr);
    return g_abbs_base;
}
static bool write_code_word(uintptr_t address, uint32_t value) {
    const long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) return false;
    const uintptr_t page = address & ~static_cast<uintptr_t>(page_size - 1);
    if (mprotect(reinterpret_cast<void *>(page), static_cast<size_t>(page_size), PROT_READ | PROT_WRITE | PROT_EXEC) != 0) return false;
    *reinterpret_cast<volatile uint32_t *>(address) = value;
    __builtin___clear_cache(reinterpret_cast<char *>(address), reinterpret_cast<char *>(address + 4));
    return mprotect(reinterpret_cast<void *>(page), static_cast<size_t>(page_size), PROT_READ | PROT_EXEC) == 0;
}
static int current_graphics(uintptr_t base) {
    using GetCurrent = int (*)();
    auto get = reinterpret_cast<GetCurrent>(base + 0x5152e8);
    return get();
}
static int set_graphics(uintptr_t base, int target) {
    if (target < 0 || target > 3) return -1;
    int current = current_graphics(base);
    if (current < 0 || current > 4) return -2;
    if (current == target) return target + 1;
    using ChangePerformance = int (*)(int);
    auto change = reinterpret_cast<ChangePerformance>(base + 0x51518c);
    if (current == 4) {
        current = 1;
        if (target == 1) {
            const int up = change(1);
            if (up != 1 || current_graphics(base) != 2) return -3;
            const int down = change(-1);
            if (down != 1 || current_graphics(base) != 1) return -4;
            return 2;
        }
    }
    for (int step = 0; step < 3 && current != target; ++step) {
        const int direction = target > current ? 1 : -1;
        const int changed = change(direction);
        if (changed != 1) return -5;
        const int updated = current_graphics(base);
        if (updated != current + direction) return -6;
        current = updated;
    }
    return current == target ? target + 1 : -7;
}
}
extern "C" JNIEXPORT jint JNICALL Java_com_rovio_angrybirdstransformers_RevivalNative_setFps(JNIEnv *, jclass, jint) { return -9; }
extern "C" JNIEXPORT jint JNICALL Java_com_rovio_angrybirdstransformers_RevivalNative_getGraphicsLevel(JNIEnv *, jclass) {
    const uintptr_t base = abbs_base(); return base ? current_graphics(base) : -2;
}
extern "C" JNIEXPORT jint JNICALL Java_com_rovio_angrybirdstransformers_RevivalNative_changeGraphics(JNIEnv *, jclass, jint direction) {
    const uintptr_t base = abbs_base(); if (!base) return -2;
    if (direction != -1 && direction != 1) return -1;
    const int current = current_graphics(base); if (current < 0 || current > 4) return -3;
    const int effective = current == 4 ? 1 : current;
    return set_graphics(base, effective + direction);
}
extern "C" JNIEXPORT jint JNICALL Java_com_rovio_angrybirdstransformers_RevivalNative_setPendingGraphicsLevel(JNIEnv *, jclass, jint) { return -9; }
extern "C" JNIEXPORT jint JNICALL Java_com_rovio_angrybirdstransformers_RevivalNative_setGraphicsLevel(JNIEnv *, jclass, jint target) {
    const uintptr_t base = abbs_base(); if (!base) return -2;
    return set_graphics(base, target);
}
#endif