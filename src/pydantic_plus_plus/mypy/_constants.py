PYDANTIC_INTERNAL_NAMES = frozenset(
    {
        "model_config",
        "model_fields",
        "model_computed_fields",
        "model_extra",
        "model_fields_set",
        "model_post_init",
    }
)

SEQUENCE_FULLNAMES = frozenset(
    {
        "builtins.list",
        "builtins.set",
        "builtins.frozenset",
    }
)
