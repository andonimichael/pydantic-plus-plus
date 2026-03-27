def test_import() -> None:
    """Smoke test that the package is importable."""
    import pydantic_plus_plus

    assert pydantic_plus_plus.__doc__ is not None
