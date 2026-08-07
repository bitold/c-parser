#include "math_utils.h"

int add(int a, int b) {
    return a + b;
}

int distance_sq(Point a, Point b) {
    int dx = a.x - b.x;
    int dy = a.y - b.y;
    return SQUARE(dx) + SQUARE(dy);
}
