int add(int a, int b) {
    return a + b;
}

struct Point {
    int x;
    int y;
};

int foo(int a) {
    return bar(a) + baz();
}

int bar(int a) {
    return a;
}

int baz(void) {
    return 1;
}

typedef unsigned long size_t_alias;

#define MAX_ITEMS 100
