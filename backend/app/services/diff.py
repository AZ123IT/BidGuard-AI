from app.services.field_extractor import FIELD_NAMES


def compare_extracted_fields(left: dict[str, dict], right: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for field_name in FIELD_NAMES:
        left_field = left.get(field_name, {})
        right_field = right.get(field_name, {})
        left_value = left_field.get("value")
        right_value = right_field.get("value")
        if not left_value or not right_value:
            status = "uncertain"
        elif _normalise(left_value) == _normalise(right_value):
            status = "same"
        else:
            status = "changed"
        rows.append(
            {
                "field": field_name,
                "document_a_value": left_value,
                "document_b_value": right_value,
                "document_a_page": left_field.get("page_number"),
                "document_b_page": right_field.get("page_number"),
                "document_a_confidence": left_field.get("confidence", 0.0),
                "document_b_confidence": right_field.get("confidence", 0.0),
                "status": status,
            }
        )
    return rows


def _normalise(value: str) -> str:
    return " ".join(value.lower().split())
