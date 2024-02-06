# Mapping the openMINDS schema language to LinkML

## Schemas


| OMI                | LinkML              |
|:-------------------|:--------------------|
| _categories        |                     |
| type               | class_uri           |
| description        | description         |
| label              | title               |
| name               | <schema name (key)> |
| properties         | attributes or slots |
| required           | slot/required       |
| semanticEquivalent |                     |


## Properties

### General

| OMI                | LinkML       |
|:-------------------|:-------------|
| <key>              | slot_uri     |
| type               | range        |
| name               | ?annotations |
| namePlural         | ?annotations |
| description        | description  |
| label              | ?annotations |
| labelPlural        | ?title       |
| nameForReverseLink | inverse      |
| _instruction       | ?comments    |


### Strings

| OMI          | LinkML                               |
|:-------------|:-------------------------------------|
| _formats*    | structured_pattern or TypeDefinition |
| formatting** | ?comments                            |
| pattern      | pattern                              |
| minLength    | ?pattern                             |
| maxLength    |  ?pattern                            |
| multiline    | ?pattern                             |

* iri, date, date-time, time, email, ECMA262
** content type (text/plain or text/markdown)

### Numbers

| OMI        | LinkML        |
|:-----------|:--------------|
| multipleOf | X             |
| minimum    | minimum_value |
| maximum    | maximum_value |

### Objects

| OMI            | LinkML                          |
|:---------------|:--------------------------------|
| _embeddedTypes | inlined, range, inlined_as_list |
| _linkedTypes   | range                           |

### Arrays

| OMI            | LinkML               |
|:---------------|:---------------------|
| (type="array") | multivalued          |
| items          |                      |
| items/type     | range                |
| items/pattern  | pattern              |
| minItems       | X                    |
| maxItems       | X                    |
| uniqueItems    | list_elements_unique |

