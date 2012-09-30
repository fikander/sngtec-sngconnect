from pyramid import events

@events.subscriber(events.BeforeRender)
def add_google_maps_api_key(event):
    event['google_maps_api_key'] = (
        event['request'].registry.settings['google_maps.api_key']
    )
