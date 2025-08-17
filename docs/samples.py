# Example functions and their corresponding unit tests

# 1. Simple math function
def multiply(a: int, b: int) -> int:
    return a * b


# Unit test for multiply
def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(-1, 5) == -5
    assert multiply(0, 99) == 0


# 2. String utility
def reverse_string(s: str) -> str:
    return s[::-1]


# Unit test for reverse_string
def test_reverse_string():
    assert reverse_string("hello") == "olleh"
    assert reverse_string("") == ""
    assert reverse_string("a") == "a"


# 3. List utility
def find_max(values: list[int]) -> int:
    if not values:
        raise ValueError("List is empty")
    return max(values)


# Unit test for find_max
def test_find_max():
    assert find_max([1, 2, 3, 4]) == 4
    assert find_max([-5, -2, -9]) == -2
    try:
        find_max([])
    except ValueError as e:
        assert str(e) == "List is empty"
