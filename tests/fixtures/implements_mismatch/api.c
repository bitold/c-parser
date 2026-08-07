#include "api.h"

// Same name, incompatible signature — must not IMPLEMENTS the header decl
int foo(char *s) {
    return s ? 1 : 0;
}
