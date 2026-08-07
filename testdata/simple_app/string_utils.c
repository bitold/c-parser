#include "string_utils.h"

static int add_one(int n) {
    return n + 1;
}

int str_len(const char *s) {
    int n = 0;
    while (s[n] != '\0') {
        n = add_one(n);
    }
    return n;
}

void str_copy(char *dst, const char *src) {
    int i = 0;
    int len = str_len(src);
    while (i < len) {
        dst[i] = src[i];
        i = add_one(i);
    }
    dst[len] = '\0';
}
