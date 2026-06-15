from dataclasses import dataclass


@dataclass(frozen=True)
class EffectiveQuality:
    requested_qp: int
    quality_param_kind: str
    effective_value: int
    mapping_rule: str


def map_linear(value: int, src_min: int, src_max: int, dst_min: int, dst_max: int) -> int:
    ratio = (value - src_min) / (src_max - src_min)
    mapped = dst_min + ratio * (dst_max - dst_min)
    return int(round(mapped))


def resolve_quality(requested_qp: int, mapping_rule: str) -> EffectiveQuality:
    if mapping_rule == "identity":
        return EffectiveQuality(requested_qp, "qp", requested_qp, mapping_rule)

    if mapping_rule == "linear_h26x_qp_to_av1_q":
        value = map_linear(requested_qp, 20, 51, 15, 55)
        value = max(15, min(55, value))
        return EffectiveQuality(requested_qp, "q", value, mapping_rule)

    if mapping_rule == "linear_h26x_qp_to_vp9_crf":
        value = map_linear(requested_qp, 20, 51, 15, 55)
        value = max(15, min(55, value))
        return EffectiveQuality(requested_qp, "crf", value, mapping_rule)

    raise ValueError(f"Unknown QP mapping rule: {mapping_rule}")

