import weaviate
from weaviate.util import generate_uuid5

# client =weaviate.Client("http://host.docker.internal:8999")
# client = weaviate.Client("http://127.0.0.1:8999")

def get_schema(name):
    class_obj = {
        # Class definition
        "class": name,

        # Property definitions
        "properties": [

            {
                "name": "content",
                "dataType": ["text"],
            }
        ],
    }
    return class_obj


def storeData(name, contents):
    client = weaviate.Client("http://localhost:8999")
    if not client.schema.exists(name):
        print("creating the " + str(name) + " schema")
        new_schema = get_schema(name)
        client.schema.create_class(new_schema)

    print(client.schema.get(name))
    with client.batch(
            batch_size=2,  # Specify batch size
            num_workers=2,  # Parallelize the process
    ) as batch:
            for content in contents:
                data_object = {
                    "content": content
                }
                batch.add_data_object(
                    data_object,
                    class_name=name,
                    uuid=generate_uuid5(data_object)
                )



def fetch_top_k_content(name, k_size=2, additional_props=[]):
    res = (client.query.get(name, ["content"])
           .with_additional(additional_props)
           .with_limit(k_size)
           .do())

    return res['data']['Get'][name]

def fetch_top_k_nearest_content(name, content, k_size=2, additional_props=[]):
    res = (client.query.get(name, ["content"])
        .with_additional(additional_props) #["id", "distance"]
        .with_near_text({"concepts": content})
        .with_limit(k_size)
        .do())

    return res['data']['Get'][name]



# opening_statement_example = [
#     "Excellent, well, I haven?t spoken to you about this before, but I want to show you some exciting information about Gaboderm ointment for your moderate to severe eczema patients.
#     These are patients who are having frequent flares, so the chances are that you?ll be seeing them in the practice on a regular basis. It would be great if you could identify one of these patients to use
#     Gaboderm in and see how it reduces their flares for yourself.",
#     "Thank you, Doctor, for your time. This call is about the lipid management of your CHD patients.",
#     "So, it's about your CHD risk patients who, despite maximum statin and Acetamib therapy, do not reach their LDL targets. Is that alright with you?",
# ]
# storeData("OPENING_STATEMENT_EXAMPLE", opening_statement_example)

# print(fetch_top_k_content("OPENING_STATEMENT_EXAMPLE", 3, []))
# print(fetch_top_k_nearest_content("OPENING_STATEMENT_EXAMPLE",  "are you alright", 2,['distance']))
