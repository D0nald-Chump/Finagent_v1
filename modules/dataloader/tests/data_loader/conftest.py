import os
import pytest

SEC_UA = os.environ.get("SEC_UA")

@pytest.fixture(scope="session")
def sec_user_agent():
    return SEC_UA

skip_live = pytest.mark.skipif(
    SEC_UA is None,
    reason="Set SEC_UA='Your UA (contact@example.com)' to run live SEC integration tests.",
)
