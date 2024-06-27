import json
import os
import unittest
from unittest import mock
import yaml

from azimuth_caas_operator.models.v1alpha1 import cluster as cluster_crd
from azimuth_caas_operator.models.v1alpha1 import cluster_type as cluster_type_crd
from azimuth_caas_operator.tests import async_utils
from azimuth_caas_operator.tests import base
from azimuth_caas_operator.utils import ansible_runner


class TestAnsibleRunner(base.TestCase):
    @mock.patch.dict(
        os.environ,
        {
            "ANSIBLE_RUNNER_IMAGE_TAG": "12345ab",
        },
        clear=True,
    )
    def test_get_job_remove(self):
        cluster = cluster_crd.get_fake()
        cluster_type = cluster_type_crd.get_fake()

        job = ansible_runner.get_job(cluster, cluster_type.spec, remove=True)

        expected = """\
apiVersion: batch/v1
kind: Job
metadata:
  generateName: test1-remove-
  labels:
    azimuth-caas-action: remove
    azimuth-caas-cluster: test1
  namespace: ns1
  ownerReferences:
  - apiVersion: caas.azimuth.stackhpc.com/v1alpha1
    kind: Cluster
    name: test1
    uid: fakeuid1
spec:
  activeDeadlineSeconds: 1200
  backoffLimit: 1
  template:
    spec:
      containers:
      - command:
        - /bin/bash
        - -c
        - "set -ex\\nexport ANSIBLE_CALLBACK_PLUGINS=\\"$(python3 -m ara.setup.callback_plugins)\\"\\
          \\nif [ -f /runner/project/requirements.yml ]; then\\n  ansible-galaxy install\\
          \\ -r /runner/project/requirements.yml\\nelif [ -f /runner/project/roles/requirements.yml\\
          \\ ]; then\\n  ansible-galaxy install -r /runner/project/roles/requirements.yml\\n\\
          fi\\nansible-runner run /runner -j\\nopenstack application credential delete\\
          \\ az-caas-test1 || true\\n"
        env:
        - name: RUNNER_PLAYBOOK
          value: sample.yaml
        - name: OS_CLOUD
          value: openstack
        - name: OS_CLIENT_CONFIG_FILE
          value: /var/lib/caas/cloudcreds/clouds.yaml
        - name: ANSIBLE_CONFIG
          value: /runner/project/ansible.cfg
        - name: ANSIBLE_HOME
          value: /var/lib/ansible
        image: ghcr.io/stackhpc/azimuth-caas-operator-ee:12345ab
        name: run
        volumeMounts:
        - mountPath: /runner/project
          name: runner-data
          subPath: project
        - mountPath: /runner/inventory
          name: runner-data
          subPath: inventory
        - mountPath: /runner/artifacts
          name: runner-data
          subPath: artifacts
        - mountPath: /var/lib/ansible
          name: ansible-home
        - mountPath: /runner/env
          name: env
          readOnly: true
        - mountPath: /var/lib/caas/cloudcreds
          name: cloudcreds
          readOnly: true
        - mountPath: /var/lib/caas/ssh
          name: deploy-key
          readOnly: true
        - mountPath: /home/runner/.ssh
          name: ssh
          readOnly: true
      initContainers:
      - command:
        - /bin/bash
        - -c
        - 'echo ''[openstack]'' >/runner/inventory/hosts

          echo ''localhost ansible_connection=local ansible_python_interpreter=/usr/bin/python3''
          >>/runner/inventory/hosts

          '
        image: ghcr.io/stackhpc/azimuth-caas-operator-ee:12345ab
        name: inventory
        volumeMounts:
        - mountPath: /runner/inventory
          name: runner-data
          subPath: inventory
        workingDir: /inventory
      - command:
        - /bin/bash
        - -c
        - 'set -ex

          git clone https://github.com/test.git /runner/project

          git config --global --add safe.directory /runner/project

          cd /runner/project

          git checkout 12345ab

          git submodule update --init --recursive

          ls -al /runner/project

          '
        image: ghcr.io/stackhpc/azimuth-caas-operator-ee:12345ab
        name: clone
        volumeMounts:
        - mountPath: /runner/project
          name: runner-data
          subPath: project
        workingDir: /runner
      restartPolicy: Never
      securityContext:
        fsGroup: 1000
        runAsGroup: 1000
        runAsUser: 1000
      ttlSecondsAfterFinished: 3600
      volumes:
      - emptyDir: {}
        name: runner-data
      - emptyDir: {}
        name: ansible-home
      - configMap:
          name: test1-remove
        name: env
      - name: cloudcreds
        secret:
          secretName: cloudsyaml
      - name: deploy-key
        secret:
          defaultMode: 256
          secretName: test1-deploy-key
      - name: ssh
        secret:
          defaultMode: 256
          optional: true
          secretName: ssh-type1
"""  # noqa
        self.assertEqual(expected, yaml.safe_dump(job))

    @mock.patch.dict(
        os.environ,
        {
            "ARA_API_SERVER": "fakearaurl",
        },
        clear=True,
    )
    def test_get_job_env_configmap(self):
        cluster = cluster_crd.get_fake()
        cluster_type = cluster_type_crd.get_fake()
        global_extravars = {
            "global_extravar1": "value1",
            "global_extravar2": "value2",
        }

        config = ansible_runner.get_env_configmap(
            cluster, cluster_type.spec, "fakekey", global_extravars
        )
        expected = """\
apiVersion: v1
data:
  envvars: 'ARA_API_CLIENT: http

    ARA_API_SERVER: fakearaurl

    '
  extravars: "cluster_deploy_ssh_public_key: fakekey\\ncluster_id: fakeclusterID1\\n\\
    cluster_image: testimage1\\ncluster_name: test1\\ncluster_ssh_private_key_file:\\
    \\ /var/lib/caas/ssh/id_ed25519\\ncluster_type: type1\\nfoo: bar\\nglobal_extravar1:\\
    \\ value1\\nglobal_extravar2: value2\\nnested:\\n  baz: bob\\nrandom_bool: true\\nrandom_dict:\\n\\
    \\  random_str: foo\\nrandom_int: 8\\nvery_random_int: 42\\n"
kind: ConfigMap
metadata:
  name: test1-create
  namespace: ns1
  ownerReferences:
  - apiVersion: caas.azimuth.stackhpc.com/v1alpha1
    kind: Cluster
    name: test1
    uid: fakeuid1
"""  # noqa
        self.assertEqual(expected, yaml.safe_dump(config))


