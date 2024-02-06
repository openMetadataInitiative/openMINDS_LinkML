import json
import yaml
import os.path
from typing import List, Optional, Dict

from pipeline.utils import get_short_name


class LinkMLClassBuilder(object):
    def __init__(self, schema_file_path: str, root_path: str, slots: Dict):
        _relative_path_without_extension = (
            schema_file_path[len(root_path) + 1 :]
            .replace(".schema.omi.json", "")
            .split("/")
        )
        self.version = _relative_path_without_extension[0]
        self.relative_path_without_extension = _relative_path_without_extension[1:]
        with open(schema_file_path, "r") as schema_f:
            self._schema_payload = json.load(schema_f)
        self.slots = slots

    def _target_file_without_extension(self) -> str:
        return os.path.join(
            self.version, "/".join(self.relative_path_without_extension)
        )

    def _resolve_string_property(self, property) -> Dict:
        format_map = {  # see https://linkml.io/linkml-registry/
            "iri": "Uri",  # not ideal mapping, will do for now
            "date": "Date",
            "date-time": "Datetime",
            "time": "Time",
            "email": "Email",  # need to define this type
            "ECMA262": "ECMA262",  # need to define this type
        }

        string_property_spec = {"range": "string"}
        if "_formats" in property and property["_formats"]:
            if len(property["_formats"]) > 1:
                string_property_spec["any_of"] = [
                    {"range": format_map[p] for p in property["_formats"]}
                ]
            else:
                assert len(property["_formats"]) == 1
                string_property_spec["range"] = format_map[property["_formats"][0]]
        if "pattern" in property and property["pattern"]:
            string_property_spec["pattern"] = property["pattern"]
        # if "minLength" in property and property["minLength"]:
        #     string_property_spec["minLength"] = property["minLength"]
        # if "maxLength" in property and property["maxLength"]:
        #     string_property_spec["maxLength"] = property["maxLength"]
        return string_property_spec

    def _resolve_number_property(self, property) -> Dict:
        if property["type"] == "integer":
            number_property_spec = {"range": "int"}
        elif property["type"] == "float":
            number_property_spec = {"range": "float"}
        elif property["type"] == "number":  # or perhaps define a Number type
            number_property_spec = {"any_of": ["int", "float"]}
        else:
            raise ValueError(property["type"])
        # if "multipleOf" in property and property["multipleOf"]:
        #     number_property_spec["multipleOf"] = property["multipleOf"]
        if "minimum" in property and property["minimum"]:
            number_property_spec["minimum_value"] = property["minimum"]
        if "maximum" in property and property["maximum"]:
            number_property_spec["maximum_value"] = property["maximum"]
        return number_property_spec

    def _resolve_object_property(self, property):
        object_property_spec = {}
        if "_embeddedTypes" in property and property["_embeddedTypes"]:
            object_property_spec["inlined"] = True
            if len(property["_embeddedTypes"]) == 1:
                object_property_spec["range"] = get_short_name(
                    property["_embeddedTypes"][0]
                )
            elif len(property["_embeddedTypes"]) > 1:
                object_property_spec["any_of"] = [
                    {"range": get_short_name(_type)}
                    for _type in property["_embeddedTypes"]
                ]
        elif "_linkedTypes" in property and property["_linkedTypes"]:
            if len(property["_linkedTypes"]) == 1:
                object_property_spec["range"] = get_short_name(
                    property["_linkedTypes"][0]
                )
            elif len(property["_linkedTypes"]) > 1:
                object_property_spec["any_of"] = [
                    {"range": get_short_name(_type)}
                    for _type in property["_linkedTypes"]
                ]

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
                array_property_spec["range"] = get_short_name(
                    property.get("_linkedTypes", property.get("_embeddedTypes"))[0]
                )  # todo: handle multiple types
        # if "minItems" in property and property["minItems"]:
        #     array_property_spec["minItems"] = property["minItems"]
        # if "maxItems" in property and property["maxItems"]:
        #     array_property_spec["maxItems"] = property["maxItems"]
        if "uniqueItems" in property and property["uniqueItems"]:
            array_property_spec["list_elements_unique"] = property["uniqueItems"]

        return array_property_spec

    def _translate_property_specifications(
        self, property_uri, property, required=False
    ) -> Dict:
        _translated_prop_spec = {}
        if required:
            _translated_prop_spec["required"] = True

        prop_type = property["type"] if "type" in property else "object"

        property_handlers = {
            "string": self._resolve_string_property,
            "number": self._resolve_number_property,
            "float": self._resolve_number_property,
            "integer": self._resolve_number_property,
            "object": self._resolve_object_property,
            "array": self._resolve_array_property
        }

        if isinstance(prop_type, list):
            print("can't yet handle multiple property types")
        else:
            handle = property_handlers[prop_type]
            _translated_prop_spec.update(handle(property))

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
            "title": self._schema_payload["label"],  # labelPlural?
            "slots": ["id"],  # to fix: only if linked, not if embedded
            "slot_usage": {},
        }

        if "properties" in self._schema_payload and self._schema_payload["properties"]:
            for prop_name, prop_spec in self._schema_payload["properties"].items():
                slot_name = get_short_name(prop_name)
                self._translated_schema["slots"].append(slot_name)
                self._translated_schema["slot_usage"][slot_name] = (
                    self._translate_property_specifications(
                        prop_name, prop_spec, required=prop_name in required_properties
                    )
                )

    def build(self):
        target_file = os.path.join(
            "target", "schemas", f"{self._target_file_without_extension()}.yaml"
        )
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        short_type = get_short_name(self._schema_payload["_type"])
        self.translate()

        with open(target_file, "w") as fp:
            yaml.dump({short_type: self._translated_schema}, fp)


