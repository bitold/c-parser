#ifndef MATH_UTILS_H
#define MATH_UTILS_H

#define SQUARE(x) ((x) * (x))

typedef struct Point {
    int x;
    int y;
} Point;

int add(int a, int b);
int distance_sq(Point a, Point b);

#endif
