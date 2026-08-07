class Base {
public:
    int id_;
};

class Widget : public Base {
public:
    int value() const { return value_; }
    void run() { helper(); }
    void helper() {}

private:
    int value_;
};

namespace app {
void run();
}

enum class Mode { On, Off };

typedef Widget* WidgetPtr;

#define WIDGET_VERSION 1