class TestAsyncUtils(unittest.IsolatedAsyncioTestCase):
    @mock.patch.object(ansible_runner, "get_job_resource")
    async def test_get_jobs_for_cluster_create(self, mock_job_resource):
        fake_job_list = ["fakejob1", "fakejob2"]
        list_iter = async_utils.AsyncIterList(fake_job_list)
        mock_job_resource.return_value = list_iter

        jobs = await ansible_runner._get_jobs_for_cluster("client", "cluster1", "ns")

        self.assertEqual(fake_job_list, jobs)
        mock_job_resource.assert_awaited_once_with("client")
        self.assertEqual(
            dict(
                labels={
                    "azimuth-caas-action": "create",
                    "azimuth-caas-cluster": "cluster1",
                },
                namespace="ns",
            ),
            list_iter.kwargs,
        )

    @mock.patch.object(ansible_runner, "get_job_resource")
    async def test_get_jobs_for_cluster_remove(self, mock_job_resource):
        fake_job_list = ["fakejob1", "fakejob2"]
        list_iter = async_utils.AsyncIterList(fake_job_list)
        mock_job_resource.return_value = list_iter

        jobs = await ansible_runner._get_jobs_for_cluster(
            "client", "cluster1", "ns", remove=True
        )

        self.assertEqual(fake_job_list, jobs)
        mock_job_resource.assert_awaited_once_with("client")
        self.assertEqual(
            dict(
                labels={
                    "azimuth-caas-action": "remove",
                    "azimuth-caas-cluster": "cluster1",
                },
                namespace="ns",
            ),
            list_iter.kwargs,
        )

    @mock.patch(
        "azimuth_caas_operator.utils.k8s.get_pod_resource", new_callable=mock.AsyncMock
    )
    async def test_get_most_recent_pod_for_job(self, mock_pod):
        mock_iter = async_utils.AsyncIterList(
            [
                dict(
                    metadata=dict(name="pod1", creationTimestamp="2023-10-31T12:48:28Z")
                ),
                dict(
                    metadata=dict(name="pod2", creationTimestamp="2023-10-31T13:48:28Z")
                ),
            ]
        )
        mock_pod.return_value = mock_iter

        name = await ansible_runner._get_most_recent_pod_for_job(
            "client", "job1", "default"
        )

        self.assertEqual("pod2", name)
        self.assertEqual(
            {"labels": {"job-name": "job1"}, "namespace": "default"}, mock_iter.kwargs
        )

    @mock.patch(
        "azimuth_caas_operator.utils.k8s.get_pod_resource", new_callable=mock.AsyncMock
    )
    async def test_get_most_recent_pod_for_job_no_pods(self, mock_pod):
        mock_iter = async_utils.AsyncIterList([])
        mock_pod.return_value = mock_iter

        name = await ansible_runner._get_most_recent_pod_for_job(
            "client", "job1", "default"
        )

        self.assertIsNone(name)
        self.assertEqual(
            {"labels": {"job-name": "job1"}, "namespace": "default"}, mock_iter.kwargs
        )

    @mock.patch.object(ansible_runner, "LOG")
    @mock.patch.object(ansible_runner, "_get_pod_log_lines")
    @mock.patch.object(ansible_runner, "_get_most_recent_pod_for_job")
    async def test_get_ansible_runner_event_returns_event(
        self, mock_pod_names, mock_get_lines, mock_log
    ):
        mock_pod_names.return_value = "pod1"
        fake_event = dict(event="event_name", event_data=dict(task="stuff"))
        not_event = dict(data=dict(one="two"))
        mock_get_lines.return_value = [
            "foo",
            "bar",
            json.dumps(not_event),
            json.dumps(fake_event),
        ]

        event = await ansible_runner._get_ansible_runner_events("client", "job", "ns")

        self.assertEqual([fake_event], event)
        mock_pod_names.assert_awaited_once_with("client", "job", "ns")
        mock_get_lines.assert_awaited_once_with("client", "pod1", "ns")

    @mock.patch.object(ansible_runner, "LOG")
    @mock.patch.object(ansible_runner, "_get_pod_log_lines")
    @mock.patch.object(ansible_runner, "_get_most_recent_pod_for_job")
    async def test_get_ansible_runner_event_returns_no_event_on_bad_json(
        self, mock_pod_name, mock_get_lines, mock_log
    ):
        mock_pod_name.return_value = "pod1"
        mock_get_lines.return_value = ["foo", "bar"]

        event = await ansible_runner._get_ansible_runner_events("client", "job", "ns")

        self.assertEqual([], event)
        mock_pod_name.assert_awaited_once_with("client", "job", "ns")
        mock_get_lines.assert_awaited_once_with("client", "pod1", "ns")

    @mock.patch.object(ansible_runner, "LOG")
    @mock.patch.object(ansible_runner, "_get_pod_log_lines")
    @mock.patch.object(ansible_runner, "_get_most_recent_pod_for_job")
    async def test_get_ansible_runner_event_returns_no_event_on_no_pod(
        self, mock_pod_name, mock_get_lines, mock_log
    ):
        mock_pod_name.return_value = None

        event = await ansible_runner._get_ansible_runner_events("client", "job", "ns")

        self.assertEqual([], event)
        mock_pod_name.assert_awaited_once_with("client", "job", "ns")
        mock_get_lines.assert_not_awaited()

    @mock.patch.object(ansible_runner, "get_create_job_for_cluster")
    async def test_is_create_job_running_returns_true(self, mock_get_create_job):
        mock_job = mock.MagicMock()
        mock_job.status = {"active": 1}
        mock_get_create_job.return_value = mock_job

        result = await ansible_runner.is_create_job_running("client", "cluster", "ns")

        self.assertTrue(result)
        mock_get_create_job.assert_awaited_once_with("client", "cluster", "ns")

    @mock.patch.object(ansible_runner, "get_create_job_for_cluster")
    async def test_is_create_job_running_returns_false_no_job(
        self, mock_get_create_job
    ):
        mock_get_create_job.return_value = None

        result = await ansible_runner.is_create_job_running("client", "cluster", "ns")

        self.assertFalse(result)

    @mock.patch.object(ansible_runner, "get_create_job_for_cluster")
    async def test_is_create_job_running_returns_false_not_active(
        self, mock_get_create_job
    ):
        mock_job = mock.MagicMock()
        mock_job.status = {}
        mock_get_create_job.return_value = mock_job

        result = await ansible_runner.is_create_job_running("client", "cluster", "ns")

        self.assertFalse(result)
        mock_get_create_job.assert_awaited_once_with("client", "cluster", "ns")
