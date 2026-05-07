PERIOD_LABELS = {
    "current_week": "현재 주",
    "last_week": "지난 주",
    "last_month": "지난달 전체",
    "two_months_ago": "2달 전 전체",
    "last_year": "지난 해 전체",
}

PERIOD_SQL = {
    "current_week": """
        date_trunc('week', current_date)::date AS start_date,
        (date_trunc('week', current_date) + interval '6 day')::date AS end_date
    """,
    "last_week": """
        (date_trunc('week', current_date) - interval '7 day')::date AS start_date,
        (date_trunc('week', current_date) - interval '1 day')::date AS end_date
    """,
    "last_month": """
        date_trunc('month', current_date - interval '1 month')::date AS start_date,
        (date_trunc('month', current_date) - interval '1 day')::date AS end_date
    """,
    "two_months_ago": """
        date_trunc('month', current_date - interval '2 month')::date AS start_date,
        (date_trunc('month', current_date - interval '1 month') - interval '1 day')::date AS end_date
    """,
    "last_year": """
        date_trunc('year', current_date - interval '1 year')::date AS start_date,
        (date_trunc('year', current_date) - interval '1 day')::date AS end_date
    """
}