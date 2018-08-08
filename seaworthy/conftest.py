import os


def pytest_addoption(parser):
    parser.addoption(
        "--hub-image", action="store", default=os.environ.get(
            "HUB_IMAGE", "praekeltfoundation/ndoh-hub:develop"),
        help="NDOH Hub image to test"
    )


def pytest_report_header(config):
    return "NDOH Hub Docker image: {}".format(config.getoption("--hub-image"))
