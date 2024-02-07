import glob
import json
import os
import shutil
from typing import List

from git import Repo


def clone_sources():
    if os.path.exists("_sources"):
        shutil.rmtree("_sources")
    Repo.clone_from(
        "https://github.com/openMetadataInitiative/openMINDS.git",
        to_path="_sources",
        depth=1,
    )
    if os.path.exists("_instances"):
        shutil.rmtree("_instances")
    Repo.clone_from(
        "https://github.com/openMetadataInitiative/openMINDS_instances.git",
        to_path="_instances",
        depth=1,
    )


def get_short_name(uri):
    return uri.split("/")[-1]


class SchemaLoader(object):

    def __init__(self):
        self._root_directory = os.path.realpath(".")
        self.schemas_sources = os.path.join(self._root_directory, "_sources", "schemas")

    def get_schema_versions(self) -> List[str]:
        return os.listdir(self.schemas_sources)

    def find_schemas(self, version:str) -> List[str]:
        return glob.glob(os.path.join(self.schemas_sources, version, f'**/*.schema.omi.json'), recursive=True)

    def get_properties(self, version:str):
        path = os.path.join(self._root_directory, "_sources", "vocab", "properties.json")
        with open(path) as fp:
            all_properties = json.load(fp)
        return {name: p for name, p in all_properties.items() if version in p["usedIn"]}



class InstanceLoader:
    def __init__(self):
        self._root_directory = os.path.realpath(".")
        self.instances_sources = os.path.join(
            self._root_directory, "_instances", "instances"
        )

    def get_instance_versions(self) -> List[str]:
        return os.listdir(self.instances_sources)

    def find_instances(self, version: str) -> List[str]:
        return glob.glob(
            os.path.join(self.instances_sources, version, f"**/*.jsonld"),
            recursive=True,
        )
