from invoke import task
from subprocess import run
from tasks.demo_apps import push_to_local_registry as push_demo_apps_to_local_registry
from tasks.k8s import install as k8s_tooling_install
from tasks.k9s import install as k9s_install
from tasks.knative import install as knative_install
from tasks.kubeadm import create as k8s_create, destroy as k8s_destroy
from tasks.operator import (
    install as operator_install,
    install_cc_runtime as operator_install_cc_runtime,
)
from tasks.registry import (
    start as start_local_registry,
    stop as stop_local_registry,
)
from tasks.util.env import (
    COCO_ROOT,
    KATA_ROOT,
    KATA_IMAGE_TAG,
    KATA_VERSION,
    print_dotted_line,
)
from tasks.util.kata import replace_agent as replace_kata_agent


@task(default=True)
def deploy(ctx, debug=False, clean=False):
    """
    Deploy an SC2-enabled bare-metal Kubernetes cluster
    """
    if clean:
        for nuked_dir in [COCO_ROOT, KATA_ROOT]:
            if debug:
                print(f"WARNING: nuking {nuked_dir}")
            run(f"sudo rm -rf {nuked_dir}", shell=True, check=True)

    # Disable swap
    run("sudo swapoff -a", shell=True, check=True)

    # Install k8s tooling (including k9s)
    k8s_tooling_install(ctx, debug=debug, clean=clean)
    k9s_install(ctx, debug=debug)

    # Create a single-node k8s cluster
    k8s_create(ctx, debug=debug)

    # Install the CoCo operator as well as the CC-runtimes
    operator_install(ctx, debug=debug)
    operator_install_cc_runtime(ctx, debug=debug)

    # Start a local docker registry (must happen before the local registry,
    # as we rely on it to host our sidecar image)
    start_local_registry(ctx, debug=debug, clean=clean)

    # TODO: install sc2 runtime

    # Install Knative
    knative_install(ctx, debug=debug)

    # Apply general patches to the Kata Agent (and initrd), making sure we
    # have the latest patched version
    print_dotted_line(f"Pulling latest Kata image (v{KATA_VERSION})")
    result = run(f"docker pull {KATA_IMAGE_TAG}", shell=True, capture_output=True)
    assert result.returncode == 0, print(result.stderr.decode("utf-8").strip())
    if debug:
        print(result.stdout.decode("utf-8").strip())
    replace_kata_agent(debug=debug)
    print("Success!")

    # TODO: apply SC2 patches to things

    # Push demo apps to local registry for easy testing
    push_demo_apps_to_local_registry(ctx, debug=debug)


@task
def destroy(ctx, debug=False):
    """
    Destroy an SC2 cluster
    """
    # Destroy k8s cluster
    k8s_destroy(ctx, debug=debug)

    # Stop docker registry
    stop_local_registry(ctx, debug=debug)
