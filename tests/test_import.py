def test_import() -> None:
    """Smoke test that the package is importable."""
    import pydantic_plus_plus

    assert pydantic_plus_plus.__doc__ is not None


def test_partial_is_reexported() -> None:
    """Test that the partial function is reexported."""
    from pydantic_plus_plus import partial, PartialBaseModel

    assert partial is not None
    assert PartialBaseModel is not None
