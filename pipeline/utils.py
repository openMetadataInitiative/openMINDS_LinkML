import glob
import json
import os
import shutil
from typing import List

from git import Repo, GitCommandError

def clone_sources():
    if os.path.exists("sources"):
        shutil.rmtree("sources")
    Repo.clone_from("https://github.com/openMetadataInitiative/openMINDS.git", to_path="sources", depth=1)


def get_short_name(uri):
    return uri.split("/")[-1]


class SchemaLoader(object):

    def __init__(self):
        self._root_directory = os.path.realpath(".")
        self.schemas_sources = os.path.join(self._root_directory, "sources", "schemas")

    def get_schema_versions(self) -> List[str]:
        return os.listdir(self.schemas_sources)

    def find_schemas(self, version:str) -> List[str]:
        return glob.glob(os.path.join(self.schemas_sources, version, f'**/*.schema.omi.json'), recursive=True)

    def get_properties(self, version:str):
        path = os.path.join(self._root_directory, "sources", "vocab", "properties.json")
        with open(path) as fp:
            all_properties = json.load(fp)
        return {name: p for name, p in all_properties.items() if version in p["usedIn"]}
