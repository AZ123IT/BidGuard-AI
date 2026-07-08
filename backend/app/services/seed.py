from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RiskRule
from app.services.risk_rules import BUILT_IN_RULES


def seed_risk_rules(session: Session) -> None:
    existing = set(session.scalars(select(RiskRule.name)).all())
    for rule in BUILT_IN_RULES:
        if rule["name"] not in existing:
            session.add(
                RiskRule(
                    name=rule["name"],
                    severity=rule["severity"],
                    description=rule["description"],
                    enabled=True,
                )
            )
    session.commit()
