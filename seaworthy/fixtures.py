import pytest
from seaworthy.containers.postgresql import PostgreSQLContainer
from seaworthy.definitions import ContainerDefinition

HUB_IMAGE = pytest.config.getoption("--hub-image")


class HubContainer(ContainerDefinition):
    WAIT_PATTERNS = (r"Listening at: unix:/run/gunicorn/gunicorn.sock",)

    def __init__(self, name, db_url, image=HUB_IMAGE):
        super().__init__(name, image, self.WAIT_PATTERNS)
        self.db_url = db_url

    def base_kwargs(self):
        return {
            "ports": {"8000/tcp": None},
            "environment": {"HUB_DATABASE": self.db_url},
        }


postgresql_container = PostgreSQLContainer("postgresql")
f = postgresql_container.pytest_clean_fixtures("postgresql_container")
postgresql_fixture, clean_postgresql_fixture = f

hub_container = HubContainer("ndoh-hub", postgresql_container.database_url())
hub_fixture = hub_container.pytest_fixture(
    "hub_container", dependencies=["postgresql_container"]
)

__all__ = ["clean_postgresql_fixture", "hub_fixture", "postgresql_fixture"]
