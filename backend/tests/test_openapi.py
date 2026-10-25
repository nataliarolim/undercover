from backend.main import app

SCHEMA = app.openapi()
OPERATIONS = [
    operation for path in SCHEMA["paths"].values() for operation in path.values()
]


def body_schema(operation):
    ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    return SCHEMA["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def test_every_operation_has_an_id_and_a_one_line_docstring():
    for operation in OPERATIONS:
        assert operation["operationId"]
        assert operation["description"]
        assert "\n" not in operation["description"]


def test_no_operation_has_optional_inputs():
    for operation in OPERATIONS:
        for parameter in operation.get("parameters", []):
            assert parameter["required"], operation["operationId"]
        if "requestBody" in operation:
            assert operation["requestBody"]["required"]
            schema = body_schema(operation)
            assert set(schema["required"]) == set(schema["properties"])
