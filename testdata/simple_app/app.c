#include <stdio.h>
#include "math_utils.h"
#include "string_utils.h"

static void print_point(Point p) {
    printf("(%d, %d)\n", p.x, p.y);
}

int main(void) {
    Point a = {0, 0};
    Point b = {3, 4};
    int d = distance_sq(a, b);
    char buf[32];

    print_point(a);
    print_point(b);
    str_copy(buf, "hello");
    printf("dist_sq=%d len=%d\n", d, str_len(buf));
    return add(d, 0);
}
