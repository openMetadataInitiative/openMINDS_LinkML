import os.path
import shutil

import yaml

from pipeline.translator import LinkMLBuilder
from pipeline.utils import clone_sources, SchemaLoader

print("********************************************************")
print(f"Triggering the generation of LinkML models for openMINDS")
print("********************************************************")

# Step 1 - clone central repository in main branch to get the latest sources
clone_sources()
schema_loader = SchemaLoader()
if os.path.exists("target"):
    shutil.rmtree("target")

for schema_version in schema_loader.get_schema_versions():
    imports = []

    # Step 2 - find all involved schemas for the current version
    schemas_file_paths = schema_loader.find_schemas(schema_version)

    for schema_file_path in schemas_file_paths:
        # Step 3 - translate and build each openMINDS schema as a LinkML schema
        LinkMLBuilder(schema_file_path, schema_loader.schemas_sources).build()
        imports.append(
            os.path.relpath(
                schema_file_path, start=f"sources/schemas/{schema_version}"
            ).replace(".schema.omi.json", "")
        )

    # Step 4 - create overall schema file
    schema_metadata = {
        "id": f"https://openminds.ebrains.eu/schemas/latest/?format=linkml",
        "name": f'OpenMINDS version "{schema_version}"',
        "description": f'The complete collection of schemas for all metadata models of the openMINDS metadata framework, version "{schema_version}"',
        "license": "https://spdx.org/licenses/MIT.html",
        "imports": ["linkml:types"] + imports,
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "schema": "http://schema.org/",
            "omi": "https://openminds.ebrains.eu",
        },
        "default_prefix": "omi",
    }
    with open(
        os.path.join(
            "target", "schemas", schema_version, f"openMINDS-{schema_version}.yml"
        ),
        "w",
    ) as fp:
        yaml.dump(schema_metadata, fp)
