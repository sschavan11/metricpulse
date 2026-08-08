import pytest

from metricpulse import db


@pytest.fixture(scope="session")
def mart_df():
    return db.load_mart()
