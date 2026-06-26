from demo_service.hello import greet


def test_greet_default() -> None:
    assert greet() == "hello world"


def test_greet_name() -> None:
    assert greet("fixture") == "hello fixture"
