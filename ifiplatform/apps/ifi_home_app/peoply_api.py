import requests

url = "https://api.peoply.app"

def get_events(union_id, after_date):
    events = []

    # use skip/offset and take for safety. Take caps at 500(though I doubt there will ever more than 500)
    offset = 0 # starts at 0 to get from
    # think of this as getting pages (max 500 event on each). If full page, means you have to chekc next page
    while True:
        response = requests.get(
            url + "/events",
            params={
                "organizationId": union_id,
                "afterDate": after_date.isoformat(), # safetycall to make sure right formatting
                "orderBy": "startDate",
                "orderDirection": "asc", # ascending
                "skip": offset,
                "take": 500,
            },
            timeout=10, # don't wait forever(ex. server down)
        )

        page = response.json()
        events += page
        take = len(page) # to check actual count
        if take < 500: # not a full page, means no more pages after
            break

        offset +=take # used to figure out next pagenr

    return events