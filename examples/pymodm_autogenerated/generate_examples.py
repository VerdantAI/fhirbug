from collections import defaultdict
from pathlib import Path
from bson import ObjectId
import json
import sys

# Relative or absolute path to a directory that contains resource profile files
profile_folder = "tools/fhir_parser/downloads"


def generate(files=profile_folder):
    result = defaultdict(list)
    files = Path(files).glob("*-example*.json")
    for file in files:
        with open(file, "r") as f:
            # Parse json
            resource = json.loads(f.read())
            resourceType = resource['resourceType']
            result[resourceType].append(resource)
    return result

def find(examples, type, id):
    try:
        return next(filter(lambda e: e['id'] == id, examples[type]))
    except StopIteration:
        return None

references = {}
def replaceReference(ref):
    if ref not in references:
        try:
            resource, oldId = ref.split('/')
        except:
            print(ref)
            return ref
        id = ObjectId()
        references[ref] = resource + '/' + str(id)
    return references[ref]

def replaceAllReferences(examples):
    for ex_list in examples.values():
        for ex in ex_list:
            for val in ex.values():
                if type(val) is dict and 'reference' in val:
                    val['reference'] = replaceReference(val['reference'])

def replaceIds(examples):
    for cls, ex_list in examples.items():
        for ex in ex_list:
            try:
                id = ex['id']
                type = ex['resourceType']
                ref = type + '/' + id
                if ref in references:
                    ex['id'] = references[ref].split('/')[1]
            except:
                print(ex)


if __name__ == '__main__':
    examples = generate()
    replaceAllReferences(examples)
    replaceIds(examples)
    from fhirbug.config import settings, import_models
    settings.configure('examples.pymodm_autogenerated.settings')
    import pymodm
    pymodm.connect(settings.PYMODM_CONFIG["URI"])
    models = import_models()
    from fhirbug.Fhir import resources

    for ex_list in examples.items():
        pass