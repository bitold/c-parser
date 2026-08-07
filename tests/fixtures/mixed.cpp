/// Widget container.
class DocumentedWidget {
public:
    int value() const { return value_; }

private:
    int value_;
};

class UndocumentedGadget {
    int id;
};
