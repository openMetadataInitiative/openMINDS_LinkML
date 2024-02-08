"""

"""

# note: this code is hard to understand, and needs refactoring

from collections import defaultdict
import os.path
import shutil
import json
import yaml

from pipeline.translator import LinkMLClassBuilder, LinkMLSlotBuilder, LinkMLEnumBuilder
from pipeline.utils import clone_sources, SchemaLoader, InstanceLoader, get_short_name


terms_as_enums = True

print("********************************************************")
print(f"Triggering the generation of LinkML models for openMINDS")
print("********************************************************")

# Step 1 - clone central repository in main branch to get the latest sources
clone_sources()
schema_loader = SchemaLoader()
instance_loader = InstanceLoader()

if os.path.exists("target"):
    shutil.rmtree("target")

# Step 2 - load instances
instances = {}
for version in instance_loader.get_instance_versions():
    instances[version] = defaultdict(list)
    for instance_path in instance_loader.find_instances(version):
        with open(instance_path) as fp:
            instance_data = json.load(fp)
        instances[version][instance_data["@type"]].append(instance_data)


for schema_version in schema_loader.get_schema_versions():
    imports = []

    # Step 3 - find all involved schemas for the current version
    schemas_file_paths = schema_loader.find_schemas(schema_version)

    # Step 4 - build slots
    properties = schema_loader.get_properties(schema_version)
    slots = {
        get_short_name(uri): LinkMLSlotBuilder(uri, property, schema_version).build()
        for uri, property in properties.items()
    }
    slots["id"] = {
        "identifier": True,
        "slot_uri": "schema:identifier",
        "required": True,
    }
    for schema_file_path in schemas_file_paths:
        LinkMLClassBuilder(
            schema_file_path, schema_loader.schemas_sources, slots
        ).update_slots()

    linkml_classes = defaultdict(list)
    linkml_enum_imports = []
    for schema_file_path in schemas_file_paths:
        # Step 5 - translate and build each openMINDS schema as a LinkML schema
        relative_path = os.path.relpath(
            schema_file_path, start=f"_sources/schemas/{schema_version}"
        )
        module = relative_path.split(os.path.sep)[0]
        instances_for_version = instances.get(schema_version, None)
        if (
            terms_as_enums
            and instances_for_version
            and "controlled" in schema_file_path
        ):
            LinkMLEnumBuilder(
                schema_file_path,
                schema_loader.schemas_sources,
                instances_for_version,
            ).build()
            linkml_enum_imports.append(
                os.path.join("enums", relative_path.replace(".schema.omi.json", ""))
            )
        else:
            linkml_class = LinkMLClassBuilder(
                schema_file_path, schema_loader.schemas_sources, slots
            ).build()
            linkml_classes[module].append(linkml_class)
    enum_schema = {
        "id": f"https://openminds.ebrains.eu/schemas/latest/enums?format=linkml",
        "name": "openMINDS-enums",
        "title": f'OpenMINDS instance library as LinkML enums, version "{schema_version}"',
        "description": f'Enums for the LinkML representation of openMINDS metadata framework, version "{schema_version}"',
        "license": "https://spdx.org/licenses/MIT.html",
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "schema": "http://schema.org/",
            "omi": "https://openminds.ebrains.eu",
        },
        "default_prefix": "omi",
        "imports": ["linkml:types"] + linkml_enum_imports,
    }
    target_file = os.path.join("target", "schemas", schema_version, f"enums.yaml")
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w") as fp:
        yaml.dump(enum_schema, fp, sort_keys=False)

    for module_name, class_list in linkml_classes.items():
        target_file = os.path.join(
            "target", "schemas", schema_version, f"{module_name}.yaml"
        )
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        module_schema = {
            "id": f"https://openminds.ebrains.eu/schemas/latest/{module_name}?format=linkml",
            "name": f"openMINDS-{module_name}",
            "title": f'OpenMINDS {module_name} module, version "{schema_version}"',
            "description": f'Schemas for the {module_name} module of the openMINDS metadata framework, version "{schema_version}"',
            "license": "https://spdx.org/licenses/MIT.html",
            "imports": ["linkml:types", "slots", "enums"],
            "prefixes": {
                "linkml": "https://w3id.org/linkml/",
                "schema": "http://schema.org/",
                "omi": "https://openminds.ebrains.eu",
            },
            "default_prefix": "omi",
            "classes": class_list,
        }
        imports.append(module_name)
        with open(target_file, "w") as fp:
            yaml.dump(module_schema, fp, sort_keys=False)

    # Step 6 - write slots file
    slots_schema = {
        "id": f"https://openminds.ebrains.eu/schemas/latest/slots?format=linkml",
        "name": "openMINDS-slots",
        "title": f'OpenMINDS properties as LinkML slots, version "{schema_version}"',
        "description": f'Slots for the LinkML representation of the openMINDS metadata framework, version "{schema_version}"',
        "license": "https://spdx.org/licenses/MIT.html",
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "schema": "http://schema.org/",
            "omi": "https://openminds.ebrains.eu",
        },
        "default_prefix": "omi",
        "imports": ["linkml:types"],
        "slots": slots
    }
    with open(
        os.path.join("target", "schemas", schema_version, f"slots.yaml"),
        "w",
    ) as fp:
        yaml.dump(slots_schema, fp, sort_keys=False)

    # Step 7 - create overall schema file
    schema_metadata = {
        "id": f"https://openminds.ebrains.eu/schemas/latest/?format=linkml",
        "name": "openMINDS",
        "title": f'OpenMINDS version "{schema_version}"',
        "description": f'The complete collection of schemas for all metadata models of the openMINDS metadata framework, version "{schema_version}"',
        "license": "https://spdx.org/licenses/MIT.html",
        "imports": ["linkml:types", "slots"] + imports,
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
        yaml.dump(schema_metadata, fp, sort_keys=False)
