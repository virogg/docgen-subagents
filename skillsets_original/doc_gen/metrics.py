def calculate_composite_score(md_to_code, code_to_md, dus):
    """
    Calculate compositionm score of metrics.

    Args:
        md_to_code (float): precision, grounded truthness score.
        code_to_md (float): recall, document completeness score.
        dus (float): document usefulness score.

    Returns:
        float: result of formula.
    """
    return (5 / 3) * (md_to_code + code_to_md + dus)
