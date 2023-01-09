import json

from azimuth_caas_operator.models import registry
from azimuth_caas_operator.tests import base


class TestModels(base.TestCase):
    def test_cluster_type_crd_json(self):
        cluster_type_crd = None
        for resource in registry.get_crd_resources():
            meta = resource.get("metadata", {})
            name = meta.get("name")
            if name == "clustertypes.caas.azimuth.stackhpc.com":
                cluster_type_crd = resource

        actual = json.dumps(cluster_type_crd, indent=2)
        expected = """{
  "apiVersion": "apiextensions.k8s.io/v1",
  "kind": "CustomResourceDefinition",
  "metadata": {
    "name": "clustertypes.caas.azimuth.stackhpc.com"
  },
  "spec": {
    "group": "caas.azimuth.stackhpc.com",
    "scope": "Cluster",
    "names": {
      "kind": "ClusterType",
      "singular": "clustertype",
      "plural": "clustertypes",
      "shortNames": [],
      "categories": [
        "azimuth"
      ]
    },
    "versions": [
      {
        "name": "v1alpha1",
        "served": true,
        "storage": true,
        "schema": {
          "openAPIV3Schema": {
            "description": "Base class for defining custom resources.",
            "type": "object",
            "properties": {
              "spec": {
                "description": "Base model for use within CRD definitions.",
                "type": "object",
                "properties": {
                  "gitUrl": {
                    "type": "string"
                  }
                },
                "required": [
                  "gitUrl"
                ]
              },
              "status": {
                "description": "Base model for use within CRD definitions.",
                "type": "object",
                "properties": {
                  "phase": {
                    "description": "An enumeration.",
                    "enum": [
                      "Pending",
                      "Available",
                      "Failed"
                    ],
                    "type": "string"
                  }
                }
              }
            },
            "required": [
              "spec"
            ],
            "x-kubernetes-preserve-unknown-fields": true
          }
        },
        "subresources": {},
        "additionalPrinterColumns": [
          {
            "name": "Age",
            "type": "date",
            "jsonPath": ".metadata.creationTimestamp"
          }
        ]
      }
    ]
  }
}"""
        self.assertEqual(expected, actual)

    def test_cluster_crd_json(self):
        cluster_crd = None
        for resource in registry.get_crd_resources():
            meta = resource.get("metadata", {})
            name = meta.get("name")
            if name == "clusters.caas.azimuth.stackhpc.com":
                cluster_crd = resource

        actual = json.dumps(cluster_crd, indent=2)
        expected = """{
  "apiVersion": "apiextensions.k8s.io/v1",
  "kind": "CustomResourceDefinition",
  "metadata": {
    "name": "clusters.caas.azimuth.stackhpc.com"
  },
  "spec": {
    "group": "caas.azimuth.stackhpc.com",
    "scope": "Cluster",
    "names": {
      "kind": "Cluster",
      "singular": "cluster",
      "plural": "clusters",
      "shortNames": [],
      "categories": [
        "azimuth"
      ]
    },
    "versions": [
      {
        "name": "v1alpha1",
        "served": true,
        "storage": true,
        "schema": {
          "openAPIV3Schema": {
            "description": "Base class for defining custom resources.",
            "type": "object",
            "properties": {
              "spec": {
                "description": "Base model for use within CRD definitions.",
                "type": "object",
                "properties": {
                  "clusterTypeName": {
                    "type": "string"
                  }
                },
                "required": [
                  "clusterTypeName"
                ]
              },
              "status": {
                "description": "Base model for use within CRD definitions.",
                "type": "object",
                "properties": {
                  "phase": {
                    "description": "An enumeration.",
                    "enum": [
                      "Pending",
                      "Configuring",
                      "Ready",
                      "Failed",
                      "Deleting"
                    ],
                    "type": "string"
                  }
                }
              }
            },
            "required": [
              "spec"
            ],
            "x-kubernetes-preserve-unknown-fields": true
          }
        },
        "subresources": {},
        "additionalPrinterColumns": [
          {
            "name": "Age",
            "type": "date",
            "jsonPath": ".metadata.creationTimestamp"
          }
        ]
      }
    ]
  }
}"""
        self.assertEqual(expected, actual)