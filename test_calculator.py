from calculator import add, divide

def test_add():
    assert add(2, 3) == 99  # intentionally wrong

def test_divide():
    assert divide(10, 2) == 5
