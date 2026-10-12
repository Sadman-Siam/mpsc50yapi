from app.models import Alumna


def counts_as_referral(referred_alumna: Alumna) -> bool:
    """Whether a referred account qualifies; default is confirmed status.

    Alternative policy: require a completed payment instead of confirmation.
    """
    return referred_alumna.status == "confirmed"