class LinkMLSlotBuilder:

    def __init__(self, property_uri, property, version):
        self.property_uri = property_uri
        self.property = property
        self.version = version

    def _resolve_string_property(self) -> Dict:
        property = self.property
        format_map = {  # see https://linkml.io/linkml-registry/
            "iri": "Uri",  # not ideal mapping, will do for now
            "date": "Date",
            "date-time": "Datetime",
            "time": "Time",
            "email": "Email",  # need to define this type
            "ECMA262": "ECMA262",  # need to define this type
        }

        string_property_spec = {"range": "string"}
        if "_formats" in property and property["_formats"]:
            if len(property["_formats"]) > 1:
                string_property_spec["any_of"] = [
                    {"range": format_map[p] for p in property["_formats"]}
                ]
            else:
                assert len(property["_formats"]) == 1
                string_property_spec["range"] = format_map[property["_formats"][0]]
        if "pattern" in property and property["pattern"]:
            string_property_spec["pattern"] = property["pattern"]
        # if "minLength" in property and property["minLength"]:
        #     string_property_spec["minLength"] = property["minLength"]
        # if "maxLength" in property and property["maxLength"]:
        #     string_property_spec["maxLength"] = property["maxLength"]
        return string_property_spec

    def _resolve_number_property(self) -> Dict:
        property = self.property
        if property["type"] == "integer":
            number_property_spec = {"range": "int"}
        elif property["type"] == "float":
            number_property_spec = {"range": "float"}
        elif property["type"] == "number":  # or perhaps define a Number type
            number_property_spec = {"any_of": ["int", "float"]}
        else:
            raise ValueError()
        # if "multipleOf" in property and property["multipleOf"]:
        #     number_property_spec["multipleOf"] = property["multipleOf"]
        if "minimum" in property and property["minimum"]:
            number_property_spec["minimum_value"] = property["minimum"]
        if "maximum" in property and property["maximum"]:
            number_property_spec["maximum_value"] = property["maximum"]
        return number_property_spec

    def _resolve_object_property(self):
        property = self.property
        object_property_spec = {}
        if "_embeddedTypes" in property and property["_embeddedTypes"]:
            object_property_spec["inlined"] = True
            if len(property["_embeddedTypes"]) == 1:
                object_property_spec["range"] = get_short_name(
                    property["_embeddedTypes"][0]
                )
            elif len(property["_embeddedTypes"]) > 1:
                object_property_spec["any_of"] = [
                    {"range": get_short_name(_type)}
                    for _type in property["_embeddedTypes"]
                ]
        elif "_linkedTypes" in property and property["_linkedTypes"]:
            if len(property["_linkedTypes"]) == 1:
                object_property_spec["range"] = get_short_name(
                    property["_linkedTypes"][0]
                )
            elif len(property["_linkedTypes"]) > 1:
                object_property_spec["any_of"] = [
                    {"range": get_short_name(_type)}
                    for _type in property["_linkedTypes"]
                ]

        return object_property_spec

    def _resolve_array_property(self):
        property = self.property
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
                array_property_spec["range"] = get_short_name(
                    property.get("_linkedTypes", property.get("_embeddedTypes"))[0]
                )  # todo: handle multiple types
        # if "minItems" in property and property["minItems"]:
        #     array_property_spec["minItems"] = property["minItems"]
        # if "maxItems" in property and property["maxItems"]:
        #     array_property_spec["maxItems"] = property["maxItems"]
        if "uniqueItems" in property and property["uniqueItems"]:
            array_property_spec["list_elements_unique"] = property["uniqueItems"]

        return array_property_spec

    def build(self):
        property = self.property
        slot = {"slot_uri": self.property_uri}
        if "description" in property:
            slot["description"] = property["description"]
        if "asEdge" in property:
            target_classes = property["asEdge"]["canPointTo"].get(self.version, [])
            if len(target_classes) == 1:
                slot["range"] = target_classes[0]
            elif len(target_classes) > 1:
                slot["any_of"] = [{"range": tc} for tc in target_classes]
        return slot
