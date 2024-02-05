import os.path
import shutil

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

    # Step 2 - find all involved schemas for the current version
    schemas_file_paths = schema_loader.find_schemas(schema_version)

    for schema_file_path in schemas_file_paths:
        # Step 3 - translate and build each openMINDS schema as JSON-Schema
        LinkMLBuilder(schema_file_path, schema_loader.schemas_sources).build()
