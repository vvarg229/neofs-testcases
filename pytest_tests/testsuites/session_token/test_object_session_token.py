import random

import allure
import pytest
from cluster_test_base import ClusterTestBase
from common import WALLET_PASS
from epoch import get_epoch
from file_helper import generate_file
from grpc_responses import EXPIRED_SESSION_TOKEN, SESSION_NOT_FOUND
from neofs_testlib.utils.wallet import get_last_address_from_wallet
from python_keywords.container import create_container
from python_keywords.neofs_verbs import delete_object, put_object, put_object_to_random_node

from steps.session_token import create_session_token


@pytest.mark.session_token
class TestDynamicObjectSession(ClusterTestBase):
    @allure.title("Test Object Operations with Session Token")
    @pytest.mark.parametrize(
        "object_size",
        [pytest.lazy_fixture("simple_object_size"), pytest.lazy_fixture("complex_object_size")],
        ids=["simple object", "complex object"],
    )
    def test_object_session_token(self, default_wallet, object_size):
        """
        Test how operations over objects are executed with a session token

        Steps:
        1. Create a private container
        2. Obj operation requests to the node which IS NOT in the container but granted
            with a session token
        3. Obj operation requests to the node which IS in the container and NOT granted
            with a session token
        4. Obj operation requests to the node which IS NOT in the container and NOT granted
            with a session token
        """

        with allure.step("Init wallet"):
            wallet = default_wallet
            address = get_last_address_from_wallet(wallet, "")

        with allure.step("Nodes Settlements"):
            (
                session_token_node,
                container_node,
                non_container_node,
            ) = random.sample(self.cluster.storage_nodes, 3)

        with allure.step("Create Session Token"):
            session_token = create_session_token(
                shell=self.shell,
                owner=address,
                wallet_path=wallet,
                wallet_password=WALLET_PASS,
                rpc_endpoint=session_token_node.get_rpc_endpoint(),
            )

        with allure.step("Create Private Container"):
            un_locode = container_node.get_un_locode()
            locode = "SPB" if un_locode == "RU LED" else un_locode.split()[1]
            placement_policy = (
                f"REP 1 IN LOC_{locode}_PLACE CBF 1 SELECT 1 FROM LOC_{locode} "
                f'AS LOC_{locode}_PLACE FILTER "UN-LOCODE" '
                f'EQ "{un_locode}" AS LOC_{locode}'
            )
            cid = create_container(
                wallet,
                shell=self.shell,
                endpoint=self.cluster.default_rpc_endpoint,
                rule=placement_policy,
            )

        with allure.step("Put Objects"):
            file_path = generate_file(object_size)
            oid = put_object_to_random_node(
                wallet=wallet,
                path=file_path,
                cid=cid,
                shell=self.shell,
                cluster=self.cluster,
            )
            oid_delete = put_object_to_random_node(
                wallet=wallet,
                path=file_path,
                cid=cid,
                shell=self.shell,
                cluster=self.cluster,
            )

        with allure.step("Node not in container but granted a session token"):
            put_object(
                wallet=wallet,
                path=file_path,
                cid=cid,
                shell=self.shell,
                endpoint=session_token_node.get_rpc_endpoint(),
                session=session_token,
            )
            delete_object(
                wallet=wallet,
                cid=cid,
                oid=oid_delete,
                shell=self.shell,
                endpoint=session_token_node.get_rpc_endpoint(),
                session=session_token,
            )

        with allure.step("Node in container and not granted a session token"):
            with pytest.raises(Exception, match=SESSION_NOT_FOUND):
                put_object(
                    wallet=wallet,
                    path=file_path,
                    cid=cid,
                    shell=self.shell,
                    endpoint=container_node.get_rpc_endpoint(),
                    session=session_token,
                )
            with pytest.raises(Exception, match=SESSION_NOT_FOUND):
                delete_object(
                    wallet=wallet,
                    cid=cid,
                    oid=oid,
                    shell=self.shell,
                    endpoint=container_node.get_rpc_endpoint(),
                    session=session_token,
                )

        with allure.step("Node not in container and not granted a session token"):
            with pytest.raises(Exception, match=SESSION_NOT_FOUND):
                put_object(
                    wallet=wallet,
                    path=file_path,
                    cid=cid,
                    shell=self.shell,
                    endpoint=non_container_node.get_rpc_endpoint(),
                    session=session_token,
                )
            with pytest.raises(Exception, match=SESSION_NOT_FOUND):
                delete_object(
                    wallet=wallet,
                    cid=cid,
                    oid=oid,
                    shell=self.shell,
                    endpoint=non_container_node.get_rpc_endpoint(),
                    session=session_token,
                )

    @allure.title("Verify session token expiration flags")
    @pytest.mark.parametrize("expiration_flag", ["lifetime", "expire_at"])
    def test_session_token_expiration_flags(
        self, default_wallet, simple_object_size, expiration_flag, cluster
    ):
        rpc_endpoint = self.cluster.storage_nodes[0].get_rpc_endpoint()

        with allure.step("Create Session Token with Lifetime param"):
            current_epoch = get_epoch(self.shell, cluster)

            session_token = create_session_token(
                shell=self.shell,
                owner=get_last_address_from_wallet(default_wallet, ""),
                wallet_path=default_wallet,
                wallet_password=WALLET_PASS,
                rpc_endpoint=rpc_endpoint,
                lifetime=1 if expiration_flag == "lifetime" else None,
                expire_at=current_epoch + 1 if expiration_flag == "expire_at" else None,
            )

        with allure.step("Create Private Container"):
            un_locode = self.cluster.storage_nodes[0].get_un_locode()
            locode = "SPB" if un_locode == "RU LED" else un_locode.split()[1]
            placement_policy = (
                f"REP 1 IN LOC_{locode}_PLACE CBF 1 SELECT 1 FROM LOC_{locode} "
                f'AS LOC_{locode}_PLACE FILTER "UN-LOCODE" '
                f'EQ "{un_locode}" AS LOC_{locode}'
            )
            cid = create_container(
                default_wallet,
                shell=self.shell,
                endpoint=self.cluster.default_rpc_endpoint,
                rule=placement_policy,
            )

        with allure.step("Verify object operations with created session token are allowed"):
            file_path = generate_file(simple_object_size)
            oid = put_object(
                wallet=default_wallet,
                path=file_path,
                cid=cid,
                shell=self.shell,
                endpoint=rpc_endpoint,
                session=session_token,
            )
            delete_object(
                wallet=default_wallet,
                cid=cid,
                oid=oid,
                shell=self.shell,
                endpoint=rpc_endpoint,
                session=session_token,
            )

        self.tick_epochs_and_wait(2)

        with allure.step("Verify object operations with created session token are not allowed"):
            file_path = generate_file(simple_object_size)
            with pytest.raises(RuntimeError, match=EXPIRED_SESSION_TOKEN):
                oid = put_object(
                    wallet=default_wallet,
                    path=file_path,
                    cid=cid,
                    shell=self.shell,
                    endpoint=rpc_endpoint,
                    session=session_token,
                )
