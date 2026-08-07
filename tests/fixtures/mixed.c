/// Adds two integers.
int documented_add(int a, int b) {
    return a + b;
}

/** Point in 2D space. */
struct DocumentedPoint {
    int x;
    int y;
};

/// Alias for size.
typedef unsigned long documented_size_t;

//! Maximum item count.
#define DOCUMENTED_MAX 100

int undocumented_sub(int a, int b) {
    return a - b;
}
