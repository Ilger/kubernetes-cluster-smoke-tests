import unittest
from kubernetes import client, config
from time import sleep

# Load the Kubernetes configuration
config.load_kube_config()

# Create the Kubernetes API client
api = client.CoreV1Api()


class SmokeTests(unittest.TestCase):

    # Test 1: Check the Kubernetes API server
    def test_api_server(self):
        nodes = api.list_node()
        for node in nodes.items:
            if node.status.conditions:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status != "True":
                        self.fail("Node {0} is not ready".format(
                            node.metadata.name))

    # Test 2: Verify that all the Kubernetes system components are running
    def test_kube_system_components(self):
        pods = api.list_namespaced_pod(namespace="kube-system")
        for pod in pods.items:
            if pod.status.phase != "Running":
                self.fail("Pod {0} is not running".format(pod.metadata.name))

    # Test 3: Test Kubernetes networking
    def test_kubernetes_networking(self):
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test-pod"},
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "busybox",
                        "command": ["sleep", "3600"],
                    }
                ]
            },
        }
        api.create_namespaced_pod(namespace="default", body=pod_manifest)

        sleep(5)

        test_pod = api.read_namespaced_pod(
            namespace="default", name="test-pod")
        if test_pod.status.phase != "Running":
            self.fail("Test pod is not running")

    # Test 4: Verify that Kubernetes services are running and accessible
    def test_kubernetes_services(self):
        services = api.list_service_for_all_namespaces()
        for service in services.items:
            if service.status.load_balancer.ingress:
                print("Service {0} is accessible at {1}".format(
                    service.metadata.name, service.status.load_balancer.ingress[0].ip))
            else:
                self.fail("Service {0} is not accessible".format(
                    service.metadata.name))

    # Test 5: Ensure that your application deployments are functioning as expected
    def test_application_deployments(self):
        deployments = api.list_namespaced_deployment(namespace="default")
        for deployment in deployments.items:
            replicas = deployment.spec.replicas
            deployment.spec.replicas = replicas + 1
            api.patch_namespaced_deployment(
                namespace="default", name=deployment.metadata.name, body=deployment)

            sleep(5)

            updated_deployment = api.read_namespaced_deployment(
                namespace="default", name=deployment.metadata.name)
            if updated_deployment.status.ready_replicas == replicas + 1:
                print("Deployment {0} was updated successfully".format(
                    deployment.metadata.name))
            else:
                self.fail("Deployment {0} update failed".format(
                    deployment.metadata.name))

    # Test 6: Test the cluster's resilience to node failures
    def test_node_resilience(self):
        nodes = api.list_node()
        for node in nodes.items:
            if node.metadata.labels["kubernetes.io/hostname"] == "NODE_TO_DELETE":
                api.delete_node(name=node.metadata.name,
                                body=client.V1DeleteOptions())

                sleep(30)

                updated_nodes = api.list_node()
                for updated_node in updated_nodes.items:
                    if updated_node.metadata.name == node.metadata.name:
                        self.fail("Node {0} deletion failed
