from invoke import task
from os.path import join
from tasks.util.env import COCO_RELEASE_VERSION
from tasks.util.uk8s import (
    run_uk8s_kubectl_cmd,
    wait_for_pod,
)
from time import sleep

OPERATOR_GITHUB_URL = "github.com/confidential-containers/operator"
OPERATOR_NAMESPACE = "confidential-containers-system"


@task
def install(ctx):
    """
    Install the cc-operator on the cluster
    """
    # Before anything, make sure our k8s node has the worker label
    node_label = "node.kubernetes.io/worker="
    kube_cmd = """get nodes -o jsonpath='{.items..status..addresses
                  [?(@.type==\"Hostname\")].address}'"""
    node_name = run_uk8s_kubectl_cmd(kube_cmd, capture_output=True)
    run_uk8s_kubectl_cmd("label node {} {}".format(node_name, node_label))

    # Install the operator from the confidential-containers/operator
    # release tag
    operator_url = join(
        OPERATOR_GITHUB_URL, "config", "release?ref=v{}".format(COCO_RELEASE_VERSION)
    )
    run_uk8s_kubectl_cmd("apply -k {}".format(operator_url))
    wait_for_pod(OPERATOR_NAMESPACE, "cc-operator-controller-manager")


@task
def install_cc_runtime(ctx, runtime_class="kata-qemu"):
    """
    Install the CoCo runtime through the operator
    """
    cc_runtime_url = join(
        OPERATOR_GITHUB_URL,
        "config",
        "samples",
        "ccruntime",
        "default?ref=v{}".format(COCO_RELEASE_VERSION),
    )
    run_uk8s_kubectl_cmd("create -k {}".format(cc_runtime_url))

    for pod in ["cc-operator-daemon-install", "cc-operator-pre-install-daemon"]:
        wait_for_pod(OPERATOR_NAMESPACE, pod)

    # We check that the registered runtime classes are the same ones
    # we expect. We deliberately hardcode the following list
    expected_runtime_classes = [
        "kata",
        "kata-clh",
        "kata-clh-tdx",
        "kata-quemu",
        "kata-qemu-tdx",
        "kata-qemu-sev",
        "kata-qemu-snp",
    ]
    run_class_cmd = "get runtimeclass -o jsonpath='{.items..handler}'"
    runtime_classes = run_uk8s_kubectl_cmd(run_class_cmd, capture_output=True).split(
        " "
    )
    while len(expected_runtime_classes) != len(runtime_classes):
        print(
            "Not all expected runtime classes are registered ({} != {})".format(
                len(expected_runtime_classes), len(runtime_classes)
            )
        )
        sleep(5)
        runtime_classes = run_uk8s_kubectl_cmd(
            run_class_cmd, capture_output=True
        ).split(" ")


@task
def uninstall(ctx):
    """
    Uninstall the operator
    """
    operator_url = join(
        OPERATOR_GITHUB_URL, "config", "release?ref=v{}".format(COCO_RELEASE_VERSION)
    )
    run_uk8s_kubectl_cmd("delete -k {}".format(operator_url))


@task
def uninstall_cc_runtime(ctx):
    cc_runtime_url = join(
        OPERATOR_GITHUB_URL,
        "config",
        "samples",
        "ccruntime",
        "default?ref=v{}".format(COCO_RELEASE_VERSION),
    )
    run_uk8s_kubectl_cmd("delete -k {}".format(cc_runtime_url))
