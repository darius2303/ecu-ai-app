import json

from app.services.map_definitions import parse_map_definitions


def test_parses_csv_map_definition_with_scaling_and_category():
    csv_content = (
        "name,address,rows,columns,data_type,byte_order,factor,offset,unit\n"
        "Torque request,0x10,2,3,u16,little,0.5,1,Nm\n"
    ).encode()

    definitions, warnings = parse_map_definitions("maps.csv", csv_content)

    assert warnings == []
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.name == "Torque request"
    assert definition.address == 0x10
    assert definition.rows == 2
    assert definition.columns == 3
    assert definition.data_type == "u16"
    assert definition.byte_order == "little"
    assert definition.factor == 0.5
    assert definition.offset == 1
    assert definition.category == "torque"
    assert definition.value_unit == "Nm"


def test_parses_json_map_definitions_payload():
    payload = {
        "maps": [
            {
                "name": "RPM Limiter",
                "address": 4,
                "rows": 1,
                "columns": 2,
                "data_type": "u16",
                "factor": 1,
                "offset": 0,
            }
        ]
    }

    definitions, warnings = parse_map_definitions(
        "maps.json",
        json.dumps(payload).encode(),
    )

    assert warnings == []
    assert len(definitions) == 1
    assert definitions[0].category == "limiter"


def test_skips_invalid_csv_rows_and_reports_warning():
    csv_content = (
        "name,address,rows,columns\n"
        "Broken map,,2,2\n"
    ).encode()

    definitions, warnings = parse_map_definitions("maps.csv", csv_content)

    assert definitions == []
    assert any("Definition 1 was skipped" in warning for warning in warnings)
    assert "No usable map definitions were found." in warnings
