import os
import shutil
import uuid
from typing import Optional

import allure
import pytest
from common import (
    ASSETS_DIR,
    COMPLEX_OBJECT_CHUNKS_COUNT,
    COMPLEX_OBJECT_TAIL_SIZE,
    SIMPLE_OBJECT_SIZE,
    TEST_FILES_DIR,
    TEST_OBJECTS_DIR,
)
from neofs_testlib.env.env import NeoFSEnv, NodeWallet
from neofs_testlib.shell import Shell
from neofs_testlib.utils.wallet import init_wallet
from python_keywords.neofs_verbs import get_netmap_netinfo


def pytest_addoption(parser):
    parser.addoption(
        "--persist-env", action="store_true", default=False, help="persist deployed env"
    )
    parser.addoption("--load-env", action="store", help="load persisted env from file")


@pytest.fixture(scope="session")
def neofs_env(request):
    if request.config.getoption("--load-env"):
        neofs_env = NeoFSEnv.load(request.config.getoption("--load-env"))
    else:
        neofs_env = NeoFSEnv.simple()

    neofs_env.neofs_adm().morph.set_config(
        rpc_endpoint=f"http://{neofs_env.morph_rpc}",
        alphabet_wallets=neofs_env.alphabet_wallets_dir,
        post_data=f"ContainerFee=0 ContainerAliasFee=0",
    )

    yield neofs_env

    if request.config.getoption("--persist-env"):
        neofs_env.persist()
    else:
        if not request.config.getoption("--load-env"):
            neofs_env.kill()


@pytest.fixture(scope="session")
@allure.title("Prepare default wallet and deposit")
def default_wallet(temp_directory):
    return create_wallet()


@pytest.fixture(scope="session")
def client_shell(neofs_env: NeoFSEnv) -> Shell:
    yield neofs_env.shell


@allure.title("Prepare wallet and deposit")
def create_wallet(name: Optional[str] = None) -> NodeWallet:
    if name is None:
        wallet_name = f"{str(uuid.uuid4())}.json"
    else:
        wallet_name = f"{name}.json"

    wallet_path = os.path.join(os.getcwd(), ASSETS_DIR, wallet_name)
    wallet_password = "password"
    wallet_address = init_wallet(wallet_path, wallet_password)

    allure.attach.file(wallet_path, os.path.basename(wallet_path), allure.attachment_type.JSON)

    return NodeWallet(path=wallet_path, address=wallet_address, password=wallet_password)


@pytest.fixture(scope="session")
def max_object_size(neofs_env: NeoFSEnv, client_shell: Shell) -> int:
    storage_node = neofs_env.storage_nodes[0]
    net_info = get_netmap_netinfo(
        wallet=storage_node.wallet.path,
        wallet_config=storage_node.cli_config,
        endpoint=storage_node.endpoint,
        shell=client_shell,
    )
    yield net_info["maximum_object_size"]


@pytest.fixture(scope="session")
def simple_object_size(max_object_size: int) -> int:
    yield int(SIMPLE_OBJECT_SIZE) if int(SIMPLE_OBJECT_SIZE) < max_object_size else max_object_size


@pytest.fixture(scope="session")
def complex_object_size(max_object_size: int) -> int:
    return max_object_size * int(COMPLEX_OBJECT_CHUNKS_COUNT) + int(COMPLEX_OBJECT_TAIL_SIZE)


@pytest.fixture(scope="session")
@allure.title("Prepare tmp directory")
def temp_directory() -> str:
    with allure.step("Prepare tmp directory"):
        full_path = os.path.join(os.getcwd(), ASSETS_DIR)
        create_dir(full_path)

    yield full_path

    with allure.step("Remove tmp directory"):
        remove_dir(full_path)


@pytest.fixture(scope="module", autouse=True)
@allure.title(f"Prepare test files directories")
def artifacts_directory(temp_directory: str) -> None:
    dirs = [TEST_FILES_DIR, TEST_OBJECTS_DIR]
    for dir_name in dirs:
        with allure.step(f"Prepare {dir_name} directory"):
            full_path = os.path.join(temp_directory, dir_name)
            create_dir(full_path)

    yield

    for dir_name in dirs:
        with allure.step(f"Remove {dir_name} directory"):
            remove_dir(full_path)


def create_dir(dir_path: str) -> None:
    with allure.step("Create directory"):
        remove_dir(dir_path)
        os.mkdir(dir_path)


def remove_dir(dir_path: str) -> None:
    with allure.step("Remove directory"):
        shutil.rmtree(dir_path, ignore_errors=True)