import json
import yaml
import os.path
from typing import List, Optional, Dict


class LinkMLBuilder(object):
    def __init__(self, schema_file_path: str, root_path: str):
        _relative_path_without_extension = (
            schema_file_path[len(root_path) + 1 :]
            .replace(".schema.omi.json", "")
            .split("/")
        )
        self.version = _relative_path_without_extension[0]
        self.relative_path_without_extension = _relative_path_without_extension[1:]
        with open(schema_file_path, "r") as schema_f:
            self._schema_payload = json.load(schema_f)

    def _target_file_without_extension(self) -> str:
        return os.path.join(
            self.version, "/".join(self.relative_path_without_extension)
        )

    def _resolve_string_property(self, property) -> Dict:
        return {"range": "string"}
        string_property_spec = {}
        if "_formats" in property and property["_formats"]:
            if len(property["_formats"]) == 1:
                string_property_spec["format"] = property["_formats"][0]
                string_property_spec["type"] = property["type"]
            elif len(property["_formats"]) > 1:
                string_property_spec["anyOf"] = []
                for format in property["_formats"]:
                    string_property_spec["anyOf"].append(
                        {"type": property["type"], "format": format}
                    )
        else:
            string_property_spec["type"] = property["type"]
        if "pattern" in property and property["pattern"]:
            string_property_spec["pattern"] = property["pattern"]
        if "minLength" in property and property["minLength"]:
            string_property_spec["minLength"] = property["minLength"]
        if "maxLength" in property and property["maxLength"]:
            string_property_spec["maxLength"] = property["maxLength"]
        return string_property_spec

    def _resolve_number_property(self, property) -> Dict:
        return {}
        number_property_spec = {"type": property["type"]}
        if "multipleOf" in property and property["multipleOf"]:
            number_property_spec["multipleOf"] = property["multipleOf"]
        if "minimum" in property and property["minimum"]:
            number_property_spec["minimum"] = property["minimum"]
        if "maximum" in property and property["maximum"]:
            number_property_spec["maximum"] = property["maximum"]
        return number_property_spec

    def _resolve_object_property(self, property):
        return {}
        object_property_spec = {}
        if "_embeddedTypes" in property and property["_embeddedTypes"]:
            if len(property["_embeddedTypes"]) == 1:
                object_property_spec["type"] = "object"
                object_property_spec[
                    "$ref"
                ] = f"{property['_embeddedTypes'][0]}?format=json-schema"
            elif len(property["_embeddedTypes"]) > 1:
                object_property_spec["anyOf"] = []
                for embedded_type in property["_embeddedTypes"]:
                    object_property_spec["anyOf"].append(
                        {
                            "type": "object",
                            "$ref": f"{embedded_type}?format=json-schema",
                        }
                    )
        elif "_linkedTypes" in property and property["_linkedTypes"]:
            object_property_spec["type"] = "object"
            object_property_spec["if"] = {"required": ["@type"]}
            object_property_spec["then"] = {
                "properties": {
                    "@id": {"type": "string", "format": "iri"},
                    "@type": {
                        "type": "string",
                        "format": "iri",
                        "enum": property["_linkedTypes"],
                    },
                },
                "required": ["@id"],
            }
            object_property_spec["else"] = {
                "properties": {"@id": {"type": "string", "format": "iri"}},
                "required": ["@id"],
            }

        return object_property_spec

    def _resolve_array_property(self, property):
        array_property_spec = {"multivalued": True}
        if "items" in property and property["items"]:
            if "type" in property["items"] and property["items"]["type"]:
                if property["items"]["type"] == "string":
                    array_property_spec.update(
                        self._resolve_string_property(property["items"])
                    )
                elif property["items"]["type"] in ["number", "float", "integer"]:
                    array_property_spec.update(
                        self._resolve_number_property(property["items"])
                    )
                else:
                    raise NotImplementedError
        else:
            types = property.get("_linkedTypes", property.get("_embeddedTypes"))
            if len(property.get("_embeddedTypes", [])) > 0:
                array_property_spec["inlined"] = True
                # array_property_spec["inlined_as_list"] = True
            if len(types) > 0:
                array_property_spec["range"] = self._get_short_name(
                    property.get("_linkedTypes", property.get("_embeddedTypes"))[0]
                )  # todo: handle multiple types
        # if "minItems" in property and property["minItems"]:
        #     array_property_spec["minItems"] = property["minItems"]
        # if "maxItems" in property and property["maxItems"]:
        #     array_property_spec["maxItems"] = property["maxItems"]
        if "uniqueItems" in property and property["uniqueItems"]:
            array_property_spec["list_elements_unique"] = property["uniqueItems"]

        return array_property_spec

    def _translate_property_specifications(self, property_uri, property, required=False) -> Dict:
        _translated_prop_spec = {
            "slot_uri": property_uri
        }
        if required:
            _translated_prop_spec["required"] = True

        # prop_description = property["description"] if "description" in property else None
        # _translated_prop_spec["description"] = prop_description

        prop_type = property["type"] if "type" in property else "object"

        if "_linkedTypes" in property:
            property_classes = property.get(
                "_linkedTypes", property.get("_embeddedTypes")
            )

        if prop_type == "string":
            _translated_prop_spec.update(self._resolve_string_property(property))
        elif prop_type in ["number", "float", "integer"]:
            _translated_prop_spec.update(self._resolve_number_property(property))
        elif prop_type == "object":
            _translated_prop_spec.update(self._resolve_object_property(property))
        elif prop_type == "array":
            _translated_prop_spec.update(self._resolve_array_property(property))
        else:
            _translated_prop_spec["type"] = "UNKNOWN_TYPE"

        return _translated_prop_spec

    def _get_short_name(self, uri):
        return uri.split("/")[-1]

    def translate(self):
        # set required properties
        required_properties = (
            self._schema_payload["required"]
            if "required" in self._schema_payload
            else []
        )
        # set description
        description = (
            self._schema_payload["description"]
            if "description" in self._schema_payload
            else None
        )

        self._translated_schema = {
            "class_uri": f"{self._schema_payload['_type']}",  # ?format=linkml",
            "description": description,
            "attributes": {
                "id": {"identifier": True, "slot_uri": "schema:identifier", "required": True}
            }  # TODO: use slots instead
            # "required": sorted(required_prop)
        }

        if "properties" in self._schema_payload and self._schema_payload["properties"]:
            for prop_name, prop_spec in self._schema_payload["properties"].items():
                self._translated_schema["attributes"][
                    self._get_short_name(prop_name)
                ] = self._translate_property_specifications(
                    prop_name, prop_spec, required=prop_name in required_properties
                )

    def build(self):
        target_file = os.path.join(
            "target", "schemas", f"{self._target_file_without_extension()}.yaml"
        )
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        short_type = self._get_short_name(self._schema_payload["_type"])
        self.translate()

        with open(target_file, "w") as fp:
            yaml.dump({short_type: self._translated_schema}, fp)
