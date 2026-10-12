
def predict_struggle(features):
    """
    Experimental, rule-based programming struggle indicator.

    Uses observed coding behaviour, not an ML model.
    It is not a validated assessment of student struggle.
    """

    if not isinstance(features, dict):
        raise ValueError("features must be a dictionary")

    required = [
        "attempt_number",
        "error_count",
        "execution_count",
        "time_spent_seconds",
        "total_events",
        "execution_events",
        "error_events",
        "submission_events",
    ]

    missing = [key for key in required if key not in features]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    values = {}
    for key in required:
        try:
            values[key] = float(features[key])
        except (TypeError, ValueError):
            raise ValueError(f"Feature {key} must be numeric") from None

        if values[key] < 0:
            raise ValueError(f"Feature {key} cannot be negative")

    score = 0
    reasons = []

    errors = values["error_count"] + values["error_events"]
    executions = values["execution_count"] + values["execution_events"]

    if errors >= 5:
        score += 3
        reasons.append("Many recorded errors")
    elif errors >= 2:
        score += 2
        reasons.append("Repeated recorded errors")
    elif errors >= 1:
        score += 1
        reasons.append("At least one recorded error")

    if values["attempt_number"] >= 5:
        score += 2
        reasons.append("High attempt number")
    elif values["attempt_number"] >= 3:
        score += 1
        reasons.append("Multiple attempts")

    if executions >= 8:
        score += 2
        reasons.append("Many recorded executions")
    elif executions >= 4:
        score += 1
        reasons.append("Several recorded executions")

    if values["time_spent_seconds"] >= 1800:
        score += 1
        reasons.append("Long time recorded for this submission")


    # Convert the rule score into a no-struggle indicator.
    # Maximum possible rule score = 8.
    no_struggle_percentage = round((1 - score / 8) * 100)
    no_struggle_percentage = max(0, min(100, no_struggle_percentage))

    if no_struggle_percentage >= 75:
        level = "Low"
    elif no_struggle_percentage >= 46:
        level = "Moderate"
    else:
        level = "High"


    return {
        "struggle_level": level,
        "indicator_score": score,
        "no_struggle_percentage": no_struggle_percentage,
        "reasons": reasons or ["No struggle signals detected"],
        "model_type": "experimental_rule_based",
        "message": (
            "This is a behaviour-based indicator, not a validated "
            "measurement of student struggle."
        ),
    }
