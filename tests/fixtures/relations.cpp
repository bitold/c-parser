namespace util {
void log(int code) {}
class Base {};
}

class Base {};

class Child : public util::Base {};

namespace util {
void caller() {
    log(1);
}
}

struct Widget {
    void helper() {}
    void run() {
        this->helper();
        helper();
    }
};

void free_helper() {}

void use_widget(Widget* w) {
    w->run();
    util::log(2);
}
